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

    # Base de datos: por defecto usa SQLite (un solo archivo, sin servidor
    # aparte, ideal para hosting gratuito como PythonAnywhere free tier).
    # Si más adelante querés pasar a MySQL (por ejemplo en un plan pago),
    # definí las variables DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME y
    # el sistema arma la conexión a MySQL automáticamente.
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_HOST = os.environ.get("DB_HOST")
    DB_PORT = os.environ.get("DB_PORT", "3306")
    DB_NAME = os.environ.get("DB_NAME", "prestamos_db")

    if os.environ.get("DATABASE_URL"):
        SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    elif DB_USER and DB_HOST:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(basedir, 'prestamos.db')}"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Sesión de administrador expira tras un tiempo de inactividad.
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Días sin pago para considerar un préstamo "en mora".
    DIAS_PARA_MORA = int(os.environ.get("DIAS_PARA_MORA", "2"))

    # Protección CSRF (Flask-WTF)
    WTF_CSRF_ENABLED = True
