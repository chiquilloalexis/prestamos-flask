# Cambios respecto a la versión anterior

## Lo que pediste

### Panel
- **"Dinero prestado"** ahora es el **capital que sigue en la calle**: el capital
  de los créditos activos que todavía no ha vuelto, **sin intereses**. Antes
  sumaba todo lo prestado en la historia, incluidos los créditos ya pagados.
- **"Dinero recuperado"** se eliminó.
- El "Resultado del mes" muestra la ganancia, los gastos y la ganancia neta.
  Se reinicia solo cada día 1.

### Clientes y créditos
- El cliente se crea **una sola vez** (la cédula no se puede repetir). El primer
  crédito se puede cargar al crearlo, o después.
- Mientras el cliente debe, el crédito nuevo aparece **bloqueado**, con un aviso
  de cuánto le falta. Apenas paga el último peso, en su ficha aparece el
  formulario **"Nuevo crédito"**. No hay que crear el cliente otra vez.
- La ficha muestra **"Crédito del dd/mm/aaaa"** en el crédito actual y en cada
  crédito anterior, con su capital, interés, cobros y ganancia.
- Ahora el cobrador también puede hacer créditos nuevos, igual que antes podía
  crear clientes con su primer crédito. La regla de "no presta si debe" vale
  para todos.

### Reportes
- Se filtran por **día, mes, año, rango de fechas o todo**, y por cliente.
- Tienen atajos: Hoy, Ayer, Últimos 7 días, Este mes, Mes pasado y Este año.
  Las flechas pasan al día, mes o año anterior o siguiente.
- Muestran:
  - Un gráfico de lo cobrado.
  - La lista de cobros y la de créditos otorgados en el período.
  - El estado actual de la cartera.
- La exportación a Excel (CSV con `;` para Excel en español) y a PDF incluye
  el detalle de cobros y créditos.

### Diseño
- Es un diseño nuevo: menú lateral en el computador, menú desplegable en el
  celular y la tablet.
- En el celular, las tablas se ven como filas compactas y no hay que moverse
  de lado.
- Los botones y los campos tienen tamaño para el dedo. Mientras escribes los
  pesos, se agregan los puntos de miles (1.000.000).
- No depende de internet: se quitaron Bootstrap, los iconos y Chart.js de CDN.
- El texto pasó de español rioplatense ("Iniciá") a español neutro.

## Seguridad (lo que estaba mal)

| Problema | Solución |
|---|---|
| Cualquiera que adivinara una cédula veía el saldo del cliente | El portal pide **cédula y PIN de 6 dígitos**. El PIN se guarda cifrado, se muestra una sola vez y se puede regenerar desde la ficha. Además, se limitan los intentos |
| Sin protección contra adivinar contraseñas | Bloqueo temporal tras 5 intentos fallidos por usuario (o 15 por IP) en 15 minutos. Mismo tiempo de respuesta exista o no el usuario |
| Redirección abierta con `?next=` | Solo se aceptan rutas internas del sitio |
| Cerrar sesión por enlace (GET) | Ahora se cierra con un botón protegido (POST con token) |
| Clave secreta por defecto conocida | Si no defines `SECRET_KEY`, se genera una aleatoria y se guarda en `instance/` |
| Contraseñas débiles (por ejemplo "123456") | Mínimo 8 caracteres, que no sean solo números ni de las más comunes |
| Cambiar la contraseña no cerraba otras sesiones | Ahora sí las cierra |
| Borrar un cliente borraba todo su historial de dinero | No se puede borrar si tiene créditos: se **archiva**. Su historial se conserva y se puede restaurar |
| Sin registro de acciones | Nueva sección **Actividad**: quién creó, cobró o eliminó qué, y cuándo |
| Páginas expuestas a scripts externos e incrustación | Cabeceras CSP, X-Frame-Options, nosniff y Referrer-Policy. Los datos no quedan en la caché del navegador |
| Excel podía ejecutar fórmulas escritas en un nombre | Las celdas que empiezan con `= + - @` se neutralizan al exportar |

## Errores corregidos

- Escribir **"50.000"** se interpretaba como cincuenta pesos. Ahora es cincuenta mil.
- Una cuota o fecha mal escrita daba **error 500**. Ahora sale un mensaje claro.
- Se podía **cobrar más que el saldo**, con fecha futura o anterior al crédito.
  Ahora no se puede.
- Un doble toque en el celular podía registrar el **mismo cobro dos veces**.
  Ahora no.
- Al eliminar un cobro intermedio, los saldos del historial quedaban mal. Ahora
  se recalculan.
- El crédito "actual" se tomaba sin un orden garantizado. Ahora se ordena por
  fecha.
- "Hoy" dependía de la hora del servidor (en un hosting el día cambiaba a las
  7 p. m.). Ahora usa la hora de Colombia.
- El panel y los reportes cargaban todo en memoria. Ahora suman en la base de
  datos, así que siguen rápidos con miles de cobros.
- Los créditos se calculan en pesos enteros, para que el saldo siempre pueda
  llegar a $0.
- Una contraseña de MySQL con `@` o `#` rompía la conexión. Ahora no.
- El README hablaba de un comando `actualizar-mora` que no existía. Se quitó
  la referencia.

## Archivos que no se incluyen (a propósito)

- La carpeta duplicada `prestamos_flask/`, que tenía una versión vieja del código.
- `prestamos_db.sql`, que es un **respaldo con datos reales de tus clientes**
  (cédulas, teléfonos, direcciones) y contraseñas cifradas. Si ese repositorio
  está en GitHub, bórralo de ahí y cambia las contraseñas de esos usuarios.
- `migrar_datos.py`, que creaba un administrador con la clave `123456`.
