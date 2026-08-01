# Sistema de Préstamos — Flask + MySQL

Sistema completo para administrar un negocio de préstamos personales
("gota a gota" / préstamos por cuotas): panel de administrador, portal
de consulta para clientes, dashboard con estadísticas y gráficos,
reportes exportables y control de mora.

## Tecnologías

- **Backend:** Python 3.10+, Flask, SQLAlchemy, Flask-Login, Flask-WTF (CSRF)
- **Base de datos:** MySQL 8+
- **Frontend:** HTML5, Bootstrap 5, Chart.js, JavaScript vanilla
- **Arquitectura:** MVC (modelos en `app/models.py`, vistas en `app/templates/`, controladores en `app/routes/`)

## Estructura del proyecto

```
prestamos_flask/
├── app/
│   ├── __init__.py          # Factory de la app, registro de blueprints
│   ├── cli.py                # Comandos: crear-admin, actualizar-mora
│   ├── models.py             # Usuario, Cliente, Prestamo, Pago, Configuracion
│   ├── routes/
│   │   ├── auth.py           # Login / logout del administrador
│   │   ├── admin.py          # Dashboard, CRUD clientes/préstamos, pagos
│   │   ├── portal.py         # Portal público del cliente (por cédula)
│   │   └── reports.py        # Reportes + exportación PDF/Excel
│   ├── templates/            # Vistas Jinja2 (Bootstrap 5)
│   └── static/css/style.css
├── config.py                 # Configuración (lee variables de entorno)
├── run.py                    # Punto de entrada
├── requirements.txt
├── schema.sql                # DDL de referencia (las tablas las crea SQLAlchemy)
├── .env.example
└── install.sh                # Instalación automática (Linux/Mac)
```

## Instalación

### Requisitos previos
- Python 3.10 o superior
- MySQL 8 corriendo (local o remoto) con un usuario que pueda crear bases de datos
- pip

### Pasos

```bash
# 1. Entrar a la carpeta del proyecto
cd prestamos_flask

# 2. Correr el instalador (crea venv, instala dependencias, crea la base y el admin)
bash install.sh
```

Si preferís hacerlo manualmente:

```bash
python3 -m venv venv
source venv/bin/activate          # En Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Editá .env con los datos reales de tu base MySQL

export FLASK_APP=run.py
python3 -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()"

flask crear-admin                 # Te pide usuario y contraseña
flask --app run.py run            # Levanta el servidor en http://localhost:5000
```

## Uso

- **Panel de administrador:** `http://localhost:5000/login`
  - Dashboard con tarjetas de estadísticas y gráficos
  - Clientes: alta, edición, baja, búsqueda
  - Registro de pagos (actualiza saldo, historial y estadísticas automáticamente)
  - Reportes filtrables por día / semana / mes / año / cliente, exportables a PDF y Excel

- **Portal del cliente:** `http://localhost:5000/portal`
  - El cliente ingresa únicamente su número de cédula
  - Ve solo su propia información: préstamo, cuotas, historial de pagos
  - No requiere contraseña ni puede modificar nada

## Mantenimiento

### Actualizar el estado de mora automáticamente

El estado de cada préstamo se recalcula al registrar un pago, pero si
un cliente deja de pagar sin que vos entres al sistema, el estado
puede quedar desactualizado hasta la próxima visita. Para mantenerlo
al día, programá este comando para que corra una vez por día (por
ejemplo con `cron`):

```bash
flask actualizar-mora
```

Ejemplo de entrada de cron (todos los días a las 6am):

```
0 6 * * * cd /ruta/al/proyecto && venv/bin/flask actualizar-mora
```

### Cambiar los días para considerar mora

Por defecto son 2 días sin pago. Se ajusta con la variable de entorno
`DIAS_PARA_MORA` en tu archivo `.env`.

## Instalación local en Windows con MySQL

Esta opción hace que el sistema corra **en tu propia computadora**, sin
depender de internet ni de ningún hosting. Los datos quedan guardados en
MySQL instalado en tu misma PC. Podés acceder desde el navegador de esa
computadora, y también desde tu celular si están conectados a la misma
red WiFi (ver el paso final).

### Paso 1 — Instalar Python

