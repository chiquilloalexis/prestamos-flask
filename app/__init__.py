from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Iniciá sesión para continuar."
    login_manager.login_message_category = "warning"

    from app.models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # Blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.portal import portal_bp
    from app.routes.reports import reports_bp
    from app.routes.gastos import gastos_bp
    from app.routes.usuarios import usuarios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(gastos_bp)
    app.register_blueprint(usuarios_bp)

    from app import cli
    cli.register(app)

    @app.context_processor
    def inject_globals():
        from datetime import date
        return {"hoy": date.today()}

    return app
