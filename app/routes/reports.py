import csv
import io
from datetime import timedelta
from xml.sax.saxutils import escape

from flask import Blueprint, render_template, request, send_file
from flask_login import login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import db, stats
from app.auth_utils import admin_required
from app.models import Cliente
from app.periodos import resolver_periodo
from app.utils import MESES, MESES_CORTOS, cop, fecha_corta, hoy_local, pct, redondear_pesos, titulo

reports_bp = Blueprint("reports", __name__, url_prefix="/admin/reportes")

FILAS_PANTALLA = 300
FILAS_EXPORTAR = 5000


# ---------------------------------------------------------------- filtros
def _leer_filtros():
    hoy = hoy_local()
    a = request.args
    periodo = resolver_periodo(
        a.get("tipo", "mes"), hoy,
        dia=a.get("dia"), mes=a.get("mes"), anio=a.get("anio"),
        desde=a.get("desde"), hasta=a.get("hasta"),
    )
    cliente_id = a.get("cliente_id", type=int)
    cliente = db.session.get(Cliente, cliente_id) if cliente_id else None
    return hoy, periodo, cliente


def _calcular(periodo, cliente):
    cid = cliente.id if cliente else None
    cobrado, ganancia, n_pagos = stats.totales_cobros(periodo.inicio, periodo.fin, cid)
    r = {
        "capital_prestado": stats.capital_prestado(periodo.inicio, periodo.fin, cid),
        "cobrado": cobrado,
        "ganancia": ganancia,
        "n_pagos": n_pagos,
        "gastos": None,
        "ganancia_neta": None,
    }
    if cliente:
        r.update(stats.resumen_cartera_cliente(cid))
    else:
        r.update(stats.resumen_cartera())
        # Los gastos son del negocio, no de un cliente: solo van en el reporte general.
        r["gastos"] = stats.total_gastos(periodo.inicio, periodo.fin)
        r["ganancia_neta"] = ganancia - r["gastos"]
    return r


def _atajos(hoy):
    ayer = hoy - timedelta(days=1)
    mes_pasado = hoy.replace(day=1) - timedelta(days=1)
    return [
        ("Hoy", {"tipo": "dia", "dia": hoy.isoformat()}),
        ("Ayer", {"tipo": "dia", "dia": ayer.isoformat()}),
        ("Últimos 7 días", {"tipo": "rango", "desde": (hoy - timedelta(days=6)).isoformat(), "hasta": hoy.isoformat()}),
        ("Este mes", {"tipo": "mes", "mes": hoy.month, "anio": hoy.year}),
        ("Mes pasado", {"tipo": "mes", "mes": mes_pasado.month, "anio": mes_pasado.year}),
        ("Este año", {"tipo": "anio", "anio": hoy.year}),
    ]


def _vecinos(periodo, hoy):
    """Parámetros para ir al período anterior / siguiente (día, mes o año)."""
    if periodo.tipo == "dia":
        ant, sig = periodo.inicio - timedelta(days=1), periodo.inicio + timedelta(days=1)
        return {"tipo": "dia", "dia": ant.isoformat()}, ({"tipo": "dia", "dia": sig.isoformat()} if sig <= hoy else None)
    if periodo.tipo == "mes":
        ant, sig = periodo.inicio - timedelta(days=1), periodo.fin + timedelta(days=1)
        return ({"tipo": "mes", "mes": ant.month, "anio": ant.year},
                {"tipo": "mes", "mes": sig.month, "anio": sig.year} if sig <= hoy else None)
    if periodo.tipo == "anio":
        a = periodo.inicio.year
        return ({"tipo": "anio", "anio": a - 1} if a > 2000 else None,
                {"tipo": "anio", "anio": a + 1} if a < hoy.year else None)
    return None, None


def _grafico(periodo, hoy, filas):
    """Barras de lo cobrado: por día (períodos cortos), por mes o por año."""
    if periodo.tipo == "todo":
        if not filas:
            return None
        inicio = filas[0][0]
    else:
        inicio = periodo.inicio
    fin = min(periodo.fin, hoy)
    dias = (fin - inicio).days + 1
    if dias <= 1:
        return None

    cobrado = {f: float(c) for f, c, _ in filas}
    etiquetas, valores = [], []

    if dias <= 62:
        mismo_mes = inicio.month == fin.month and inicio.year == fin.year
        d = inicio
        while d <= fin:
            etiquetas.append(str(d.day) if mismo_mes else f"{d.day}/{d.month}")
            valores.append(cobrado.get(d, 0.0))
            d += timedelta(days=1)
    elif dias <= 1100:
        por_mes = {}
        for f, v in cobrado.items():
            por_mes[(f.year, f.month)] = por_mes.get((f.year, f.month), 0.0) + v
        y, m = inicio.year, inicio.month
        while (y, m) <= (fin.year, fin.month):
            etiquetas.append(f"{MESES_CORTOS[m - 1]} {str(y)[2:]}")
            valores.append(por_mes.get((y, m), 0.0))
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    else:
        por_anio = {}
        for f, v in cobrado.items():
            por_anio[f.year] = por_anio.get(f.year, 0.0) + v
        for y in range(inicio.year, fin.year + 1):
            etiquetas.append(str(y))
            valores.append(por_anio.get(y, 0.0))

    return {
        "tipo": "barras",
        "etiquetas": etiquetas,
        "series": [{"nombre": "Cobrado", "valores": valores, "color": "brand"}],
        "dinero": True,
    }


