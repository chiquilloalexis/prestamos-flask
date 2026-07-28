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
        y = hoy.year + ((hoy.month - i - 1) // 12)
        meses.append((y, m))
    labels = [f"{m:02d}/{y}" for (y, m) in meses]
    counts = []
    for (y, m) in meses:
        inicio, fin = _rango_mes(y, m)
        inicio_dt = datetime.combine(inicio, datetime.min.time())
        fin_dt = datetime.combine(fin, datetime.max.time())
        c = Cliente.query.filter(
            Cliente.created_at >= inicio_dt, Cliente.created_at <= fin_dt
        ).count()
        counts.append(c)
    return labels, counts


# ==================== CLIENTES ====================
@admin_bp.route("/clientes")
@login_required
def clientes_list():
    q = request.args.get("q", "").strip()
    query = Cliente.query

    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Cliente.nombres.ilike(like),
                Cliente.apellidos.ilike(like),
                Cliente.cedula.ilike(like),
                Cliente.telefono.ilike(like),
            )
        )

    clientes = query.order_by(Cliente.created_at.desc()).all()
    return render_template("clientes_list.html", clientes=clientes, q=q)


@admin_bp.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
def cliente_nuevo():
    if request.method == "POST":
        cedula = request.form.get("cedula", "").strip()

        if Cliente.query.filter_by(cedula=cedula).first():
            flash("Ya existe un cliente con esa cédula.", "danger")
            return render_template("cliente_form.html", cliente=None, form=request.form)

        cliente = Cliente(
            cedula=cedula,
            nombres=request.form.get("nombres", "").strip(),
            apellidos=request.form.get("apellidos", "").strip(),
            direccion=request.form.get("direccion", "").strip(),
            telefono=request.form.get("telefono", "").strip(),
            barrio=request.form.get("barrio", "").strip(),
        )
        db.session.add(cliente)
        db.session.flush()  # para obtener cliente.id antes del commit

        valor_inicial = _to_decimal(request.form.get("valor_inicial"))
        porcentaje = _to_decimal(request.form.get("porcentaje_interes"))
        cuotas = int(request.form.get("cantidad_cuotas") or 1)

        total_pagar = valor_inicial + (valor_inicial * porcentaje / Decimal("100"))
        valor_cuota = (total_pagar / cuotas) if cuotas > 0 else total_pagar

        prestamo = Prestamo(
            cliente_id=cliente.id,
            fecha_prestamo=request.form.get("fecha_prestamo") or date.today(),
            valor_inicial=valor_inicial,
            porcentaje_interes=porcentaje,
            total_pagar=total_pagar,
            cantidad_cuotas=cuotas,
            valor_cuota=valor_cuota.quantize(Decimal("1")),
            observaciones=request.form.get("observaciones", "").strip(),
            estado=Prestamo.ESTADO_ACTIVO,
        )
        db.session.add(prestamo)
        db.session.commit()

        flash(f"Cliente {cliente.nombre_completo} creado correctamente.", "success")
        return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))

    return render_template("cliente_form.html", cliente=None, form=None)


@admin_bp.route("/clientes/<int:cliente_id>")
@login_required
def cliente_detalle(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    prestamo = cliente.prestamos[-1] if cliente.prestamos else None
    return render_template("cliente_detail.html", cliente=cliente, prestamo=prestamo)


@admin_bp.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def cliente_editar(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)

    if request.method == "POST":
        nueva_cedula = request.form.get("cedula", "").strip()
        existente = Cliente.query.filter(
            Cliente.cedula == nueva_cedula, Cliente.id != cliente.id
        ).first()
        if existente:
            flash("Ya existe otro cliente con esa cédula.", "danger")
            return render_template("cliente_form.html", cliente=cliente, form=request.form)

        cliente.cedula = nueva_cedula
        cliente.nombres = request.form.get("nombres", "").strip()
        cliente.apellidos = request.form.get("apellidos", "").strip()
        cliente.direccion = request.form.get("direccion", "").strip()
        cliente.telefono = request.form.get("telefono", "").strip()
        cliente.barrio = request.form.get("barrio", "").strip()
        db.session.commit()

        flash("Datos del cliente actualizados.", "success")
        return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))

    return render_template("cliente_form.html", cliente=cliente, form=None)


