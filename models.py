import hashlib
import hmac
from datetime import date
from decimal import Decimal

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.utils import ahora_utc

CERO = Decimal("0")
UN_PESO = Decimal("1")  # un saldo menor a un peso (centavos sueltos) cuenta como pagado


class Usuario(db.Model, UserMixin):
    """Persona con acceso al sistema. Dos roles:
    - 'admin': acceso total (panel, reportes, gastos, usuarios, editar y eliminar).
    - 'empleado': ve clientes, crea clientes y créditos, y registra cobros.
      No ve panel, reportes ni gastos, y no puede editar ni eliminar."""

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

    # La sesión guarda "id-sello". El sello cambia si cambia la contraseña,
    # así que cambiarla cierra todas las sesiones abiertas de esa persona.
    @property
    def sello(self):
        return hashlib.sha256(self.password_hash.encode()).hexdigest()[:20]

    def get_id(self):
        return f"{self.id}-{self.sello}"

    @staticmethod
    def desde_sesion(valor):
        try:
            pk, sello = str(valor).split("-", 1)
            usuario = db.session.get(Usuario, int(pk))
        except (ValueError, TypeError):
            return None
        if usuario and hmac.compare_digest(usuario.sello, sello):
            return usuario
        return None

    @property
    def es_admin(self):
        return self.rol == self.ROL_ADMIN

    @property
    def nombre_corto(self):
        return (self.nombre_completo or self.username).split(" ")[0]

    def __repr__(self):
        return f"<Usuario {self.username} ({self.rol})>"


class Cliente(db.Model):
    """Datos personales. La cédula es el identificador único: un cliente se
    crea UNA sola vez y acumula sus créditos a lo largo del tiempo."""

    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False, index=True)
    nombres = db.Column(db.String(100), nullable=False)
    apellidos = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(30))
    barrio = db.Column(db.String(100))
    archivado = db.Column(db.Boolean, nullable=False, default=False, server_default=db.false(), index=True)
    portal_pin_hash = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # Sin "delete": borrar un cliente NUNCA arrastra su historial de dinero.
    prestamos = db.relationship(
        "Prestamo",
        backref="cliente",
        lazy=True,
        cascade="save-update, merge",
        order_by="[Prestamo.fecha_prestamo, Prestamo.id]",
    )

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}"

    @property
    def prestamo_activo(self):
        for p in self.prestamos:
            if not p.esta_saldado:
                return p
        return None

    @property
    def prestamo_actual(self):
        """El crédito en curso; si no hay, el más reciente (ya pagado)."""
        return self.prestamo_activo or (self.prestamos[-1] if self.prestamos else None)

    @property
    def puede_nuevo_prestamo(self):
        """Regla de negocio: solo se le presta de nuevo si no debe nada."""
        return (not self.archivado) and self.prestamo_activo is None

    def __repr__(self):
        return f"<Cliente {self.cedula} - {self.nombre_completo}>"


