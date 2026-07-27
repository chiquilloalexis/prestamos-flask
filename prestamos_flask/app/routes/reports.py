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


def
