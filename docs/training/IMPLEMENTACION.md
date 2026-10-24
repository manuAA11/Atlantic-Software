# Rutinas, clases y reservas de Atlantic Gym

Candidata 3.8.0 compartida en `pruebas`, para los perfiles x86/x64. No hay una edición
funcional separada para ZTATTUZ. Este documento describe la implementación y no
representa el estado operativo de un gimnasio. Consultar `DESPLIEGUE_COMPATIBLE.md`
para publicar; conservar recibos y comprobaciones de entornos reales en privado.

## Implementado

- Catálogo existente de League reutilizado: búsqueda sin distinción de tildes en
  escritorio, filtros por grupo/equipamiento, creación y edición de ejercicios
  propios, baja lógica, orden, indicaciones y enlaces HTTPS opcionales a medios.
  Un ejercicio global se adapta creando una variante del gimnasio; no se modifica
  para otros gimnasios. La asignación guarda su referencia y parámetros propios.
- Carga **opcional** con 44 ejercicios y 8 plantillas: Push, Pull, Legs, Full Body,
  Upper Body, Lower Body, Hipertrofia de 4 días y Principiantes. `ON CONFLICT DO
  NOTHING` evita duplicados y conserva las ediciones. No se ejecuta al abrir la app.
- Editor con casillas reales dibujadas, buscador, filtros, contador y panel de
  seleccionados; orden, eliminación, repetición del mismo ejercicio en otro día,
  series, repeticiones, kilos, descanso, días e indicaciones. La selección se
  mantiene al buscar o filtrar. Todos los parámetros se editan en una ventana.
- Búsqueda paginada de clientes por nombre/documento, selección persistente entre
  páginas, asignación individual/grupal (hasta 50), duplicación, plantillas propias,
  lista de clientes sin plan e historial de planes activos/archivados.
- Editar un plan crea una nueva revisión y archiva la anterior. No se eliminan sus
  ejercicios ni snapshots móviles. Los ejercicios manuales antiguos pueden
  vincularse al catálogo conservando sus parámetros; sólo una coincidencia exacta
  y única de nombre se reconoce automáticamente y el entrenador confirma el plan.
- Clases: búsqueda, filtros por entrenador/fechas/estado, calendario mensual con
  conteos agregados completos, lista paginada, edición con control de versión,
  duración, descripción, condiciones, cupos, entrenador, repetición semanal acotada
  (hasta 26 fechas), cancelación y reprogramación individual de cada fecha.
- Reservas: búsqueda por cliente/documento/clase, filtros por fechas/estado,
  participantes de una clase, inscripción desde la ficha existente, cancelación,
  asistencia a clase y registro de cambios. Esta asistencia no crea una entrada
  de puerta ni consume tiqueteras.
- Estado de carga/error/éxito/listas vacías; consultas en trabajadores existentes,
  debounce, páginas de 50 filas, actualización por ID de tablas y barras de
  desplazamiento condicionales. Los controles mantienen el estilo League.
- Apariencia sólo en **Configuración → Apariencia** en Administración y Recepción.
  Se elimina la copia en Sistema y avisos y el acceso directo de Recepción. Se
  conserva la preferencia local y los temas anteriores. Se corrigen mapas de color
  de campos, combos y barras y se compactan los controles League/calendario.
- Permisos de entrenamiento explícitos para cuentas existentes del gimnasio.
  Administración puede autorizar/retirar la función desde Rutinas. Una cuenta
  de recepción autorizada recibe sólo las páginas de entrenamiento adicionales;
  conserva su rol original y no obtiene finanzas, licencias ni administración.
  La autorización se comprueba de nuevo en el servidor en cada petición.

## Datos e integración

`public.gym_training` es una RPC SECURITY INVOKER. Sus implementaciones privadas
validan identidad confirmada, rol, gimnasio y la licencia/equipo existente cuando
ese control existe. No se cambia el mecanismo de membresías o acceso.

Se amplían `routines`, `exercises`, `classes`, `reservations` y el catálogo existente.
Sólo se añaden `gym_routine_templates`, un registro privado de solicitudes para
idempotencia, auditoría e historial de reservas. Las tablas nuevas tienen RLS y no
permiten escritura directa a clientes anónimos o autenticados. No hay claves
privilegiadas en escritorio. El staff de otro gimnasio no puede leer/modificar datos.

El bloqueo de la fila de clase protege tanto al escritorio como al flujo móvil.
La restricción única existente evita reservas repetidas. Cambiar capacidad no puede
invalidar cupos ocupados; cancelar una clase cancela sus reservas pendientes y deja
el historial. Una clase puede exigir membresía vigente: se consulta el estado
canónico del servidor, incluida congelación. La política anterior de inscripción
manual se conserva para clases existentes. La condición queda sin especificar en
las filas antiguas: se conserva la membresía obligatoria del flujo móvil anterior.
Las clases creadas o editadas eligen una condición explícita, igual en ambos
clientes. Una clase abierta sólo admite al deportista previamente vinculado y
autorizado; reservar no habilita la puerta ni modifica su membresía.

