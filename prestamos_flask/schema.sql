-- ============================================================
-- Sistema de Préstamos - Schema de base de datos MySQL
-- ============================================================
-- Este archivo es solo de referencia / respaldo manual.
-- En el uso normal, las tablas las crea SQLAlchemy automáticamente
-- con el comando: flask --app run.py shell -> db.create_all()
-- o corriendo install.sh, que ejecuta ese paso por vos.
-- ============================================================

CREATE DATABASE IF NOT EXISTS prestamos_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE prestamos_db;

-- ---------- usuarios ----------
CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  nombre_completo VARCHAR(150),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------- clientes ----------
CREATE TABLE IF NOT EXISTS clientes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cedula VARCHAR(20) NOT NULL UNIQUE,
  nombres VARCHAR(100) NOT NULL,
  apellidos VARCHAR(100) NOT NULL,
  direccion VARCHAR(200),
  telefono VARCHAR(30),
  barrio VARCHAR(100),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_cedula (cedula)
) ENGINE=InnoDB;

-- ---------- prestamos ----------
CREATE TABLE IF NOT EXISTS prestamos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cliente_id INT NOT NULL,
  fecha_prestamo DATE NOT NULL,
  valor_inicial DECIMAL(12,2) NOT NULL,
  porcentaje_interes DECIMAL(5,2) NOT NULL DEFAULT 0,
  total_pagar DECIMAL(12,2) NOT NULL,
  cantidad_cuotas INT NOT NULL,
  valor_cuota DECIMAL(12,2) NOT NULL,
  observaciones TEXT,
  estado ENUM('activo', 'mora', 'cancelado') NOT NULL DEFAULT 'activo',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
  INDEX idx_estado (estado)
) ENGINE=InnoDB;

-- ---------- pagos ----------
CREATE TABLE IF NOT EXISTS pagos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  prestamo_id INT NOT NULL,
  fecha DATE NOT NULL,
  valor_pagado DECIMAL(12,2) NOT NULL,
  saldo_restante DECIMAL(12,2) NOT NULL,
  observacion VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (prestamo_id) REFERENCES prestamos(id) ON DELETE CASCADE,
  INDEX idx_fecha (fecha)
) ENGINE=InnoDB;

-- ---------- configuraciones ----------
CREATE TABLE IF NOT EXISTS configuraciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  clave VARCHAR(80) NOT NULL UNIQUE,
  valor VARCHAR(255)
) ENGINE=InnoDB;

-- ---------- Datos de ejemplo (opcional) ----------
INSERT INTO clientes (cedula, nombres, apellidos, direccion, telefono, barrio) VALUES
  ('10345678', 'Marta', 'Gómez', 'Av. Siempreviva 742', '381 555-1234', 'Centro'),
  ('20987654', 'Rubén', 'Díaz', 'Belgrano 210', '381 555-5678', 'San Cayetano');

INSERT INTO prestamos (cliente_id, fecha_prestamo, valor_inicial, porcentaje_interes, total_pagar, cantidad_cuotas, valor_cuota, estado) VALUES
  (1, CURDATE(), 50000, 30, 65000, 20, 3250, 'activo'),
  (2, CURDATE(), 30000, 30, 39000, 20, 1950, 'activo');
