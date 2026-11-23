# Atlantic Gym 3.8.9 y Atlantic League · 23 de noviembre de 2026

Administración crea, edita, publica, elimina y restaura eventos desde Clases y reservas → Eventos del gimnasio. La app de socios sólo los consulta: no ofrece edición, cupos ficticios ni botones para reservar eventos. Las clases mantienen su flujo de reservas. El servidor impide las escrituras de eventos a socios y entrenadores.

El mismo botón Renovar membresía abre WhatsApp del gimnasio al +57 313 858 5683, destino indicado por el propietario. No envía mensajes automáticamente, registra pagos ni crea solicitudes. No hay un segundo botón de WhatsApp en Perfil. Los planes internos no se renuevan.

Los datos se consultan en el proveedor compartido. La app vuelve a consultarlos al recuperar conexión, volver a primer plano y pulsar Actualizar información. No se modifica el vencimiento ni el saldo de entradas en el dispositivo.

Incluye los cambios pendientes de archivo de rutinas/plantillas/ejercicios propios y configuración de la biblioteca compartida. Se preservan revisiones e historial. La versión 3.8.9 es un candidato beta opcional; los gates externos de entrega final conservan su estado.

## Verificación

- 41 grupos locales de pruebas PWA/SQL/HTTP aprobados y compilación TypeScript/Vite aprobada.
- Cuatro pruebas de los modelos Python aprobadas; sintaxis de las interfaces y adaptador aprobada.
- Migración `20261123230451_league_desktop_events_member_delivery` aplicada en ZTATTUZ.
- Recorrido SQL alojado: creación administrativa → lectura del socio → evento eliminado oculto, en transacción revertida. Ningún evento de prueba permanece.
- Tras esa comprobación: 248 clientes, 432 membresías y dos rutinas; sin cambios por la migración/prueba.
- RPC público con SECURITY INVOKER y ejecución anónima revocada; la implementación privilegiada reside en esquema privado y comprueba rol/gimnasio.

## Publicación y límites

El commit de entrega inicia la validación Windows de Comercial, ZTATTUZ x64 y ZTATTUZ x86; el publicador sólo ofrece la actualización opcional si aprueban los tres perfiles. El despliegue PWA usa la autorización temporal de Cloudflare y su verificación HTTPS. Registrar los resultados definitivos de esas ejecuciones al terminar; este documento no sustituye sus evidencias.

No se habilitan nuevos socios ni se amplía la lista del piloto con esta migración. League sigue siendo opcional. Meta/Wompi no se activan. La aceptación del equipo instalado, Windows32 nativo, lector/relé y teléfonos físicos sigue pendiente.
