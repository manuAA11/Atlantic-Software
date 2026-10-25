# Sincronización de sesiones compartidas

La sesión cifrada es la referencia compartida entre procesos del mismo perfil.
La carga anterior actualizaba PostgREST, pero no invalidaba los clientes Edge y
Storage que el SDK ya había creado ni actualizaba el encabezado de Auth.
Una renovación realizada en otro proceso podía dejar esas conexiones usando
el token anterior. La prueba con el SDK fijado reproduce el fallo antes del
cambio y comprueba el encabezado enviado después de corregirlo.

La carga ahora usa el mismo mecanismo de enlace de credenciales del SDK
Supabase 2.31.0. Sincroniza Auth y reconstruye sus conexiones cacheadas cuando
cambia el token, incluyendo el cierre de sesión de otro proceso. No hace una
petición adicional ni renueva de nuevo una credencial ya rotada por un proceso
del mismo perfil. Si un adaptador no emite TOKEN_REFRESHED, se persiste y enlaza
la respuesta de renovación igualmente.

El arranque conserva una sesión todavía vigente y renueva cuando corresponde,
sin forzar una rotación en cada apertura. Se mantienen el cifrado DPAPI,
los espacios separados por proveedor/perfil y la exclusión entre procesos.

## Alcance y verificación

- SDK real sobre transporte HTTP simulado: expiración, rotación compartida,
  encabezados de PostgREST/Edge/Storage y salida de sesión compartida.
- Restauración al arrancar sin rotación forzada, conservación de identidad,
  recuperación de red y prohibición de repetir escrituras ambiguas.
- DPAPI y empaquetado x86/x64 requieren su comprobación en Windows.

Estos cambios no corrigen un reloj interno defectuoso de PostgREST. Si una
petición ya lleva el token nuevo, con una fecha válida, y el servidor devuelve
PGRST303 «JWT issued at future», renovar otra vez no soluciona esa causa.
La corrección del servicio está documentada por sus mantenedores:
https://github.com/PostgREST/postgrest/pull/5208

No se reinicia el proyecto, se modifican firmas/timestamps de JWT ni se reducen
las comprobaciones de autenticación. La recuperación del acceso real permanece
pendiente mientras el servicio siga rechazando tokens válidos. No publicar
estos cambios como una solución comprobada de ese incidente de servidor.
