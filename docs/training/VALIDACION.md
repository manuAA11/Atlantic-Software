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
en curso para la misma revisión, con los tres perfiles. Incluye las pruebas
nuevas, regresiones existentes, compilación, instaladores técnicos e instalación
en un Windows Server 2022 desechable. No modifica `release_readiness.json`.

Pendientes para publicar: resultado de CI Windows de la revisión definitiva,
escalado en el equipo del gimnasio, gates de la versión nueva, aceptación de instalación y prueba
controlada del piloto. No se han generado ni anunciado instaladores finales.


## Herramientas de compilación

`npm audit` informa cinco entradas de severidad alta derivadas de dos avisos
transitivos del CLI de Expo: `node-forge` (GHSA-86w9-cpqp-85rv) y Zod
(GHSA-mrhx-c7xc-m3w5). No son dependencias de validación del backend Gym.
La corrección automática propuesta cambia Expo a 44.0.6; no se ejecuta esa
incompatibilidad sobre el SDK actual. Queda pendiente actualizar el CLI con una
combinación compatible. No se presenta la auditoría npm como limpia ni se cambian
certificados o credenciales de firma durante este desarrollo.
