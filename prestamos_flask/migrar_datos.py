from app import create_app, db
from app.models import Usuario, Cliente, Prestamo, Pago, Gasto, Configuracion

app = create_app()

with app.app_context():

    print("Creando tablas...")
    db.create_all()

    print("Tablas creadas correctamente")

    # Crear usuario administrador
    existe = Usuario.query.filter_by(username="admin").first()

    if not existe:
        admin = Usuario(
            username="admin",
            nombre_completo="Administrador",
            rol="admin"
        )

        admin.set_password("123456")

        db.session.add(admin)
        db.session.commit()

        print("Usuario creado:")
        print("Usuario: admin")
        print("Clave: 123456")

    else:
        print("El usuario admin ya existe")