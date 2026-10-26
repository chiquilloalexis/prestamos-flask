from decimal import ROUND_CEILING, Decimal

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app import db, stats
from app.auth_utils import admin_required
from app.models import Cliente, Pago, Prestamo
from app.security import auditar, generar_pin, hash_pin
from app.utils import (
    FECHA_MINIMA, MESES_CORTOS, MONTO_MAXIMO, cop, fecha_corta, hoy_local,
    limpiar_telefono, limpiar_texto, normalizar_cedula, parse_decimal,
    parse_entero, parse_fecha, redondear_centavos, redondear_pesos,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

CERO = Decimal("0")
POR_PAGINA = 20
ESTADOS = ("todos", "deuda", "disponibles", "archivados")


# ==================== PANEL ====================
@admin_bp.route("/")
@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    hoy = hoy_local()
    inicio_mes = hoy.replace(day=1)

    cartera = stats.resumen_cartera()
    cobros_hoy, _, pagos_hoy = stats.totales_cobros(hoy, hoy)
    cobros_mes, ganancia_mes, pagos_mes = stats.totales_cobros(inicio_mes, hoy)
    gastos_mes = stats.total_gastos(inicio_mes, hoy)
    serie = stats.serie_mensual(6, hoy)

    etiquetas = [f"{MESES_CORTOS[m - 1]} {str(y)[2:]}" for y, m in serie["meses"]]
    grafico_cobros = {
        "tipo": "linea",
        "etiquetas": etiquetas,
        "series": [
            {"nombre": "Cobrado", "valores": serie["cobrado"], "color": "brand"},
            {"nombre": "Ganancia", "valores": serie["ganancia"], "color": "gold"},
        ],
        "dinero": True,
    }
    grafico_clientes = {
        "tipo": "barras",
        "etiquetas": etiquetas,
        "series": [{"nombre": "Clientes nuevos", "valores": serie["clientes_nuevos"], "color": "brand"}],
        "dinero": False,
    }

    return render_template(
        "dashboard.html",
        cartera=cartera,
        cobros_hoy=cobros_hoy,
        pagos_hoy=pagos_hoy,
        cobros_mes=cobros_mes,
        pagos_mes=pagos_mes,
        ganancia_mes=ganancia_mes,
        gastos_mes=gastos_mes,
        ganancia_neta_mes=ganancia_mes - gastos_mes,
        grafico_cobros=grafico_cobros,
        grafico_clientes=grafico_clientes,
    )


# ==================== AYUDAS ====================
def _escapar_like(texto):
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _condiciones_busqueda(q):
    """Cada palabra debe aparecer en nombre, apellido, cédula, teléfono o barrio
    (así 'yoelvis yacub' encuentra al cliente aunque estén en columnas distintas)."""
    condiciones = []
    for palabra in q.split()[:5]:
        like = f"%{_escapar_like(palabra)}%"
        condiciones.append(
            or_(
                Cliente.nombres.ilike(like, escape="\\"),
                Cliente.apellidos.ilike(like, escape="\\"),
                Cliente.cedula.ilike(like, escape="\\"),
                Cliente.telefono.ilike(like, escape="\\"),
                Cliente.barrio.ilike(like, escape="\\"),
            )
        )
    return condiciones


def _leer_cliente(form):
    errores = []
    cedula = normalizar_cedula(form.get("cedula"))
    if not cedula:
        errores.append("Escribe una cédula válida (entre 5 y 20 números o letras, sin símbolos).")
    nombres = limpiar_texto(form.get("nombres"), 100)
    apellidos = limpiar_texto(form.get("apellidos"), 100)
    if not nombres or not apellidos:
        errores.append("Los nombres y los apellidos son obligatorios.")
    datos = {
        "cedula": cedula,
        "nombres": nombres,
        "apellidos": apellidos,
        "telefono": limpiar_telefono(form.get("telefono")),
        "barrio": limpiar_texto(form.get("barrio"), 100),
        "direccion": limpiar_texto(form.get("direccion"), 200),
    }
    return datos, errores


def _leer_prestamo(form):
    """Valida los datos de un crédito. Devuelve (datos, error)."""
    hoy = hoy_local()
    valor = parse_decimal(form.get("valor_inicial"))
    interes = parse_decimal(form.get("porcentaje_interes") or "0", miles_=False)
    cuotas = parse_entero(form.get("cantidad_cuotas"), 1, 1000)
    texto_fecha = (form.get("fecha_prestamo") or "").strip()
    fecha = parse_fecha(texto_fecha) if texto_fecha else hoy

    if valor is None or valor < 1 or valor > MONTO_MAXIMO:
        return None, "Escribe un valor prestado válido, mayor a cero."
    if interes is None or interes < 0 or interes > 500:
        return None, "El porcentaje de interés debe estar entre 0 y 500."
    if cuotas is None:
        return None, "La cantidad de cuotas debe ser un número entre 1 y 1000."
    if fecha is None or fecha < FECHA_MINIMA:
        return None, "La fecha del crédito no es válida."
    if fecha > hoy:
        return None, "La fecha del crédito no puede ser futura."

    # Pesos enteros: así el saldo siempre puede llegar exactamente a cero.
    valor = redondear_pesos(valor)
    total = redondear_pesos(valor + valor * interes / Decimal("100"))
    cuota = redondear_pesos(total / cuotas)
    if cuota <= 0 or total > MONTO_MAXIMO:
        return None, "Los valores del crédito no son válidos."
    return {
        "fecha_prestamo": fecha,
        "valor_inicial": valor,
        "porcentaje_interes": redondear_centavos(interes),
        "total_pagar": total,
        "cantidad_cuotas": cuotas,
        "valor_cuota": cuota,
        "observaciones": limpiar_texto(form.get("observaciones"), 500) or None,
    }, None


def _nuevo_prestamo(cliente, datos):
    prestamo = Prestamo(cliente=cliente, estado=Prestamo.ESTADO_ACTIVO, **datos)
    db.session.add(prestamo)
    return prestamo


def _valores_formulario(cliente, form):
    """Valores para rellenar los formularios (y conservar lo escrito si hay error)."""
    base = {
        "cedula": "", "nombres": "", "apellidos": "", "telefono": "", "barrio": "", "direccion": "",
        "fecha_prestamo": "", "valor_inicial": "", "porcentaje_interes": "30",
        "cantidad_cuotas": "20", "observaciones": "",
    }
    if cliente is not None:
        for k in ("cedula", "nombres", "apellidos", "telefono", "barrio", "direccion"):
            base[k] = getattr(cliente, k) or ""
    if form is not None:
        for k in base:
            if k in form:
                base[k] = form.get(k, "")
    return base


def _flash_errores(errores):
    for e in errores:
        flash(e, "danger")


def _avisar_pin(cliente, pin):
    # Se muestra una sola vez: en la base solo queda su "hash".
    flash(f"{cliente.nombre_completo}||{pin}", "pin")


# ==================== CLIENTES ====================
@admin_bp.route("/clientes")
@login_required
def clientes_list():
    q = request.args.get("q", "").strip()[:80]
    estado = request.args.get("estado", "todos")
    if estado not in ESTADOS:
        estado = "todos"
    pagina = request.args.get("pagina", 1, type=int)

    query = Cliente.query.options(selectinload(Cliente.prestamos).selectinload(Prestamo.pagos))
    if estado == "archivados":
        query = query.filter(Cliente.archivado.is_(True))
    else:
        query = query.filter(Cliente.archivado.is_(False))
        if estado == "deuda":
            query = query.filter(Cliente.id.in_(stats.ids_clientes_con_deuda()))
        elif estado == "disponibles":
            query = query.filter(Cliente.id.not_in(stats.ids_clientes_con_deuda()))
    for condicion in _condiciones_busqueda(q):
        query = query.filter(condicion)

    paginacion = query.order_by(Cliente.created_at.desc(), Cliente.id.desc()).paginate(
        page=pagina, per_page=POR_PAGINA, error_out=False
    )
    return render_template("clientes_list.html", paginacion=paginacion, q=q, estado=estado)


@admin_bp.route("/clientes/nuevo", methods=["GET", "POST"])
@login_required
def cliente_nuevo():
    if request.method == "POST":
        datos, errores = _leer_cliente(request.form)

        # El crédito es opcional: se puede crear solo el cliente.
        quiere_credito = bool((request.form.get("valor_inicial") or "").strip())
        datos_prestamo = None
        if quiere_credito:
            datos_prestamo, error_prestamo = _leer_prestamo(request.form)
            if error_prestamo:
                errores.append(error_prestamo)

        if not errores and Cliente.query.filter_by(cedula=datos["cedula"]).first():
            errores.append("Ya existe un cliente con esa cédula. Búscalo en la lista de clientes.")

        if errores:
            _flash_errores(errores)
            return render_template("cliente_form.html", cliente=None, valores=_valores_formulario(None, request.form))

        pin = generar_pin()
        cliente = Cliente(**datos, portal_pin_hash=hash_pin(pin))
        db.session.add(cliente)
        if datos_prestamo:
            _nuevo_prestamo(cliente, datos_prestamo)
        auditar(
            "cliente_creado",
            f"{cliente.nombre_completo} (C.C. {cliente.cedula})"
            + (f" con crédito de {cop(datos_prestamo['valor_inicial'])}" if datos_prestamo else ""),
        )
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Ya existe un cliente con esa cédula.", "danger")
            return render_template("cliente_form.html", cliente=None, valores=_valores_formulario(None, request.form))

        flash(f"Cliente {cliente.nombre_completo} creado correctamente.", "success")
        _avisar_pin(cliente, pin)
        return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))

    return render_template("cliente_form.html", cliente=None, valores=_valores_formulario(None, None))


