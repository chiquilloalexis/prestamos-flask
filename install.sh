#!/usr/bin/env bash
# Mi Cartera - instalación en Linux / Mac.  Uso: bash install.sh
set -e
echo "== Mi Cartera: instalación =="

[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Se creó .env: edítalo con los datos de tu base de datos y vuelve a ejecutar este script."
  exit 0
fi

export FLASK_APP=run.py
flask actualizar-bd
read -r -p "¿Crear un usuario administrador ahora? (s/n): " r
[ "$r" = "s" ] && flask crear-admin
read -r -p "¿Generar PIN del portal para los clientes existentes? (s/n): " r
[ "$r" = "s" ] && flask generar-pins

echo
echo "Listo. Para iniciar:  source venv/bin/activate && gunicorn -b 0.0.0.0:5000 run:app"
