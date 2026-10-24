# Validación del desarrollo de entrenamiento

Los datos de todas las pruebas descritas aquí son sintéticos. No se consultaron
ni modificaron clientes reales para estas validaciones.

## Ejecutado localmente

- `npm test` desde `league`: **27 pruebas de integración/seguridad aprobadas**.
  Incluyen la instalación aditiva dos veces sobre ambos esquemas reales del
  repositorio (Comercial y proveedor histórico), carga repetida de ejemplos,
  aislamiento, roles, licencia/equipo, idempotencia, planes, clases y reservas.
- Pruebas Python de modelos, ubicación de Apariencia, preferencias, unificación,
  hardware compartido y fuentes de respaldo: aprobadas. **24 pruebas Python aprobadas** en la ejecución agregada.
- `tools/theme_ui_smoke.py`: **468 comprobaciones Tk aprobadas**, Administración y
  Recepción, a 100/125 %, alternando los temas y conservando entradas/selecciones.
- `tools/training_ui_smoke.py`: **77 comprobaciones Tk aprobadas**, claro/oscuro,
  100/125 %, búsqueda, casillas, parámetros, plantillas, asignación grupal,
  paginación de clientes, recurrencia, reservas y preferencia guardada desde la
  página real de Configuración de Recepción. Incluye un temporizador de UI que
  sigue ejecutándose durante una lectura lenta simulada. Se comprueban también
  el icono cian heredado en Recepción, el bloqueo de actualización con un formulario
  abierto y el fondo del diálogo y sus acciones en ambos temas.
- `tools/training_integrated_ui_smoke.py`: **aprobado**. Ventanas Tk → adaptador RPC
  real de entrenamiento → PostgreSQL embebido aislado (PGlite). Guarda el plan
  para dos clientes, lo revisa sin borrar el anterior, crea una clase e inscribe
  un cliente. Los servicios source de League consultan esas mismas filas. Una
  reserva desde el flujo source móvil aparece en la consulta del escritorio.
  Una cancelación posterior también actualiza la página completa de Clases aunque
  el contexto de identidad permanezca igual. Las pruebas del esquema comercial
  verifican la emisión de eventos de clase en el canal existente.
  El transporte de pruebas es STDIN privado, no un servicio productivo.
- `GymSoft_Comercial_3.6.0/tests/performance_ui_smoke.py`: **15 páginas aprobadas**,
  consultas fuera de Tk, respuestas vigentes, modales, ráfagas de eventos y
  selección conservada. Medición local de esa ejecución: despacho 0,07 ms y
  actualización sin cambios de 1.000 filas 1,91 ms, sin borrar/reinsertar filas.
  Su prueba adicional de Dashboard pasó **58 comprobaciones** al 100/125 %.
- TypeScript (`tsc --noEmit`), compilación Python y `git diff --check`: aprobadas.

Estas pruebas gráficas se ejecutaron en Linux/Tk con pantalla virtual y escalado
simulado. No equivalen a Windows físico, hardware real o un iPhone real. Los
valores de rendimiento son locales, con consultas sintéticas, no latencias de red
ni una garantía sobre el computador del gimnasio.

## Matriz solicitada

| Requisito | Evidencia |
|---|---|
| Búsqueda por nombre, grupo y equipo | Modelo puro y controles Tk, tildes incluidas |
| Múltiples casillas y selección persistente | Tk, filtros y páginas de clientes |
| Parámetros y orden del plan | Modelo, Tk y escritura SQL integrada |
| Rutina personalizada y plantillas editables | SQL, Tk y referencias al catálogo |
| Asignación individual/grupal | SQL e integración de editor con dos clientes |
| Búsqueda de clientes y clientes sin rutina | SQL paginada y selector Tk |
| Creación/edición de clases | SQL, control de versión y formulario Tk |
| Calendario, filtros y recurrencia | SQL y Tk; prueba de cambios horarios DST |
| Reservar/cancelar/asistir e historial | SQL e integración Tk de reserva |
| Persistencia | Consultas SQL posteriores a operaciones desde las ventanas |
| Duplicados y aforo | Restricción/bloqueo SQL y pruebas secuenciales; carrera real con dos sesiones aprobada en CI |
| Aislamiento y roles | Otro gimnasio, recepción ordinaria, coach autorizado/revocado |
| Apariencia sólo en Configuración | Inspección de puntos de entrada y página real de Recepción |
| Preferencia persistente | Escritura atómica, fallo de escritura y reapertura por los perfiles |
| Fluidez y 100/125 % | Pruebas Tk y latencia simulada; falta aceptación Windows |
| Sistemas actuales | Esquemas previos, contrato compartido, carga de páginas y pruebas existentes |

## CI de la revisión actual

`league/tests/training-postgres.mjs` utiliza **dos conexiones PostgreSQL reales**
y verifica que la segunda espere el bloqueo de la clase. Cubre escritorio contra
escritorio, escritorio contra flujo móvil y reintento simultáneo del mismo cliente.
El workflow de League lo ejecutó contra su servicio PostgreSQL 17 desechable,
con dos PID de backend y espera de bloqueo comprobada, en la revisión
`66f1eba953a24c606d7cc73031546ccd37dad025`.