# ----------------------------------------------------------------- vistas
@reports_bp.route("/")
@login_required
@admin_required
def index():
    hoy, periodo, cliente = _leer_filtros()
    cid = cliente.id if cliente else None

    cobros = stats.detalle_cobros(periodo.inicio, periodo.fin, cid, limite=FILAS_PANTALLA + 1)
    prestamos = stats.detalle_prestamos(periodo.inicio, periodo.fin, cid, limite=FILAS_PANTALLA + 1)
    previo, proximo = _vecinos(periodo, hoy)

    clientes = (
        db.session.query(Cliente.id, Cliente.nombres, Cliente.apellidos, Cliente.cedula)
        .order_by(Cliente.nombres, Cliente.apellidos)
        .limit(2000)
        .all()
    )

    return render_template(
        "reportes.html",
        periodo=periodo,
        cliente=cliente,
        reporte=_calcular(periodo, cliente),
        cobros=cobros[:FILAS_PANTALLA],
        cobros_truncado=len(cobros) > FILAS_PANTALLA,
        prestamos=prestamos[:FILAS_PANTALLA],
        prestamos_truncado=len(prestamos) > FILAS_PANTALLA,
        limite=FILAS_PANTALLA,
        grafico=_grafico(periodo, hoy, stats.cobros_por_dia(periodo.inicio, periodo.fin, cid)),
        atajos=_atajos(hoy),
        previo=previo,
        proximo=proximo,
        clientes=clientes,
        anios=stats.anios_disponibles(hoy),
        meses=list(enumerate(MESES, start=1)),
        dia_valor=periodo.inicio.isoformat() if periodo.tipo == "dia" else hoy.isoformat(),
        mes_valor=periodo.inicio.month if periodo.tipo == "mes" else hoy.month,
        anio_valor=periodo.inicio.year if periodo.tipo in ("mes", "anio") else hoy.year,
        desde_valor=periodo.inicio.isoformat() if periodo.tipo == "rango" else hoy.replace(day=1).isoformat(),
        hasta_valor=periodo.fin.isoformat() if periodo.tipo == "rango" else hoy.isoformat(),
    )


def _pesos(valor):
    return int(redondear_pesos(valor))


def _celda(texto):
    """Evita que Excel ejecute como fórmula un texto que empiece por = + - @
    (por ejemplo, un nombre de cliente escrito a propósito para eso)."""
    texto = "" if texto is None else str(texto)
    return "'" + texto if texto[:1] in ("=", "+", "-", "@", "\t", "\r") else texto


@reports_bp.route("/exportar/csv")
@login_required
@admin_required
def exportar_csv():
    hoy, periodo, cliente = _leer_filtros()
    cid = cliente.id if cliente else None
    r = _calcular(periodo, cliente)

    salida = io.StringIO()
    w = csv.writer(salida, delimiter=";")  # punto y coma: Excel en español lo abre en columnas
    w.writerow(["Reporte de préstamos"])
    w.writerow(["Período", periodo.etiqueta])
    w.writerow(["Desde", fecha_corta(periodo.inicio), "Hasta", fecha_corta(periodo.fin)])
    w.writerow(["Cliente", _celda(titulo(cliente.nombre_completo)) if cliente else "Todos"])
    w.writerow([])
    w.writerow(["Resumen (pesos)"])
    w.writerow(["Capital prestado en el período", _pesos(r["capital_prestado"])])
    w.writerow(["Cobrado", _pesos(r["cobrado"])])
    w.writerow(["Ganancia de lo cobrado", _pesos(r["ganancia"])])
    if r["gastos"] is not None:
        w.writerow(["Gastos", _pesos(r["gastos"])])
        w.writerow(["Ganancia neta", _pesos(r["ganancia_neta"])])
    w.writerow(["Capital por recuperar (hoy)", _pesos(r["capital_pendiente"])])
    w.writerow(["Pendiente por cobrar con interés (hoy)", _pesos(r["pendiente_cobrar"])])
    w.writerow([])

    w.writerow(["Cobros del período"])
    w.writerow(["Fecha", "Cliente", "Cédula", "Valor cobrado", "Ganancia"])
    for c in stats.detalle_cobros(periodo.inicio, periodo.fin, cid, limite=FILAS_EXPORTAR):
        w.writerow([fecha_corta(c["fecha"]), _celda(titulo(c["cliente"])), _celda(c["cedula"]),
                    _pesos(c["valor"]), _pesos(c["ganancia"])])
    w.writerow([])

    w.writerow(["Créditos otorgados en el período"])
    w.writerow(["Fecha del crédito", "Cliente", "Cédula", "Capital", "Interés", "Total a pagar", "Cuotas"])
    for p in stats.detalle_prestamos(periodo.inicio, periodo.fin, cid, limite=FILAS_EXPORTAR):
        w.writerow([fecha_corta(p["fecha"]), _celda(titulo(p["cliente"])), _celda(p["cedula"]),
                    _pesos(p["capital"]), pct(p["interes"]), _pesos(p["total"]), p["cuotas"]])

    datos = io.BytesIO(salida.getvalue().encode("utf-8-sig"))  # BOM: Excel lee bien las tildes
    return send_file(datos, mimetype="text/csv", as_attachment=True,
                     download_name=f"reporte_{periodo.tipo}_{hoy.isoformat()}.csv")


