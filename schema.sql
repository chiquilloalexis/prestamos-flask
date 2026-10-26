-- ============================================================
-- Mi Cartera - Esquema de referencia (MySQL / MariaDB)
-- ============================================================
-- NO hace falta ejecutar este archivo: la aplicación crea las tablas y
-- agrega las columnas nuevas sola al arrancar (o con: flask actualizar-bd),
-- sin borrar los datos que ya tengas. Queda como documentación.
-- ============================================================

CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  nombre_completo VARCHAR(150),
  rol VARCHAR(20) NOT NULL DEFAULT 'admin',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS clientes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cedula VARCHAR(20) NOT NULL UNIQUE,
  nombres VARCHAR(100) NOT NULL,
  apellidos VARCHAR(100) NOT NULL,
  direccion VARCHAR(200),
  telefono VARCHAR(30),
  barrio VARCHAR(100),
  archivado TINYINT(1) NOT NULL DEFAULT 0,          -- NUEVO: ocultar sin borrar historial
  portal_pin_hash VARCHAR(255) NULL,                -- NUEVO: PIN del portal (cifrado)
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_clientes_archivado (archivado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS prestamos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cliente_id INT NOT NULL,
  fecha_prestamo DATE NOT NULL,
  valor_inicial DECIMAL(12,2) NOT NULL,     -- capital
  porcentaje_interes DECIMAL(5,2) NOT NULL DEFAULT 0,
  total_pagar DECIMAL(12,2) NOT NULL,       -- capital + interés
  cantidad_cuotas INT NOT NULL,
  valor_cuota DECIMAL(12,2) NOT NULL,
  observaciones TEXT,
  estado VARCHAR(20) NOT NULL DEFAULT 'activo',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (cliente_id) REFERENCES clientes(id),   -- sin borrado en cascada
  INDEX ix_prestamos_fecha_prestamo (fecha_prestamo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pagos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  prestamo_id INT NOT NULL,
  fecha DATE NOT NULL,
  valor_pagado DECIMAL(12,2) NOT NULL,
  saldo_restante DECIMAL(12,2) NOT NULL,
  observacion VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (prestamo_id) REFERENCES prestamos(id),
  INDEX ix_pagos_fecha (fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS gastos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  fecha DATE NOT NULL,
  categoria VARCHAR(80) NOT NULL,
  descripcion VARCHAR(255),
  monto DECIMAL(12,2) NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_gastos_fecha (fecha)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS configuraciones (
  id INT AUTO_INCREMENT PRIMARY KEY,
  clave VARCHAR(80) NOT NULL UNIQUE,
  valor VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- NUEVA: bitácora de quién hizo qué
CREATE TABLE IF NOT EXISTS auditoria (
  id INT AUTO_INCREMENT PRIMARY KEY,
  creado DATETIME NOT NULL,
  usuario_id INT,
  usuario VARCHAR(80),
  accion VARCHAR(40) NOT NULL,
  detalle VARCHAR(500),
  ip VARCHAR(45),
  INDEX ix_auditoria_creado (creado),
  INDEX ix_auditoria_accion (accion)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- NUEVA: intentos fallidos de acceso (bloqueo temporal anti-adivinanzas)
CREATE TABLE IF NOT EXISTS intentos_acceso (
  id INT AUTO_INCREMENT PRIMARY KEY,
  tipo VARCHAR(20) NOT NULL,
  clave VARCHAR(120) NOT NULL,
  creado DATETIME NOT NULL,
  INDEX ix_intentos_tipo_clave_creado (tipo, clave, creado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
