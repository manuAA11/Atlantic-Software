# Operación y despliegue de la actualización en desarrollo

Este documento acompaña código fuente en desarrollo. No es un instalador final.

## Congelar una membresía

Abra Clientes y pagos, seleccione al cliente y abra «Membresía y congelación». CONGELAR 7 DÍAS aparece para una membresía comercial vigente elegible. Recepción puede congelar según la política; Administración y el propietario autorizado pueden reanudar antes, configurar la política y justificar una excepción.

Los eventos nuevos comienzan en el instante real del servidor y tienen un máximo de siete períodos de 24 horas. Congelar bloquea las entradas y el relé, pero no suma días al vencimiento todavía. REANUDAR MEMBRESÍA consulta al servidor y confirma los días completos efectivamente utilizados; la confirmación se invalida si ese número cambió. Una nueva congelación sigue contando para el límite de una por membresía aunque se reanude el mismo día. La excepción exige motivo.

Ejemplo: congelar el 20/10/2026 a las 09:00 de Bogotá, con vencimiento original 30/10, y reanudar el 22/10 a las 09:00 agrega dos días: vence el 01/11. Congelar a las 23:00 y reanudar a las 08:00 del día siguiente agrega cero días. Si se cumplen los siete días, se agregan siete una sola vez; un scheduler tardío no agrega más días. La consulta de acceso también completa eventos vencidos antes de decidir el ingreso.

Las tiqueteras conservan cupos y consumo anterior; al reanudar, una reentrada del mismo día local no consume otro cupo. Los ciclos futuros ya comprados se desplazan por la extensión real al cerrarse la congelación. Reanudar no genera un pago. El historial guarda inicio, plazo máximo, instante real de cierre, días utilizados, actor, motivo y fechas original/nueva. Los eventos anteriores mantienen sus datos y su extensión preaplicada; al cerrarlos se ajustan únicamente los días pendientes.

STAFF se crea como plan **Interno / No comercial**, normalmente con precio cero, acceso ilimitado y vigencia indefinida. No hay fechas ni cupos ficticios, cobros, deuda, renovación, congelación ni recordatorios financieros. Administración puede desactivarlo inmediatamente. Sus asistencias se registran y se muestran separadas de los indicadores comerciales. La clasificación depende del tipo del plan, no del nombre. Consulte `docs/MEMBRESIAS_STAFF_REANUDACION.md`.

## Calendario e historial

PostgreSQL es la fuente de instantes de eventos. TIMESTAMPTZ conserva el instante; DATE conserva vencimiento, inicio y día local de consumo. La UI convierte el instante a la zona IANA del gimnasio. Los eventos de WhatsApp, Wompi y chatbot también se incluyen en el registro general de actividades con el mismo reloj de servidor y responsable cuando está disponible. ZTATTUZ se configura en America/Bogota mediante migración; Comercial mantiene la zona de cada gimnasio, con Bogotá como default para nuevos registros sin zona.

02:30 UTC del 8 de octubre corresponde a 21:30 del 7 de octubre en Bogotá. 9 AM Bogotá corresponde a 14 UTC. Los horarios de automatización se interpretan por gimnasio y también se prueban con otra zona y cambio de horario estacional. Un recordatorio tres días antes de un vencimiento extendido al 27 se programa para el 24.

No volver a etiquetar UTC con una zona local ni convertir los datos históricos dos veces. Las fechas sin hora no representan eventos. La importación de un campo de instante requiere hora y offset; una fila ambigua debe corregirse desde su fuente antes de importar. Los respaldos actuales conservan timestamps e historial de congelación; restaurar un respaldo no vuelve a sumar días. La base SQLite antigua se conserva para lectura/migración de respaldos; las aplicaciones actuales operan con CloudDatabase/ReceptionDatabase.

## Orden de despliegue

Antes de ejecutar, revisar schema real, historial de migraciones y hashes de audit_logs/memberships/checkins. No instalar el schema inicial sobre una base existente. Estos archivos se validan como upgrades aditivos y transaccionales:

1. `supabase/migrations/20261003035126_daily_tickets_timezone.sql`: timezone, reloj y consumo diario.
2. `supabase/migrations/20261003124254_marketing_automation.sql`: WhatsApp, chatbot, automatizaciones y Wompi.
3. `supabase/migrations/20261008024020_membership_freezes_time_pipeline.sql`: congelación y pipeline temporal.
4. `supabase/migrations/20261008031059_marketing_server_scheduler.sql`: scheduler de servidor y health.