@admin_bp.route("/clientes/<int:cliente_id>")
@login_required
def cliente_detalle(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    activo = cliente.prestamo_activo
    # Los demás créditos, del más reciente al más antiguo (cada uno con su fecha).
    historial = [p for p in reversed(cliente.prestamos) if p is not activo]
    return render_template(
        "cliente_detail.html",
        cliente=cliente,
        activo=activo,
        historial=historial,
        valores=_valores_formulario(None, None),
    )


@admin_bp.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def cliente_editar(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)

    if request.method == "POST":
        datos, errores = _leer_cliente(request.form)
        if not errores:
            otro = Cliente.query.filter(Cliente.cedula == datos["cedula"], Cliente.id != cliente.id).first()
            if otro:
                errores.append("Ya existe otro cliente con esa cédula.")
        if errores:
            _flash_errores(errores)
            return render_template("cliente_form.html", cliente=cliente, valores=_valores_formulario(cliente, request.form))

        for campo, valor in datos.items():
            setattr(cliente, campo, valor)
        auditar("cliente_editado", f"{cliente.nombre_completo} (C.C. {cliente.cedula})")
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Ya existe otro cliente con esa cédula.", "danger")
            return redirect(url_for("admin.cliente_editar", cliente_id=cliente.id))
        flash("Datos del cliente actualizados.", "success")
        return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))

    return render_template("cliente_form.html", cliente=cliente, valores=_valores_formulario(cliente, None))