League sigue leyendo las mismas tablas mediante sus servicios existentes.
Se reutiliza `gym_events` para avisar cambios de rutinas, ejercicios, clases y
reservas a las sesiones de personal. La página vuelve a consultar sus datos aun
si la identidad y los permisos no cambiaron. Agenda y Mis rutinas en la PWA
consultan al abrirse, al volver al primer plano y cada 30 segundos mientras están
visibles; descartan respuestas anteriores al cambiar de gimnasio. Este código también requiere
publicar la nueva PWA antes de aparecer en la versión operativa. La nueva
RPC no crea cuentas deportivas, vínculos ni mensualidades ficticias, ni cambia la
lista del piloto. Los ejercicios desactivados se ocultan de los catálogos de League
sin borrar entrenamientos anteriores. Los datos de ejemplo nunca se muestran como
actividad real de deportistas.

El adaptador source amplía las respuestas existentes con duración, condiciones,
zona IANA y requisito de membresía de las clases e indicaciones de ejercicios.
Conserva la comprobación del perfil y la lista permitida del piloto. Las horas de
Agenda se muestran en la zona del gimnasio; una respuesta antigua sin esa zona se
identifica como hora del dispositivo. No se rellenan duraciones históricas.

## Archivos principales

| Área | Archivos |
|---|---|
| Pantallas | `common/training_ui.py`, puntos de entrada de `app.py` y `reception_app.py` |
| Modelo y conexión | `training_models.py`, `training_service.py`, ambos adaptadores de base de datos |
| Apariencia y carga | `appearance.py`, `platform_ui.py`, `ui_performance.py` |
| PWA compartida | `GymScreen.tsx`, `TrainingScreen.tsx`, `WorkoutScreen.tsx`, `gymSchedule.ts`, `useVisibleRefresh.ts` |
| Migración | `training/supabase/migrations/20261024013933_gym_training_workspace.sql` |
| Ejemplos controlados | `training/seeds/examples.sql`, `examples.json`, generador sin conexión |
| Reversión | `training/rollback/disable_workspace.sql` |
| Pruebas | `league/tests/training*`, `tools/test_training_models.py`, `test_appearance_location.py`, `training_ui_smoke.py`, `training_integrated_ui_smoke.py` |
| Validación y fuentes | workflows existentes de League/Windows y `tools/backup_complete_sources.py` |

## Despliegue controlado y reversión

1. Respaldar el proyecto completo por el procedimiento del servidor, incluyendo
   esquemas `public`, `league_private` y `league_source_private` y la identidad
   necesaria para restaurarlos. Verificar la restauración en una copia aislada.
   Los JSON/Excel anteriores de Gym **no sustituyen** este respaldo completo de
   los nuevos catálogos, plantillas e historiales.
2. Confirmar que el catálogo hub y el adaptador source de League estén en el mismo
   proyecto Gym. Es la topología del piloto actual, sin contratar otro proyecto.
   Primero aplicar y verificar la migración en la copia aislada. No aplicar de
   nuevo el instalador completo de esquema de Gym sobre una base existente.
3. Revisar `examples.sql` y cargarlo sólo en ese entorno autorizado. Puede omitirse.
   Repetir la carga no debe cambiar ejercicios existentes ni multiplicar plantillas.
4. Revisar permisos/licencia de dos gimnasios, un administrador, un entrenador
   autorizado y una cuenta de recepción ordinaria. Verificar denegación entre gyms.
5. Probar un grupo de clientes de QA y comprobar ambas direcciones Gym/League.
6. Validar Windows x86/x64 a 100/125 %, los gates actuales y la instalación. Sólo
   entonces preparar una versión y el aviso remoto. La app operativa no recibe
   este desarrollo automáticamente.
7. Ante problemas, volver al cliente anterior y ejecutar `disable_workspace.sql`.
   Conserva los datos y las protecciones de cupos; no borra tablas. Para reactivar,
   repetir la migración verificada. Nunca restaurar un respaldo antiguo sobre
   nuevas operaciones de clientes sin un procedimiento de conciliación aprobado.

## Pruebas y límites

Ver `VALIDACION.md` para los resultados y el alcance exacto. CI de League y los
tres perfiles Windows aprobados. La instalación x64 se verificó en el runner;
la instalación x86 requiere un Windows de 32 bits y sigue sin acreditar. Los
artefactos de CI son técnicos NO_FINAL, no una publicación en el actualizador.

- La topología con hub League remoto necesita sincronizar el catálogo con IDs
  verificables antes de habilitar esta RPC allí. No se simula esa conexión.
- Las repeticiones se materializan como fechas editables independientes, no como
  una serie infinita. La lista de espera y recordatorios no forman parte de esta fase.
- Los primeros ejemplos se revisan con el entrenador; no son prescripciones
  personales. Cardio puede describirse en indicaciones; un registro específico de
  distancia/tiempo en League queda pendiente.
- No se despliega un nuevo administrador dentro de la PWA. Se conservan los
  servicios existentes de eventos/marcas/vinculaciones; una gestión adicional de
  eventos generales no se anuncia como implementada en este cambio.
- No se han aplicado migraciones, semillas, cambios de clientes, cuentas o licencias
  en ZTATTUZ durante esta tarea. Windows físico, hardware y aceptación del piloto
  siguen siendo necesarios para una publicación final.

Preparación actual de servidor y respaldos: `DESPLIEGUE_CONTROLADO.md`.
