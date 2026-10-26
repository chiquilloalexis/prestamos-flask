# Mi Cartera: sistema de préstamos (Flask)

Sistema para administrar un negocio de préstamos por cuotas: clientes, créditos,
cobros, gastos, reportes por día, mes o año, y un portal donde cada cliente
consulta su saldo con su cédula y un PIN. Funciona en celular, tablet y computador.

## Qué cambió en esta versión

Consulta **CAMBIOS.md** para ver la lista completa. Lo más importante:

- **Clientes:** el cliente se crea una sola vez. El crédito nuevo se habilita
  solo cuando termina de pagar el anterior. La ficha muestra la fecha de cada
  crédito y el historial de los anteriores.
- **Panel:** "Dinero prestado" muestra solo el capital que sigue en la calle
  (sin intereses). Se quitó "Dinero recuperado".
- **Reportes:** se filtran por día, mes, año, rango de fechas o cliente, con
  flechas para pasar al período anterior o siguiente. Se exportan a Excel y PDF.
- **Diseño:** es nuevo, se adapta a cualquier pantalla y no depende de internet
  (no usa CDN).
- **Seguridad:**
  - Bloquea temporalmente a quien intente adivinar contraseñas o PIN.
  - El portal pide un PIN, además de la cédula.
  - La clave secreta es aleatoria.
  - Las cabeceras de seguridad están activas.
  - Hay una bitácora de actividad.
  - Ya no se puede borrar el historial de dinero de un cliente.

## Instalación en Windows (XAMPP / MySQL)

1. Instala Python 3.10 o superior desde python.org y marca **"Add Python to PATH"**.
2. Enciende MySQL en XAMPP. La base de datos debe existir (por ejemplo `prestamos_db`).
3. Haz doble clic en **`instalar_windows.bat`** y sigue los pasos. Ahí completas el
   archivo `.env`, creas tu usuario administrador y generas los PIN de tus clientes.
4. Para usarlo cada día, haz doble clic en **`iniciar_windows.bat`**.

**Si ya usabas la versión anterior:** apunta el `.env` a la misma base de datos.
El sistema agrega solo las columnas y tablas nuevas, **sin borrar nada**. Antes,
haz un respaldo desde phpMyAdmin (pestaña Exportar) por precaución.

## Instalación en Linux / Mac

```bash
bash install.sh
source venv/bin/activate
gunicorn -b 0.0.0.0:5000 run:app
```

## En un hosting (Render u otro)

- Define estas variables de entorno: `SECRET_KEY` (una cadena larga y aleatoria),
  `DATABASE_URL`, `COOKIE_SECURE=1` y `TRUST_PROXY=1`.
- Comando de inicio: `gunicorn run:app`.
- Sin `SECRET_KEY`, la clave se genera en el disco del servidor. Si el hosting
  borra ese disco en cada despliegue, todos tendrán que volver a iniciar sesión.

## Comandos útiles

| Comando | Para qué sirve |
|---|---|
| `flask crear-admin` | Crear un administrador |
| `flask crear-empleado` | Crear un cobrador (clientes, créditos y cobros) |
| `flask cambiar-clave` | Cambiar una contraseña olvidada |
| `flask generar-pins` | Crear el PIN del portal a los clientes que no tienen; guarda la lista en `pins_clientes.csv` (entrégalos y borra el archivo) |
| `flask actualizar-bd` | Agregar a la base las columnas e índices nuevos (seguro de repetir) |

Ejecútalos con el entorno virtual activo (`venv\Scripts\activate` en Windows)
y con `FLASK_APP=run.py`.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas usan una base de datos temporal y no tocan tus datos. Recorren el flujo
completo:

- Crear un cliente y no poder crearlo dos veces.
- Ver bloqueado el crédito nuevo mientras debe, y habilitado al pagar.
- Comprobar las cifras del panel y los reportes por día, mes y año.
- Exportar a Excel y PDF.
- Verificar el bloqueo por intentos y el portal con PIN.

## Roles

| | Administrador | Empleado |
|---|---|---|
| Ver y crear clientes, registrar cobros | Sí | Sí |
| Hacer créditos nuevos (solo si el cliente no debe) | Sí | Sí |
| Panel, reportes, gastos, usuarios, actividad | Sí | No |
| Editar, archivar, eliminar cobros | Sí | No |

## Estructura

```
app/
  __init__.py      Fábrica de la app, cabeceras de seguridad, errores
  models.py        Usuario, Cliente, Prestamo, Pago, Gasto, Auditoria, IntentoAcceso
  stats.py         Sumas y conteos hechos en la base de datos (rápido con muchos datos)
  security.py      Bloqueo por intentos, bitácora, PIN del portal
  migrations.py    Agrega columnas e índices nuevos sin borrar datos
  utils.py         Pesos, fechas, validaciones (funciones puras)
  periodos.py      Día / mes / año / rango para reportes
  routes/          auth, admin (clientes, créditos, cobros), reports, gastos, usuarios, portal
  templates/       Pantallas
  static/          css/style.css, js/app.js, js/charts.js (sin librerías externas)
tests/             Pruebas automáticas
```