1. Andá a [python.org/downloads](https://www.python.org/downloads/) y
   descargá la última versión para Windows.
2. Al instalar, **marcá la casilla "Add Python to PATH"** antes de
   hacer clic en Install — es el paso que más gente se salta y después
   da error.

### Paso 2 — Instalar MySQL

1. Descargá el instalador desde
   [dev.mysql.com/downloads/installer](https://dev.mysql.com/downloads/installer/)
   (elegí "MySQL Installer for Windows").
2. Corré el instalador, elegí **"Server only"** (no hace falta todo el
   paquete completo) o **"Developer Default"** si querés también las
   herramientas visuales.
3. Durante la instalación te va a pedir que definas una **contraseña
   para el usuario root**. Anotala en un lugar seguro — la vas a
   necesitar en el paso 4.
4. Dejá que el instalador configure MySQL como servicio de Windows
   (así arranca solo cada vez que prendés la computadora).

### Paso 3 — Descomprimir el proyecto

Descomprimí el archivo `prestamos_flask.zip` en una carpeta fija de tu
computadora (por ejemplo, `C:\Prestamos\`). No la muevas después de
instalado.

### Paso 4 — Instalar y configurar (automático)

Dentro de la carpeta del proyecto, hacé **doble clic en
`instalar_windows.bat`**. Este script:

1. Verifica que Python esté instalado
2. Crea un entorno virtual e instala todas las dependencias
3. Crea el archivo `.env` y lo abre en el Bloc de notas para que
   completes `DB_PASSWORD` con la contraseña de MySQL que definiste
   en el paso 2 (guardalo con Ctrl+S y cerrá el Bloc de notas para
   que el instalador continúe)
4. Crea la base de datos y las tablas automáticamente
5. Te pide que definas tu usuario y contraseña de administrador del
   sistema (no confundir con el usuario de MySQL)

Si en el paso 4 te da un error de conexión a MySQL, lo más común es
que el servicio no esté corriendo — buscá "Servicios" en el menú de
Windows, buscá "MySQL80" (o similar) en la lista, y verificá que diga
"En ejecución".

### Paso 5 — Usar el sistema

Cada vez que quieras usar el sistema, hacé doble clic en
**`iniciar_windows.bat`**. Se abre una ventana negra que tenés que
dejar abierta mientras lo usás (no la cierres, minimizala si querés).

Abrí tu navegador en:
- **Panel administrador:** http://localhost:5000/login
- **Portal del cliente:** http://localhost:5000/portal

### Para usarlo también desde el celular (misma casa/local)

Si tu celular está conectado al mismo WiFi que la computadora:

1. En la computadora, abrí la consola (`cmd`) y escribí `ipconfig`.
   Buscá algo como "Dirección IPv4": `192.168.1.XX`.
2. Desde el navegador del celular, entrá a `http://192.168.1.XX:5000/login`
   (con la IP real de tu compu).
3. Esto solo funciona **mientras la computadora esté prendida y
   `iniciar_windows.bat` esté corriendo**, y **solo dentro de la misma
   red WiFi** — no anda desde la calle. Para eso sí necesitás un
   hosting real (ver la sección de PythonAnywhere más abajo).

### Hacer respaldos

Con MySQL local, tus datos están en tu computadora — si se rompe o
formateás la PC sin respaldo, se pierden. Te recomiendo exportar la
base cada tanto: abrí una consola dentro de la carpeta del proyecto y
corré:
```
mysqldump -u root -p prestamos_db > respaldo.sql
```
Te va a pedir la contraseña de MySQL y va a generar un archivo
`respaldo.sql` que podés copiar a un pendrive o subir a Google Drive.

## Despliegue gratis en PythonAnywhere (recomendado para empezar)

PythonAnywhere tiene un plan gratuito ideal para este proyecto: todo se hace
desde el navegador, sin instalar nada en tu computadora. Desde enero de 2026
el plan gratis no incluye MySQL, así que este proyecto usa **SQLite** por
defecto (un archivo de base de datos, sin servidor aparte) — funciona igual
de bien para la cantidad de clientes de un negocio de préstamos chico o
mediano, y no requiere ninguna configuración extra.

1. **Crear la cuenta:** entrá a [pythonanywhere.com](https://www.pythonanywhere.com),
   "Start running Python online in less than a minute", elegí el plan
   **Beginner (gratis)**. No pide tarjeta.

2. **Subir el proyecto:** en el dashboard, abrí la pestaña **Consoles** →
   **Bash**. Subí el archivo `prestamos_flask.zip` con el botón **Upload a
   file** de la pestaña **Files** (arriba de todo), y en la consola Bash
   corré:
   ```bash
   unzip prestamos_flask.zip
   cd prestamos_flask
   ```

3. **Crear el entorno virtual e instalar dependencias** (en la misma consola Bash):
   ```bash
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Crear las tablas y tu usuario administrador:**
   ```bash
   export FLASK_APP=run.py
   python3 -c "from app import create_app, db; app=create_app(); app.app_context().push(); db.create_all()"
   flask crear-admin
   ```
   (te va a pedir usuario y contraseña — elegilos ahí mismo)

5. **Crear la aplicación web:** pestaña **Web** → **Add a new web app** →
   Next → elegí **Manual configuration** (NO "Flask", porque ya tenemos
   el proyecto armado) → Python 3.10.

6. **Configurar el WSGI:** en la misma página **Web**, hacé clic en el
   link del archivo WSGI (algo como
   `/var/www/tuusuario_pythonanywhere_com_wsgi.py`), borrá todo su
   contenido y pegá esto (cambiando `tuusuario` por tu usuario real):
   ```python
   import sys
   path = '/home/tuusuario/prestamos_flask'
   if path not in sys.path:
       sys.path.append(path)

   from run import app as application
   ```

7. **Apuntar al entorno virtual:** en la sección **Virtualenv** de la
   página Web, escribí: `/home/tuusuario/prestamos_flask/venv`

8. Tocá el botón verde **Reload** arriba de la página Web.

Listo — tu sistema ya está en `https://tuusuario.pythonanywhere.com`.
El panel de administrador está en `/login` y el portal para tus clientes
en `/portal`. Ese link (`https://tuusuario.pythonanywhere.com/portal`) es
el que le mandás a cada cliente — todos entran ahí, cada uno ve solo lo
suyo con su cédula.

**Para que no se apague:** en el plan gratis, si no entrás a tu cuenta de
PythonAnywhere durante un mes, la aplicación se pausa. Con entrar una vez
por mes (aunque sea a mirar el dashboard) alcanza para mantenerla activa.

**Si más adelante crecés y querés MySQL real:** PythonAnywhere lo habilita
desde el plan pago (~US$10/mes). Ese día solo hay que definir las variables
de entorno `DB_USER`, `DB_HOST`, etc. en la pestaña Web — el proyecto ya
está preparado para usar MySQL automáticamente en cuanto esas variables
existan, sin tocar código.

## Despliegue en producción (VPS propio u otro hosting)

Este proyecto viene listo para correr con `gunicorn` detrás de un
proxy (nginx, Apache, o el que ofrezca tu hosting):

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "run:app"
```

Recomendaciones para producción:
- Cambiá `SECRET_KEY` por un valor largo y aleatorio.
- Usá HTTPS (Let's Encrypt es gratuito).
- No dejes `FLASK_DEBUG=1` en producción.
- Hacé backups periódicos de la base de datos MySQL.
- Considerá restringir el acceso a `/login` por IP si tu hosting lo permite.

## Seguridad implementada

- Contraseñas de administrador con hash (Werkzeug `generate_password_hash`, no se guardan en texto plano)
- Protección CSRF en formularios (Flask-WTF)
- Sesión de administrador con expiración por inactividad
- Consultas parametrizadas vía SQLAlchemy ORM (protección contra SQL Injection)
- El portal del cliente es de solo lectura: no expone ninguna ruta de escritura
- Validaciones de formulario en servidor (no solo en el navegador)

## Notas sobre el cálculo de ganancia

La ganancia de cada pago se calcula de forma proporcional: si un
préstamo tiene $50.000 de capital sobre un total a pagar de $65.000,
el 76,9% de cada pago se considera recuperación de capital y el
23,1% restante es ganancia. Esto hace que la "ganancia generada"
siempre refleje lo efectivamente cobrado, nunca lo prometido.