@admin_bp.route("/clientes/<int:cliente_id>/pin", methods=["POST"])
@login_required
def cliente_pin(cliente_id):
    """Genera un PIN nuevo para el portal (reemplaza al anterior)."""
    cliente = db.get_or_404(Cliente, cliente_id)
    pin = generar_pin()
    cliente.portal_pin_hash = hash_pin(pin)
    auditar("pin_generado", f"{cliente.nombre_completo} (C.C. {cliente.cedula})")
    db.session.commit()
    _avisar_pin(cliente, pin)
    return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))


@admin_bp.route("/clientes/<int:cliente_id>/archivar", methods=["POST"])
@login_required
@admin_required
def cliente_archivar(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    if cliente.prestamo_activo:
        flash("No se puede archivar a un cliente que todavía debe. Primero debe terminar de pagar.", "danger")
        return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))
    cliente.archivado = True
    auditar("cliente_archivado", f"{cliente.nombre_completo} (C.C. {cliente.cedula})")
    db.session.commit()
    flash(f"{cliente.nombre_completo} fue archivado. Su historial se conserva y puedes restaurarlo cuando quieras.", "info")
    return redirect(url_for("admin.clientes_list"))


@admin_bp.route("/clientes/<int:cliente_id>/restaurar", methods=["POST"])
@login_required
@admin_required
def cliente_restaurar(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    cliente.archivado = False
    auditar("cliente_restaurado", f"{cliente.nombre_completo} (C.C. {cliente.cedula})")
    db.session.commit()
    flash(f"{cliente.nombre_completo} fue restaurado.", "success")
    return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))


@admin_bp.route("/clientes/<int:cliente_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def cliente_eliminar(cliente_id):
    cliente = db.get_or_404(Cliente, cliente_id)
    if cliente.prestamos:
        flash(
            "Este cliente tiene créditos en su historial, por eso no se puede eliminar "
            "(se perdería el registro del dinero). Puedes archivarlo para ocultarlo.",
            "danger",
        )
        return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))
    nombre = cliente.nombre_completo
    auditar("cliente_eliminado", f"{nombre} (C.C. {cliente.cedula})")
    db.session.delete(cliente)
    db.session.commit()
    flash(f"Cliente {nombre} eliminado.", "info")
    return redirect(url_for("admin.clientes_list"))


