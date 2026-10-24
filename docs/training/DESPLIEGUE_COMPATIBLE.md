# Publicación compatible de las herramientas de entrenamiento

Esta guía describe el procedimiento técnico reutilizable. Los identificadores,
configuraciones, métricas, recibos y estados operativos de gimnasios reales se
conservan de forma privada; no deben añadirse al repositorio público.

## Servidor

La migración versionada amplía las tablas y servicios existentes. El compositor
`league/scripts/training-rollout.mjs` añade una transacción acotada y compara el
contenido anterior de las tablas afectadas, las cuentas y las funciones públicas
existentes antes del COMMIT. Si cambia un elemento protegido, rechaza el cambio.
La prueba `training-rollout.test.mjs` cubre la aplicación compatible y el rechazo
de una modificación indebida de acceso.

Antes de aplicar, ejecutar el preflight y preparar el resguardo y la reversión
apropiados al entorno. Una copia de definiciones y permisos permite recuperar
esos objetos, pero no sustituye un respaldo integral de datos, identidad o archivos.
Guardar los resultados y copias con acceso privado. La carga de ejemplos es
explícita, idempotente y separada de las cuentas y membresías de deportistas.

La reversión funcional `training/rollback/disable_workspace.sql` conserva las
tablas, planes e historiales. No restaurar un respaldo anterior sobre actividad
nueva sin un procedimiento de conciliación.

## Web

Para una compilación real, ejecutar primero
`node league/scripts/check-live-pwa-env.mjs`. Requiere una clave publicable moderna
compatible con el cliente y una pasarela del mismo proyecto. No rotar claves ni
revocar sesiones para publicar una interfaz.

Compilar con el procedimiento PWA existente, verificar el bundle y conservar los
archivos estáticos con nombres hash de versiones anteriores durante la transición.
Así, una pestaña abierta mantiene sus referencias. Conservar el acceso del sitio
y la activación del service worker mediante confirmación del usuario.

## Escritorio y aviso remoto

La publicación de prueba exige el resultado satisfactorio de Windows para el
commit exacto de los instaladores, sus manifiestos, tamaños, hashes y comprobantes.
El proceso excluye las herramientas privadas del propietario. Una compilación
x86 no acredita instalar el controlador en un Windows de 32 bits; su alcance debe
conservarse explícitamente cuando no se haya probado.

Después de comprobar la release publicada, registrar en Core únicamente los
archivos compatibles con el gimnasio, proveedor y arquitectura previstos. Usar
una política opcional durante un piloto y conservar el resto de configuración,
licencia, suscripción y autorizaciones de equipos. El aviso no debe revocar el
acceso de una versión anterior ni forzar la instalación.

Comprobar la respuesta del servicio para la versión existente y confirmar que
sigue autorizada y recibe el instalador correcto. El usuario puede consultar
**Sistema y avisos → Buscar actualizaciones** y decidir cuándo actualizar después
de terminar sus operaciones. Esa comprobación del servicio no acredita haber
instalado físicamente en su PC.

Los gates de `release_readiness.json`, la aceptación de hardware y las pruebas
físicas pendientes deben conservarse. Un piloto no se anuncia como entrega final.
