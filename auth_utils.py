from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(vista):
    """Solo el rol 'admin' puede entrar. Un empleado que lo intente vuelve a
    la lista de clientes con un aviso, en vez de ver un error."""

    @wraps(vista)
    def envuelta(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_admin:
            flash("No tienes permiso para entrar a esa sección.", "warning")
            return redirect(url_for("admin.clientes_list"))
        return vista(*args, **kwargs)

    return envuelta
