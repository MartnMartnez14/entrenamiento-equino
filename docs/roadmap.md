# Roadmap

**Estado: prototipo cerrado como aprendizaje, disponible para ampliaciones.** No hay desarrollo activo ni fechas comprometidas. Las propuestas siguientes describen posibilidades, no funciones disponibles.

## Disponible

Caballos e historial; tiempos por tramo, acumulados y solo tiempo final; distancias variables; cinco estados; filtros; evolución de sesiones comparables; barras de parciales y resumen semanal; tortas del período con tablas; temas y presentación adaptable; copias JSON 1/2 compatibles. Demo independiente con IndexedDB y servidor local con Flask, cuentas, permisos, auditoría, migraciones y comandos de respaldo/restauración SQLite.

## Posibles ampliaciones, de menor a mayor complejidad

1. **Ensayos de uso y dispositivos.** Probar con personas con distintas capacidades digitales; revisar textos y recorridos. Ensayar teléfonos físicos, orientación, tacto, gráficas, leyendas, tablas, teclado, Safari/iOS y lectores de pantalla. Los tamaños móviles simulados no reemplazan esos ensayos.
2. **Ajustes visuales y filtros.** Afinar legibilidad, presentación y selección de períodos a partir de observaciones reales.
3. **Comparación entre caballos.** Elegir ejemplares y períodos, distancias y trabajos equivalentes; mostrar pista/intensidad y exigir límites iguales para parciales. Mantener las diferencias descriptivas, sin recomendaciones de carga.
4. **Agenda y cronómetro.** Separar trabajo planificado del realizado; prever estados y operación con interrupciones antes de incorporarlos al registro.
5. **Servidor online.** Evaluar hosting, WSGI, HTTPS, configuración de proxy, base central, límites de uso, actualizaciones y política de copias externas. Elegir proveedor y presupuesto antes de contratar. Pages seguirá siendo una demo estática sin backend.
6. **Fotos y después videos.** Adjuntar evidencia visual a caballos y entrenamientos desde PC o celular; posteriormente capturar y guardar desde la cámara de la aplicación. Definir permisos, formatos, tamaños, duración, compresión, almacenamiento privado, retención y respaldo. Evaluar costos de almacenamiento, transferencia/reproducción y procesamiento. Probar cámara, conexiones interrumpidas, progreso, reintentos sin duplicados y acceso autorizado.

«En tiempo real» significa capturar y guardar desde el celular; no implica transmisión en vivo. Los adjuntos aportarían contexto sin alterar cálculos. El análisis automático de multimedia y los trabajos definidos exclusivamente por duración sin distancia quedan fuera del alcance inicial.
