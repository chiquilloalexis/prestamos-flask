#!/bin/bash
# ============================================================
# Script de instalación - Sistema de Préstamos
# Uso: bash install.sh
# ============================================================
set -e

echo "== Sistema de Préstamos: instalación =="

# 1. Entorno virtual
if [ ! -d "venv" ]; then
  echo "Creando entorno virtual..."
  python3 -m venv venv
fi
source venv/bin/activate

# 2. Dependencias
echo "Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# 3. Archivo .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Se creó el archivo .env a partir de .env.example."
  echo "IMPORTANTE: editá .env con los datos reales de tu base MySQL antes de continuar."
  read -p "Presioná Enter cuando hayas editado .env para continuar..."
fi

export $(grep -v '^#' .env | xargs)

# 4. Crear base de datos si no existe
echo "Creando base de datos (si no existe)..."
mysql -u "$DB_USER" -p"$DB_PASSWORD" -h "$DB_HOST" -P "$DB_PORT" \
  -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" \
  || echo "No se pudo crear la base automáticamente. Creála manualmente y volvé a correr este script."

# 5. Crear tablas vía SQLAlchemy
echo "Creando tablas..."
export FLASK_APP=run.py
python3 -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Tablas creadas.')"

# 6. Crear usuario administrador
echo ""
echo "Ahora vas a crear tu usuario administrador."
flask crear-admin

echo ""
echo "== Instalación completa =="
echo "Para iniciar el servidor: source venv/bin/activate && flask --app run.py run"
echo "Portal del cliente: http://localhost:5000/portal"
echo "Panel de administrador: http://localhost:5000/login"