class Prestamo(db.Model):
    """Un crédito individual. Un cliente puede tener varios a lo largo del
    tiempo, pero solo uno en curso a la vez."""

    __tablename__ = "prestamos"

    ESTADO_ACTIVO = "activo"
    ESTADO_CANCELADO = "cancelado"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False, index=True)

    fecha_prestamo = db.Column(db.Date, nullable=False, default=date.today, index=True)
    valor_inicial = db.Column(db.Numeric(12, 2), nullable=False)  # capital
    porcentaje_interes = db.Column(db.Numeric(5, 2), nullable=False, default=0)
    total_pagar = db.Column(db.Numeric(12, 2), nullable=False)  # capital + interés
    cantidad_cuotas = db.Column(db.Integer, nullable=False)
    valor_cuota = db.Column(db.Numeric(12, 2), nullable=False)
    observaciones = db.Column(db.Text)
    estado = db.Column(db.String(20), nullable=False, default=ESTADO_ACTIVO)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    pagos = db.relationship(
        "Pago",
        backref="prestamo",
        lazy=True,
        cascade="all, delete-orphan",
        order_by="[Pago.fecha.desc(), Pago.id.desc()]",
    )

    # ---------- Cálculos derivados ----------
    @property
    def total_cobrado(self):
        return sum((p.valor_pagado for p in self.pagos), CERO)

    @property
    def saldo_pendiente(self):
        restante = Decimal(self.total_pagar) - self.total_cobrado
        return restante if restante >= UN_PESO else CERO

    @property
    def esta_saldado(self):
        return self.saldo_pendiente <= 0

    @property
    def ratio_capital(self):
        """Qué parte de cada peso cobrado es capital (el resto es ganancia)."""
        if not self.total_pagar or Decimal(self.total_pagar) == 0:
            return CERO
        return Decimal(self.valor_inicial) / Decimal(self.total_pagar)

    @property
    def capital_recuperado(self):
        return self.total_cobrado * self.ratio_capital

    @property
    def capital_pendiente(self):
        """Capital que aún no vuelve (sin contar intereses)."""
        if self.esta_saldado:
            return CERO
        restante = Decimal(self.valor_inicial) - self.capital_recuperado
        return restante if restante > 0 else CERO

    @property
    def ganancia_generada(self):
        cobrado = self.total_cobrado
        return cobrado - (cobrado * self.ratio_capital)

    @property
    def ganancia_total_prevista(self):
        return Decimal(self.total_pagar) - Decimal(self.valor_inicial)

    @property
    def cuotas_pagadas(self):
        if self.esta_saldado:
            return self.cantidad_cuotas
        if not self.valor_cuota or Decimal(self.valor_cuota) == 0:
            return 0
        return min(int(self.total_cobrado // Decimal(self.valor_cuota)), self.cantidad_cuotas)

    @property
    def cuotas_pendientes(self):
        return max(self.cantidad_cuotas - self.cuotas_pagadas, 0)

    @property
    def progreso(self):
        """0-100, para la barra de avance."""
        if not self.total_pagar or Decimal(self.total_pagar) == 0:
            return 0
        return min(int(self.total_cobrado / Decimal(self.total_pagar) * 100), 100)

    # ---------- Mantenimiento ----------
    def actualizar_estado(self):
        self.estado = self.ESTADO_CANCELADO if self.esta_saldado else self.ESTADO_ACTIVO

    def recalcular_saldos(self):
        """Recalcula el 'saldo restante' de cada pago en orden cronológico.
        Se llama tras crear o eliminar un pago, para que el historial nunca
        quede con saldos viejos (por ejemplo, al borrar un pago intermedio
        o registrar uno con fecha anterior)."""
        corriente = Decimal(self.total_pagar)
        for pago in sorted(self.pagos, key=lambda p: (p.fecha, p.id or 10**12)):
            corriente -= pago.valor_pagado
            pago.saldo_restante = corriente if corriente > 0 else CERO

    def __repr__(self):
        return f"<Prestamo #{self.id} cliente={self.cliente_id} estado={self.estado}>"


class Pago(db.Model):
    """Cada abono registrado sobre un crédito."""

    __tablename__ = "pagos"

    id = db.Column(db.Integer, primary_key=True)
    prestamo_id = db.Column(db.Integer, db.ForeignKey("prestamos.id"), nullable=False, index=True)

    fecha = db.Column(db.Date, nullable=False, default=date.today, index=True)
    valor_pagado = db.Column(db.Numeric(12, 2), nullable=False)
    saldo_restante = db.Column(db.Numeric(12, 2), nullable=False)
    observacion = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<Pago #{self.id} prestamo={self.prestamo_id} valor={self.valor_pagado}>"


class Gasto(db.Model):
    """Gasto administrativo (combustible, pago a un cobrador, etc.). No toca
    los créditos; se resta de la ganancia para obtener la ganancia neta."""

    __tablename__ = "gastos"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False, default=date.today, index=True)
    categoria = db.Column(db.String(80), nullable=False)
    descripcion = db.Column(db.String(255))
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<Gasto #{self.id} {self.categoria} ${self.monto}>"


class Configuracion(db.Model):
    """Pares clave/valor para ajustes generales."""

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


class Auditoria(db.Model):
    """Bitácora: quién hizo qué y cuándo. Sirve para detectar errores o
    movimientos raros de dinero. No se edita desde la aplicación."""

    __tablename__ = "auditoria"

    id = db.Column(db.Integer, primary_key=True)
    creado = db.Column(db.DateTime, nullable=False, default=ahora_utc, index=True)
    usuario_id = db.Column(db.Integer)
    usuario = db.Column(db.String(80))  # copia del nombre: sobrevive si se borra el usuario
    accion = db.Column(db.String(40), nullable=False, index=True)
    detalle = db.Column(db.String(500))
    ip = db.Column(db.String(45))


class IntentoAcceso(db.Model):
    """Intentos fallidos de login / portal, para bloquear temporalmente a
    quien intente adivinar contraseñas o PIN."""

    __tablename__ = "intentos_acceso"

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), nullable=False)
    clave = db.Column(db.String(120), nullable=False)
    creado = db.Column(db.DateTime, nullable=False, default=ahora_utc)

    __table_args__ = (db.Index("ix_intentos_tipo_clave_creado", "tipo", "clave", "creado"),)
