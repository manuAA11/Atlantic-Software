# Gym Soft y ZTATTUZ: actualización en desarrollo

Revisión: 8 de octubre de 2026. Este paquete conserva código fuente, migraciones, pruebas y capturas. No es un instalador final. Las versiones permanecen en Comercial 3.6.0 y ZTATTUZ 3.6.1 x86/x64.

## Resultado y límites actuales

Se continuó WhatsApp oficial, automatizaciones, chatbot y Wompi. La congelación y el reloj del gimnasio están integrados en sus motores compartidos, sin una segunda lógica de membresía. Las Edge Functions marketing se desplegaron en ambos proyectos. Las cuatro migraciones nuevas aún no aparecen aplicadas en los servidores: sus comandos no devolvieron respuesta incluso con 120 segundos de espera, y se comprobó después que no había transacciones de migración activas o bloqueadas ni tablas nuevas instaladas. El entorno local se desconectó temporalmente; el acceso se recuperó para guardar este avance.

No se activaron campañas ni se realizaron cobros reales. Las pruebas locales no sustituyen un piloto con Meta, un pago Wompi externo, dos sesiones PostgreSQL reales o el lector/relay físico. No se marca la actualización como terminada.

## Pruebas ejecutadas

| Edición | Etapas datos | Etapas UI | Python | Congelación SQL | Tiempo SQL | Contratos Marketing |
| --- | --- | --- | --- | --- | --- | --- |
| Comercial | 17 PASS | 16 PASS | 132 PASS | 52 PASS | 55 PASS | 90 PASS |
| ZTATTUZ x86 | 16 PASS | 17 PASS | 147 PASS | 52 PASS | 55 PASS | 87 PASS |
| ZTATTUZ x64 | 16 PASS | 17 PASS | 148 PASS | 52 PASS | 55 PASS | 87 PASS |

Las suites completas suman 99 etapas PASS. Los casos de Python y SQL están incluidos en esas etapas; las columnas no deben sumarse como casos únicos. Backend compartido: 54 tests PASS en cada edición. Los últimos cambios afectados se volvieron a verificar: contratos Marketing 90/87, ocho pantallas Marketing 76 comprobaciones por edición, congelación UI 48 comprobaciones y pipeline SQL 55. Los resultados JSON y sus logs se conservan en evidence/tests; los rechecks finales están en evidence/tests/rechecks.

Los ensayos de SQL usan PGlite. Promise.all comparte una sesión de ese motor y no acredita dos PCs concurrentes. La huella y el relé se prueban con adaptadores simulados. Los smoke tests de Tk se ejecutan en Linux con pantalla de prueba, incluso los que se llaman windows_ui_smoke; la compilación y ejecución Windows físicas siguen pendientes.

## Causa raíz de las horas y corrección

Se corrigió el truncamiento del offset UTC durante presentación y el uso de DATE como datetime a medianoche durante importación. También se encontraron fuentes del reloj del PC en reglas de negocio y cálculo duplicado del estado del cliente. El motor activo de Supabase ahora consulta el reloj del servidor, conserva DATE para calendario y TIMESTAMPTZ para instantes, y convierte una sola vez el instante a gym.timezone. Se usa ZoneInfo; no se reetiqueta un instante UTC como hora local.

Los nuevos eventos de entrada, pago, venta, gasto y auditoría reciben reloj del servidor aunque el escritorio envíe un valor falso. Los eventos de WhatsApp, chatbot y Wompi se integran en Registro de actividades con ese mismo reloj y responsable verificado cuando corresponde. El timestamp original de Wompi se conserva y aparece convertido en el detalle del pago. Una fecha sin hora no se convierte en un evento 00:00 ficticio.

Los usos residuales de hora del PC quedan clasificados como diagnóstico, nombres de archivos o UI cosmética y en la base SQLite antigua de respaldo; no son la fuente de los eventos actuales de negocio. El inventario global está en temporal_inventory.txt y temporal_inventory_current.txt.

