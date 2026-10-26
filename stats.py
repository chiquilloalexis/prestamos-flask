"""Consultas agregadas (sumas, conteos) hechas directamente en la base de
datos. Así el panel y los reportes siguen siendo rápidos aunque haya miles de
créditos y pagos, en vez de cargar todo en memoria y recorrerlo en Python.

Ganancia de un pago = pago x (1 - capital / total_a_pagar): cada peso cobrado
se reparte entre capital y ganancia en la misma proporción del crédito.
"""
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Numeric, case, func, literal_column, select

from app import db
from app.models import Cliente, Gasto, Pago, Prestamo

CERO = Decimal("0")


def _dec(valor):
    if valor is None:
        return CERO
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def _total_sin_cero():
    return func.nullif(Prestamo.total_pagar, 0, type_=Numeric(12, 2))


def _parte_capital():
    """capital / total. Se multiplica por 1.0 porque SQLite divide enteros
    como enteros (1000000 / 1300000 = 0) y la ganancia saldría mal."""
    return (Prestamo.valor_inicial * literal_column("1.0")) / _total_sin_cero()


def _ganancia_pago():
    return Pago.valor_pagado * (1 - _parte_capital())


def cobrado_por_prestamo():
    """Subconsulta: cuánto se ha cobrado de cada crédito."""
    return (
        select(
            Pago.prestamo_id.label("prestamo_id"),
            func.sum(Pago.valor_pagado).label("cobrado"),
        )
        .group_by(Pago.prestamo_id)
        .subquery()
    )


def ids_clientes_con_deuda():
    """Subconsulta con los clientes que tienen un crédito sin terminar de pagar."""
    sub = cobrado_por_prestamo()
    saldo = Prestamo.total_pagar - func.coalesce(sub.c.cobrado, 0)
    return (
        select(Prestamo.cliente_id)
        .outerjoin(sub, sub.c.prestamo_id == Prestamo.id)
        .where(saldo >= 1)
    )


def _agregados_cartera(cliente_id=None):
    sub = cobrado_por_prestamo()
    cobrado = func.coalesce(sub.c.cobrado, 0)
    saldo = Prestamo.total_pagar - cobrado
    capital_pendiente = Prestamo.valor_inicial - cobrado * _parte_capital()
    debe = saldo >= 1  # mismo criterio que Prestamo.saldo_pendiente

    stmt = (
        select(
            func.coalesce(func.sum(case((debe, 1), else_=0)), 0),
            func.coalesce(func.sum(case((debe, 0), else_=1)), 0),
            func.coalesce(func.sum(case((debe, saldo), else_=0)), 0),
            func.coalesce(func.sum(case((debe, capital_pendiente), else_=0)), 0),
        )
        .select_from(Prestamo)
        .outerjoin(sub, sub.c.prestamo_id == Prestamo.id)
    )
    if cliente_id:
        stmt = stmt.where(Prestamo.cliente_id == cliente_id)
    activos, pagados, pendiente, capital = db.session.execute(stmt).one()
    return {
        "creditos_activos": int(activos or 0),
        "creditos_pagados": int(pagados or 0),
        "pendiente_cobrar": _dec(pendiente),             # capital + interés por cobrar
        "capital_pendiente": max(_dec(capital), CERO),   # SOLO capital, sin interés
    }


def resumen_cartera():
    """Estado actual de toda la cartera (no depende de fechas)."""
    r = _agregados_cartera()
    r["clientes"] = (
        db.session.query(func.count(Cliente.id)).filter(Cliente.archivado.is_(False)).scalar() or 0
    )
    return r


def resumen_cartera_cliente(cliente_id):
    return _agregados_cartera(cliente_id)


def totales_cobros(inicio, fin, cliente_id=None):
    """(total cobrado, ganancia, cantidad de pagos) entre dos fechas."""
    stmt = (
        select(
            func.coalesce(func.sum(Pago.valor_pagado), 0),
            func.coalesce(func.sum(_ganancia_pago()), 0),
            func.count(Pago.id),
        )
        .select_from(Pago)
        .join(Prestamo, Pago.prestamo_id == Prestamo.id)
        .where(Pago.fecha >= inicio, Pago.fecha <= fin)
    )
    if cliente_id:
        stmt = stmt.where(Prestamo.cliente_id == cliente_id)
    cobrado, ganancia, cantidad = db.session.execute(stmt).one()
    return _dec(cobrado), _dec(ganancia), int(cantidad or 0)


def capital_prestado(inicio, fin, cliente_id=None):
    """Capital entregado en créditos otorgados entre dos fechas."""
    stmt = select(func.coalesce(func.sum(Prestamo.valor_inicial), 0)).where(
        Prestamo.fecha_prestamo >= inicio, Prestamo.fecha_prestamo <= fin
    )
    if cliente_id:
        stmt = stmt.where(Prestamo.cliente_id == cliente_id)
    return _dec(db.session.execute(stmt).scalar())


def total_gastos(inicio, fin):
    stmt = select(func.coalesce(func.sum(Gasto.monto), 0)).where(
        Gasto.fecha >= inicio, Gasto.fecha <= fin
    )
    return _dec(db.session.execute(stmt).scalar())


