import os

from flask import Flask, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Política de seguridad del navegador: solo se permite código, estilos e
# imágenes de este mismo sitio. Nada de CDN ni scripts de terceros.
CSP = (
    "default-src 'self'; "
    "img-src 'self' data:; "
    "style-src 'self'; "
    "script-src 'self'; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)


@event.listens_for(Engine, "connect")
def _sqlite_claves_foraneas(dbapi_conn, _record):
    """SQLite ignora las llaves foráneas por defecto; las activamos."""
    if dbapi_conn.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if app.config.get("TRUST_PROXY"):
        # Detrás de Render/Nginx: usar la IP y el esquema (https) reales.
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    db.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."
    login_manager.login_message_category = "warning"
    # "basic" y no "strong": con "strong" un cobrador que pasa del wifi a los
    # datos del celular (cambia la IP) quedaría desconectado a cada rato.
    login_manager.session_protection = "basic"

    from app.models import Usuario

    @login_manager.user_loader
    def cargar_usuario(valor):
        return Usuario.desde_sesion(valor)

    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.gastos import gastos_bp
    from app.routes.portal import portal_bp
    from app.routes.reports import reports_bp
    from app.routes.usuarios import usuarios_bp

    for bp in (auth_bp, admin_bp, portal_bp, reports_bp, gastos_bp, usuarios_bp):
        app.register_blueprint(bp)

    @app.route("/")
    def inicio():
        if current_user.is_authenticated and not current_user.es_admin:
            return redirect(url_for("admin.clientes_list"))
        return redirect(url_for("admin.dashboard"))

    from app import cli

    cli.register(app)

    registrar_plantillas(app)
    _registrar_cabeceras(app)
    _registrar_errores(app)

    if app.config.get("AUTO_MIGRATE"):
        from app.migrations import asegurar_esquema

        with app.app_context():
            try:
                asegurar_esquema(app)
            except Exception:  # No impedir el arranque; el detalle queda en el log.
                app.logger.exception("No se pudo actualizar la base de datos al iniciar")

    return app


# --------------------------------------------------------------------------
def registrar_plantillas(app):
    from app import utils
    from app.icons import ICONS

    app.jinja_env.filters.update(
        cop=utils.cop,
        miles=utils.miles,
        pct=utils.pct,
        fecha=utils.fecha_corta,
        fecha_larga=utils.fecha_larga,
        fecha_hora=utils.fecha_hora,
        titulo=utils.titulo,
    )
    app.jinja_env.globals["ICONS"] = ICONS
    app.jinja_env.globals["MESES"] = utils.MESES

    cache = {}

    def static_v(nombre):
        """URL de un archivo estático con su fecha de modificación, para que el
        navegador baje la versión nueva apenas se actualiza el sistema."""
        if nombre not in cache:
            try:
                version = int(os.path.getmtime(os.path.join(app.static_folder, nombre)))
            except OSError:
                version = 0
            cache[nombre] = url_for("static", filename=nombre, v=version)
        return cache[nombre]

    app.jinja_env.globals["static_v"] = static_v

    @app.context_processor
    def globales():
        return {"hoy": utils.hoy_local()}


def _registrar_cabeceras(app):
    @app.after_request
    def cabeceras_seguridad(resp):
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        resp.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=(), payment=()"
        resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.is_secure:
            resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Datos financieros: que el navegador no los guarde ni los muestre
        # con el botón "atrás" después de cerrar sesión.
        if not request.path.startswith("/static/"):
            resp.headers["Cache-Control"] = "no-store"
        return resp


def _registrar_errores(app):
    def pagina(codigo, titulo, mensaje):
        return render_template("error.html", codigo=codigo, titulo=titulo, mensaje=mensaje), codigo

    @app.errorhandler(CSRFError)
    def csrf_vencido(_e):
        return pagina(400, "El formulario caducó",
                      "Por seguridad, esta página ya no es válida. Vuelve atrás, recárgala e intenta de nuevo.")

    @app.errorhandler(400)
    def e400(_e):
        return pagina(400, "Solicitud no válida", "No pudimos entender los datos enviados.")

    @app.errorhandler(403)
    def e403(_e):
        return pagina(403, "Sin permiso", "No tienes permiso para ver esta página.")

    @app.errorhandler(404)
    def e404(_e):
        return pagina(404, "No encontramos esa página", "Revisa la dirección o vuelve al inicio.")

    @app.errorhandler(405)
    def e405(_e):
        return pagina(405, "Acción no permitida", "Esa acción no está disponible desde esta dirección.")

    @app.errorhandler(413)
    def e413(_e):
        return pagina(413, "Datos demasiado grandes", "La información enviada supera el tamaño permitido.")

    @app.errorhandler(500)
    def e500(_e):
        db.session.rollback()
        return pagina(500, "Algo salió mal", "Ocurrió un error inesperado. Tus datos no se perdieron; intenta de nuevo.")
