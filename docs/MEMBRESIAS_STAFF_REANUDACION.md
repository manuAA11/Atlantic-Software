# STAFF y reanudación de membresías

Revisión: 13 de octubre de 2026. Código de Comercial 3.6.0 y ZTATTUZ 3.6.1 x64/x86; el usuario autorizó posteriormente generar instaladores para todas las aplicaciones. Se preparan paquetes de configuración y pruebas con el pipeline Windows existente; la aceptación final sigue separada.

## Operación

En Administración → Planes → Nuevo plan, escribir **STAFF** y seleccionar **Interno / No comercial**. Los valores recomendados son $0, acceso ilimitado y vigencia indefinida. El propietario de Comercial usa el mismo formulario desde su editor de registros. La configuración es opcional: no se crea ningún plan automáticamente ni se clasifica por su nombre. Se pueden configurar otros nombres, vigencia limitada o cupos explícitos.

Asignarlo desde el formulario normal de membresías del cliente. La asignación interna oculta campos de cobro y traslado de tiquetera, conserva una referencia de petición para evitar duplicados y consulta el servidor. No utiliza vencimientos 2099, cupos artificiales ni recibos de pago por cero pesos. En «Membresía y congelación», Administración puede activar o desactivar con motivo; la desactivación bloquea inmediatamente todos los métodos de acceso, incluso el override ordinario. Recepción puede consultar, pero no crear ni asignar planes internos.

STAFF no cuenta en ingresos, ventas, promedios, pagos de caja, contabilidad ni indicadores comerciales. El panel separa «Personal interno» y «Asistencias del personal hoy». Las estadísticas comerciales excluyen sus asistencias; el registro completo de entradas conserva identidad, gimnasio, método, instante del servidor y resultado. Las ventas históricas comerciales se conservan aunque posteriormente una persona reciba STAFF.

No recibe enlaces Wompi, cobros ni recordatorios de renovación, vencimiento o deuda. El chatbot verificado muestra plan, estado y acceso; un plan indefinido no muestra un vencimiento inexistente ni botones de renovar/pagar. Los mensajes operativos de asistencia pueden seguir funcionando con consentimiento. Un cargo confirmado de un enlace comercial anterior a STAFF queda marcado para revisión, sin renovar automáticamente ni crear una deuda interna.

Para una membresía comercial elegible, «Membresía y congelación» permite congelar y luego **REANUDAR MEMBRESÍA**. La confirmación utiliza el número del servidor; si cruzó otro período completo, hay que confirmarlo de nuevo. Se suman días al cerrar el evento, una sola vez. Ejemplo: 20/10 → 22/10, vencimiento 30/10 → 01/11. De 23:00 a 08:00 del día siguiente son cero días. El máximo es siete días de 24 horas, incluso con cambio de horario estacional o scheduler tardío. La reanudación no registra un pago.

Se mantiene una congelación por membresía, salvo excepción administrativa con motivo. Reanudar antes no borra el uso ni permite pedir otra semana ordinaria. Las tiqueteras conservan entradas y consumo por día local; los ciclos futuros ya comprados se desplazan por los días realmente utilizados.

## Base de datos y despliegue

Las migraciones son aditivas y transaccionales. Primero verificar el historial del proyecto: deben estar aplicados consumo diario, Marketing, congelación, scheduler e índices anteriores. **No ejecutar el esquema inicial sobre una instalación existente ni volver a aplicar migraciones antiguas después de estas.** No se aplicaron a proyectos reales en esta tarea.

1. `supabase/migrations/20261013090000_internal_plans.sql` / `ACTUALIZAR_PLANES_INTERNOS.sql`.
2. `supabase/migrations/20261013091000_early_resume.sql` / `ACTUALIZAR_REANUDACION_MEMBRESIAS.sql`.

Cada edición incluye copias idénticas de estos dos upgrades. Después, desplegar el backend Marketing actualizado y ejecutar el cliente actualizado. El cron anterior continúa usando la función de finalización reemplazada; se debe verificar su instalación real en cada proyecto. Las credenciales Meta/Wompi siguen en el servidor/Vault, y las capacidades requieren configuración desde la aplicación.

| Datos | Comportamiento |
|---|---|
| `plans.plan_type` | `COMMERCIAL` por defecto; `INTERNAL` explícito |
| `unlimited_access`, `has_expiration` | Flags reales; cupo o vencimiento `NULL` cuando no aplican |
| `include_in_financial_stats` | Falso obligatorio para internos |
| `memberships.membership_type` | Copia inmutable del tipo al asignar; conserva condiciones de compras anteriores |
| `membership_active`, `assignment_request_id` | Autorización revocable y asignación idempotente |
| `payment_status=non_commercial` | Sin pago, importe cero y `paid_at=NULL` |
| Historial de congelación | Inicio/plazo `TIMESTAMPTZ`, días máximos/usados, instante y usuario de reanudación, motivo y cierre manual/automático |
| `calculation_version` | Eventos nuevos por duración real; eventos antiguos con extensión preaplicada conservada |

