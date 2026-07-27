-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1:3307
-- Tiempo de generación: 27-07-2026 a las 06:11:43
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `prestamos_db`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `clientes`
--

CREATE TABLE `clientes` (
  `id` int(11) NOT NULL,
  `cedula` varchar(20) NOT NULL,
  `nombres` varchar(100) NOT NULL,
  `apellidos` varchar(100) NOT NULL,
  `direccion` varchar(200) DEFAULT NULL,
  `telefono` varchar(30) DEFAULT NULL,
  `barrio` varchar(100) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `clientes`
--

INSERT INTO `clientes` (`id`, `cedula`, `nombres`, `apellidos`, `direccion`, `telefono`, `barrio`, `created_at`) VALUES
(3, '23479212', 'yoelvis', 'yacub', 'calle 35 # 18e - 36', '3506160469', 'san martin', '2026-07-25 23:09:43'),
(5, '23479214', 'enmanuel', 'castillo', 'avenida fundacion', '3017855032', '1 mayo', '2026-07-25 23:17:13'),
(6, '23479215', 'jhon', 'quintero', 'calle 14 # 17a - 35', '3135464515', 'alfonzo lopez', '2026-07-25 23:25:15'),
(7, '23479216', 'enith', 'deluquez', 'calle 11a # 25 - 04', '3015990374', 'garupal', '2026-07-25 23:29:22'),
(8, '23479217', 'keiner', 'fuentes', 'calle 7 mocha', '3022139953', 'alto de pimienta', '2026-07-25 23:30:39'),
(9, '23479219', 'emiro', 'lopez', 'calle 21bis # 4f - 05', '3136948859', 'candelaria sur', '2026-07-25 23:32:35'),
(10, '23479222', 'larry', 'redondo', 'carrera 38 # 5f - 24', '3155797449', 'nevada', '2026-07-25 23:42:08'),
(11, '23479223', 'alvaro', 'ruiz', 'mz 17 casa 23', '3170708995', '450 años', '2026-07-25 23:44:16'),
(12, '23479224', 'ricardo', 'castillo', 'diagonal 18b # 25 - 16', '3161471855', 'fundadores', '2026-07-25 23:46:05'),
(13, '23479225', 'nelson', 'freyle', 'transversal 27 # 16b - 52', '3005984217', 'villa corelca', '2026-07-25 23:49:27'),
(14, '234792226', 'fabian', 'martinez', 'calle 21bis # 4c - 17', '3015854748', 'candelaria sur', '2026-07-25 23:52:05'),
(15, '23479226', 'yacer', 'gonzalez', 'carrera 48 # 5 - 06', '3116983396', 'nevada', '2026-07-25 23:53:34'),
(16, '23479227', 'jose', 'landazabal', 'carrera 27 # 7a - 95', '3242248450', 'villa concha', '2026-07-25 23:55:40'),
(17, '23479228', 'jose ricardo', 'rangel', 'mz 12 casa 12', '3147000989', 'villa mirian', '2026-07-25 23:57:05'),
(18, '23479230', 'karen', 'araque', '', '3117042051', 'fundadores', '2026-07-25 23:58:18'),
(19, '1066269491', 'doris', 'argote', 'diagonal 18d # 25a - 41', '3016199858', 'fundadores', '2026-07-26 00:00:21'),
(20, '32811042', 'damaris', 'mendoza', 'calle 12 # 10 - 03', '3042620439', '', '2026-07-26 00:02:27'),
(21, '1069468133', 'fernanda', 'villalba', 'calle 21 # 6a - 57', '3208823618', 'san jorge', '2026-07-26 00:07:51'),
(22, '24786625', 'javier', 'machado', 'mz casa', '3147866206', 'rosario norte 1', '2026-07-26 00:15:13');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `configuraciones`
--

CREATE TABLE `configuraciones` (
  `id` int(11) NOT NULL,
  `clave` varchar(80) NOT NULL,
  `valor` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `gastos`
--

CREATE TABLE `gastos` (
  `id` int(11) NOT NULL,
  `fecha` date NOT NULL,
  `categoria` varchar(80) NOT NULL,
  `descripcion` varchar(255) DEFAULT NULL,
  `monto` decimal(12,2) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `pagos`
--

CREATE TABLE `pagos` (
  `id` int(11) NOT NULL,
  `prestamo_id` int(11) NOT NULL,
  `fecha` date NOT NULL,
  `valor_pagado` decimal(12,2) NOT NULL,
  `saldo_restante` decimal(12,2) NOT NULL,
  `observacion` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `pagos`
--

INSERT INTO `pagos` (`id`, `prestamo_id`, `fecha`, `valor_pagado`, `saldo_restante`, `observacion`, `created_at`) VALUES
(4, 3, '2026-07-16', 20000.00, 1180000.00, '', '2026-07-25 23:10:00'),
(5, 3, '2026-07-17', 20000.00, 1160000.00, '', '2026-07-25 23:10:07'),
(6, 3, '2026-07-18', 20000.00, 1140000.00, '', '2026-07-25 23:10:13'),
(7, 3, '2026-07-20', 20000.00, 1120000.00, '', '2026-07-25 23:10:24'),
(8, 3, '2026-07-21', 20000.00, 1100000.00, '', '2026-07-25 23:10:36'),
(9, 3, '2026-07-22', 20000.00, 1080000.00, '', '2026-07-25 23:10:47'),
(10, 3, '2026-07-23', 20000.00, 1060000.00, '', '2026-07-25 23:10:53'),
(11, 3, '2026-07-25', 20000.00, 1040000.00, '', '2026-07-25 23:10:56'),
(12, 3, '2026-07-24', 20000.00, 1020000.00, '', '2026-07-25 23:11:02'),
(14, 5, '2026-07-17', 16000.00, 464000.00, '', '2026-07-25 23:17:24'),
(15, 5, '2026-07-18', 16000.00, 448000.00, '', '2026-07-25 23:17:33'),
(16, 5, '2026-07-20', 16000.00, 432000.00, '', '2026-07-25 23:17:43'),
(17, 5, '2026-07-21', 16000.00, 416000.00, '', '2026-07-25 23:17:52'),
(18, 5, '2026-07-22', 16000.00, 400000.00, '', '2026-07-25 23:18:00'),
(19, 5, '2026-07-23', 16000.00, 384000.00, '', '2026-07-25 23:18:08'),
(20, 5, '2026-07-25', 16000.00, 368000.00, '', '2026-07-25 23:18:17'),
(21, 6, '2026-07-17', 45000.00, 1755000.00, '', '2026-07-25 23:25:31'),
(22, 6, '2026-07-18', 45000.00, 1710000.00, '', '2026-07-25 23:25:43'),
(23, 6, '2026-07-21', 45000.00, 1665000.00, '', '2026-07-25 23:25:56'),
(24, 6, '2026-07-22', 45000.00, 1620000.00, '', '2026-07-25 23:26:02'),
(25, 6, '2026-07-23', 45000.00, 1575000.00, '', '2026-07-25 23:26:10'),
(26, 6, '2026-07-24', 45000.00, 1530000.00, '', '2026-07-25 23:26:17'),
(27, 6, '2026-07-25', 45000.00, 1485000.00, '', '2026-07-25 23:26:25'),
(28, 8, '2026-07-25', 30000.00, 90000.00, '', '2026-07-25 23:30:50'),
(29, 9, '2026-07-25', 60000.00, 300000.00, '', '2026-07-25 23:32:40'),
(30, 10, '2026-07-25', 110000.00, 0.00, '', '2026-07-25 23:42:13'),
(31, 11, '2026-07-25', 90000.00, 270000.00, '', '2026-07-25 23:44:23'),
(32, 12, '2026-07-21', 10000.00, 350000.00, '', '2026-07-25 23:46:17'),
(33, 12, '2026-07-22', 10000.00, 340000.00, '', '2026-07-25 23:46:25'),
(34, 12, '2026-07-23', 10000.00, 330000.00, '', '2026-07-25 23:46:35'),
(35, 12, '2026-07-24', 10000.00, 320000.00, '', '2026-07-25 23:46:44'),
(36, 12, '2026-07-25', 10000.00, 310000.00, '', '2026-07-25 23:46:48'),
(37, 13, '2026-07-21', 10000.00, 350000.00, '', '2026-07-25 23:49:37'),
(38, 13, '2026-07-22', 10000.00, 340000.00, '', '2026-07-25 23:49:44'),
(39, 13, '2026-07-23', 10000.00, 330000.00, '', '2026-07-25 23:49:51'),
(40, 13, '2026-07-24', 10000.00, 320000.00, '', '2026-07-25 23:49:58'),
(41, 13, '2026-07-25', 10000.00, 310000.00, '', '2026-07-25 23:50:03'),
(42, 14, '2026-07-25', 60000.00, 240000.00, '', '2026-07-25 23:52:09'),
(43, 15, '2026-07-22', 5000.00, 115000.00, '', '2026-07-25 23:53:48'),
(44, 15, '2026-07-23', 5000.00, 110000.00, '', '2026-07-25 23:53:57'),
(45, 15, '2026-07-24', 5000.00, 105000.00, '', '2026-07-25 23:54:04'),
(46, 15, '2026-07-25', 5000.00, 100000.00, '', '2026-07-25 23:54:11'),
(47, 22, '2026-07-26', 1100000.00, 0.00, '', '2026-07-26 00:15:18');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `prestamos`
--

CREATE TABLE `prestamos` (
  `id` int(11) NOT NULL,
  `cliente_id` int(11) NOT NULL,
  `fecha_prestamo` date NOT NULL,
  `valor_inicial` decimal(12,2) NOT NULL,
  `porcentaje_interes` decimal(5,2) NOT NULL,
  `total_pagar` decimal(12,2) NOT NULL,
  `cantidad_cuotas` int(11) NOT NULL,
  `valor_cuota` decimal(12,2) NOT NULL,
  `observaciones` text DEFAULT NULL,
  `estado` varchar(20) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `prestamos`
--

INSERT INTO `prestamos` (`id`, `cliente_id`, `fecha_prestamo`, `valor_inicial`, `porcentaje_interes`, `total_pagar`, `cantidad_cuotas`, `valor_cuota`, `observaciones`, `estado`, `created_at`) VALUES
(3, 3, '2026-07-15', 1000000.00, 20.00, 1200000.00, 60, 20000.00, '', 'activo', '2026-07-25 23:09:43'),
(5, 5, '2026-07-16', 400000.00, 20.00, 480000.00, 30, 16000.00, '', 'mora', '2026-07-25 23:17:13'),
(6, 6, '2026-07-16', 1500000.00, 20.00, 1800000.00, 40, 45000.00, '', 'activo', '2026-07-25 23:25:15'),
(7, 7, '2026-07-16', 200000.00, 10.00, 220000.00, 1, 220000.00, 'unico pago', 'activo', '2026-07-25 23:29:22'),
(8, 8, '2026-07-16', 100000.00, 20.00, 120000.00, 4, 30000.00, 'semanal', 'mora', '2026-07-25 23:30:39'),
(9, 9, '2026-07-17', 300000.00, 20.00, 360000.00, 6, 60000.00, 'semanal', 'mora', '2026-07-25 23:32:35'),
(10, 10, '2026-07-18', 100000.00, 10.00, 110000.00, 1, 110000.00, '', 'mora', '2026-07-25 23:42:08'),
(11, 11, '2026-07-18', 300000.00, 20.00, 360000.00, 4, 90000.00, '', 'mora', '2026-07-25 23:44:16'),
(12, 12, '2026-07-19', 300000.00, 20.00, 360000.00, 36, 10000.00, '', 'activo', '2026-07-25 23:46:05'),
(13, 13, '2026-07-20', 300000.00, 20.00, 360000.00, 36, 10000.00, '', 'activo', '2026-07-25 23:49:27'),
(14, 14, '2026-07-20', 250000.00, 20.00, 300000.00, 5, 60000.00, 'semanal', 'mora', '2026-07-25 23:52:05'),
(15, 15, '2026-07-21', 100000.00, 20.00, 120000.00, 24, 5000.00, '', 'activo', '2026-07-25 23:53:34'),
(16, 16, '2026-07-22', 1000000.00, 10.00, 1100000.00, 1, 1100000.00, '', 'activo', '2026-07-25 23:55:40'),
(17, 17, '2026-07-24', 200000.00, 20.00, 240000.00, 5, 48000.00, '', 'mora', '2026-07-25 23:57:05'),
(18, 18, '2026-07-24', 500000.00, 20.00, 600000.00, 2, 300000.00, 'quincenal', 'activo', '2026-07-25 23:58:18'),
(19, 19, '2026-07-25', 300000.00, 20.00, 360000.00, 2, 180000.00, 'quincenal', 'activo', '2026-07-26 00:00:21'),
(20, 20, '2026-07-25', 500000.00, 20.00, 600000.00, 40, 15000.00, '', 'activo', '2026-07-26 00:02:27'),
(21, 21, '2026-07-25', 200000.00, 20.00, 240000.00, 4, 60000.00, 'semanal', 'activo', '2026-07-26 00:07:51'),
(22, 22, '2026-07-15', 1000000.00, 10.00, 1100000.00, 1, 1100000.00, '', 'mora', '2026-07-26 00:15:13');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuarios`
--

CREATE TABLE `usuarios` (
  `id` int(11) NOT NULL,
  `username` varchar(80) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `nombre_completo` varchar(150) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `rol` varchar(20) NOT NULL DEFAULT 'admin'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `usuarios`
--

INSERT INTO `usuarios` (`id`, `username`, `password_hash`, `nombre_completo`, `created_at`, `rol`) VALUES
(1, 'admin', 'scrypt:32768:8:1$slrkrq07klRWquYe$f78d06849090bfd85d3b08045a2ee537bb774900b1573148f27cf4776d6375e9936a6e19dcc5e1a791cafca2514040f8021103783bdd943409924d2adf53fe3a', 'alexis chiquillo', '2026-07-25 09:38:45', 'admin'),
(2, 'trabajador', 'scrypt:32768:8:1$WHB4N6R7ItAA7ekF$2dc4f2b753079dc1d7a60c7950fdba11553a3d3476cc91796f132191da38782b2c35ec9da28a7eba5ae1230a3881c160faf825a7b05aabe547697f5c6c03ef4e', '', '2026-07-25 22:59:26', 'empleado');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `clientes`
--
ALTER TABLE `clientes`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_clientes_cedula` (`cedula`);

--
-- Indices de la tabla `configuraciones`
--
ALTER TABLE `configuraciones`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `clave` (`clave`);

--
-- Indices de la tabla `gastos`
--
ALTER TABLE `gastos`
  ADD PRIMARY KEY (`id`);

--
-- Indices de la tabla `pagos`
--
ALTER TABLE `pagos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `prestamo_id` (`prestamo_id`);

--
-- Indices de la tabla `prestamos`
--
ALTER TABLE `prestamos`
  ADD PRIMARY KEY (`id`),
  ADD KEY `cliente_id` (`cliente_id`);

--
-- Indices de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `clientes`
--
ALTER TABLE `clientes`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=23;

--
-- AUTO_INCREMENT de la tabla `configuraciones`
--
ALTER TABLE `configuraciones`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `gastos`
--
ALTER TABLE `gastos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `pagos`
--
ALTER TABLE `pagos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=49;

--
-- AUTO_INCREMENT de la tabla `prestamos`
--
ALTER TABLE `prestamos`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=23;

--
-- AUTO_INCREMENT de la tabla `usuarios`
--
ALTER TABLE `usuarios`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `pagos`
--
ALTER TABLE `pagos`
  ADD CONSTRAINT `pagos_ibfk_1` FOREIGN KEY (`prestamo_id`) REFERENCES `prestamos` (`id`);

--
-- Filtros para la tabla `prestamos`
--
ALTER TABLE `prestamos`
  ADD CONSTRAINT `prestamos_ibfk_1` FOREIGN KEY (`cliente_id`) REFERENCES `clientes` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
