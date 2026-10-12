# Validación de la publicación

La versión de origen contaba con 38 pruebas backend y 24 JavaScript: validación de tiempos y copias, permisos, autenticación, versiones, idempotencia, respaldo/restauración, distribuciones, límites equivalentes y huecos en las series. La entrega genérica debe conservarlas.

La publicación incluye pruebas adicionales del generador estático: lista cerrada, exclusión de archivos privados, resolución de módulos y rutas bajo un subdirectorio. Los workflows ejecutan las pruebas antes de publicar la demo.

## Comprobaciones de entrega

- 12/10/2026: **41 tests Python aprobados** (38 backend y 3 del paquete estático) y **24 tests JavaScript aprobados** (9 dominio, 4 comparativas, 4 conservación de tiempos y 7 gráficas).
- Demo genérica local verificada bajo `/entrenamiento-equino/`, sin login. Se probó 38/37/36 → acumulados 38/75/111 → tiempo final 1:51, guardado, recarga y lectura del registro.
- Se exportó una copia JSON 2 y se recuperó mediante la interfaz; se mantuvo el registro de tiempo final. Se comprobaron totales, barras de dos sesiones equivalentes y tortas/tablas del período.
- Teclado: después de modalidad, Tab llega a distancia. Revisión de escritorio 1366×900 y móvil simulado solicitado de 375×812 (ancho efectivo de documento informado: 360 px), sin desbordamiento general y con ambas paletas.
- Las capturas nuevas de escritorio, comparativas y móvil oscuro usan exclusivamente la identidad genérica y datos ficticios. No se incluyeron capturas anteriores.
- El artefacto estático tiene diez archivos permitidos. Los tests comprueban exclusión de backend/datos privados, resolución de módulos relativos y rechazo de salidas contaminadas. Las sesiones, copias y secretos locales originales quedaron fuera del repositorio nuevo.

La comprobación pública de Pages se registra al finalizar el despliegue.

No se afirma ensayo en teléfonos físicos, Safari/iOS ni lectores de pantalla. Los tamaños móviles simulados no acreditan esa cobertura. La demo pública no prueba operación multiusuario online: el backend permanece local.
