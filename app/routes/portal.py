import re

from flask import Blueprint, current_app, flash, make_response, render_template, request

from app import db
from app.models import Cliente
from app.security import bloqueo, ip_cliente, limpiar_fallos, pin_correcto, registrar_fallo
from app.utils import normalizar_cedula

portal_bp = Blueprint("portal", __name__, url_prefix="/portal")


def _respuesta(cliente=None, status=200):
    resp = make_response(render_template("portal.html", cliente=cliente), status)
    resp.headers["Cache-Control"] = "no-store"
    return resp


@portal_bp.route("/", methods=["GET", "POST"])
def entrada():
    """El cliente entra con su cédula y su PIN de 6 dígitos (que le da su
    prestamista). Solo ve su propia información. Los intentos fallidos se
    limitan por IP y por cédula para que nadie pueda adivinar un PIN."""
    if request.method != "POST":
        return _respuesta()

    cfg = current_app.config
    cedula = normalizar_cedula(request.form.get("cedula"))
    pin = re.sub(r"\D", "", request.form.get("pin", ""))[:12]
    ip = ip_cliente()

    espera = max(
        bloqueo("portal_ip", ip, cfg["RL_PORTAL_POR_IP"]),
        bloqueo("portal_cedula", cedula, cfg["RL_PORTAL_POR_CEDULA"]) if cedula else 0,
    )
    if espera:
        flash(f"Demasiados intentos. Espera {espera} minuto{'s' if espera != 1 else ''} e intenta de nuevo.", "danger")
        return _respuesta(status=429)

    cliente = Cliente.query.filter_by(cedula=cedula).first() if cedula else None
    if pin_correcto(cliente, pin):
        limpiar_fallos("portal_cedula", cedula)
        db.session.commit()
        return _respuesta(cliente)

    registrar_fallo("portal_ip", ip)
    if cedula:
        registrar_fallo("portal_cedula", cedula)
    db.session.commit()
    # Mismo mensaje si falla la cédula o el PIN: no revela cuáles existen.
    flash("Cédula o PIN incorrectos.", "danger")
    return _respuesta()
