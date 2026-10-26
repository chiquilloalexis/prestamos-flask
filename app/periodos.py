"""Resolución de períodos para reportes y gastos (día, mes, año, rango, todo).

Pura: recibe lo que llegó en la URL y devuelve fechas válidas. Si algo viene
mal escrito, cae en un valor razonable en vez de romper la página.
"""
from calendar import monthrange
from collections import namedtuple
from datetime import date

from app.utils import FECHA_MINIMA, fecha_corta, fecha_larga, mes_anio, parse_entero, parse_fecha

Periodo = namedtuple("Periodo", "tipo inicio fin etiqueta params")

TIPOS = ("dia", "mes", "anio", "rango", "todo")


def _anio(valor, hoy):
    n = parse_entero(valor, 2000, 2100)
    return n if n is not None else hoy.year


def _mes(valor, hoy):
    n = parse_entero(valor, 1, 12)
    return n if n is not None else hoy.month


def resolver_periodo(tipo, hoy, dia=None, mes=None, anio=None, desde=None, hasta=None):
    tipo = tipo if tipo in TIPOS else "mes"

    if tipo == "dia":
        d = parse_fecha(dia) or hoy
        if d < FECHA_MINIMA:
            d = hoy
        return Periodo("dia", d, d, fecha_larga(d) + f" de {d.year}", {"tipo": "dia", "dia": d.isoformat()})

    if tipo == "anio":
        a = _anio(anio, hoy)
        return Periodo("anio", date(a, 1, 1), date(a, 12, 31), f"Año {a}", {"tipo": "anio", "anio": a})

    if tipo == "rango":
        ini = parse_fecha(desde) or hoy.replace(day=1)
        fin = parse_fecha(hasta) or hoy
        if ini > fin:
            ini, fin = fin, ini
        etiqueta = f"Del {fecha_corta(ini)} al {fecha_corta(fin)}"
        return Periodo("rango", ini, fin, etiqueta,
                       {"tipo": "rango", "desde": ini.isoformat(), "hasta": fin.isoformat()})

    if tipo == "todo":
        return Periodo("todo", FECHA_MINIMA, hoy, "Todo el historial", {"tipo": "todo"})

    # mes (por defecto)
    a, m = _anio(anio, hoy), _mes(mes, hoy)
    return Periodo("mes", date(a, m, 1), date(a, m, monthrange(a, m)[1]),
                   mes_anio(a, m).capitalize(), {"tipo": "mes", "mes": m, "anio": a})
