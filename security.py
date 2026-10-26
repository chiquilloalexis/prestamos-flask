"""Protección contra fuerza bruta, bitácora de acciones y PIN del portal."""
import math
import secrets
from datetime import timedelta

from flask import current_app, request
from flask_login import current_user
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import Auditoria, IntentoAcceso
from app.utils import ahora_utc, limpiar_texto

# Hash falso para gastar el mismo tiempo cuando el usuario o la cédula no
# existen; así no se puede adivinar cuáles existen midiendo la respuesta.
_HASH_FALSO = generate_password_hash("clave-falsa-que-nadie-usa")


def gastar_tiempo():
    check_password_hash(_HASH_FALSO, "otra-cosa")


def ip_cliente():
    return (request.remote_addr or "desconocida")[:45]


# ------------------------------------------------------- límite de intentos
def _desde():
    return ahora_utc() - timedelta(minutes=current_app.config["RL_VENTANA_MIN"])


def bloqueo(tipo, clave, maximo):
    """Devuelve 0 si puede intentar, o los minutos que debe esperar."""
    desde = _desde()
    cantidad, mas_antiguo = db.session.query(
        func.count(IntentoAcceso.id), func.min(IntentoAcceso.creado)
    ).filter(
        IntentoAcceso.tipo == tipo,
        IntentoAcceso.clave == clave,
        IntentoAcceso.creado >= desde,
    ).one()
    if cantidad < maximo or mas_antiguo is None:
        return 0
    libre = mas_antiguo + timedelta(minutes=current_app.config["RL_VENTANA_MIN"])
    segundos = (libre - ahora_utc()).total_seconds()
    return max(1, math.ceil(segundos / 60))


def registrar_fallo(tipo, clave):
    db.session.add(IntentoAcceso(tipo=tipo, clave=clave[:120]))
    # Limpieza: lo de más de un día ya no sirve.
    db.session.query(IntentoAcceso).filter(
        IntentoAcceso.creado < ahora_utc() - timedelta(days=1)
    ).delete(synchronize_session=False)


def limpiar_fallos(tipo, clave):
    db.session.query(IntentoAcceso).filter(
        IntentoAcceso.tipo == tipo, IntentoAcceso.clave == clave[:120]
    ).delete(synchronize_session=False)


# ----------------------------------------------------------------- bitácora
def auditar(accion, detalle="", usuario=None):
    """Anota una acción. No hace commit: se guarda junto con el resto de la
    operación (si la operación falla, la nota tampoco se guarda)."""
    if usuario is None and current_user and current_user.is_authenticated:
        usuario = current_user
    db.session.add(
        Auditoria(
            usuario_id=getattr(usuario, "id", None),
            usuario=(getattr(usuario, "username", None) or "")[:80] or None,
            accion=accion[:40],
            detalle=limpiar_texto(detalle, 500) or None,
            ip=ip_cliente(),
        )
    )


# ---------------------------------------------------------- PIN del portal
def generar_pin():
    """PIN de 6 dígitos. Evita los obvios (000000, 123456, 111111...)."""
    while True:
        pin = f"{secrets.randbelow(10**6):06d}"
        if len(set(pin)) <= 2:
            continue
        if pin in "01234567890" or pin in "98765432109":
            continue
        return pin


def hash_pin(pin):
    return generate_password_hash(pin)


def pin_correcto(cliente, pin):
    if cliente is None or not cliente.portal_pin_hash or not pin:
        gastar_tiempo()
        return False
    return check_password_hash(cliente.portal_pin_hash, pin)
