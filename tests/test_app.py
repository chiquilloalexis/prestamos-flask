"""Prueba completa del sistema con una base de datos temporal (no toca tus datos).

Ejecutar desde la carpeta del proyecto, con el entorno virtual activo:

    python -m unittest discover -s tests -v
"""
import os
import re
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from config import Config  # noqa: E402

_carpeta = tempfile.mkdtemp()


class ConfigPrueba(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False  # en pruebas no hay navegador que envíe el token
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(_carpeta, "prueba.db")
    AUTO_MIGRATE = True


from app import create_app, db  # noqa: E402
from app.models import Cliente, Prestamo, Usuario  # noqa: E402
from app.utils import hoy_local  # noqa: E402

CLAVE = "Cartera#2026"


class BaseCase(unittest.TestCase):
    def setUp(self):
        ruta = ConfigPrueba.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
        if os.path.exists(ruta):
            os.remove(ruta)
        self.app = create_app(ConfigPrueba)
        self.ctx = self.app.app_context()
        self.ctx.push()
        for nombre, rol in (("admin", Usuario.ROL_ADMIN), ("cobrador", Usuario.ROL_EMPLEADO)):
            u = Usuario(username=nombre, nombre_completo=nombre.title(), rol=rol)
            u.set_password(CLAVE)
            db.session.add(u)
        db.session.commit()
        self.c = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.ctx.pop()

    # ---------------------------------------------------------- ayudas
    def entrar(self, usuario="admin", clave=CLAVE):
        return self.c.post("/login", data={"username": usuario, "password": clave})

    def crear_cliente(self, cedula="1.065.123.456", valor="1.000.000", interes="30", cuotas="20"):
        r = self.c.post("/admin/clientes/nuevo", data={
            "cedula": cedula, "nombres": "yoelvis", "apellidos": "yacub", "telefono": "3506160469",
            "barrio": "San Martín", "direccion": "Calle 35", "valor_inicial": valor,
            "porcentaje_interes": interes, "cantidad_cuotas": cuotas,
        }, follow_redirects=True)
        html = r.get_data(as_text=True)
        pin = re.search(r'<div class="pin"><strong>(\d{6})</strong>', html)
        cliente = Cliente.query.filter_by(cedula=re.sub(r"\D", "", cedula)).first()
        return cliente, (pin.group(1) if pin else None), html

    def cobrar(self, prestamo_id, valor):
        return self.c.post(f"/admin/prestamos/{prestamo_id}/pago", data={"valor_pagado": valor}, follow_redirects=True)


class FlujoCreditos(BaseCase):
    def test_cliente_unico_y_nuevo_credito_solo_al_pagar(self):
        self.entrar()
        cliente, pin, _ = self.crear_cliente()
        self.assertIsNotNone(cliente, "el cliente debió crearse (cédula normalizada sin puntos)")
        self.assertEqual(len(cliente.prestamos), 1)
        p = cliente.prestamos[0]
        self.assertEqual(int(p.valor_inicial), 1000000, "'1.000.000' debe leerse como un millón")
        self.assertEqual(int(p.total_pagar), 1300000)

        # Misma cédula: no se puede crear dos veces
        _, _, html = self.crear_cliente()
        self.assertIn("Ya existe un cliente con esa cédula", html)
        self.assertEqual(Cliente.query.count(), 1)

        # Debe dinero: el crédito nuevo está bloqueado
        r = self.c.post(f"/admin/prestamos/nuevo/{cliente.id}", data={"valor_inicial": "500.000", "porcentaje_interes": "20", "cantidad_cuotas": "10"}, follow_redirects=True)
        self.assertIn("No se puede crear un crédito nuevo", r.get_data(as_text=True))
        self.assertEqual(Prestamo.query.count(), 1)

        # Cobro mayor al saldo: rechazado
        r = self.cobrar(p.id, "2.000.000")
        self.assertIn("mayor que el saldo", r.get_data(as_text=True))

        # Pagar todo: se habilita el nuevo crédito
        self.cobrar(p.id, "65.000")
        r = self.cobrar(p.id, "1.235.000")
        self.assertIn("terminó de pagar", r.get_data(as_text=True))
        db.session.expire_all()
        self.assertTrue(db.session.get(Prestamo, p.id).esta_saldado)

        hoy = hoy_local()
        r = self.c.post(f"/admin/prestamos/nuevo/{cliente.id}", data={
            "valor_inicial": "500.000", "porcentaje_interes": "20", "cantidad_cuotas": "10", "fecha_prestamo": hoy.isoformat(),
        }, follow_redirects=True)
        html = r.get_data(as_text=True)
        self.assertEqual(Prestamo.query.count(), 2)
        self.assertIn(f"Crédito del {hoy.strftime('%d/%m/%Y')}", html, "la ficha debe mostrar la fecha del crédito nuevo")
        self.assertIn("Créditos anteriores", html)

    def test_no_se_borra_historial(self):
        self.entrar()
        cliente, _, _ = self.crear_cliente()
        r = self.c.post(f"/admin/clientes/{cliente.id}/eliminar", follow_redirects=True)
        self.assertIn("no se puede eliminar", r.get_data(as_text=True))
        self.assertEqual(Cliente.query.count(), 1)

    def test_eliminar_cobro_recalcula_saldos(self):
        self.entrar()
        cliente, _, _ = self.crear_cliente()
        p = cliente.prestamos[0]
        for _ in range(3):
            self.cobrar(p.id, "100.000")
        db.session.expire_all()
        p = db.session.get(Prestamo, p.id)
        intermedio = sorted(p.pagos, key=lambda x: x.id)[1]
        self.c.post(f"/admin/pagos/{intermedio.id}/eliminar")
        db.session.expire_all()
        p = db.session.get(Prestamo, p.id)
        saldos = sorted(int(x.saldo_restante) for x in p.pagos)
        self.assertEqual(saldos, [1100000, 1200000])


class PanelYReportes(BaseCase):
    def setUp(self):
        super().setUp()
        self.entrar()
        cliente, _, _ = self.crear_cliente()
        self.p = cliente.prestamos[0]
        for _ in range(4):
            self.cobrar(self.p.id, "65.000")  # 260.000 cobrados

    def test_panel_muestra_capital_y_no_dinero_recuperado(self):
        html = self.c.get("/admin/").get_data(as_text=True)
        # 1.000.000 - 260.000 x (1.000.000 / 1.300.000) = 800.000 de capital en la calle
        self.assertIn("$800.000", html)
        self.assertIn("$260.000", html)   # cobrado hoy
        self.assertIn("$60.000", html)    # ganancia del mes
        self.assertNotIn("Dinero recuperado", html)

    def test_reportes_por_dia_mes_anio(self):
        hoy = hoy_local()
        for url in (f"/admin/reportes/?tipo=dia&dia={hoy.isoformat()}",
                    f"/admin/reportes/?tipo=mes&mes={hoy.month}&anio={hoy.year}",
                    f"/admin/reportes/?tipo=anio&anio={hoy.year}"):
            html = self.c.get(url).get_data(as_text=True)
            self.assertIn("$260.000", html, url)
        html = self.c.get("/admin/reportes/?tipo=anio&anio=2001").get_data(as_text=True)
        self.assertIn("No hubo cobros en este período", html)
        # Valores raros en la URL no rompen la página
        self.assertEqual(self.c.get("/admin/reportes/?tipo=mes&mes=99&anio=xx").status_code, 200)

    def test_exportar(self):
        r = self.c.get("/admin/reportes/exportar/csv?tipo=anio&anio=" + str(hoy_local().year))
        self.assertEqual(r.status_code, 200)
        texto = r.get_data().decode("utf-8-sig")
        self.assertIn("Cobrado;260000", texto)
        r = self.c.get("/admin/reportes/exportar/pdf")
        self.assertTrue(r.get_data().startswith(b"%PDF"))


class Seguridad(BaseCase):
    def test_cabeceras(self):
        r = self.c.get("/login")
        self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual(r.headers["X-Frame-Options"], "DENY")

    def test_bloqueo_por_intentos(self):
        for _ in range(5):
            self.entrar("admin", "clave-equivocada")
        r = self.entrar("admin", CLAVE)  # aun con la clave correcta, espera
        self.assertEqual(r.status_code, 429)

    def test_redireccion_abierta(self):
        r = self.c.post("/login?next=https://sitio-malo.com", data={"username": "admin", "password": CLAVE})
        self.assertNotIn("sitio-malo", r.headers.get("Location", ""))

    def test_logout_por_get_no_cierra_sesion(self):
        self.entrar()
        self.c.get("/logout")
        self.assertEqual(self.c.get("/admin/").status_code, 200)
        self.c.post("/logout")
        self.assertEqual(self.c.get("/admin/").status_code, 302)

    def test_empleado_sin_reportes(self):
        self.entrar("cobrador")
        r = self.c.get("/admin/reportes/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/admin/clientes", r.headers["Location"])

    def test_portal_con_pin(self):
        self.entrar()
        cliente, pin, _ = self.crear_cliente()
        self.assertIsNotNone(pin, "al crear el cliente se debe mostrar su PIN")
        self.c.post("/logout")
        r = self.c.post("/portal/", data={"cedula": cliente.cedula, "pin": "000000"})
        self.assertIn("Cédula o PIN incorrectos", r.get_data(as_text=True))
        r = self.c.post("/portal/", data={"cedula": cliente.cedula, "pin": pin})
        self.assertIn("Te falta pagar", r.get_data(as_text=True))

    def test_cambiar_clave_cierra_sesiones(self):
        self.entrar()
        otro = self.app.test_client()
        otro.post("/login", data={"username": "admin", "password": CLAVE})
        self.c.post("/cuenta", data={"actual": CLAVE, "nueva": "OtraClave#99", "repetir": "OtraClave#99"})
        self.assertEqual(otro.get("/admin/").status_code, 302, "la otra sesión debió cerrarse")


if __name__ == "__main__":
    unittest.main()