[Run League 40085884463](https://github.com/manuAA11/Atlantic-Software/actions/runs/40085884463):
**SUCCESS**. Pasaron TypeScript, 27 casos de integración/seguridad, las carreras
escritorio/escritorio, escritorio/móvil y reintento del mismo cliente, y la
exportación de JavaScript iOS/Android. Las **8 pruebas de navegador** aprobaron
navegación en tres tamaños de teléfono, redimensionado de viewport, tema oscuro
persistente, registro de entrenamiento, reserva, borrador cifrado, shell sin red y
exportación de una imagen PNG de 1080 × 1920. Son datos simulados y Chromium; no
se acredita un iPhone físico ni la carga en los servidores productivos.

Se conservan los FAIL anteriores: dependencia del fixture sin instalar
(`40054590505`) y aserciones de navegador (`40054860899`). Se corrigieron la
instalación de dependencias, el selector exacto del aviso y el límite dinámico
de viewport. No se retiraron pruebas ni se aflojaron sus límites.

No se etiqueta PGlite como una carrera entre dos backends. En este contenedor no
hay un PostgreSQL de sistema disponible para esa prueba. La validación Windows
existente incorpora las nuevas pruebas de formularios y la integración SQL nativa,
reutilizando Node/PGlite de cada perfil.

[Run Windows 40085884474](https://github.com/manuAA11/Atlantic-Software/actions/runs/40085884474):
**SUCCESS en los tres perfiles**, código nativo `66f1eba`. Windows Server 2022
x64, con procesos Python 3.14 x64 y x86 según el perfil. Cada uno aprobó 110
pruebas de guardas, 468 comprobaciones de apariencia y 77 del flujo nuevo, la
integración Tk/SQL, el aviso de actualización y las regresiones completas de su
programa. Se construyeron los ejecutables e instaladores técnicos, se verificaron
arquitecturas/iconos y se confirmó que la entrega final continúa bloqueada sin
aceptación. No se modifica `release_readiness.json`.

| Perfil de compatibilidad de la aplicación compartida | Compilación/regresiones | Instalación, actualización y desinstalación |
|---|---|---|
| Comercial x64 | PASS | PASS, runner Windows x64 desechable |
| Proveedor histórico x64 | PASS | PASS, runner Windows x64 desechable |
| Proveedor histórico x86 | PASS, proceso real de 32 bits | **NOT_RUN**: falta Windows de 32 bits |

El MSI DigitalPersona x86 exige `NOT VersionNT64`. El runner de 64 bits no puede
acreditar esa instalación; el job exitoso no se presenta como instalación x86
aprobada. El lector y el relé físicos, el escalado de Windows en el equipo del
cliente y la aceptación del piloto siguen pendientes. Los paquetes publicados
por este workflow están identificados **NO_FINAL** y no se enviaron al actualizador
productivo. La ejecución anterior `40054590456` conserva el FAIL del fixture de
`responsive_ui_smoke`; la respuesta simulada se corrigió en los tres perfiles y
se repitieron las validaciones completas.

[Run League 40086794784](https://github.com/manuAA11/Atlantic-Software/actions/runs/40086794784):
**SUCCESS** sobre `758ca041`, posterior a Windows únicamente en la pantalla PWA.
Repite 27 casos, dos conexiones PostgreSQL y 8 pruebas de navegador. Incluye la
presentación de indicaciones generales del plan y el nombre conservado del
ejercicio asignado cuando se desactiva en el catálogo. El código nativo coincide
con el validado en el run Windows anterior.

Pendientes para publicar en clientes: respaldo restaurable y migración/carga
controlada en el servidor autorizado; instalación en Windows de 32 bits; prueba
física del equipo y aceptación de los gates vigentes de la versión. No se han
generado ni anunciado instaladores finales. El resumen estructurado de evidencias
está en `evidence/training-validation-20261024.json`.


## Herramientas de compilación

`npm audit` informa cinco entradas de severidad alta derivadas de dos avisos
transitivos del CLI de Expo: `node-forge` (GHSA-86w9-cpqp-85rv) y Zod
(GHSA-mrhx-c7xc-m3w5). No son dependencias de validación del backend Gym.
La corrección automática propuesta cambia Expo a 44.0.6; no se ejecuta esa
incompatibilidad sobre el SDK actual. Queda pendiente actualizar el CLI con una
combinación compatible. No se presenta la auditoría npm como limpia ni se cambian
certificados o credenciales de firma durante este desarrollo.


## Candidata 3.8.0 y preparación del despliegue

El desarrollo continúa en `pruebas` con versión nativa 3.8.0. El marcador de
publicación está en `publish: false`; las tres fichas de aceptación tienen la
versión nueva y conservan sus comprobaciones pendientes.

Se consultó el servidor actual mediante una transacción de sólo lectura:
PostgreSQL 17.6 y esquema previo compatible, con RPC nueva aún sin instalar.
`evidence/training-preflight-20261024.json` conserva el resultado sin datos de
clientes. El comprobador rechaza un despliegue parcial, permisos incorrectos,
metadatos incompletos y ausencia de restricciones de duplicados/cupos.

[League 40101080081](https://github.com/manuAA11/Atlantic-Software/actions/runs/40101080081)
aprobó 29 casos, 8 pruebas de navegador y el nuevo ensayo `pg_dump`/`pg_restore`:
respaldo previo y posterior, restauración de 22 tablas sintéticas, secuencias,
permisos, reintentos idempotentes, reversión sin pérdida de datos y rechazo de un
archivo corrupto. No se presenta ese ensayo como respaldo del Supabase real.

[Windows 40101080087](https://github.com/manuAA11/Atlantic-Software/actions/runs/40101080087)
valida los instaladores técnicos de la candidata 3.8.0; su resultado se registra
al terminar. La publicación opcional `40101080102` omitió sus pasos de entrega
porque el marcador está desactivado. No se crea una release ni un aviso productivo.

Se añaden pruebas del rechazo de destinos remotos, URLs con sustitución de host y
URLs mal formadas sin registrar contraseñas. La guía operativa actual es
`DESPLIEGUE_CONTROLADO.md`. Las pruebas previas de 3.7.1 arriba se conservan como
históricas; no se trasladan sus aceptaciones físicas a 3.8.0.
