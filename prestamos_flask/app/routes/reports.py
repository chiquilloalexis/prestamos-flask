import csv
import io
from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, render_template, request, Response, send_file
from flask_login import login_required
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from app.models import Cliente, Prestamo, Pago, Gasto
from app.auth_utils import admin_required

reports_bp = Blueprint("reports", __name__, url_prefix="/admin/reportes")


def _rango_por_filtro(filtro):
    hoy = date.today()
    if filtro == "dia":
        return hoy, hoy
    if filtro == "semana":
        return hoy - timedelta(days=7), hoy
    if filtro == "mes":
        return hoy.replace(day=1), hoy
    if filtro == "anio":
        return hoy.replace(month=1, day=1), hoy
    return date(2000, 1, 1), hoy  # "todo" / cliente


def _calcular_reporte(filtro, cliente_id=None):
    inicio, fin = _rango_por_filtro(filtro)

    if filtro == "cliente" and cliente_id:
        prestamos = Prestamo.query.filter_by(cliente_id=cliente_id).all()
    else:
        prestamos = Prestamo.query.all()

    total_prestado = Decimal("0")
    total_cobrado = Decimal("0")
    ganancia_generada = Decimal("0")
    capital_pendiente = Decimal("0")

    for p in prestamos:
        capital_pendiente += p.saldo_pendiente

        if filtro == "cliente":
            total_prestado += p.valor_inicial
            total_cobrado += p.total_cobrado
            ganancia_generada += p.ganancia_generada
        else:
            if inicio <= p.fecha_prestamo <= fin:
                total_prestado += p.valor_inicial
            ratio = p.ratio_capital
            for pago in p.pagos:
                if inicio <= pago.fecha <= fin:
                    total_cobrado += pago.valor_pagado
                    ganancia_generada += pago.valor_pagado - (pago.valor_pagado * ratio)

    # Los gastos administrativos (combustible, pago a trabajador, etc.) se
    # filtran siempre por fecha del gasto dentro del período, sin importar
    # el tipo de filtro -- así el reporte "por cliente" no arrastra gastos
    # que no tienen relación con ese cliente puntual.
    gastos_periodo = Gasto.query.filter(Gasto.fecha >= inicio, Gasto.fecha <= fin).all()
    total_gastos = sum((g.monto for g in gastos_periodo), Decimal("0"))
    ganancia_neta = ganancia_generada - total_gastos

    return {
        "total_prestado": total_prestado,
        "total_cobrado": total_cobrado,
        "ganancia_generada": ganancia_generada,
        "capital_pendiente": capital_pendiente,
        "total_gastos": total_gastos,
        "ganancia_neta": ganancia_neta,
        "inicio": inicio,
        "fin": fin,
    }


@reports_bp.route("/")
@login_required
@admin_required
def index():
    filtro = request.args.get("filtro", "mes")
    cliente_id = request.args.get("cliente_id", type=int)

    clientes = Cliente.query.order_by(Cliente.nombres).all()
    reporte = _calcular_reporte(filtro, cliente_id)

    return render_template(
        "reportes.html", reporte=reporte, filtro=filtro,
        clientes=clientes, cliente_id=cliente_id,
    )


@reports_bp.route("/exportar/csv")
@login_required
@admin_required
def exportar_csv():
    filtro = request.args.get("filtro", "mes")
    cliente_id = request.args.get("cliente_id", type=int)
    reporte = _calcular_reporte(filtro, cliente_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Reporte", filtro])
    writer.writerow(["Periodo", f"{reporte['inicio']} a {reporte['fin']}"])
    writer.writerow([])
    writer.writerow(["Total prestado", f"{reporte['total_prestado']:.2f}"])
    writer.writerow(["Total cobrado", f"{reporte['total_cobrado']:.2f}"])
    writer.writerow(["Ganancia generada", f"{reporte['ganancia_generada']:.2f}"])
    writer.writerow(["Gastos administrativos", f"{reporte['total_gastos']:.2f}"])
    writer.writerow(["Ganancia neta", f"{reporte['ganancia_neta']:.2f}"])
    writer.writerow(["Capital pendiente", f"{reporte['capital_pendiente']:.2f}"])

    mem = io.BytesIO(output.getvalue().encode("utf-8-sig"))  # BOM para Excel
    mem.seek(0)
    return send_file(
        mem, mimetype="text/csv", as_attachment=True,
        download_name=f"reporte_{filtro}_{date.today()}.csv",
    )


@reports_bp.route("/exportar/pdf")
@login_required
@admin_required
def exportar_pdf():
    filtro = request.args.get("filtro", "mes")
    cliente_id = request.args.get("cliente_id", type=int)
    reporte = _calcular_reporte(filtro, cliente_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=2 * cm)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Reporte de préstamos", styles["Title"]),
        Paragraph(f"Periodo: {reporte['inicio']} a {reporte['fin']}", styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    data = [
        ["Concepto", "Valor"],
        ["Total prestado", f"${reporte['total_prestado']:,.0f}"],
        ["Total cobrado", f"${reporte['total_cobrado']:,.0f}"],
        ["Ganancia generada", f"${reporte['ganancia_generada']:,.0f}"],
        ["Gastos administrativos", f"${reporte['total_gastos']:,.0f}"],
        ["Ganancia neta", f"${reporte['ganancia_neta']:,.0f}"],
        ["Capital pendiente", f"${reporte['capital_pendiente']:,.0f}"],
    ]
    table = Table(data, colWidths=[8 * cm, 6 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#171F1B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return send_file(
        buffer, mimetype="application/pdf", as_attachment=True,
        download_name=f"reporte_{filtro}_{date.today()}.pdf",
    )