Crear un plan nuevo si uno con membresías necesita cambiar de categoría o condiciones de acceso. No se convierten ventas históricas en internas. Exportación/respaldos conservan flags, fechas nulas, tipo de asignación e historial; una importación autorizada no vuelve a extender fechas.

## Implementación

| Área | Archivos principales |
|---|---|
| Motor, permisos, acceso, finanzas, métricas, auditoría y protecciones de Marketing | `common/internal_plans.sql` |
| Congelación, reanudación, límites, cierre idempotente, reloj y respaldo | `common/early_resume.sql` |
| Formulario compartido y validación | `common/plan_editor_ui.py`, `common/plan_forms.py`, `common/membership_features.py` |
| Confirmación de reanudación e historial | `common/membership_freeze_ui.py` |
| Adaptadores, panel y exportación de las tres ediciones | `cloud_database.py`, `app.py`, `reception_database.py`, `reception_app.py`, `payment_revision.py` |
| Propietario global exclusivo de Comercial | `owner_editor.py`, `owner_editor_forms.py` |
| Chatbot, automatizaciones y copias por edición | `backend/core/chatbot.mjs`, `backend/core/automation.mjs` |
| Sincronización de upgrades nuevos | `common/sync_membership_features.py` |

Se preservan licencias/sesiones/equipos aprobados de Comercial, relé exclusivo de ZTATTUZ, identidad Atlantic azul/cian, fuentes nativas, UI Kit, migraciones antiguas y funciones existentes.

## Validación y límites

Las pruebas nuevas se integran en la validación habitual: la etapa SQL `membership_freezes` conserva el contrato histórico y ejecuta también `internal_memberships.mjs` y `early_resume.mjs`; la etapa `freeze_ui_smoke` incluye `membership_editor_smoke.py`. No se omiten gates ni se cambia el número de etapas del creador Windows.

Cobertura interna: planes opcionales, STAFF y nombres arbitrarios, cero ingresos/promedios, valores realmente nulos, acceso repetido y asistencia, ledger sin consumo ilimitado, finanzas/caja, métricas comerciales separadas, desactivación y override, roles y gimnasios ajenos, auditoría, propietario, planes finitos/con cupos, comercial/tiquetera existente, rechazo Wompi y recordatorios, confirmación de enlaces antiguos, persistencia en años posteriores, respaldo y reaplicación.

Cobertura de congelación: inicio real sin extensión anticipada, bloqueo de métodos/override, caso de dos días, confirmación obsoleta, extensión única y acceso inmediato, límite/excepción, cero días al cruzar medianoche, fracciones de 24 horas, ciclos futuros, tiqueteras y reentrada diaria, deadline exacto, finalización tardía máxima siete, snapshots y morosos durante congelación, permisos/RLS, reintentos simultáneos en una conexión, auditoría no financiera, respaldo, otra zona/DST y actualización de eventos históricos poblados. Tk real comprueba controles, escalas 100/125%, confirmación/cancelación y el valor del servidor al reanudar. Backend comprueba ausencia de links/botones de pago y recordatorios internos, consentimiento y fecha corregida después de reanudar.

Los resultados completos de esta revisión se conservan en `evidence/closure-validation-20261008/*/all-internal-resume-20261013-v2/`. El intento `v1` conserva fallos detectados antes de su corrección; consultar `v2` para el estado final. El resumen consolidado conserva la procedencia de cada etapa: `evidence/membership-features-20261013/summary.json`. Se aprobaron 38 etapas locales por edición, 499 pruebas Python y 74 tests del backend por edición; las correcciones se repitieron y los fallos anteriores se conservaron. El helper Linux agrega una etapa de migraciones; el creador Windows mantiene sus 37 etapas.

Son pruebas locales de PostgreSQL PGlite, transporte/Vault ficticios, Python y Tk en Linux con hardware simulado. Ejecutar x86 como código Python en este host no prueba un proceso Windows de 32 bits. No acreditan dos sesiones PostgreSQL reales, despliegue remoto, Meta/Wompi reales, Windows ni lector/relé físicos para estos cambios. Los instaladores publicados anteriormente corresponden al código anterior y no incluyen esta ampliación.

Los requisitos originales se conservan en `REQUISITOS_PLANES_INTERNOS.txt` y `REQUISITOS_REANUDACION.txt`. Decisiones posteriores: el nombre elegido es STAFF y se cuentan sólo días completos de 24 horas.
