from datetime import date, timedelta
from decimal import Decimal
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class Usuario(db.Model, UserMixin):
    """Persona con acceso al sistema. Dos roles posibles:
    - 'admin': acceso total (panel, clientes, préstamos, pagos, reportes,
      gastos, editar y eliminar).
    - 'empleado': solo puede ver la lista de clientes, cargar un cliente
      nuevo, y registrar pagos. No ve panel, reportes ni gastos, y no
      puede editar ni eliminar nada."""

    __tablename__ = "usuarios"

    ROL_ADMIN = "admin"
    ROL_EMPLEADO = "empleado"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    nombre_completo = db.Column(db.String(150))
    rol = db.Column(db.String(20), nullable=False, default=ROL_ADMIN)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def es_admin(self):
        return self.rol == self.ROL_ADMIN

    def __repr__(self):
        return f"<Usuario {self.username} ({self.rol})>"


class Cliente(db.Model):
    """Datos personales del cliente. La cédula es su identificador único
    y es lo único que necesita para entrar al portal de consulta."""

    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(30))
    barrio = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    prestamos = db.relationship(
        "Prestamo", backref="cliente", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    def __repr__(self):
        return f"<Cliente {self.cedula} - {self.nombre_completo}>"


class Prestamo(db.Model):
    """Un préstamo individual. Un cliente puede tener
