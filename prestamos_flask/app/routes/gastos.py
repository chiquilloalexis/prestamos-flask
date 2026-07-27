from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app import db
from app.models import Gasto
from app.auth_utils import admin_required

gastos_bp = Blueprint("gastos", __name__, url_prefix="/admin/gastos")


def _to_decimal(value, default="0"):
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, TypeError):
        return Decimal(default)


@gastos_bp.route("/")
@login_required
@admin_required
def gastos_list():
    gastos = Gasto.query.order_by(Gasto.fecha.desc(), Gasto.created_at.desc()).all()

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)
    total_mes = sum(
        (g.monto for g in gastos if g.fecha >= inicio_mes), Decimal("0")
    )
    total_general = sum((g.monto for g in gastos), Decimal("0"))

    # Categorías ya usadas, para sugerir en el campo de texto libre (datalist)
    categorias = sorted({g.categoria for g in gastos if g.categoria})

    return render_template(
        "gastos_list.html",
        gastos=gastos,
        total_mes=total_mes,
        total_general=total_general,
        categorias=categorias,
        hoy=hoy,
    )


@gastos_bp.route("/nuevo", methods=["POST"])
@login_required
@admin_required
def gasto_nuevo():
    monto = _to_decimal(request.form.get("monto"))
    categoria = request.form.get("categoria", "").strip()

    if monto <= 0 or not categoria:
        flash("Completá la categoría y un monto mayor a cero.", "danger")
        return redirect(url_for("gastos.gastos_list"))

    gasto = Gasto(
        fecha=request.form.get("fecha") or date.today(),
        categoria=categoria,
        descripcion=request.form.get("descripcion", "").strip(),
        monto=monto,
    )
    db.session.add(gasto)
    db.session.commit()
    flash(f"Gasto de ${monto:,.0f} registrado.", "success")
    return redirect(url_for("gastos.gastos_list"))


@gastos_bp.route("/<int:gasto_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def gasto_eliminar(gasto_id):
    gasto = Gasto.query.get_or_404(gasto_id)
    db.session.delete(gasto)
    db.session.commit()
    flash("Gasto eliminado.", "info")
    return redirect(url_for("gastos.gastos_list"))