@admin_bp.route("/clientes/<int:cliente_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def cliente_eliminar(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    nombre = cliente.nombre_completo
    db.session.delete(cliente)  # cascade borra préstamos y pagos asociados
    db.session.commit()
    flash(f"Cliente {nombre} eliminado.", "info")
    return redirect(url_for("admin.clientes_list"))


# ==================== PRÉSTAMOS ====================
@admin_bp.route("/prestamos/nuevo/<int:cliente_id>", methods=["POST"])
@login_required
@admin_required
def prestamo_nuevo(cliente_id):
    """Permite abrir un préstamo adicional para un cliente existente
    (por ejemplo, tras saldar el anterior)."""
    cliente = Cliente.query.get_or_404(cliente_id)

    valor_inicial = _to_decimal(request.form.get("valor_inicial"))
    porcentaje = _to_decimal(request.form.get("porcentaje_interes"))
    cuotas = int(request.form.get("cantidad_cuotas") or 1)
    total_pagar = valor_inicial + (valor_inicial * porcentaje / Decimal("100"))
    valor_cuota = (total_pagar / cuotas) if cuotas > 0 else total_pagar

    prestamo = Prestamo(
        cliente_id=cliente.id,
        fecha_prestamo=request.form.get("fecha_prestamo") or date.today(),
        valor_inicial=valor_inicial,
        porcentaje_interes=porcentaje,
        total_pagar=total_pagar,
        cantidad_cuotas=cuotas,
        valor_cuota=valor_cuota.quantize(Decimal("1")),
        observaciones=request.form.get("observaciones", "").strip(),
        estado=Prestamo.ESTADO_ACTIVO,
    )
    db.session.add(prestamo)
    db.session.commit()
    flash("Nuevo préstamo registrado.", "success")
    return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))


# ==================== PAGOS ====================
@admin_bp.route("/prestamos/<int:prestamo_id>/pago", methods=["POST"])
@login_required
def registrar_pago(prestamo_id):
    prestamo = Prestamo.query.get_or_404(prestamo_id)

    valor = _to_decimal(request.form.get("valor_pagado"))
    fecha = request.form.get("fecha") or date.today()
    observacion = request.form.get("observacion", "").strip()

    if valor <= 0:
        flash("El valor del pago debe ser mayor a cero.", "danger")
        return redirect(url_for("admin.cliente_detalle", cliente_id=prestamo.cliente_id))

    # Guardamos el pago con el saldo restante ya calculado (incluyendo este pago)
    saldo_previo = prestamo.saldo_pendiente
    saldo_nuevo = saldo_previo - valor
    if saldo_nuevo < 0:
        saldo_nuevo = Decimal("0")

    pago = Pago(
        prestamo_id=prestamo.id,
        fecha=fecha,
        valor_pagado=valor,
        saldo_restante=saldo_nuevo,
        observacion=observacion,
    )
    db.session.add(pago)
    db.session.flush()

    # Todo se actualiza automáticamente: el saldo se recalcula sobre la marcha
    # (es una propiedad derivada) y acá solo dejamos el estado consistente.
    prestamo.actualizar_estado()
    db.session.commit()

    flash(f"Pago de ${valor:,.0f} registrado.", "success")
    return redirect(url_for("admin.cliente_detalle", cliente_id=prestamo.cliente_id))


@admin_bp.route("/pagos/<int:pago_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def pago_eliminar(pago_id):
    pago = Pago.query.get_or_404(pago_id)
    prestamo = pago.prestamo
    cliente_id = prestamo.cliente_id
    db.session.delete(pago)
    db.session.flush()
    prestamo.actualizar_estado()
    db.session.commit()
    flash("Pago eliminado y saldo recalculado.", "info")
    return redirect(url_for("admin.cliente_detalle", cliente_id=cliente_id))
