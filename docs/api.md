# API privada local

Todas las respuestas son JSON. `/api/auth` y `/api/login` son los únicos endpoints de API que no requieren usuario autenticado. Las mutaciones requieren `X-CSRFToken`, obtenido desde `/api/auth`. Las cookies gestionan la sesión; no se guardan tokens de autenticación en localStorage.

- `GET /api/auth`: usuario actual o null y token CSRF.
- `POST /api/login`: usuario/contraseña. `POST /api/logout`: cierre. `POST /api/password`: contraseña actual y nueva.
- `GET /api/state`: caballos y sesiones compartidos. El prototipo carga el historial completo.
- `POST /api/horses`, `PUT /api/horses/<id>`: solo administrador.
- `POST /api/sessions`, `PUT /api/sessions/<id>`: registros; trabajador edita únicamente los suyos.
- `GET /api/users`, `POST /api/users`, `PUT /api/users/<id>`, `POST /api/users/<id>/reset-password`: solo administrador.
- `GET /api/audit`: últimas 200 operaciones, solo administrador.
- `GET /api/export`: copia deportiva versión 1, solo administrador.
- `POST /api/import/preview`: validar y contar una copia para una base deportiva vacía. `POST /api/import`: importar transaccionalmente. Ambos requieren administrador.

Caballos y sesiones conservan los nombres de campos del JSON de la demo. Se añaden `version`, `authorId`, `createdAt`, `updatedAt`, `trackCondition` e `intensity` cuando corresponde. El servidor determina autor y fechas de auditoría; calcula y comprueba los totales. `splits` contiene duraciones en milisegundos, no acumulados; la interfaz convierte los acumulados antes de enviar.

El guardado de caballos y sesiones requiere `Idempotency-Key` y una versión actual para editar. La respuesta devuelve el registro confirmado. Los conflictos responden 409 y, cuando se detectan antes de actualizar, incluyen `current`. Las colisiones de escritura detectadas durante la transacción pueden devolver un 409 sin `current`; la interfaz permite recargar el registro.

Sin acceso: 401. Falta de permisos: 403. Datos o CSRF inválidos: 400. Límite de login: 429. Base ocupada o problema de conexión: 503. No existen endpoints ordinarios para borrar caballos o historial. Los respaldos completos se gestionan mediante comandos locales, no URLs públicas.

## Modalidad de tiempos y copias versión 2
Los registros de sesiones admiten `timingMode`: `split`, `cumulative` o `final`. Se devuelve en creación, edición, estado y exportación. En las dos primeras modalidades, `splits` contiene duraciones enteras en milisegundos (también cuando el formulario muestra acumulados) y `total` su suma. Para `final`, `splits=[]` y `total` es el tiempo final positivo, o `null` para un borrador sin tiempo. No hay parciales ficticios. `segmentLength` queda como dato técnico positivo por compatibilidad, sin requerirse en el formulario final. Estados sin cronometraje se normalizan a `split` y mantienen sus validaciones existentes.

Estado/exportación devuelven versión 2. Importación y vista previa aceptan versiones 1 y 2; la ausencia de modalidad se normaliza a `split`. Los endpoints, permisos, CSRF, idempotencia y control de versiones por registro siguen aplicándose.
