"""Actualización automática de la base de datos.

`db.create_all()` crea tablas nuevas pero NO agrega columnas ni índices a
tablas que ya existen. Como este sistema ya puede tener datos reales, aquí se
agregan (de forma segura y repetible) las columnas e índices que faltan.
Es seguro ejecutarlo muchas veces: si ya está todo, no hace nada.
"""
from sqlalchemy import inspect, text

from app import db

# (tabla, columna, definición por motor)
_COLUMNAS = [
    (
        "clientes",
        "archivado",
        {
            "sqlite": "BOOLEAN NOT NULL DEFAULT 0",
            "mysql": "TINYINT(1) NOT NULL DEFAULT 0",
            "postgresql": "BOOLEAN NOT NULL DEFAULT FALSE",
        },
    ),
    ("clientes", "portal_pin_hash", {"*": "VARCHAR(255) NULL"}),
]

# (tabla, nombre del índice, columnas)
_INDICES = [
    ("pagos", "ix_pagos_fecha", ["fecha"]),
    ("pagos", "ix_pagos_prestamo_id", ["prestamo_id"]),
    ("prestamos", "ix_prestamos_cliente_id", ["cliente_id"]),
    ("prestamos", "ix_prestamos_fecha_prestamo", ["fecha_prestamo"]),
    ("gastos", "ix_gastos_fecha", ["fecha"]),
    ("clientes", "ix_clientes_archivado", ["archivado"]),
]


def asegurar_esquema(app=None):
    """Crea tablas faltantes, agrega columnas nuevas e índices.
    Devuelve la lista de cambios aplicados (vacía si no hubo nada que hacer)."""
    cambios = []
    db.create_all()

    motor = db.engine.dialect.name
    inspector = inspect(db.engine)
    tablas = set(inspector.get_table_names())

    for tabla, columna, definiciones in _COLUMNAS:
        if tabla not in tablas:
            continue
        existentes = {c["name"] for c in inspector.get_columns(tabla)}
        if columna in existentes:
            continue
        definicion = definiciones.get(motor) or definiciones.get("*") or next(iter(definiciones.values()))
        db.session.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}"))
        db.session.commit()
        cambios.append(f"columna {tabla}.{columna}")

    inspector = inspect(db.engine)  # refrescar después de agregar columnas
    for tabla, nombre, columnas in _INDICES:
        if tabla not in tablas:
            continue
        existentes = inspector.get_indexes(tabla)
        ya_cubierto = any(list(i["column_names"]) == columnas for i in existentes)
        # En MySQL las llaves foráneas ya crean su propio índice.
        if ya_cubierto or any(i["name"] == nombre for i in existentes):
            continue
        db.session.execute(text(f"CREATE INDEX {nombre} ON {tabla} ({', '.join(columnas)})"))
        db.session.commit()
        cambios.append(f"índice {nombre}")

    if app is not None and cambios:
        app.logger.info("Base de datos actualizada: %s", ", ".join(cambios))
    return cambios
