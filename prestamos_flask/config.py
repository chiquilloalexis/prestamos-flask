import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

# Carga las variables definidas en el archivo .env (si existe) al entorno
# del proceso. Sin esto, DB_PASSWORD y el resto de los valores del .env
# quedarían ignorados y el sistema arrancaría siempre con los valores
# por defecto (SQLite) sin avisar.
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    # Clave secreta para sesiones y CSRF. En producción, definila como variable
    # de entorno y NO la dejes con este valor por defecto.
    SECRET_KEY = os.environ.get("SECRET_KEY", "cambia-esta-clave-en-produccion")

    # Base de datos: soporta PostgreSQL (ej: Render), MySQL, o SQLite como
    # último recurso si no hay nada configurado.
    #
    # - Si existe DATABASE_URL (Render la define sola al conectar una base
    #   de datos), se usa esa. Render a veces la entrega con el prefijo
    #   "postgres://", que las versiones recientes de SQLAlchemy no
    #   aceptan -- hay que normalizarlo a "postgresql://".
    # - Si no hay DATABASE_URL pero sí DB_USER/DB_HOST, arma una conexión
    #   MySQL (para hosting local con XAMPP/MySQL, por ejemplo).
    # - Si no hay nada de lo anterior, usa SQLite como último recurso
    #   (ideal para probar en el plan gratis de PythonAnywhere).
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "prestamos_db")

    _database_url = os.environ.get("DATABASE_URL")
    if _database_url:
        if _database_url.startswith("postgres://"):
            _database_url = _database_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = _database_url
    elif DB_USER and DB_HOST:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'prestamos.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Sesión de administrador expira tras un tiempo de inactividad.
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Protección CSRF (Flask-WTF)
    WTF_CSRF_ENABLED = True
