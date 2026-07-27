from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(view_func):
    """Protege una ruta para que solo el rol 'admin' pueda entrar.
    Un usuario 'empleado' que intente acceder es redirigido a la lista
    de clientes con un aviso, en vez de ver un error crudo."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.es_admin:
            flash("No tenés permiso para acceder a esa sección.", "warning")
            return redirect(url_for("admin.clientes_list"))
        return view_func(*args, **kwargs)

    return wrapped
