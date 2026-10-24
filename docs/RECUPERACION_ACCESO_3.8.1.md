# Atlantic Gym 3.8.1: recuperación del acceso

La restauración de una sesión guardada podía fallar antes de abrir el formulario.
Reintentar restauraba la misma sesión y Cancelar devolvía `None` al inicio,
cerrando la aplicación. Ahora cualquier fallo recuperable vuelve al formulario
real de acceso. El correo permanece, la contraseña se pide de nuevo y el error
aparece dentro del formulario. Cerrar ese formulario cancela el inicio de forma
explícita. Administración y Recepción usan la misma implementación.

Ante un rechazo concreto de PostgREST `PGRST301`/`PGRST303` con
`JWT issued at future`, se espera 1, 2 y 3 segundos con el mismo token antes de
mostrar el error. No se renueva repetidamente un token recién emitido. El
servidor siempre valida la sesión; no se modifica el reloj ni la validación JWT.
Un rechazo por caducidad conserva la renovación única existente. Una respuesta
perdida, un timeout, un error de red o un 401 genérico nunca repiten escrituras.

No requiere migraciones de base de datos, cambios de licencia ni revocación de
sesiones. Se conservan los identificadores de instalación y el almacén DPAPI.
Los problemas persistentes del reloj del proveedor requieren revisión del
servicio; esta corrección evita el bloqueo de la interfaz y limita la espera.

## Verificación

- `tools.test_login_recovery`: sesión guardada fallida, contraseña incorrecta,
  reintento con credenciales nuevas, Recepción y cierre explícito del formulario.
- `tools.test_session_manager` y `tools.test_session_sdk`: rechazo temporal con
  el SDK real sobre transporte simulado, espera limitada, sesión conservada,
  renovación única y ausencia de repetición ante errores ambiguos.
- `tools/login_ui_smoke.py`: formulario Tk real tras ambos errores, correo
  conservado, contraseña vacía, acción visible y ventana abierta al 100/125 %.
- El workflow Windows ejecuta esos casos en los tres perfiles compatibles y
  produce únicamente instaladores de prueba hasta superar la aceptación.

La versión se publica como actualización opcional de prueba. La instalación en
Windows de 32 bits y la prueba presencial de lector/relé siguen pendientes.