No se actualizan masivamente timestamps históricos. Se inspeccionaron tipos y ejemplos reales y se conservaron hashes de audit_logs, memberships y checkins. En la última comprobación, los 30 registros de auditoría comercial y los 1304 de ZTATTUZ y sus hashes seguían iguales al baseline. Esto protege los datos observados; no reconstruye horas que se hubieran perdido históricamente ni atribuye todos los reportes antiguos de medianoche a una sola fila sin evidencia.

| Instante o regla | America/Bogota |
| --- | --- |
| 08/10/2026 02:30:00Z | 07/10/2026 21:30:00 (9:30 PM) |
| 08/10/2026 04:59:59Z | 07/10/2026 23:59:59 |
| 08/10/2026 05:00:00Z | 08/10/2026 00:00:00 |
| Recordatorio 09:00 local | 14:00 UTC |

Las primeras tres conversiones también se verificaron mediante consultas reales de solo lectura en ambos proyectos. El timezone de ZTATTUZ debe quedar America/Bogota al aplicar la migración diaria; antes del despliegue su tabla gyms todavía no contiene esa columna. Comercial usa el timezone de cada gym. Se prueban otra zona y los límites de días, incluidos horarios estacionales.

## Congelación y membresías

Congelar desde el 08/10/2026 bloquea del 8 al 14 inclusive, reactiva el 15 a medianoche local y mueve un vencimiento del 20 al 27. El motor informa FROZEN y deniega huella, código, búsqueda manual y override de acceso. El controlador no solicita apertura del relay ni aunque reciba una respuesta contradictoria.

La política inicial es siete días y una congelación por ciclo, configurable por gym/plan. La excepción y cancelación administrativas exigen motivo. Se guardan responsable real, fechas locales, instantes UTC, días añadidos, estado, motivo, cancelación y finalización. Los eventos son MEMBERSHIP_FROZEN, MEMBERSHIP_FREEZE_COMPLETED, MEMBERSHIP_FREEZE_CANCELLED y CHECK_IN_DENIED_MEMBERSHIP_FROZEN.

La tiquetera conserva entradas y extiende vigencia. El máximo de un consumo por día se calcula con el día del gimnasio. La extensión conserva el tiempo restante y mueve ciclos prepagados para evitar superposición. La renovación Wompi usa el vencimiento extendido y no borra congelación ni historial. Un respaldo/importación conserva el historial sin conceder extensión de nuevo.

Los recordatorios de vencimiento usan la fecha nueva: para vencer el 27, tres días antes es el 24. Se invalidan los mensajes obsoletos y el envío vuelve a comprobar congelación y vencimiento antes de contactar Meta. El chatbot muestra CONGELADA, último día congelado, reactivación y nuevo vencimiento. Cumpleaños y comunicaciones generales mantienen su política propia. No se implementó prórroga.

Se prueban duplicación e idempotencia, máximo uno, override con motivo, cancelación, auditoría, cinco rutas de acceso, conservación de cupos, vencimiento +7, recordatorios, chatbot, renovación e importación. El código usa locks transaccionales y unicidad; queda pendiente demostrarlo con dos sesiones PostgreSQL reales.

## Archivos modificados y añadidos

- common/membership_freezes.sql: políticas, historial, bloqueo transaccional, cancelación, vencimiento, entrada, auditoría y reloj.
- common/gym_time.py y common/server_date.py: instantes aware, calendario IANA y caché del reloj del servidor limitada por medianoche local.
- common/membership_freeze_ui.py: elegibilidad, confirmación, política por plan/gym, excepción, cancelación e historial.
- common/marketing_api.sql y marketing_service.sql: eventos en auditoría general y responsable del vínculo Meta/Wompi.
- common/marketing_payments.sql y marketing_desktop.sql: validación, conservación y exposición del instante original del proveedor.
- common/marketing_scheduler.sql: pg_cron, pg_net, Vault, finalización y health de infraestructura.
- backend/handler.mjs y core: autenticación, chatbot, scheduler, webhook, pagos, estado de salud y onboarding.
- common/marketing_ui.py y copias de marketing_client.py, payment_revision.py, ui_text.py, cloud_database.py, reception_database.py, reception_app.py y app.py en las tres ediciones.
- onboarding/index.html, common/build_onboarding.mjs y deployment/configure_meta.mjs: conexión oficial Meta y configuración privada.
- common/release_gate.py, release_readiness.json y build_windows.py: bloqueo de builds sin aceptación y evidencia de la versión.
- Tests SQL/Python, backend y UI de congelación y tiempo, sincronizados en las tres ediciones.

