@echo off
REM ============================================================
REM Sistema de Prestamos - Iniciar (uso diario)
REM Doble clic para levantar el servidor. Dejalo abierto mientras
REM uses el sistema; para cerrarlo, cerra esta ventana.
REM ============================================================

call venv\Scripts\activate.bat
set FLASK_APP=run.py

echo.
echo ============================================
echo  Sistema de Prestamos corriendo
echo.
echo  Panel administrador: http://localhost:5000/login
echo  Portal del cliente:  http://localhost:5000/portal
echo.
echo  Para usarlo desde tu celular (misma red WiFi),
echo  fijate tu IP local con el comando "ipconfig"
echo  y entra a http://TU_IP:5000/portal
echo.
echo  NO CIERRES ESTA VENTANA mientras uses el sistema.
echo ============================================
echo.

flask run --host=0.0.0.0 --port=5000
pause
