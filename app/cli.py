import csv
import os

import click
from flask.cli import with_appcontext

from app import db
from app.models import Cliente, Usuario
from app.security import generar_pin, hash_pin
from app.utils import validar_password


def _crear_usuario(username, password, nombre, rol):
    username = username.strip()
    if not username:
        click.echo("El usuario no puede estar vacío.")
        return
    if Usuario.query.filter(db.func.lower(Usuario.username) == username.lower()).first():
        click.echo("Ya existe un usuario con ese nombre.")
        return
    error = validar_password(password, username)
    if error:
        click.echo(error)
        return
    user = Usuario(username=username, nombre_completo=nombre, rol=rol)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Usuario '{username}' ({rol}) creado correctamente.")


def register(app):
    @app.cli.command("crear-admin")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--nombre", prompt="Nombre completo", default="")
    @with_appcontext
    def crear_admin(username, password, nombre):
        """Crea un usuario administrador."""
        _crear_usuario(username, password, nombre, Usuario.ROL_ADMIN)

    @app.cli.command("crear-empleado")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--nombre", prompt="Nombre completo", default="")
    @with_appcontext
    def crear_empleado(username, password, nombre):
        """Crea un usuario con rol empleado (clientes, créditos y cobros)."""
        _crear_usuario(username, password, nombre, Usuario.ROL_EMPLEADO)

    @app.cli.command("cambiar-clave")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt="Nueva contraseña", hide_input=True, confirmation_prompt=True)
    @with_appcontext
    def cambiar_clave(username, password):
        """Cambia la contraseña de un usuario (útil si la olvidaste)."""
        user = Usuario.query.filter(db.func.lower(Usuario.username) == username.strip().lower()).first()
        if not user:
            click.echo("No existe ese usuario.")
            return
        error = validar_password(password, user.username)
        if error:
            click.echo(error)
            return
        user.set_password(password)
        db.session.commit()
        click.echo("Contraseña actualizada. Las sesiones abiertas de ese usuario se cerraron.")

    @app.cli.command("actualizar-bd")
    @with_appcontext
    def actualizar_bd():
        """Agrega a la base de datos las columnas e índices nuevos (seguro de repetir)."""
        from app.migrations import asegurar_esquema

        cambios = asegurar_esquema(app)
        click.echo("Cambios aplicados: " + (", ".join(cambios) if cambios else "ninguno, ya estaba al día."))

    @app.cli.command("generar-pins")
    @click.option("--archivo", default="pins_clientes.csv", show_default=True)
    @with_appcontext
    def generar_pins(archivo):
        """Crea el PIN del portal a los clientes que todavía no tienen uno y
        guarda la lista en un CSV para que se los entregues. Los PIN no se
        pueden volver a ver después: guarda bien ese archivo y bórralo luego."""
        pendientes = Cliente.query.filter(Cliente.portal_pin_hash.is_(None)).order_by(Cliente.id).all()
        if not pendientes:
            click.echo("Todos los clientes ya tienen PIN.")
            return
        with open(archivo, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["cedula", "cliente", "telefono", "pin"])
            for c in pendientes:
                pin = generar_pin()
                c.portal_pin_hash = hash_pin(pin)
                w.writerow([c.cedula, c.nombre_completo, c.telefono or "", pin])
        db.session.commit()
        try:
            os.chmod(archivo, 0o600)
        except OSError:
            pass
        click.echo(f"Se generaron {len(pendientes)} PIN. Lista guardada en: {archivo}")
        click.echo("Entrégalos a cada cliente y luego borra ese archivo.")
