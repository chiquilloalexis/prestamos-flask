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
    """Un préstamo individual. Un cliente puede tener varios préstamos
    a lo largo del tiempo (históricos + el activo actual)."""

    __tablename__ = "prestamos"

    ESTADO_ACTIVO = "activo"
    ESTADO_CANCELADO = "cancelado"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)

    fecha_prestamo = db.Column(db.Date, nullable=False, default=date.today)
    valor_inicial = db.Column(db.Numeric(12, 2), nullable=False)
    porcentaje_interes = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    total_pagar = db.Column(db.Numeric(12, 2), nullable=False)
    cantidad_cuotas = db.Column(db.Integer, nullable=False)
    valor_cuota = db.Column(db.Numeric(12, 2), nullable=False)
    observaciones = db.Column(db.Text)
    estado = db.Column(db.String(20), nullable=False, default=ESTADO_ACTIVO)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    pagos = db.relationship(
        "Pago", backref="prestamo", lazy=True, cascade="all, delete-orphan",
        order_by="Pago.fecha.desc()",
    )

    # ---------- Cálculos derivados ----------
    @property
    def total_cobrado(self):
        return sum((p.valor_pagado for p in self.pagos), Decimal("0"))

    @property
    def saldo_pendiente(self):
        restante = Decimal(self.total_pagar) - self.total_cobrado
        return restante if restante > 0 else Decimal("0")

    @property
    def capital_recuperado(self):
        """Parte de lo cobrado hasta ahora que corresponde a capital
        (no a ganancia)."""
        return self.total_cobrado * self.ratio_capital

    @property
    def capital_pendiente(self):
        """Saldo que falta recuperar SIN contar la ganancia/interés --
        distinto de saldo_pendiente, que sí la incluye. Por ejemplo, si
        prestaste $1.000.000 con un total a pagar de $1.300.000 y ya
        cobraste $200.000, el saldo_pendiente es $1.100.000 pero el
        capital_pendiente es menor, porque una parte de esos $200.000
        cobrados ya cubrió capital."""
        restante = Decimal(self.valor_inicial) - self.capital_recuperado
        return restante if restante > 0 else Decimal("0")

    @property
    def ratio_capital(self):
        """Proporción del total a pagar que corresponde a capital (no ganancia)."""
        if not self.total_pagar or Decimal(self.total_pagar) == 0:
            return Decimal("0")
        return Decimal(self.valor_inicial) / Decimal(self.total_pagar)

    @property
    def ganancia_generada(self):
        """Ganancia realmente cobrada hasta la fecha, proporcional a lo cobrado."""
        return self.total_cobrado - (self.total_cobrado * self.ratio_capital)

    @property
    def ganancia_total_prevista(self):
        return Decimal(self.total_pagar) - Decimal(self.valor_inicial)

    @property
    def cuotas_pagadas(self):
        if not self.valor_cuota or Decimal(self.valor_cuota) == 0:
            return 0
        return int(self.total_cobrado // Decimal(self.valor_cuota))

    @property
    def cuotas_pendientes(self):
        return max(self.cantidad_cuotas - self.cuotas_pagadas, 0)

    @property
    def esta_saldado(self):
        return self.saldo_pendiente <= 0

    def actualizar_estado(self):
        """Recalcula y guarda el estado del préstamo: solo dos posibles --
        'activo' mientras deba algo, o 'cancelado' (se muestra como
        Inactivo) apenas el saldo llega a cero. Se llama tras cada pago."""
        self.estado = self.ESTADO_CANCELADO if self.esta_saldado else self.ESTADO_ACTIVO

    def __repr__(self):
        return f"<Prestamo #{self.id} cliente={self.cliente_id} estado={self.estado}>"


class Pago(db.Model):
    """Cada abono registrado sobre un préstamo. El saldo_restante queda
    congelado en el momento del pago para que el historial sea inmutable
    aunque después se editen otros pagos."""

    __tablename__ = "pagos"

    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey("prestamos.id"), nullable=False)

    fecha = db.Column(db.Date, nullable=False, default=date.today)
    valor_pagado = db.Column(db.Numeric(12, 2), nullable=False)
    saldo_restante = db.Column(db.Numeric(12, 2), nullable=False)
    observacion = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<Pago #{self.id} prestamo={self.prestamo_id} valor={self.valor_pagado}>"


class Gasto(db.Model):
    """Gasto administrativo del negocio: combustible, pago a un cobrador/
    trabajador, o cualquier otro costo operativo. No afecta los préstamos
    ni a los clientes; se usa para calcular la ganancia neta (ganancia de
    los cobros menos estos gastos) en el dashboard y en los reportes."""

    __tablename__ = "gastos"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today)
    categoria = db.Column(db.String(80), nullable=False)
    descripcion = db.Column(db.String(255))
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<Gasto #{self.id} {self.categoria} ${self.monto}>"


class Configuracion(db.Model):
    """Pares clave/valor para ajustes generales del sistema
    (nombre del negocio, etc.)."""

    __tablename__ = "configuraciones"

    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(80), unique=True, nullable=False)
    valor = db.Column(db.String(255))

    @staticmethod
    def get(clave, default=None):
        conf = Configuracion.query.filter_by(clave=clave).first()
        return conf.valor if conf else default

    @staticmethod
    def set(clave, valor):
        conf = Configuracion.query.filter_by(clave=clave).first()
        if not conf:
            conf = Configuracion(clave=clave, valor=str(valor))
            db.session.add(conf)
        else:
            conf.valor = str(valor)
        db.session.commit()
