from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app import db
from app.models import Usuario
from app.auth_utils import admin_required

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/admin/usuarios")


@usuarios_bp.route("/")
@login_required
@admin_required
def usuarios_list():
    usuarios = Usuario.query.order_by(Usuario.rol.desc(), Usuario.username).all()
    return render_template("usuarios_list.html", usuarios=usuarios)


@usuarios_bp.route("/nuevo", methods=["POST"])
@login_required
@admin_required
def usuario_nuevo():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    nombre = request.form.get("nombre_completo", "").strip()
    rol = request.form.get("rol", Usuario.ROL_EMPLEADO)

    if rol not in (Usuario.ROL_ADMIN, Usuario.ROL_EMPLEADO):
        rol = Usuario.ROL_EMPLEADO

    if not username or not password:
        flash("Completá usuario y contraseña.", "danger")
        return redirect(url_for("usuarios.usuarios_list"))

    if Usuario.query.filter_by(username=username).first():
        flash("Ya existe un usuario con ese nombre.", "danger")
        return redirect(url_for("usuarios.usuarios_list"))

    user = Usuario(username=username, nombre_completo=nombre, rol=rol)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    etiqueta_rol = "administrador" if rol == Usuario.ROL_ADMIN else "empleado"
    flash(f"Usuario '{username}' ({etiqueta_rol}) creado correctamente.", "success")
    return redirect(url_for("usuarios.usuarios_list"))


@usuarios_bp.route("/<int:usuario_id>/eliminar", methods=["POST"])
@login_required
@admin_required
def usuario_eliminar(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)

    if usuario.id == current_user.id:
        flash("No podés eliminar tu propia cuenta mientras estás conectado con ella.", "danger")
        return redirect(url_for("usuarios.usuarios_list"))

    if usuario.es_admin:
        otros_admins = Usuario.query.filter(
            Usuario.rol == Usuario.ROL_ADMIN, Usuario.id != usuario.id
        ).count()
        if otros_admins == 0:
            flash("No podés eliminar al único administrador del sistema.", "danger")
            return redirect(url_for("usuarios.usuarios_list"))

    nombre = usuario.username
    db.session.delete(usuario)
    db.session.commit()
    flash(f"Usuario '{nombre}' eliminado.", "info")
    return redirect(url_for("usuarios.usuarios_list"))
