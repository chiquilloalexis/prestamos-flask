@echo off
chcp 65001 >nul
REM ============================================================
REM  Mi Cartera - Iniciar (uso diario). Deja esta ventana abierta.
REM ============================================================
call venv\Scripts\activate.bat

echo.
echo ============================================
echo  Mi Cartera esta funcionando
echo.
echo  En este computador:  http://localhost:5000
echo  Desde tu celular o tablet (misma red WiFi):
echo     busca tu IP con el comando "ipconfig" y entra a http://TU_IP:5000
echo.
echo  NO CIERRES ESTA VENTANA mientras uses el sistema.
echo ============================================
echo.

REM waitress es un servidor apto para uso real (el de "flask run" es solo para pruebas)
waitress-serve --host=0.0.0.0 --port=5000 run:app
pause
