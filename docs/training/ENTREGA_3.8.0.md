# Atlantic Gym 3.8.0 — entrega para pruebas

Una aplicación compartida, con ejecutables de 32 y 64 bits. Los nombres históricos
de carpetas e instaladores conservan la compatibilidad del proveedor y los IDs de
instalación. No representan dos aplicaciones funcionales distintas. El desarrollo
está en `pruebas`; `main` continúa como rama oficial.

## Funciones incluidas

- Rutinas: catálogo reutilizable, búsqueda por nombre, grupo y equipamiento,
  casillas de selección, contador y panel de elegidos, orden y parámetros por día.
  La selección permanece al buscar, filtrar o cambiar de página.
- Clientes: búsqueda por nombre/documento, asignación individual o grupal,
  duplicación, plantillas, clientes sin rutina e historial. Editar un plan crea
  otra revisión y conserva los ejercicios y entrenamientos anteriores.
- Ejemplos opcionales: 44 ejercicios y ocho plantillas editables. La carga es
  controlada, idempotente y no se ejecuta al abrir la aplicación.
- Clases: buscadores y filtros, calendario/lista, entrenador, duración, cupos,
  condiciones, repetición semanal acotada, edición, cancelación y reprogramación.
- Reservas: cliente existente, participantes, cancelación, asistencia e historial.
  El bloqueo del servidor y la restricción única impiden sobrecupos y duplicados,
  también cuando se reservan los últimos cupos simultáneamente desde Gym y League.
- Apariencia: únicamente Configuración → Apariencia, tanto en Administración como
  en Recepción. Se conserva la preferencia y los permisos del usuario.
- League PWA: servicios existentes y las mismas tablas de rutinas, clases y
  reservas; actualización al abrir, volver al primer plano y durante la consulta.
  Este código web necesita su propia publicación antes de aparecer en el sitio.

## Descargas y comprobantes

Los ZIP de cliente incluyen el instalador completo, instrucciones y comprobantes
SHA-256. No incluyen el panel privado del propietario. Sus manifiestos permiten
comprobar versión, arquitectura, código fuente, ejecución de Windows y alcance
de instalación. Los hashes de esta entrega están registrados
en `evidence/candidate-3.8.0-validation.json`.

| Archivo | Bytes | Integridad |
|---|---|---|
| `AtlanticGym_3.8.0_32bits_PRUEBAS_NO_FINAL.zip` | 97.366.730 | PASS |
| `AtlanticGym_3.8.0_64bits_PRUEBAS_NO_FINAL.zip` | 177.072.372 | PASS |

SHA-256 del ZIP de 32 bits:

`ec96890157a1efc5177c983eec669e166fd7fa225a22f047cfeb93b4133f38ad`

SHA-256 del ZIP de 64 bits:

`dbe4858ce4fc6d62f2f2094cbe1a1b8189b01864a5c92a3343a2e0de8cd3548c`

Son paquetes **PRUEBAS / NO FINAL**, para un equipo de pruebas con el mismo perfil
y arquitectura que la instalación correspondiente. Extraer el ZIP y abrir su
`VALIDACION_NO_FINAL_*.exe`; no se necesita instalar Python o Node.js.

La versión x86 incluye el MSI original DigitalPersona, que exige Windows de
32 bits (`NOT VersionNT64`). Compilar y ejecutar pruebas en un proceso x86 dentro
de Windows x64 no acredita instalar ese controlador en Windows de 32 bits.

## Validación

Código comprobado: `5f738c2ab06ddd47fb46a174557e6eafad4613bf`.

| Comprobación | Resultado y alcance |
|---|---|
| TypeScript e integración/seguridad | PASS, 30 casos con datos sintéticos |
| Navegador | PASS, ocho casos; Chromium con tamaños de teléfono |
| Reservas simultáneas | PASS, dos sesiones PostgreSQL 17.11 y espera de bloqueo comprobada |
| Respaldo/restauración | PASS, `pg_dump`/`pg_restore` reales y 22 tablas sintéticas |
| Compilación y regresiones Windows 3.8.0 | PASS en los tres perfiles; 40/41 etapas completas por perfil |
| Instalación/actualización/desinstalación x64 | PASS en ambos perfiles x64, Windows Server 2022 desechable |
| Instalación x86 en Windows de 32 bits | NOT_RUN; se necesita ese sistema operativo |
| Lector, relé y aceptación en el gimnasio | Pendientes de prueba física |

