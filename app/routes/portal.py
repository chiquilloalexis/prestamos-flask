from flask import Blueprint, render_template, request, flash
from app.models import Cliente

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")


@portal_bp.route("/", methods=["GET", "POST"])
def entrada():
    """El cliente solo escribe su cédula. No hay contraseña ni cuenta:
    si la cédula existe, ve su propia información y nada más."""
    cliente = None
    buscado = False

    if request.method == "POST":
        cedula = request.form.get("cedula", "").strip()
        buscado = True
        cliente = Cliente.query.filter_by(cedula=cedula).first()
        if not cliente:
            flash("No encontramos esa cédula. Verificala e intentá de nuevo.", "danger")

    return render_template("portal_login.html", cliente=cliente, buscado=buscado)