evidence/changed_files_manifest.json enumera los archivos de código/documentación cambiados respecto al baseline 77ac9fc y sus SHA-256. No enumera binarios originales como si fueran cambios de esta implementación.

## Migraciones preparadas, orden y huellas

| Archivo en supabase/migrations | Bytes | SHA-256 |
| --- | --- | --- |
| 20261003035126_daily_tickets_timezone.sql | 27728 | 9a4f7141fdd6f0738b3ca40af4d90b1d4a880a60ff57ccb225eb29fe8e6677cd |
| 20261003124254_marketing_automation.sql | 91941 | 215892a7b8c24eaf49e9d8586dcfdbf319fb4e4e97bbbed51b3332ab39b7790d |
| 20261008024020_membership_freezes_time_pipeline.sql | 27651 | 8ba8e038eeabf188fbc674d60a80e204638ec9f44ec46c72503181dc85da9a20 |
| 20261008031059_marketing_server_scheduler.sql | 4504 | 07337e955eb5ba76bb7f1730557f72bdcfc1d8aac0e8e6dd81990f1c4c8b6326 |

Las copias ACTUALIZAR_CONSUMO_DIARIO.sql, ACTUALIZAR_MARKETING.sql, ACTUALIZAR_CONGELACION_Y_HORAS.sql y ACTUALIZAR_SCHEDULER.sql están en cada edición. No instalar el esquema inicial sobre una base existente ni ejecutar una migración vieja después de las nuevas. El historial remoto se debe inspeccionar y registrar por proyecto.

## Problemas encontrados y corregidos

- Instantes UTC truncados, fechas importadas como medianoche y respaldo a la fecha del PC para gastos: corregidos en las fuentes y helpers.
- Marketing no aparecía en el registro general: se añadieron productores de actividad del servidor y etiquetas legibles; actualizar SENT dos veces no duplica el evento.
- Estado de cliente inferido de nuevo en escritorio: se consume el resultado autoritativo del motor, incluida congelación.
- Fixtures antiguos no tenían el nuevo reloj ni las respuestas completas de integración: se actualizaron antes de ejecutar las regresiones.
- El bloqueo de release ocultaba el error de arquitectura del Python x64: se ordenó después de comprobar arquitectura y antes de compilar; el último suite x64 pasó 148 tests.
- Un log anterior llamado python_ztattuz_x64_final.log conserva el intento fallido anterior; la evidencia autoritativa más reciente está en evidence/tests/GymSoft_ZTATTUZ_3.6.1_x64/python.log, PASS.
- apply_migration no devuelve resultado ni instala cambios; se comprobó el schema y las sesiones. No se usa execute_sql para eludir el mecanismo de migraciones.

## Cierre pendiente

- Aplicar y verificar las cuatro migraciones; timezone real de ZTATTUZ; scheduler instalado con capacidades de envío y pagos desactivadas.
- Dos sesiones PostgreSQL concurrentes con un cliente ficticio, sin duplicar congelaciones ni consumir dos entradas.
- Publicar y registrar el dominio HTTPS oficial de autorización Meta; configurar la aplicación y el número del titular; validar un mensaje, su webhook, chatbot y automatización con destinatario autorizado.
- Configurar llaves Wompi Sandbox por el formulario privado; validar pago externo, idempotencia, conciliación y renovación mientras está congelado. Sin cobros reales ni habilitación de producción.
- Probar huella y relay físicos, ejecutables Windows de las dos arquitecturas e instalación/actualización.
- Actualizar documentación y evidencia de aceptación, después versión/changelog final e instaladores.

release_readiness.json mantiene todas las aceptaciones externas pendientes. Ningún PASS de simulación se presenta como prueba real de Meta, Wompi, hardware o dos PCs. GUIA_CONGELACION_Y_HORAS.md contiene el procedimiento operativo y de despliegue. Los runtimes e iconos originales permanecen en los paquetes completos previos; este checkpoint de fuente los excluye deliberadamente y no es un instalador.