La restauración comprueba actividad, planes, clases, reservas, permisos, secuencias,
reintentos, archivo corrupto y deshabilitación/reactivación sin pérdida de datos.
El importador antiguo también se probó con un cliente vinculado a League: el
servidor bloquea su eliminación y revierte toda la transacción, conservando la
clase previa. No se han retirado pruebas ni desactivado gates.

Windows aprobó además 110 guardas, 468 comprobaciones de apariencia y 77 del flujo
nuevo por perfil, con procesos reales Python 3.14.9 de 32/64 bits y ejecutables
congelados. La prueba de escalado Tk a 100/125 % no acredita la revisión física
del escalado del equipo del cliente. La instalación x86 permanece pendiente.

- Windows: https://github.com/manuAA11/Atlantic-Software/actions/runs/40103947031
- League: https://github.com/manuAA11/Atlantic-Software/actions/runs/40103947068

Resultados completos, runs, perfiles y límites: `VALIDACION.md` y el JSON de
evidencia de esta versión. Los resultados de 3.7.1 se conservan por separado.

## Servidor y puesta en marcha

El preflight real, de sólo lectura, encontró el servidor compatible pero **sin la
RPC nueva**. Instalar el cliente no instala el backend. Con el servidor anterior,
las herramientas nuevas muestran que se requiere actualizar el servidor; no se
simulan guardados exitosos.

La migración pendiente es:

`training/supabase/migrations/20261024013933_gym_training_workspace.sql`

SHA-256: `537a19b7309874beee9c2a79347766b13faf7ff5fef7d9b69180d49915c3cc41`.

Reutiliza el proyecto actual. Debe aplicarse primero a una copia aislada y después
seguir `DESPLIEGUE_CONTROLADO.md`: respaldo completo real restaurado, preflight,
autorización de cambio productivo y prueba controlada. El ensayo con datos
sintéticos no es un respaldo del proyecto real ni incluye archivos de Storage,
ajustes de Auth, Vault o secretos. Los JSON/Excel antiguos tampoco lo sustituyen.

La carga opcional está en `training/seeds/examples.sql`. La reversión funcional es
`training/rollback/disable_workspace.sql`; conserva tablas, registros e historiales.
No se debe restaurar un respaldo antiguo sobre actividad nueva sin conciliación.

No se aplicaron migraciones, ejemplos ni cambios de clientes en producción durante
esta tarea. La publicación remota sigue desactivada (`publish: false`); la versión
instalada de los gimnasios y el sitio web operativo no reciben estos cambios
automáticamente. No se ha enviado el aviso de actualización.

La regla de `AGENTS.md` sigue vigente: «No marcar la actualización como terminada
ni producir instaladores finales hasta cumplir `release_readiness.json` con
evidencia válida de la versión». Las fichas de 3.8.0 conservan sus aceptaciones
pendientes; esta entrega no las aprueba.

## Archivos y seguimiento

Las pantallas, servicios, datos, permisos y puntos de integración modificados están
enumerados en `IMPLEMENTACION.md`; el diagnóstico previo está en `DIAGNOSTICO.md`.
La preparación de esta candidata añade:

- Versión compartida y ocho valores por defecto Inno 3.8.0; instrucciones de
  actualización por perfil y prueba que exige su existencia.
- `league/source/training-preflight.sql` y
  `league/scripts/training-preflight.mjs`: consulta de metadatos sin escribir datos.
- `league/tests/training-preflight.test.mjs`: esquema, permisos, errores de conexión
  y rechazo de credenciales en salida.
- `league/tests/training-restore-postgres.mjs` y su paso en el workflow de League:
  ensayo reproducible de respaldo y restauración PostgreSQL.
- Regresión de restauración del cliente vinculado en
  `league/tests/training-providers.test.mjs`.
- `evidence/training-preflight-20261024.json`, evidencia específica de 3.8.0 y esta
  documentación de despliegue y entrega.

Pendientes para una publicación operativa: respaldo real y despliegue autorizado,
instalación Windows32, hardware, revisión del escalado real 100/125 %, publicación
de la PWA, piloto Gym/League y aceptaciones vigentes. El CLI de Expo mantiene los
avisos transitivos documentados en `VALIDACION.md`; su auditoría no se presenta
como limpia. Listas de espera, recordatorios y registro de distancia/tiempo para
cardio quedan fuera de esta fase.
