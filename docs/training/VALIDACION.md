# Validación del desarrollo de entrenamiento

Los datos de todas las pruebas descritas aquí son sintéticos. No se consultaron
ni modificaron clientes reales para estas validaciones.

## Ejecutado localmente

- `npm test` desde `league`: **24 pruebas de integración/seguridad aprobadas**.
  Incluyen la instalación aditiva dos veces sobre ambos esquemas reales del
  repositorio (Comercial y proveedor histórico), carga repetida de ejemplos,
  aislamiento, roles, licencia/equipo, idempotencia, planes, clases y reservas.
- Pruebas Python de modelos, ubicación de Apariencia, preferencias, unificación,
  hardware compartido y fuentes de respaldo: aprobadas. **24 pruebas Python aprobadas** en la ejecución agregada.
- `tools/theme_ui_smoke.py`: **468 comprobaciones Tk aprobadas**, Administración y
  Recepción, a 100/125 %, alternando los temas y conservando entradas/selecciones.
- `tools/training_ui_smoke.py`: **61 comprobaciones Tk aprobadas**, claro/oscuro,
  100/125 %, búsqueda, casillas, parámetros, plantillas, asignación grupal,
  paginación de clientes, recurrencia, reservas y preferencia guardada desde la
  página real de Configuración de Recepción. Incluye un temporizador de UI que
  sigue ejecutándose durante una lectura lenta simulada.
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
| Duplicados y aforo | Restricción/bloqueo SQL y pruebas secuenciales; carrera real pendiente de CI |
| Aislamiento y roles | Otro gimnasio, recepción ordinaria, coach autorizado/revocado |
| Apariencia sólo en Configuración | Inspección de puntos de entrada y página real de Recepción |
| Preferencia persistente | Escritura atómica, fallo de escritura y reapertura por los perfiles |
| Fluidez y 100/125 % | Pruebas Tk y latencia simulada; falta aceptación Windows |
| Sistemas actuales | Esquemas previos, contrato compartido, carga de páginas y pruebas existentes |

## Preparado, aún sin acreditar aquí

`league/tests/training-postgres.mjs` utiliza **dos conexiones PostgreSQL reales**
y verifica que la segunda espere el bloqueo de la clase. Cubre escritorio contra
escritorio, escritorio contra flujo móvil y reintento simultáneo del mismo cliente.
El workflow de League lo ejecutará contra su servicio PostgreSQL 17 desechable.

No se etiqueta PGlite como una carrera entre dos backends. En este contenedor no
hay un PostgreSQL de sistema disponible para esa prueba. La validación Windows
existente incorpora las nuevas pruebas de formularios y la integración SQL nativa,
reutilizando Node/PGlite de cada perfil.

Pendientes para publicar: resultado de CI de dos sesiones, Windows x86/x64 con
escalado real, gates de la versión nueva, aceptación de instalación y prueba
controlada del piloto. No se han generado ni anunciado instaladores finales.
