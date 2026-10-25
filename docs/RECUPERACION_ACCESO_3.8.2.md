# Atlantic Gym 3.8.2: continuidad de sesión

La 3.8.2 incorpora las correcciones de sincronización y reincorporación que no
están dentro de los instaladores 3.8.1 ya publicados. Conserva los espacios de
sesión DPAPI, perfiles de conexión, carpetas e identificadores de instalación.
No incluye una migración del esquema de negocio.

## Aplicación

- La credencial renovada por otro proceso se aplica a Auth, PostgREST, Edge y
  Storage usando el SDK fijado. Una sesión vigente se conserva al arrancar.
- Al revocar la sesión se limpian las conexiones cacheadas y se bloquean las
  operaciones que requieren autenticación.
- Volver a entrar reactiva el trabajador de renovación aunque el anterior
  todavía esté terminando. Cada trabajador conserva su propia señal de cierre.
- Una contraseña rechazada vuelve al formulario de reincorporación, con el
  correo conservado. Cancelar deja el espacio abierto y sigue exigiendo sesión.
- Los cortes de red conservan las credenciales recuperables; la reanudación
  comprueba su vigencia y restablece el intento de renovación. Las escrituras
  con respuesta incierta nunca se repiten automáticamente.

Detalle de pruebas y alcance: [ESTABILIDAD_SESIONES.md](ESTABILIDAD_SESIONES.md).

## Servicio de datos

Los registros del incidente muestran renovaciones Auth exitosas seguidas de
rechazos PGRST303 al enviar el token nuevo. Supabase documentó esa incidencia,
una caché de tiempo desactualizada y la actualización del proyecto que contiene
su corrección:
https://status.supabase.com/incidents/01KZZ19EQMSC9DNDA15ZGVY19V

La corrección de PostgREST sustituye el reloj cacheado por una lectura del
reloj del sistema. No elimina la validación de firmas, expiración ni permisos:
https://github.com/PostgREST/postgrest/pull/5208

El usuario autorizó aplicar la actualización administrada del proveedor
ZTATTUZ desde Postgres 17.6.1.165 a 17.11.0.003, tras conocer el corte estimado
y la imposibilidad de volver a la versión anterior desde ese panel. La operación
terminó: el proveedor informa ACTIVE_HEALTHY, Postgres 17.11.0.003 y conexiones
reales de PostgREST 14.18. No se cambió el plan Free ni se contrataron add-ons.
El usuario confirmó acceso a la aplicación; los registros posteriores muestran
renovaciones Auth y consultas autenticadas exitosas. El rechazo PGRST303 no
reaparece en el intervalo revisado después de recuperar el servicio.

La revisión de base/scheduler devuelve estado saludable. Las tareas por minuto
han seguido completándose, sin fallos en la hora revisada; los dos timeouts
observados pertenecen a la interrupción de la actualización. Las comprobaciones
no encuentran índices inválidos, restricciones sin validar, bloqueos de
conexiones ni membresías sin cliente. RLS permanece habilitado en las tablas
públicas; el acceso anónimo de prueba a clientes sigue denegado. Permanecen
avisos anteriores de endurecimiento y optimización; esta revisión no acredita
una auditoría exhaustiva de todas las funciones o integraciones externas.

## Validación y entrega

El código de sesiones en 356db844 aprobó el run Windows 40146471973 en los tres
perfiles: guardas, SDK/DPAPI, formularios Tk, ejecutable congelado y empaquetado.
La instalación, actualización y desinstalación x64 aprobaron; la instalación
x86 conserva el alcance NOT_RUN en el host Windows x64 por el MSI del lector.
Ese run no acredita todavía el empaquetado con la identidad 3.8.2.

La entrega 3.8.2 requiere una ejecución Windows de su commit exacto. El flujo
de publicación conserva manifiestos, recibos de instalación y SHA256, y publica
una actualización opcional NO FINAL. La instalación x86 en Windows de 32 bits,
la suspensión física, el lector y el relé de esta versión requieren la prueba
presencial. release_readiness.json conserva todos los criterios externos;
no se trasladan aceptaciones antiguas a la versión nueva.
