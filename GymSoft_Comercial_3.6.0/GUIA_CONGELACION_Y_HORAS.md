# Operación y despliegue de la actualización en desarrollo

Este documento acompaña código fuente en desarrollo. No es un instalador final.

## Congelar una membresía

Abra Clientes y pagos, seleccione la membresía y abra «Membresía y congelación». El botón CONGELAR 7 DÍAS aparece cuando existe un ciclo vigente elegible, quedan entradas si es una tiquetera, la política lo permite y no se alcanzó el máximo. Recepción puede usar la opción ordinaria. Administración puede configurar el gimnasio o el plan, justificar una excepción o cancelar una congelación.

La confirmación avisa que se bloquean entradas y se extiende el vencimiento. Se registra el usuario real de la sesión. Una petición repetida o simultánea no suma una nueva semana: el servidor utiliza una clave idempotente, bloqueo por cliente y restricciones únicas. El máximo inicial es una congelación por ciclo, incluso si una congelación previa se canceló. La excepción administrativa exige motivo.

Congelar el 8/10/2026 un ciclo que vencía el 20/10/2026 produce: CONGELADA hasta el 14/10, reactivación el 15/10 y vencimiento el 27/10. Durante esos días se niega huella, código, búsqueda manual y override ordinario de ingreso; no se abre el relé. La reactivación del acceso depende del día local y no necesita que un PC permanezca abierto. El proceso del servidor registra la finalización.

La tiquetera extiende vigencia y conserva cupos. Después de reactivación se mantiene un consumo máximo por día del gimnasio; una reentrada autorizada el mismo día no descuenta otro cupo. Si se cancela antes del final, se conservan los días completos ya congelados y se revierte la extensión de los días que no se congelarán. El motivo queda auditado. La congelación no concede ingreso después del vencimiento: no implementa prórroga.

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

Se entregan copias ACTUALIZAR_CONSUMO_DIARIO.sql, ACTUALIZAR_MARKETING.sql, ACTUALIZAR_CONGELACION_Y_HORAS.sql y ACTUALIZAR_SCHEDULER.sql en cada edición. No ejecutar migraciones antiguas fuera de orden después de congelación: podrían reemplazar wrappers del motor. Las migraciones nuevas se registran y verifican en cada proyecto por separado.

Desplegar `backend/index.ts` como función `marketing` con sus dependencias handler/core. La validación JWT de gateway se deshabilita exclusivamente porque la función realiza autenticación propia: JWT verificado para Administración, HMAC para Meta, firma y consulta canónica para Wompi, token privado para jobs y estado idempotente para OAuth. No exponer service_role a un cliente ni convertir service RPCs en APIs para authenticated.

Después, como operador del servidor, ejecutar `marketing_service_install_scheduler` con la URL pública del proyecto. Genera el token en Vault y programa dos jobs por minuto: Marketing y finalización de congelación. Comprobar cron.job, respuestas pg_net y GET /functions/v1/marketing/health. Un health verde sólo confirma infraestructura; no acredita un mensaje ni un pago real.

Conservar las capacidades de envío, chatbot, automatizaciones y pagos desactivadas hasta configurar las cuentas y el piloto. Volver a calcular hashes históricos tras el despliegue y revisar advisors de seguridad/performance sin cambiar timestamps históricos indiscriminadamente.

## Autorización de Meta y piloto Wompi

`onboarding/index.html` es la página estática lista para un dominio HTTPS del titular. Se genera con `node common/build_onboarding.mjs`; permite únicamente los dos backends revisados. Configurar ese dominio y el Login for Business oficial en Meta. Registrar app ID, configuration ID, secreto y verify token en Vault mediante `deployment/configure_meta.mjs`, desde un entorno privado de operador. El script lee variables de entorno, no imprime secretos y no forma parte del login de los clientes. Las credenciales no se envían por chat ni se incluyen en el paquete.

En Marketing → WhatsApp, «Conectar» abre el estado de diez minutos, autoriza el negocio y enlaza el número correcto. Comprobar elegibilidad de Coexistence en la cuenta, plantilla aprobada, envío al destinatario de prueba autorizado, webhook de entrega, respuesta del chatbot y pausa por atención humana. El dominio de autorización debe estar publicado y registrado antes de este piloto.

En Marketing → Pagos online, «Configurar Wompi» recibe las cuatro llaves Sandbox del titular por el formulario de conexión. La base las guarda en Vault. Configurar el webhook que devuelve la conexión y usar exclusivamente el cliente PRUEBA Integraciones. Un pago aprobado debe producir una sola renovación, cero ingreso contable real en Sandbox y timestamps originales de proveedor conservados como instantes. Repetir el webhook debe ser idempotente. Probar también una renovación mientras ese cliente ficticio está congelado. No habilitar producción ni hacer cobros a clientes reales en estas pruebas.

## Pruebas y compilación

PREPARAR_PRUEBAS.bat instala dependencias. `python run_validation.py` ejecuta Python, contratos RPC, SQL PostgreSQL local, backend, recorrido biométrico simulado, jornada completa y UI. Linux utiliza pantalla de prueba; Windows necesita escritorio disponible. El runtime incorpora tzdata para ZoneInfo en Windows.

Además de la validación local, conservar evidencia de dos sesiones PostgreSQL concurrentes, piloto Meta/Wompi, relé y lector físicos. El ensayo local Promise.all usa un motor PGlite de una sesión y no acredita dos PCs reales. `release_readiness.json` empieza bloqueado. Sólo marcar cada comprobación como pasada con su evidencia existente y la versión correspondiente. `build_windows.py` rechaza el instalador final hasta satisfacer este control; luego exige Python 3.13 de la arquitectura correcta, repite las pruebas y verifica el ejecutable. No se ha ejecutado la compilación final en esta revisión.
