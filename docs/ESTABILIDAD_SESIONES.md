# Continuidad y reincorporación de sesiones

Requisito del usuario del 24 de octubre de 2026: mantener Atlantic Gym abierto
ante suspensión de Windows o pérdida de internet, renovar la sesión cuando
corresponda y permitir una reincorporación segura si la sesión fue revocada.

## Cambios

- La renovación se comparte entre procesos del mismo perfil y se aplica a
  PostgREST, Auth, Edge y Storage. Una sesión vigente no se rota al arrancar.
- Un error temporal de red conserva la credencial cifrada y la identidad;
  la renovación tiene espera limitada entre intentos. Al detectar una
  reanudación o cambio de reloj se elimina la espera anterior y se comprueba
  la vigencia. El servidor sigue autorizando cada operación.
- Una revocación explícita elimina inmediatamente la credencial de las
  conexiones cacheadas. Las consultas/RPC y funciones administradas exigen
  una sesión; no continúan con acceso anónimo después de perderla.
- La renovación vuelve a arrancar aunque el trabajador anterior todavía esté
  terminando. Cada generación conserva su propia señal de cierre para no
  revivir un trabajador detenido durante una reincorporación rápida.
- La reincorporación conserva el correo y devuelve los errores al formulario,
  con la contraseña vacía. Cancelar ese formulario mantiene el espacio abierto
  y la exigencia de autenticación. Se exige la misma cuenta, gimnasio y rol.
- Una respuesta perdida a una escritura nunca provoca su repetición automática.
  Sólo un rechazo JWT explícito previo a SQL admite recuperación acotada.

## Verificación

Las regresiones reproducen los defectos de trabajador detenido, continuación
sin sesión y credencial cacheada tras revocación antes de la corrección.
Se prueba el SDK Supabase 2.31.0 sobre HTTP simulado para renovación compartida,
expiración durante suspensión simulada, corte de red, reanudación, revocación
y encabezados reales de los clientes. Estas pruebas no usan cuentas reales.

El smoke de Tk incluye reincorporación dentro de una ventana abierta,
contraseña rechazada/corregida y cancelación, al 100 % y 125 %. La tarea de
Windows ejecuta ese smoke y las pruebas DPAPI en procesos x86 y x64. La
simulación de tiempo/red no acredita una suspensión física de Windows.

La comprobación local con CPython 3.14.8/Linux x64 aprobó 318 pruebas de
Comercial, 290 del perfil histórico x64 y 289 del perfil histórico x86
(las tres ejecutadas en Linux x64). El conjunto adicional de sesiones, Core,
actualizador y compatibilidad aprobó 60 pruebas, con una prueba DPAPI omitida
por requerir Windows. El run Windows 40146471973 del commit 356db844 aprobó el
smoke Tk ampliado, SDK/DPAPI, ejecutable congelado y empaquetado de los tres
perfiles. La nueva identidad 3.8.2 necesita su ejecución exacta antes de publicarse.

## Incidencia del proveedor y entrega

Antes de actualizar, el proveedor ZTATTUZ informaba PostgREST 14.5 y rechazaba
tokens recién emitidos con PGRST303. Auth sí aceptaba renovaciones. Los cambios
del escritorio por sí solos no corregían el servicio; véase SINCRONIZACION_SESIONES.md.
La actualización del servicio requiere el panel: el plugin conectado no expone
esa operación. El acceso al panel ya se completó y el usuario autorizó la
actualización administrada, que terminó con el proveedor saludable y PostgREST
14.18. El acceso real informado por el usuario se confirma con renovaciones y
consultas autenticadas exitosas en los registros. Véase
[RECUPERACION_ACCESO_3.8.2.md](RECUPERACION_ACCESO_3.8.2.md).

Los cambios del escritorio no reinician el proyecto ni cambian claves,
políticas RLS, claims o validación de firmas. La comprobación posterior del
servidor y los registros respalda la recuperación del acceso. La publicación
3.8.1 existente es anterior a estas correcciones adicionales y no debe
presentarse como un instalador que ya las contiene. Los criterios de
release_readiness.json permanecen vigentes; no se certifica entrega final.
