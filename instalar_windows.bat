@echo off
REM ============================================================
REM Sistema de Prestamos - Instalacion para Windows (local + MySQL)
REM Doble clic para ejecutar, o correrlo desde la consola (cmd).
REM ============================================================

echo == Sistema de Prestamos: instalacion local (Windows) ==
echo.

REM 1. Verificar que Python este instalado
where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: no se encontro Python en tu computadora.
    echo Instalalo desde https://www.python.org/downloads/ 
    echo IMPORTANTE: al instalar, marca la casilla "Add Python to PATH".
    pause
    exit /b 1
)

REM 2. Crear entorno virtual
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate.bat

REM 3. Instalar dependencias
echo Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM 4. Archivo .env
if not exist ".env" (
    copy .env.example .env
    echo.
    echo Se creo el archivo .env a partir de .env.example.
    echo IMPORTANTE: abrilo con el Bloc de notas y completa DB_PASSWORD
    echo con la contrasena que le pusiste a MySQL al instalarlo.
    echo.
    notepad .env
    echo Presiona una tecla cuando hayas guardado el archivo .env...
    pause >nul
)

REM 5. Crear la base de datos en MySQL (si no existe)
echo Creando base de datos en MySQL...
for /f "tokens=2 delims==" %%a in ('findstr "DB_USER" .env') do set DB_USER=%%a
for /f "tokens=2 delims==" %%a in ('findstr "DB_PASSWORD" .env') do set DB_PASSWORD=%%a
for /f "tokens=2 delims==" %%a in ('findstr "DB_NAME" .env') do set DB_NAME=%%a
mysql -u %DB_USER% -p%DB_PASSWORD% -e "CREATE DATABASE IF NOT EXISTS %DB_NAME% CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if errorlevel 1 (
    echo.
    echo ERROR: no se pudo conectar a MySQL o crear la base de datos.
    echo Puede ser alguna de estas causas:
    echo  1^) El servicio de MySQL no esta corriendo: busca "Servicios" en el
    echo     menu de Windows y confirma que MySQL80 diga "En ejecucion".
    echo  2^) La contrasena en el archivo .env no coincide con la que le
    echo     pusiste a MySQL al instalarlo.
    echo  3^) El comando "mysql" no esta reconocido: puede que el instalador
    echo     de MySQL no lo haya agregado al PATH. Abri "MySQL Command Line
    echo     Client" desde el menu de Windows para verificar que MySQL
    echo     funciona, y si el problema persiste avisale a Claude.
    pause
    exit /b 1
)

REM 6. Crear las tablas
echo Creando tablas...
set FLASK_APP=run.py
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Tablas creadas.')"

REM 7. Crear usuario administrador
echo.
echo Ahora vas a crear tu usuario administrador.
flask crear-admin

echo.
echo == Instalacion completa ==
echo Para iniciar el sistema la proxima vez, hace doble clic en iniciar_windows.bat
echo.
pause
