# Cambios pendientes de publicación

Fecha de revisión: 8 de octubre de 2026. No se ha publicado una nueva versión.

- Se conserva la implementación de WhatsApp oficial, ocho pantallas de Marketing, automatizaciones, chatbot verificado, Wompi Sandbox y enlaces de renovación.
- Congelación por calendario local: siete días y una vez por ciclo inicialmente; configuración por gimnasio/plan; excepción y cancelación administrativas con motivo; historial, auditoría y respaldo.
- Ingreso denegado durante congelación en el motor común y en el controlador del relé; la tiquetera conserva sus entradas y extiende vigencia sin perder el consumo máximo diario.
- Renovación y recordatorios utilizan el vencimiento extendido. La renovación mantiene la congelación y su historial. El chatbot presenta las fechas de fin de congelación, reactivación y nuevo vencimiento.
- Reloj absoluto de PostgreSQL para eventos; DATE para calendario; presentación en gym.timezone; caché acotada por medianoche local; sin respaldo a la fecha del PC para gastos.
- Corrección de dos causas de horas falsas: truncamiento del offset UTC en presentación e importación de DATE como datetime a medianoche. No se convierten timestamps históricos en masa.
- Actividad de WhatsApp, Wompi y chatbot integrada en la auditoría general, con reloj del servidor, responsable verificado y protección frente a eventos repetidos.
- El detalle de pagos muestra el instante original de la transacción Wompi convertido a la zona del gimnasio; valores sin hora u offset se rechazan.
- Scheduler de servidor cada minuto con pg_cron, pg_net y Vault; reactiva congelaciones aunque las campañas estén deshabilitadas; health comprueba base y scheduler.
- Página de autorización oficial con estado de un uso, validación del backend, CORS y configuración privada en Vault. Ningún secreto de Meta aparece en la página.
- Nuevas pruebas SQL, Python, backend y Tk. Generación de instaladores bloqueada hasta completar la aceptación externa y conservar su evidencia.

Comercial conserva 3.6.0. ZTATTUZ x86/x64 conserva 3.6.1. El incremento de versión y los instaladores finales están pendientes del despliegue y del piloto externo.
