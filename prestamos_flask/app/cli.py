import click
from flask.cli import with_appcontext
from app import db
from app.models import Usuario, Prestamo


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

    @app.cli.command("actualizar-mora")
    @with_appcontext
    def actualizar_mora():
        """Recorre todos los préstamos activos y actualiza su estado
        (activo / en mora / cancelado). Pensado para correrse una vez
        por día via cron."""
        prestamos = Prestamo.query.filter(
            Prestamo.estado != Prestamo.ESTADO_CANCELADO
        ).all()
        dias_mora = app.config.get("DIAS_PARA_MORA", 2)
        actualizados = 0
        for p in prestamos:
            estado_anterior = p.estado
            p.actualizar_estado(dias_mora)
            if p.estado != estado_anterior:
                actualizados += 1
        db.session.commit()
        click.echo(f"Listo. {actualizados} préstamo(s) cambiaron de estado.")
