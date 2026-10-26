from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func

from app import db
from app.models import Usuario
from app.security import (
    auditar, bloqueo, gastar_tiempo, ip_cliente, limpiar_fallos, registrar_fallo,
)
from app.utils import destino_seguro, limpiar_texto, validar_password

auth_bp = Blueprint("auth", __name__)


def _destino_inicial(user):
    return url_for("admin.dashboard" if user.es_admin else "admin.clientes_list")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_destino_inicial(current_user))

    if request.method == "POST":
        cfg = current_app.config
        username = limpiar_texto(request.form.get("username"), 80)
        password = request.form.get("password", "")[:256]
        ip = ip_cliente()
        clave_usuario = username.lower()

        espera = max(
            bloqueo("login_ip", ip, cfg["RL_LOGIN_POR_IP"]),
            bloqueo("login_usuario", clave_usuario, cfg["RL_LOGIN_POR_USUARIO"]) if clave_usuario else 0,
        )
        if espera:
            flash(
                f"Demasiados intentos fallidos. Espera {espera} minuto{'s' if espera != 1 else ''} e intenta de nuevo.",
                "danger",
            )
            return render_template("login.html"), 429

        user = None
        if username:
            user = Usuario.query.filter(func.lower(Usuario.username) == clave_usuario).first()

        if user and user.check_password(password):
            siguiente = destino_seguro(request.args.get("next"))
            session.clear()  # evita fijación de sesión
            login_user(user, remember=False)
            session.permanent = True
            limpiar_fallos("login_usuario", clave_usuario)
            auditar("login", "Inicio de sesión", usuario=user)
            db.session.commit()
            flash(f"Bienvenido, {user.nombre_corto}.", "success")
            return redirect(siguiente or _destino_inicial(user))

        if not user:
            gastar_tiempo()  # mismo tiempo de respuesta exista o no el usuario
        registrar_fallo("login_ip", ip)
        if clave_usuario:
            registrar_fallo("login_usuario", clave_usuario)
        auditar("login_fallido", f"Intento con usuario '{username}'" if username else "Intento sin usuario")
        db.session.commit()
        flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    # Cerrar sesión por GET permitiría que cualquier página ajena (una imagen,
    # un enlace) te desconecte. Solo se cierra por POST con token CSRF.
    if request.method == "GET":
        return redirect(url_for("auth.login"))
    if current_user.is_authenticated:
        logout_user()
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/cuenta", methods=["GET", "POST"])
@login_required
def cuenta():
    if request.method == "POST":
        actual = request.form.get("actual", "")
        nueva = request.form.get("nueva", "")
        repetir = request.form.get("repetir", "")

        if not current_user.check_password(actual):
            flash("La contraseña actual no es correcta.", "danger")
        elif nueva != repetir:
            flash("La contraseña nueva y su confirmación no coinciden.", "danger")
        else:
            error = validar_password(nueva, current_user.username)
            if error:
                flash(error, "danger")
            else:
                current_user.set_password(nueva)
                auditar("clave_cambiada", "Cambió su propia contraseña")
                db.session.commit()
                # El sello de la sesión depende de la contraseña: hay que
                # volver a entrar (también se cierran las demás sesiones).
                logout_user()
                session.clear()
                flash("Contraseña actualizada. Inicia sesión con la nueva.", "success")
                return redirect(url_for("auth.login"))
    return render_template("cuenta.html")
