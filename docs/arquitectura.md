# Arquitectura y ampliación futura

## Organización

`js/domain.js` valida tiempos, distancias y copias; `js/register-form.js` conserva tiempos al cambiar configuración; `js/comparisons.js` y `js/charts.js` preparan estadísticas y gráficas. La demo utiliza `js/storage.js` e IndexedDB. La versión compartida utiliza `js/api.js` para operaciones individuales con Flask, conservando el autor desde la sesión autenticada.

El backend separa modelos SQLAlchemy, validación de dominio, API y respaldos. Alembic reproduce el esquema; los tiempos son milisegundos enteros y los parciales duraciones normalizadas. JSON 1/2 es compatible. La modalidad final guarda total y una lista vacía de parciales.

## Publicación estática

El script `scripts/build_site.py` copia únicamente la demo, sus módulos, estilos y Chart.js en `_site/`. La demo pasa a llamarse `index.html` dentro del artefacto. Rutas relativas permiten alojarla bajo `/entrenamiento-equino/`. El workflow de Pages prueba backend/frontend y publica solo ese artefacto. No hay llamadas a `/api`, usuarios ni base central en la demo.

## Servidor local

Instalar dependencias, ejecutar migraciones, crear el primer administrador mediante entrada segura y cargar ejemplos de forma explícita, como describe el README. SQLite se crea en `instance/`; la carpeta queda fuera de los archivos públicos y de Git. El servidor incluido escucha solo en localhost. Cambiar `DATABASE_URL` admite otra ubicación SQLite; otros motores requieren controladores, pruebas y un plan de migración antes de afirmar compatibilidad operativa.

## Qué requeriría un servidor online

- Seleccionar hosting que ejecute Python mediante WSGI y disponer HTTPS real.
- Configurar `ENTRENAMIENTO_EQUINO_ENV=production`, una `SECRET_KEY` privada de al menos 32 caracteres y `DATABASE_URL`; mantener cookies Secure, HttpOnly y SameSite. No publicar secretos ni habilitar debug.
- Definir proxy y encabezados de confianza según el proveedor, almacenamiento persistente, límites de capacidad y actualización de dependencias.
- Ejecutar migraciones y crear cuentas individuales; nunca reutilizar contraseñas de tests como cuentas reales.
- Planificar copias completas fuera del servidor, cifrado/retención y ensayos de restauración. Para otro motor, sustituir los comandos SQLite por las herramientas de ese motor.
- Probar permisos, CSRF, expiración, rate limiting, idempotencia, conflictos entre ediciones y recuperación de conexión en el entorno elegido.

No se ha desplegado ni contratado ese servidor. El código usa el historial completo; convendría paginarlo antes de crecer. No incluye política automática de retención de auditoría ni copias externas programadas.

## Ejemplos y límites

Los caballos y registros distribuidos son ficticios. No hay vínculo con una institución real. Los gráficos describen registros y no constituyen interpretación clínica o prescripción de entrenamiento. La arquitectura puede ampliarse, pero este repositorio no tiene desarrollo activo comprometido.
