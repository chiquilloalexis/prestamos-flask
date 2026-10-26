"""Pruebas de las funciones puras. Ejecutar:  python tests/test_puras.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import date
from decimal import Decimal
from app.utils import *
from app.periodos import resolver_periodo

casos = {"50.000": 50000, "50,000": 50000, "1.234.567": 1234567, "$ 1.234.567": 1234567, "45000": 45000,
         "1.234,56": Decimal("1234.56"), "1,234.56": Decimal("1234.56"), "0.5": Decimal("0.5"),
         "1500": 1500, "1.5": Decimal("1.5"), "-20": -20, "$50.000": 50000}
for k, v in casos.items():
    r = parse_decimal(k)
    assert r == Decimal(str(v)), (k, r, v)
for malo in ["abc", "", None, "1.2.3", "12,3,4", "1e5", "--5", "5$5", "$", "-", ".", ","]:
    assert parse_decimal(malo) is None, (malo, parse_decimal(malo))
assert parse_decimal("7,5", miles_=False) == Decimal("7.5") and parse_decimal("30", miles_=False) == 30
assert cop(1234567) == "$1.234.567" and cop(0) == "$0" and cop(None) == "$0" and cop(-5000) == "-$5.000"
assert cop(Decimal("1234.5")) == "$1.235" and miles(45000) == "45.000"
assert pct(Decimal("30.00")) == "30 %" and pct(Decimal("7.50")) == "7,5 %" and pct(0) == "0 %"
assert fecha_larga(date(2026, 10, 25)) == "domingo, 25 de octubre"
assert titulo("yoelvis  yacub") == "Yoelvis Yacub"
assert normalizar_cedula("1.065.123.456") == "1065123456" and normalizar_cedula(" 23479212 ") == "23479212"
assert normalizar_cedula("12") == "" and normalizar_cedula("ab<script>") == ""
assert validar_password("123456") and validar_password("12345678") and validar_password("password")
assert validar_password("Juan2026x", "juan") and validar_password("Cartera#2026") is None
for ok in ["/admin/clientes", "/admin/?x=1"]:
    assert destino_seguro(ok) == ok
for bad in ["https://evil.com", "//evil.com", "/\\evil.com", "javascript:alert(1)", "evil.com", None, "", "/ok\\x"]:
    assert destino_seguro(bad) is None, bad
assert parse_fecha("2026-10-25") == date(2026, 10, 25) and parse_fecha("25/10/2026") == date(2026, 10, 25)
assert parse_fecha("2026-13-40") is None

hoy = date(2026, 10, 25)
p = resolver_periodo("mes", hoy); assert (p.inicio, p.fin) == (date(2026, 10, 1), date(2026, 10, 31))
p = resolver_periodo("mes", hoy, mes="2", anio="2024"); assert (p.inicio, p.fin) == (date(2024, 2, 1), date(2024, 2, 29)) and p.etiqueta == "Febrero de 2024"
p = resolver_periodo("dia", hoy, dia="2026-03-09"); assert p.inicio == p.fin == date(2026, 3, 9)
p = resolver_periodo("dia", hoy, dia="basura"); assert p.inicio == hoy
p = resolver_periodo("anio", hoy, anio="2025"); assert (p.inicio, p.fin) == (date(2025, 1, 1), date(2025, 12, 31))
p = resolver_periodo("rango", hoy, desde="2026-10-20", hasta="2026-10-01"); assert (p.inicio, p.fin) == (date(2026, 10, 1), date(2026, 10, 20))
p = resolver_periodo("todo", hoy); assert p.fin == hoy
p = resolver_periodo("inventado", hoy, mes="99", anio="x"); assert p.tipo == "mes" and p.inicio == date(2026, 10, 1)
print("funciones puras: TODO OK")
