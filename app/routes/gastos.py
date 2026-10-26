from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app import db, stats
from app.auth_utils import admin_required
from app.models import Gasto
from app.periodos import resolver_periodo
from app.security import auditar
from app.utils import (
    FECHA_MINIMA, MESES, MONTO_MAXIMO, cop, fecha_corta, hoy_local, limpiar_texto,
    parse_decimal, parse_fecha, redondear_centavos,
)

gastos_bp = Blueprint("gastos", __name__, url_prefix="/admin/gastos")

TIPOS_PERIODO = ("mes", "anio", "todo")
LIMITE_FILAS = 500


@gastos_bp.route("/")
@login_required
@admin_required
def gastos_list():
    hoy = hoy_local()
    tipo = request.args.get("tipo", "mes")
    if tipo not in TIPOS_PERIODO:
        tipo = "mes"
    periodo = resolver_periodo(tipo, hoy, mes=request.args.get("mes"), anio=request.args.get("anio"))

    gastos = (
        Gasto.query.filter(Gasto.fecha >= periodo.inicio, Gasto.fecha <= periodo.fin)
        .order_by(Gasto.fecha.desc(), Gasto.id.desc())
        .limit(LIMITE_FILAS + 1)
        .all()
    )
    truncado = len(gastos) > LIMITE_FILAS

    categorias = [c for (c,) in db.session.query(Gasto.categoria).distinct().order_by(Gasto.categoria).limit(50)]

    return render_template(
        "gastos_list.html",
        gastos=gastos[:LIMITE_FILAS],
        truncado=truncado,
        limite=LIMITE_FILAS,
        periodo=periodo,
        total_periodo=stats.total_gastos(periodo.inicio, periodo.fin),
        por_categoria=stats.gastos_por_categoria(periodo.inicio, periodo.fin),
        categorias=categorias,
        anios=stats.anios_disponibles(hoy),
        meses=list(enumerate(MESES, start=1)),
    )


@gastos_bp.route("/nuevo", methods=["POST"])
@login_required
@admin_required
def gasto_nuevo():
    hoy = hoy_local()
    monto = parse_decimal(request.form.get("monto"))
    categoria = limpiar_texto(request.form.get("categoria"), 80)
    texto_fecha = (request.form.get("fecha") or "").strip()
    fecha = parse_fecha(texto_fecha) if texto_fecha else hoy

    if monto is None or monto <= 0 or monto > MONTO_MAXIMO or not categoria:
        flash("Escribe una categoría y un monto mayor a cero.", "danger")
        return redirect(url_for("gastos.gastos_list"))
    if fecha is None or fecha < FECHA_MINIMA or fecha > hoy:
        flash("La fecha del gasto no es válida (no puede ser futura).", "danger")
        return redirect(url_for("gastos.gastos_list"))

    monto = redondear_centavos(monto)
    descripcion = limpiar_texto(request.form.get("descripcion"), 255) or None
    db.session.add(Gasto(fecha=fecha, categoria=categoria, descripcion=descripcion, monto=monto))
    auditar("gasto_creado", f"{categoria}: {cop(monto)} del {fecha_corta(fecha)}")
    db.session.commit()
    flash(f"Gasto de {cop(monto)} registrado.", "success")
    # Si el gasto es de otro mes, llevamos a ese mes para que se vea.
    return redirect(url_for("gastos.gastos_list", tipo="mes", mes=fecha.month, anio=fecha.year))


@gastos_bp.route("/<int:gasto_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def gasto_eliminar(gasto_id):
    gasto = db.get_or_404(Gasto, gasto_id)
    auditar("gasto_eliminado", f"{gasto.categoria}: {cop(gasto.monto)} del {fecha_corta(gasto.fecha)}")
    destino = url_for("gastos.gastos_list", tipo="mes", mes=gasto.fecha.month, anio=gasto.fecha.year)
    db.session.delete(gasto)
    db.session.commit()
    flash("Gasto eliminado.", "info")
    return redirect(destino)
