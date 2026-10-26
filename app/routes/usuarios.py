from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy import func

from app import db
from app.auth_utils import admin_required
from app.models import Auditoria, Usuario
from app.security import auditar
from app.utils import limpiar_texto, validar_password

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/admin/usuarios")

NOMBRES_ACCION = {
    "login": "Inicio de sesión",
    "login_fallido": "Intento de acceso fallido",
    "clave_cambiada": "Cambio de contraseña",
    "clave_restablecida": "Contraseña restablecida",
    "cliente_creado": "Cliente creado",
    "cliente_editado": "Cliente editado",
    "cliente_archivado": "Cliente archivado",
    "cliente_restaurado": "Cliente restaurado",
    "cliente_eliminado": "Cliente eliminado",
    "pin_generado": "PIN del portal generado",
    "credito_creado": "Crédito creado",
    "pago_registrado": "Cobro registrado",
    "pago_eliminado": "Cobro eliminado",
    "gasto_creado": "Gasto registrado",
    "gasto_eliminado": "Gasto eliminado",
    "usuario_creado": "Usuario creado",
    "usuario_eliminado": "Usuario eliminado",
}


@usuarios_bp.route("/")
@login_required
@admin_required
def usuarios_list():
    usuarios = Usuario.query.order_by(Usuario.rol, Usuario.username).all()
    return render_template("usuarios_list.html", usuarios=usuarios)


@usuarios_bp.route("/nuevo", methods=["POST"])
@login_required
@admin_required
def usuario_nuevo():
    username = limpiar_texto(request.form.get("username"), 80)
    password = request.form.get("password", "")
    nombre = limpiar_texto(request.form.get("nombre_completo"), 150)
    rol = request.form.get("rol", Usuario.ROL_EMPLEADO)
    if rol not in (Usuario.ROL_ADMIN, Usuario.ROL_EMPLEADO):
        rol = Usuario.ROL_EMPLEADO

    destino = redirect(url_for("usuarios.usuarios_list"))
    if len(username) < 3 or " " in username:
        flash("El usuario debe tener al menos 3 caracteres y no llevar espacios.", "danger")
        return destino
    error = validar_password(password, username)
    if error:
        flash(error, "danger")
        return destino
    if Usuario.query.filter(func.lower(Usuario.username) == username.lower()).first():
        flash("Ya existe un usuario con ese nombre.", "danger")
        return destino

    user = Usuario(username=username, nombre_completo=nombre or None, rol=rol)
    user.set_password(password)
    db.session.add(user)
    auditar("usuario_creado", f"{username} ({rol})")
    db.session.commit()
    flash(f"Usuario '{username}' ({'administrador' if rol == Usuario.ROL_ADMIN else 'empleado'}) creado.", "success")
    return destino


@usuarios_bp.route("/<int:usuario_id>/clave", methods=["POST"])
@login_required
@admin_required
def usuario_clave(usuario_id):
    """El administrador asigna una contraseña nueva a alguien que la olvidó."""
    usuario = db.get_or_404(Usuario, usuario_id)
    nueva = request.form.get("nueva", "")
    error = validar_password(nueva, usuario.username)
    if error:
        flash(error, "danger")
        return redirect(url_for("usuarios.usuarios_list"))

    es_yo = usuario.id == current_user.id
    usuario.set_password(nueva)  # cierra las sesiones abiertas de esa persona
    auditar("clave_restablecida", f"Contraseña de '{usuario.username}'")
    db.session.commit()
    if es_yo:
        logout_user()
        session.clear()
        flash("Cambiaste tu propia contraseña: inicia sesión de nuevo.", "info")
        return redirect(url_for("auth.login"))
    flash(f"Contraseña de '{usuario.username}' actualizada.", "success")
    return redirect(url_for("usuarios.usuarios_list"))


@usuarios_bp.route("/<int:usuario_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def usuario_eliminar(usuario_id):
    usuario = db.get_or_404(Usuario, usuario_id)
    destino = redirect(url_for("usuarios.usuarios_list"))

    if usuario.id == current_user.id:
        flash("No puedes eliminar tu propia cuenta mientras la estás usando.", "danger")
        return destino
    if usuario.es_admin:
        otros = Usuario.query.filter(Usuario.rol == Usuario.ROL_ADMIN, Usuario.id != usuario.id).count()
        if otros == 0:
            flash("No puedes eliminar al único administrador del sistema.", "danger")
            return destino

    nombre = usuario.username
    auditar("usuario_eliminado", nombre)
    db.session.delete(usuario)
    db.session.commit()
    flash(f"Usuario '{nombre}' eliminado.", "info")
    return destino


@usuarios_bp.route("/actividad")
@login_required
@admin_required
def actividad():
    """Bitácora de acciones (quién hizo qué). Solo lectura."""
    pagina = request.args.get("pagina", 1, type=int)
    accion = request.args.get("accion", "").strip()[:40]
    consulta = Auditoria.query
    if accion:
        consulta = consulta.filter(Auditoria.accion == accion)
    paginacion = consulta.order_by(Auditoria.creado.desc(), Auditoria.id.desc()).paginate(
        page=pagina, per_page=50, error_out=False
    )
    acciones = [a for (a,) in db.session.query(Auditoria.accion).distinct().order_by(Auditoria.accion)]
    return render_template(
        "actividad.html", paginacion=paginacion, acciones=acciones, accion=accion, nombres=NOMBRES_ACCION
    )
