# Atlantic Gym Comercial y Core

Atlantic Gym es una aplicación común de Administración y Recepción. ZTATTUZ
se administra en Core como un gimnasio identificado por su UUID existente.
No se generan IDs nuevos ni se copian clientes al registrar el gimnasio.

## Versiones oficiales y referencia de hardware

Atlantic Gym mantiene dos versiones oficiales: x86 (32 bits) y x64 (64 bits),
con el mismo conjunto de funciones. Ambas deben aprobar sus verificaciones de
Windows y hardware. La referencia funcional recuperada es ZTATTUZ x86, que el operador
reporta que funciona con el relé. Se contrastó con la entrega Windows del commit
`9c1a6183ef214110dabddfce119f796bb6f00980`. El adaptador DigitalPersona y su
trabajador coinciden byte por byte; la lógica del relé se conserva. Sólo se añade
una propiedad de consulta para que el actualizador espere las operaciones activas.

La aplicación compartida se reconstruyó desde el código x86 y se comprobó su
igualdad con la integración. Los adaptadores conservan las diferencias de datos
necesarias para instalaciones existentes. `deployment/official_baseline.json`
registra los hashes. Las pruebas impiden modificar esta base de hardware sin
actualizar expresamente su referencia y validación. El reporte del operador no
sustituye la aceptación física de la versión nueva.

## Una implementación

`common/app.py`, `reception_app.py`, `cloud_database.py`, `reception_database.py`,
`runtime_cloud.py` y `licensing.py` contienen la aplicación compartida. Los
archivos homónimos de los directorios históricos son puntos de entrada de
compatibilidad, sin funciones distintas por edición. Los servicios de lector,
puerta, sesiones, Core y actualización también son compartidos.

`common/deployment_profile.py` adapta los contratos del proveedor existente:
RPC de contexto, formato de respaldos, columnas disponibles, plantillas ya
aprobadas y directorios históricos. Es compatibilidad de datos e instalación;
no constituye una aplicación ni un conjunto de funciones distinto. La marca
visible es Atlantic Gym en todas las instalaciones.

El registro en Core unifica la administración. Por sí solo no mueve las tablas
operativas entre servidores. Migrar físicamente un gimnasio requiere respaldo,
comparación íntegra de datos y validación antes de cambiar su conexión. Esta
extracción de código conserva su proveedor operativo y sus datos.

## Actualizaciones por gimnasio

Core selecciona versiones publicadas por `gym_id` específico o destino general,
canal (`stable`/`beta`) y arquitectura (`windows-x86`/`windows-x64`). Un gimnasio
no recibe versiones dirigidas a otro. Una versión específica y una general
pueden coexistir; el cliente escoge la versión compatible más reciente.

El campo histórico `product_variant` representa exclusivamente el perfil del
instalador (`ztattuz`/`commercial`): conserva AppId, nombres de ejecutables y
ruta de actualización de instalaciones existentes. No selecciona código ni
funciones del gimnasio. Una publicación general se ofrece a los perfiles de
instalación correspondientes; los instaladores nunca se intercambian sin una
migración de instalación previamente validada.

El panel privado de Core permite elegir gimnasio o destino general. Una
publicación no instala automáticamente: el administrador inicia el proceso,
con descarga desde el repositorio aprobado, SHA256, respaldo local y espera
de operaciones críticas. No se ejecutan comandos recibidos del servidor.

## Alcance de verificación

Las pruebas comprueban la identidad del código compartido, los contratos SQL de
ambos proveedores, conservación de rutas, aislamiento de versiones por gimnasio,
arquitectura y canal, recuperación de sesiones y barreras del actualizador.
Las pruebas Tk usan datos sintéticos. Las verificaciones locales o de Windows
CI no acreditan lector, relé, inicio de sesión real ni piloto presencial.
La entrega final sigue bloqueada hasta reunir las aceptaciones de la versión.