# ==================== CRÉDITOS ====================
@admin_bp.route("/prestamos/nuevo/<int:cliente_id>", methods=["POST"])
@login_required
def prestamo_nuevo(cliente_id):
    """Nuevo crédito para un cliente que ya existe. Solo se habilita cuando
    ya pagó todo lo que debía; si debe algo, se rechaza."""
    cliente = Cliente.query.filter_by(id=cliente_id).with_for_update().first_or_404()
    volver = redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))

    if cliente.archivado:
        flash("Este cliente está archivado. Restáuralo para hacerle un crédito.", "danger")
        return volver
    activo = cliente.prestamo_activo
    if activo:
        flash(
            f"No se puede crear un crédito nuevo: {cliente.nombres} todavía debe "
            f"{cop(activo.saldo_pendiente)}. Podrás hacerlo cuando termine de pagar.",
            "danger",
        )
        return volver

    datos, error = _leer_prestamo(request.form)
    if error:
        flash(error, "danger")
        return volver

    prestamo = _nuevo_prestamo(cliente, datos)
    auditar(
        "credito_creado",
        f"{cliente.nombre_completo}: {cop(datos['valor_inicial'])} al {datos['porcentaje_interes']}% "
        f"en {datos['cantidad_cuotas']} cuotas (fecha {fecha_corta(datos['fecha_prestamo'])})",
    )
    db.session.commit()
    flash(f"Nuevo crédito de {cop(prestamo.valor_inicial)} registrado con fecha {fecha_corta(prestamo.fecha_prestamo)}.", "success")
    return volver


# ==================== PAGOS ====================
@admin_bp.route("/prestamos/<int:prestamo_id>/pago", methods=["POST"])
@login_required
def registrar_pago(prestamo_id):
    prestamo = Prestamo.query.filter_by(id=prestamo_id).with_for_update().first_or_404()
    cliente = prestamo.cliente
    volver = redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))
    hoy = hoy_local()

    valor = parse_decimal(request.form.get("valor_pagado"))
    texto_fecha = (request.form.get("fecha") or "").strip()
    fecha = parse_fecha(texto_fecha) if texto_fecha else hoy

    if valor is None or valor < 1 or valor > MONTO_MAXIMO:
        flash("Escribe un valor de cobro válido, mayor a cero.", "danger")
        return volver
    valor = redondear_pesos(valor)

    if fecha is None:
        flash("La fecha del cobro no es válida.", "danger")
        return volver
    if fecha > hoy:
        flash("La fecha del cobro no puede ser futura.", "danger")
        return volver
    if fecha < prestamo.fecha_prestamo:
        flash(f"El cobro no puede ser anterior a la fecha del crédito ({fecha_corta(prestamo.fecha_prestamo)}).", "danger")
        return volver

    saldo = prestamo.saldo_pendiente
    if saldo <= 0:
        flash("Este crédito ya está pagado por completo.", "warning")
        return volver
    # Se acepta hasta el saldo redondeado hacia arriba (por créditos antiguos con centavos).
    if valor > saldo.to_integral_value(rounding=ROUND_CEILING):
        flash(f"El cobro ({cop(valor)}) es mayor que el saldo pendiente ({cop(saldo)}). Ajusta el valor.", "danger")
        return volver

    pago = Pago(
        prestamo=prestamo,
        fecha=fecha,
        valor_pagado=valor,
        saldo_restante=CERO,
        observacion=limpiar_texto(request.form.get("observacion"), 255) or None,
    )
    db.session.add(pago)
    db.session.flush()
    prestamo.recalcular_saldos()
    prestamo.actualizar_estado()
    auditar(
        "pago_registrado",
        f"{cliente.nombre_completo}: {cop(valor)} del {fecha_corta(fecha)} (crédito del {fecha_corta(prestamo.fecha_prestamo)})",
    )
    db.session.commit()

    if prestamo.esta_saldado:
        flash(f"Cobro de {cop(valor)} registrado. {cliente.nombres} terminó de pagar: ya puedes hacerle un crédito nuevo.", "success")
    else:
        flash(f"Cobro de {cop(valor)} registrado. Saldo pendiente: {cop(prestamo.saldo_pendiente)}.", "success")
    return volver


@admin_bp.route("/pagos/<int:pago_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def pago_eliminar(pago_id):
    pago = db.get_or_404(Pago, pago_id)
    prestamo = pago.prestamo
    cliente = prestamo.cliente
    detalle = f"{cliente.nombre_completo}: {cop(pago.valor_pagado)} del {fecha_corta(pago.fecha)}"

    db.session.delete(pago)
    db.session.flush()
    db.session.expire(prestamo, ["pagos"])
    prestamo.recalcular_saldos()
    prestamo.actualizar_estado()
    auditar("pago_eliminado", detalle)
    db.session.commit()
    flash("Cobro eliminado y saldos recalculados.", "info")
    return redirect(url_for("admin.cliente_detalle", cliente_id=cliente.id))
