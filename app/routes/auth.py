from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import Usuario

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        destino = "admin.dashboard" if current_user.es_admin else "admin.clientes_list"
        return redirect(url_for(destino))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = Usuario.query.filter_by(username=username).first()

        # Comparación segura: no revelamos si falló el usuario o la clave.
        if user and user.check_password(password):
            login_user(user, remember=False)
            next_page = request.args.get("next")
            flash(f"Bienvenido, {user.nombre_completo or user.username}.", "success")
            destino = "admin.dashboard" if user.es_admin else "admin.clientes_list"
            return redirect(next_page or url_for(destino))

        flash("Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))