def cobros_por_dia(inicio, fin, cliente_id=None):
    """[(fecha, cobrado, ganancia)] agrupado por día, ordenado."""
    stmt = (
        select(Pago.fecha, func.sum(Pago.valor_pagado), func.sum(_ganancia_pago()))
        .select_from(Pago)
        .join(Prestamo, Pago.prestamo_id == Prestamo.id)
        .where(Pago.fecha >= inicio, Pago.fecha <= fin)
        .group_by(Pago.fecha)
        .order_by(Pago.fecha)
    )
    if cliente_id:
        stmt = stmt.where(Prestamo.cliente_id == cliente_id)
    filas = []
    for f, c, g in db.session.execute(stmt).all():
        # SQLite a veces devuelve la fecha agrupada como texto.
        if isinstance(f, str):
            f = date.fromisoformat(f[:10])
        filas.append((f, _dec(c), _dec(g)))
    return filas


def detalle_cobros(inicio, fin, cliente_id=None, limite=None):
    stmt = (
        select(
            Pago.fecha, Pago.valor_pagado, _ganancia_pago().label("ganancia"),
            Cliente.id, Cliente.nombres, Cliente.apellidos, Cliente.cedula,
        )
        .select_from(Pago)
        .join(Prestamo, Pago.prestamo_id == Prestamo.id)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Pago.fecha >= inicio, Pago.fecha <= fin)
        .order_by(Pago.fecha.desc(), Pago.id.desc())
    )
    if cliente_id:
        stmt = stmt.where(Prestamo.cliente_id == cliente_id)
    if limite:
        stmt = stmt.limit(limite)
    return [
        {"fecha": r[0], "valor": _dec(r[1]), "ganancia": _dec(r[2]),
         "cliente_id": r[3], "cliente": f"{r[4]} {r[5]}", "cedula": r[6]}
        for r in db.session.execute(stmt).all()
    ]


def detalle_prestamos(inicio, fin, cliente_id=None, limite=None):
    stmt = (
        select(
            Prestamo.fecha_prestamo, Prestamo.valor_inicial, Prestamo.porcentaje_interes,
            Prestamo.total_pagar, Prestamo.cantidad_cuotas,
            Cliente.id, Cliente.nombres, Cliente.apellidos, Cliente.cedula,
        )
        .select_from(Prestamo)
        .join(Cliente, Prestamo.cliente_id == Cliente.id)
        .where(Prestamo.fecha_prestamo >= inicio, Prestamo.fecha_prestamo <= fin)
        .order_by(Prestamo.fecha_prestamo.desc(), Prestamo.id.desc())
    )
    if cliente_id:
        stmt = stmt.where(Prestamo.cliente_id == cliente_id)
    if limite:
        stmt = stmt.limit(limite)
    return [
        {"fecha": r[0], "capital": _dec(r[1]), "interes": _dec(r[2]), "total": _dec(r[3]),
         "cuotas": r[4], "cliente_id": r[5], "cliente": f"{r[6]} {r[7]}", "cedula": r[8]}
        for r in db.session.execute(stmt).all()
    ]


def gastos_por_categoria(inicio, fin):
    stmt = (
        select(Gasto.categoria, func.sum(Gasto.monto))
        .where(Gasto.fecha >= inicio, Gasto.fecha <= fin)
        .group_by(Gasto.categoria)
        .order_by(func.sum(Gasto.monto).desc())
    )
    return [(c, _dec(m)) for c, m in db.session.execute(stmt).all()]


# ------------------------------------------------------------ series (gráficos)
def ultimos_meses(n, hoy):
    """[(año, mes)] de los últimos n meses, el más antiguo primero."""
    meses = []
    y, m = hoy.year, hoy.month
    for _ in range(n):
        meses.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(meses))


def serie_mensual(n, hoy):
    """Cobrado y ganancia por mes, y clientes nuevos por mes (últimos n)."""
    meses = ultimos_meses(n, hoy)
    inicio = date(meses[0][0], meses[0][1], 1)
    fin = date(meses[-1][0], meses[-1][1], monthrange(*meses[-1])[1])

    cobrado = defaultdict(lambda: CERO)
    ganancia = defaultdict(lambda: CERO)
    for fecha, c, g in cobros_por_dia(inicio, fin):
        cobrado[(fecha.year, fecha.month)] += c
        ganancia[(fecha.year, fecha.month)] += g

    nuevos = defaultdict(int)
    desde_dt = datetime.combine(inicio, datetime.min.time())
    for (creado,) in db.session.execute(select(Cliente.created_at).where(Cliente.created_at >= desde_dt)).all():
        if creado:
            nuevos[(creado.year, creado.month)] += 1

    return {
        "meses": meses,
        "cobrado": [float(cobrado[m]) for m in meses],
        "ganancia": [float(ganancia[m]) for m in meses],
        "clientes_nuevos": [nuevos[m] for m in meses],
    }


def anios_disponibles(hoy):
    """Años con datos (para los selectores), del más reciente al más antiguo."""
    candidatos = []
    for col in (Pago.fecha, Prestamo.fecha_prestamo, Gasto.fecha):
        minimo = db.session.execute(select(func.min(col))).scalar()
        if isinstance(minimo, str):
            minimo = date.fromisoformat(minimo[:10])
        if minimo is not None and hasattr(minimo, "year"):
            candidatos.append(minimo.year)
    primero = min(candidatos) if candidatos else hoy.year
    primero = max(2000, min(primero, hoy.year))
    return list(range(hoy.year, primero - 1, -1))