@reports_bp.route("/exportar/pdf")
@login_required
@admin_required
def exportar_pdf():
    hoy, periodo, cliente = _leer_filtros()
    cid = cliente.id if cliente else None
    r = _calcular(periodo, cliente)
    buffer = io.BytesIO()
    construir_pdf(
        buffer, periodo, cliente, r,
        stats.detalle_cobros(periodo.inicio, periodo.fin, cid, limite=FILAS_EXPORTAR),
        stats.detalle_prestamos(periodo.inicio, periodo.fin, cid, limite=FILAS_EXPORTAR),
    )
    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=f"reporte_{periodo.tipo}_{hoy.isoformat()}.pdf")


def construir_pdf(buffer, periodo, cliente, r, cobros, prestamos):
    """Arma el PDF (separado de la ruta para poder probarlo sin base de datos)."""
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=1.8 * cm, bottomMargin=1.5 * cm,
                            title="Reporte de préstamos")
    estilos = getSampleStyleSheet()
    verde = colors.HexColor("#0B5D44")
    elementos = [
        Paragraph("Reporte de préstamos", estilos["Title"]),
        Paragraph(escape(f"Período: {periodo.etiqueta} ({fecha_corta(periodo.inicio)} a {fecha_corta(periodo.fin)})"), estilos["Normal"]),
        Paragraph(escape("Cliente: " + (titulo(cliente.nombre_completo) if cliente else "Todos")), estilos["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    def tabla(datos, anchos, derecha=()):
        t = Table(datos, colWidths=anchos, repeatRows=1)
        estilo = [
            ("BACKGROUND", (0, 0), (-1, 0), verde),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C9D3CE")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F6F4")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        estilo += [("ALIGN", (c, 0), (c, -1), "RIGHT") for c in derecha]
        t.setStyle(TableStyle(estilo))
        return t

    resumen = [
        ["Concepto", "Valor"],
        ["Capital prestado en el período", cop(r["capital_prestado"])],
        ["Cobrado", cop(r["cobrado"])],
        ["Ganancia de lo cobrado", cop(r["ganancia"])],
    ]
    if r["gastos"] is not None:
        resumen += [["Gastos", cop(r["gastos"])], ["Ganancia neta", cop(r["ganancia_neta"])]]
    resumen += [
        ["Capital por recuperar (hoy)", cop(r["capital_pendiente"])],
        ["Pendiente por cobrar con interés (hoy)", cop(r["pendiente_cobrar"])],
    ]
    elementos.append(tabla(resumen, [10 * cm, 6 * cm], derecha=(1,)))

    if cobros:
        elementos += [Spacer(1, 0.6 * cm), Paragraph("Cobros del período", estilos["Heading3"])]
        filas = [["Fecha", "Cliente", "Cédula", "Cobrado", "Ganancia"]]
        filas += [[fecha_corta(c["fecha"]), titulo(c["cliente"])[:32], c["cedula"], cop(c["valor"]), cop(c["ganancia"])] for c in cobros]
        elementos.append(tabla(filas, [2.4 * cm, 6 * cm, 2.8 * cm, 2.9 * cm, 2.9 * cm], derecha=(3, 4)))

    if prestamos:
        elementos += [Spacer(1, 0.6 * cm), Paragraph("Créditos otorgados en el período", estilos["Heading3"])]
        filas = [["Fecha", "Cliente", "Capital", "Interés", "Total", "Cuotas"]]
        filas += [[fecha_corta(p["fecha"]), titulo(p["cliente"])[:30], cop(p["capital"]), pct(p["interes"]),
                   cop(p["total"]), str(p["cuotas"])] for p in prestamos]
        elementos.append(tabla(filas, [2.4 * cm, 5.6 * cm, 2.9 * cm, 1.8 * cm, 2.9 * cm, 1.5 * cm], derecha=(2, 3, 4, 5)))

    doc.build(elementos)