Se entregan copias ACTUALIZAR_CONSUMO_DIARIO.sql, ACTUALIZAR_MARKETING.sql, ACTUALIZAR_CONGELACION_Y_HORAS.sql y ACTUALIZAR_SCHEDULER.sql en cada edición. No ejecutar migraciones antiguas fuera de orden después de congelación: podrían reemplazar wrappers del motor. Las migraciones nuevas se registran y verifican en cada proyecto por separado. También hay dos upgrades posteriores: `20261013090000_internal_plans.sql` y `20261013091000_early_resume.sql`, en ese orden, con sus copias `ACTUALIZAR_PLANES_INTERNOS.sql` y `ACTUALIZAR_REANUDACION_MEMBRESIAS.sql`. Aplicar únicamente los pendientes; no ejecutar de nuevo una migración antigua después de ellos.

Desplegar `backend/index.ts` como función `marketing` con sus dependencias handler/core. La validación JWT de gateway se deshabilita exclusivamente porque la función realiza autenticación propia: JWT verificado para Administración, HMAC para Meta, firma y consulta canónica para Wompi, token privado para jobs y estado idempotente para OAuth. No exponer service_role a un cliente ni convertir service RPCs en APIs para authenticated.

Después, como operador del servidor, ejecutar `marketing_service_install_scheduler` con la URL pública del proyecto. Genera el token en Vault y programa dos jobs por minuto: Marketing y finalización de congelación. Comprobar cron.job, respuestas pg_net y GET /functions/v1/marketing/health. Un health verde sólo confirma infraestructura; no acredita un mensaje ni un pago real.

Conservar las capacidades de envío, chatbot, automatizaciones y pagos desactivadas hasta configurar las cuentas y el piloto. Volver a calcular hashes históricos tras el despliegue y revisar advisors de seguridad/performance sin cambiar timestamps históricos indiscriminadamente.

## Autorización de Meta y piloto Wompi

`onboarding/index.html` es la página estática lista para un dominio HTTPS del titular. Se genera con `node common/build_onboarding.mjs`; permite únicamente los dos backends revisados. Configurar ese dominio y el Login for Business oficial en Meta. Registrar app ID, configuration ID, secreto y verify token en Vault mediante `deployment/configure_meta.mjs`, desde un entorno privado de operador. El script lee variables de entorno, no imprime secretos y no forma parte del login de los clientes. Las credenciales no se envían por chat ni se incluyen en el paquete.

En Marketing → WhatsApp, «Conectar» abre el estado de diez minutos, autoriza el negocio y enlaza el número correcto. Comprobar elegibilidad de Coexistence en la cuenta, plantilla aprobada, envío al destinatario de prueba autorizado, webhook de entrega, respuesta del chatbot y pausa por atención humana. El dominio de autorización debe estar publicado y registrado antes de este piloto.

En Marketing → Pagos online, «Configurar Wompi» recibe las cuatro llaves Sandbox del titular por el formulario de conexión. La base las guarda en Vault. Configurar el webhook que devuelve la conexión y usar exclusivamente el cliente PRUEBA Integraciones. Un pago aprobado debe producir una sola renovación, cero ingreso contable real en Sandbox y timestamps originales de proveedor conservados como instantes. Repetir el webhook debe ser idempotente. Probar también una renovación mientras ese cliente ficticio está congelado. No habilitar producción ni hacer cobros a clientes reales en estas pruebas.

## Pruebas y compilación

PREPARAR_PRUEBAS.bat instala dependencias. `python run_validation.py` ejecuta Python, contratos RPC, SQL PostgreSQL local, backend, recorrido biométrico simulado, jornada completa y UI. Linux utiliza pantalla de prueba; Windows necesita escritorio disponible. El runtime incorpora tzdata para ZoneInfo en Windows.

Además de la validación local, conservar evidencia de dos sesiones PostgreSQL concurrentes, piloto Meta/Wompi, relé y lector físicos. El ensayo local Promise.all usa un motor PGlite de una sesión y no acredita dos PCs reales. `release_readiness.json` empieza bloqueado. Sólo marcar cada comprobación como pasada con su evidencia existente y la versión correspondiente. `build_windows.py` rechaza el instalador final hasta satisfacer este control; después usa el Python compatible de la arquitectura correcta, repite las pruebas y verifica el ejecutable. Esta tarea entrega únicamente cambios de código y se genera además la entrega de instaladores para configuración y pruebas autorizada posteriormente por el usuario.
