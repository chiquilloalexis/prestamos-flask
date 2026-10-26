import os
import secrets
from datetime import timedelta
from urllib.parse import quote_plus

from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

# Valores de ejemplo que NUNCA deben usarse como clave real.
_CLAVES_INSEGURAS = {
    "",
    "cambia-esta-clave-en-produccion",
    "cambia-esta-clave-por-una-larga-y-aleatoria",
    "changeme",
    "secret",
    "dev",
}


def _env_bool(nombre, defecto=False):
    valor = os.environ.get(nombre)
    if valor is None or valor.strip() == "":
        return defecto
    return valor.strip().lower() in ("1", "true", "t", "si", "sí", "yes", "y", "on")


def _env_int(nombre, defecto):
    try:
        return int(os.environ.get(nombre, defecto))
    except (TypeError, ValueError):
        return defecto


def _obtener_secret_key():
    """Usa SECRET_KEY del entorno si es segura; si no, genera una clave
    aleatoria una sola vez y la guarda en instance/secret_key (permisos 600).
    Así nunca se arranca con una clave conocida por todo el mundo."""
    clave = os.environ.get("SECRET_KEY", "").strip()
    if clave not in _CLAVES_INSEGURAS and len(clave) >= 24:
        return clave

    carpeta = os.path.join(basedir, "instance")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, "secret_key")
    try:
        # Creación exclusiva: si varios procesos arrancan a la vez, solo uno escribe.
        fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
    with open(ruta) as f:
        return f.read().strip()


def _database_uri():
    url = os.environ.get("DATABASE_URL")
    if url:
        # Render a veces entrega "postgres://", que SQLAlchemy 2 no acepta.
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    usuario = os.environ.get("DB_USER")
    host = os.environ.get("DB_HOST")
    if usuario and host:
        clave = os.environ.get("DB_PASSWORD", "")
        puerto = os.environ.get("DB_PORT", "3306")
        nombre = os.environ.get("DB_NAME", "prestamos_db")
        # quote_plus: una contraseña con @ : / # ya no rompe la conexión.
        return (
            f"mysql+pymysql://{quote_plus(usuario)}:{quote_plus(clave)}"
            f"@{host}:{puerto}/{nombre}?charset=utf8mb4"
        )

    return f"sqlite:///{os.path.join(basedir, 'prestamos.db')}"


_en_render = bool(os.environ.get("RENDER"))


class Config:
    SECRET_KEY = _obtener_secret_key()
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Evita el error "MySQL server has gone away" tras inactividad.
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 280}

    # ---- Sesión y cookies ----
    PERMANENT_SESSION_LIFETIME = timedelta(hours=_env_int("SESION_HORAS", 8))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("COOKIE_SECURE", _en_render)
    SESSION_COOKIE_NAME = "cartera_sesion"
    REMEMBER_COOKIE_HTTPONLY = True

    # ---- CSRF ----
    WTF_CSRF_ENABLED = True
    # Sin caducidad por hora: un cobrador que deja la pantalla abierta mucho
    # rato no recibe un error al enviar. El token sigue atado a la sesión.
    WTF_CSRF_TIME_LIMIT = None

    # ---- Límites ----
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB por petición

    # ---- Protección contra adivinar contraseñas / PIN ----
    RL_VENTANA_MIN = _env_int("RL_VENTANA_MIN", 15)
    RL_LOGIN_POR_IP = _env_int("RL_LOGIN_POR_IP", 15)
    RL_LOGIN_POR_USUARIO = _env_int("RL_LOGIN_POR_USUARIO", 5)
    RL_PORTAL_POR_IP = _env_int("RL_PORTAL_POR_IP", 15)
    RL_PORTAL_POR_CEDULA = _env_int("RL_PORTAL_POR_CEDULA", 5)

    # ---- Despliegue ----
    TRUST_PROXY = _env_bool("TRUST_PROXY", _en_render)
    AUTO_MIGRATE = _env_bool("AUTO_MIGRATE", True)
