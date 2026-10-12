# Guía rápida

La [demo pública](https://martnmartnez14.github.io/entrenamiento-equino/) no pide usuario ni contraseña. Utiliza datos ficticios y guarda solamente en tu navegador.

## Registrar

El formulario tiene tres bloques: **Datos del trabajo**, **Distancia y tiempos** y **Observaciones**. Los campos con asterisco son obligatorios cuando están habilitados. El responsable puede ser distinto de la persona que registra.

| Estado | Qué representa |
|---|---|
| Completado | Trabajo realizado con todos sus tiempos positivos |
| Borrador | Registro pendiente; permite tiempos incompletos y no participa en estadísticas deportivas |
| Sin cronometraje | Trabajo realizado que cuenta en distancia y frecuencia, sin inventar tiempos |
| Descanso | Descanso registrado, sin distancia ni tiempos |
| Cancelado | Trabajo cancelado, sin distancia ni tiempos |

**Por tramo:** 38, 37 y 36 segundos suman 1:51. **Acumulados:** 38, 75 y 111 segundos generan esos mismos parciales. **Solo tiempo final:** ingresa distancia y 1:51 o 111 segundos, sin parciales.

Cambiar modalidad o distancia solicita confirmación cuando afecta a tiempos ingresados. Conservar tiempos cancela el cambio. Volver de tiempo final a parciales mantiene el total como referencia, pero pide introducir los parciales: no los reparte automáticamente.

Pulsa Guardar y espera la confirmación. Un campo inválido recibe el foco. Si hay un error, el formulario conserva lo escrito para corregir o reintentar.

## Consultar y comparar

Historial permite buscar por caballo, fechas, distancia y trabajo. Evolución muestra totales de la misma distancia y separa tipos de trabajo. Selecciona de dos a cuatro sesiones equivalentes para comparar parciales; los registros de solo tiempo final no pueden participar en esa comparación.

Las tortas usan solamente caballo y Desde/Hasta. Tipos de trabajo cuenta completados y sin cronometraje; Estados registrados incluye también borradores, descansos y cancelados. El borrador aparece como registro pendiente. Los porcentajes se redondean a un decimal.

Las tablas muestran los valores de cada gráfico. Una línea que sube es verde y una que baja roja; indican aumento o disminución del tiempo, sin valorar rendimiento. Los tiempos ausentes no son cero. El resumen semanal diferencia registros de días sin registro.

## Conservar una copia

Exportar copia descarga un JSON. Importar reemplaza los datos locales después de validar y confirmar. La copia no está cifrada. Borrar los datos del navegador puede eliminar el historial: utiliza la demo pública con información ficticia.

## Si usas el servidor local

El administrador crea las cuentas; no hay registro público ni contraseña predeterminada. Ambos roles consultan y registran. El trabajador corrige los propios registros sin límite de tiempo; el administrador puede corregir cualquiera y gestionar caballos y cuentas. **Ver registro** indica consulta de un trabajo ajeno; **Editar registro** indica permiso de corrección.

El autor se obtiene de la cuenta autenticada y el responsable del trabajo se introduce por separado. Las correcciones dejan auditoría. Los comandos de backup del servidor conservan cuentas y auditoría; el JSON deportivo no.
