"""Funciones puras (sin base de datos): fechas, dinero, validaciones.

Están separadas del resto para poder probarlas solas y reutilizarlas en
las rutas y en las plantillas.
"""
import os
import re
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from urllib.parse import urlparse

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

MONTO_MAXIMO = Decimal("9999999999")  # cabe en Numeric(12, 2)
FECHA_MINIMA = date(2000, 1, 1)


# ------------------------------------------------------------------ tiempo
def _cargar_zona():
    nombre = os.environ.get("TZ_NAME", "America/Bogota")
    if ZoneInfo is not None:
        try:
            return ZoneInfo(nombre)
        except Exception:
            pass
    # Colombia no tiene horario de verano: UTC-5 fijo es un respaldo seguro.
    return timezone(timedelta(hours=-5), "COT")


ZONA = _cargar_zona()


def ahora_utc():
    """Fecha/hora UTC sin zona (formato que guardamos en la base de datos)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ahora_local():
    return datetime.now(ZONA)


def hoy_local():
    """'Hoy' según la zona del negocio, no la del servidor. Evita que a las
    7 p. m. (medianoche UTC) los cobros del día se corten en un hosting."""
    return ahora_local().date()


def a_local(dt_utc):
    if dt_utc is None:
        return None
    return dt_utc.replace(tzinfo=timezone.utc).astimezone(ZONA)


# ---------------------------------------------------------------- formatos
def cop(valor, signo=True):
    """1234567 -> '$1.234.567' (formato colombiano, pesos enteros)."""
    if valor is None:
        valor = 0
    d = Decimal(str(valor)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    texto = f"{abs(d):,.0f}".replace(",", ".")
    return f"{'-' if d < 0 else ''}{'$' if signo else ''}{texto}"


def miles(valor):
    """45000 -> '45.000' (sin símbolo, para rellenar campos de formulario)."""
    return cop(valor, signo=False)


def pct(valor):
    """30.00 -> '30 %' ; 7.5 -> '7,5 %'."""
    if valor is None:
        return "0 %"
    d = Decimal(str(valor)).normalize()
    texto = f"{d:f}".replace(".", ",")
    return f"{texto} %"


def fecha_corta(d):
    return d.strftime("%d/%m/%Y") if d else "—"


def fecha_larga(d):
    """date(2026,10,25) -> 'domingo, 25 de octubre'."""
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]}"


def fecha_hora(dt_utc):
    local = a_local(dt_utc)
    return local.strftime("%d/%m/%Y %H:%M") if local else "—"


def titulo(texto):
    """'yoelvis yacub' -> 'Yoelvis Yacub' (para mostrar nombres bien escritos)."""
    if not texto:
        return ""
    return " ".join(p.capitalize() for p in str(texto).split())


def mes_anio(anio, mes):
    return f"{MESES[mes - 1]} de {anio}"


# ----------------------------------------------------------------- lectura
def parse_decimal(texto, miles_=True):
    """Convierte lo que escribe una persona en Decimal. Devuelve None si no
    se entiende (nunca asume 0 en silencio).

    miles_=True  -> '50.000' o '50,000' significan cincuenta mil (pesos).
    miles_=False -> '7,5' o '7.5' significan siete y medio (porcentajes).
    Acepta '$ 1.234.567', '1.234,56', '1,234.56', '45000', etc.
    """
    if texto is None:
        return None
    s = str(texto).strip().replace(" ", "").replace(" ", "")
    if not s:
        return None
    negativo = s.startswith("-")
    if s[0] in "+-":
        s = s[1:]
    if s.startswith("$"):
        s = s[1:]
    if not s or not re.fullmatch(r"[\d.,]+", s) or not re.search(r"\d", s):
        return None

    if "." in s and "," in s:
        # El último separador es el decimal; el otro agrupa miles.
        dec = "," if s.rfind(",") > s.rfind(".") else "."
        mil = "." if dec == "," else ","
        s = s.replace(mil, "").replace(dec, ".")
    elif "." in s or "," in s:
        sep = "." if "." in s else ","
        partes = s.split(sep)
        if len(partes) > 2:
            # Varios separadores iguales: solo pueden ser miles (1.234.567).
            if not all(len(p) == 3 for p in partes[1:]) or not partes[0]:
                return None
            s = "".join(partes)
        else:
            entero, fraccion = partes
            if miles_ and len(fraccion) == 3 and 1 <= len(entero) <= 3 and entero != "0":
                s = entero + fraccion  # 50.000 -> 50000
            else:
                s = f"{entero or '0'}.{fraccion}"
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    return -d if negativo else d


def parse_entero(texto, minimo=None, maximo=None):
    try:
        n = int(str(texto).strip())
    except (TypeError, ValueError):
        return None
    if minimo is not None and n < minimo:
        return None
    if maximo is not None and n > maximo:
        return None
    return n


def parse_fecha(texto):
    """Acepta AAAA-MM-DD (campos de fecha del navegador) o DD/MM/AAAA."""
    if not texto:
        return None
    texto = str(texto).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def redondear_pesos(valor):
    return Decimal(valor).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def redondear_centavos(valor):
    return Decimal(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def normalizar_cedula(texto):
    """'1.065.123.456' -> '1065123456'. Devuelve '' si no es válida."""
    if texto is None:
        return ""
    limpio = re.sub(r"[\s.,\-]", "", str(texto)).upper()
    return limpio if re.fullmatch(r"[0-9A-Z]{5,20}", limpio) else ""


def limpiar_texto(texto, maximo):
    """Quita espacios sobrantes y recorta; evita campos gigantes."""
    if texto is None:
        return ""
    return re.sub(r"\s+", " ", str(texto)).strip()[:maximo]


def limpiar_telefono(texto):
    if not texto:
        return ""
    return re.sub(r"[^\d+\s\-()]", "", str(texto)).strip()[:30]


# --------------------------------------------------------------- seguridad
_CLAVES_COMUNES = {
    "12345678", "123456789", "1234567890", "password", "contraseña",
    "contrasena", "qwertyui", "qwerty123", "11111111", "00000000",
    "admin123", "administrador", "prestamos", "abcd1234", "iloveyou",
}


def validar_password(clave, usuario=""):
    """Devuelve un mensaje de error en español, o None si la clave sirve."""
    if clave is None or len(clave) < 8:
        return "La contraseña debe tener al menos 8 caracteres."
    if len(clave) > 128:
        return "La contraseña es demasiado larga (máximo 128 caracteres)."
    if clave.isdigit():
        return "La contraseña no puede ser solo números."
    if clave.lower() in _CLAVES_COMUNES:
        return "Esa contraseña es demasiado común. Elige otra."
    if usuario and len(usuario) >= 3 and usuario.lower() in clave.lower():
        return "La contraseña no debe contener el nombre de usuario."
    return None


def destino_seguro(destino):
    """Acepta solo rutas internas ('/admin/...'). Bloquea 'https://otro.com',
    '//otro.com' y variantes con barra invertida (redirección abierta)."""
    if not destino:
        return None
    if not destino.startswith("/") or destino.startswith("//") or "\\" in destino:
        return None
    partes = urlparse(destino)
    if partes.scheme or partes.netloc:
        return None
    return destino
