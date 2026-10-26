@echo off
chcp 65001 >nul
REM ============================================================
REM  Mi Cartera - Instalacion en Windows (una sola vez)
REM  Doble clic para ejecutar.
REM ============================================================
echo == Mi Cartera: instalacion ==
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: no se encontro Python. Instalalo desde https://www.python.org/downloads/
    echo IMPORTANTE: marca la casilla "Add Python to PATH" al instalar.
    pause
    exit /b 1
)

if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate.bat

echo Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR instalando dependencias. Revisa tu conexion a internet.
    pause
    exit /b 1
)

if not exist ".env" (
    copy .env.example .env >nul
    echo.
    echo Se creo el archivo .env. Se abrira en el Bloc de notas:
    echo completa DB_PASSWORD con la contrasena de tu MySQL ^(en XAMPP suele estar vacia^).
    notepad .env
)

echo.
echo Preparando la base de datos (crea tablas nuevas y agrega columnas sin borrar datos)...
set FLASK_APP=run.py
flask actualizar-bd
if errorlevel 1 (
    echo.
    echo ERROR: no se pudo conectar a la base de datos.
    echo  - Revisa que MySQL / XAMPP este encendido.
    echo  - Revisa usuario, contrasena, puerto y nombre de la base en el archivo .env
    echo  - La base de datos debe existir (creala en phpMyAdmin si hace falta).
    pause
    exit /b 1
)

echo.
set /p CREAR=Quieres crear un usuario administrador ahora? (s/n):
if /i "%CREAR%"=="s" flask crear-admin

echo.
set /p PINS=Generar PIN del portal para los clientes que ya tienes? (s/n):
if /i "%PINS%"=="s" flask generar-pins

echo.
echo == Instalacion completa ==
echo Para usar el sistema, haz doble clic en iniciar_windows.bat
pause
