from datetime import date, timedelta, datetime
from calendar import monthrange
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.models import Cliente, Prestamo, Pago, Gasto
from app.auth_utils import admin_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _to_decimal(value, default="0"):
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError):
        return Decimal(default)


# ==================== DASHBOARD ====================
@admin_bp.route("/")
@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    clientes_total = Cliente.query.count()
    prestamos = Prestamo.query.all()

    activos = sum(1 for p in prestamos if not p.esta_saldado)
    finalizados = sum(1 for p in prestamos if p.esta_saldado)
    dinero_prestado = sum((p.valor_inicial for p in prestamos), Decimal("0"))
    dinero_recuperado = sum((p.total_cobrado for p in prestamos), Decimal("0"))
    dinero_pendiente = sum((p.saldo_pendiente for p in prestamos), Decimal("0"))

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    pagos_hoy = Pago.query.filter(Pago.fecha == hoy).all()
    pagos_mes = Pago.query.filter(Pago.fecha >= inicio_mes, Pago.fecha <= hoy).all()

    cobros_hoy = sum((p.valor_pagado for p in pagos_hoy), Decimal("0"))
    cobros_mes = sum((p.valor_pagado for p in pagos_mes), Decimal("0"))

    ganancia_mes = Decimal("0")
    for pago in pagos_mes:
        ratio = pago.prestamo.ratio_capital
        ganancia_mes += pago.valor_pagado - (pago.valor_pagado * ratio)

    # Gastos administrativos del mes (combustible, pago a trabajador, etc.)
    # y ganancia neta resultante. Al no guardar ningún acumulado -- todo se
    # calcula filtrando por fecha -- el corte de mes es automático: apenas
    # cambia el mes calendario, estos valores vuelven a arrancar en cero
    # sin que haya que hacer nada.
    gastos_mes = Gasto.query.filter(Gasto.fecha >= inicio_mes, Gasto.fecha <= hoy).all()
    total_gastos_mes = sum((g.monto for g in gastos_mes), Decimal("0"))
    ganancia_neta_mes = ganancia_mes - total_gastos_mes

    # Series para gráficos: últimos 6 meses
    meses_labels, cobros_por_mes, ganancia_por_mes = _serie_ultimos_meses(6)
    _, clientes_por_mes = _serie_clientes_nuevos(6)

    return render_template(
        "dashboard.html",
        clientes_total=clientes_total,
        activos=activos,
        finalizados=finalizados,
        dinero_prestado=dinero_prestado,
        dinero_recuperado=dinero_recuperado,
        dinero_pendiente=dinero_pendiente,
        cobros_hoy=cobros_hoy,
        cobros_mes=cobros_mes,
        ganancia_mes=ganancia_mes,
        total_gastos_mes=total_gastos_mes,
        ganancia_neta_mes=ganancia_neta_mes,
        meses_labels=meses_labels,
        cobros_por_mes=cobros_por_mes,
        ganancia_por_mes=ganancia_por_mes,
        clientes_por_mes=clientes_por_mes,
    )


def _rango_mes(y, m):
    """Primer y último día calendario del mes (y, m), como objetos date."""
    inicio = date(y, m, 1)
    fin = date(y, m, monthrange(y, m)[1])
    return inicio, fin


def _serie_ultimos_meses(n):
    hoy = date.today()
    meses = []
    for i in range(n - 1, -1, -1):
        m = (hoy.month - i - 1) % 12 + 1
        y = hoy.year + ((hoy.month - i - 1) // 12)
        meses.append((y, m))

    labels = [f"{m:02d}/{y}" for (y, m) in meses]
    cobros, ganancia = [], []

    for (y, m) in meses:
        inicio, fin = _rango_mes(y, m)
        # Filtramos por rango de fechas (no con YEAR()/MONTH()) para que
        # funcione igual en MySQL y en SQLite -- SQLite no tiene esas
        # funciones y el dashboard se rompía con un error 500 al usarlas.
        pagos = Pago.query.filter(Pago.fecha >= inicio, Pago.fecha <= fin).all()
        total_cobrado = sum((p.valor_pagado for p in pagos), Decimal("0"))
        total_ganancia = Decimal("0")
        for p in pagos:
            ratio = p.prestamo.ratio_capital
            total_ganancia += p.valor_pagado - (p.valor_pagado * ratio)
        cobros.append(float(total_cobrado))
        ganancia.append(float(total_ganancia))

    return labels, cobros, ganancia


def _serie_clientes_nuevos(n):
    hoy = date.today()
    meses = []
    for i in range(n - 1, -1, -1):
        m = (hoy.month - i - 1) % 12 + 1
        y = hoy.year + ((hoy.month - i - 1) //
