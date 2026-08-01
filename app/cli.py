import click
from flask.cli import with_appcontext
from app import db
from app.models import Usuario


def register(app):
    @app.cli.command("crear-admin")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--nombre", prompt="Nombre completo", default="")
    @with_appcontext
    def crear_admin(username, password, nombre):
        """Crea el usuario administrador. Ejecutar una sola vez tras instalar."""
        if Usuario.query.filter_by(username=username).first():
            click.echo("Ya existe un usuario con ese nombre.")
            return
        user = Usuario(username=username, nombre_completo=nombre, rol=Usuario.ROL_ADMIN)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrador '{username}' creado correctamente.")

    @app.cli.command("crear-empleado")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--nombre", prompt="Nombre completo", default="")
    @with_appcontext
    def crear_empleado(username, password, nombre):
        """Crea un usuario con rol 'empleado': solo puede ver la lista de
        clientes, cargar clientes nuevos y registrar pagos. No ve el panel,
        reportes ni gastos, y no puede editar ni eliminar nada."""
        if Usuario.query.filter_by(username=username).first():
            click.echo("Ya existe un usuario con ese nombre.")
            return
        user = Usuario(username=username, nombre_completo=nombre, rol=Usuario.ROL_EMPLEADO)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Empleado '{username}' creado correctamente.")
