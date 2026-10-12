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

## Publicación comprobada

- Repositorio público: [MartnMartnez14/entrenamiento-equino](https://github.com/MartnMartnez14/entrenamiento-equino), rama `main`, licencia MIT.
- [Pruebas y despliegue inicial](https://github.com/MartnMartnez14/entrenamiento-equino/actions/runs/38297211037): ambos jobs completados correctamente en GitHub Actions.
- [Demo real en HTTPS](https://martnmartnez14.github.io/entrenamiento-equino/) abierta y verificada el 12/10/2026: inicia sin login, presenta caballos genéricos, permite guardar 1500 m en 1:51, recargar, consultar el historial y ver ese total en evolución. Sin errores de JavaScript observados en esa comprobación.
- Los diez recursos de Pages se descargaron y compararon byte a byte con sus fuentes locales: todos coinciden. Las rutas de backend, base SQLite, adaptador API y acceso compartido devolvieron 404.
- Se auditaron los cincuenta archivos versionados: no contienen nombres institucionales del prototipo anterior, bases, secretos, respaldos o archivos de cuentas locales. El sitio publica exclusivamente el artefacto estático; ningún módulo de ese artefacto llama a la API compartida.

Estos resultados corresponden a la entrega comprobada, no garantizan disponibilidad permanente de GitHub ni funcionamiento en dispositivos todavía no ensayados.

No se afirma ensayo en teléfonos físicos, Safari/iOS ni lectores de pantalla. Los tamaños móviles simulados no acreditan esa cobertura. La demo pública no prueba operación multiusuario online: el backend permanece local.
