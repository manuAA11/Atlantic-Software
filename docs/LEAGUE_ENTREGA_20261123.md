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

- [Windows 45287062408](https://github.com/manuAA11/Atlantic-Software/actions/runs/45287062408): los tres perfiles aprobaron. Instalación, actualización y desinstalación x64 aprobadas en Windows efímero. x86 compilado y diagnosticado; instalación nativa Windows32 pendiente.
- [Validación aislada 45287062246](https://github.com/manuAA11/Atlantic-Software/actions/runs/45287062246): aprobada, incluidos PostgreSQL concurrente, restauración de fixtures, compilación móvil y navegador.
- [Publicación 45287062196](https://github.com/manuAA11/Atlantic-Software/actions/runs/45287062196): aprobada.
- [Descargas completas 45290919023](https://github.com/manuAA11/Atlantic-Software/actions/runs/45290919023): los tres instaladores fueron descargados y comprobados con el actualizador de producción. Tamaños y SHA-256 coinciden con el manifiesto de compilación y los metadatos de GitHub. Esta comprobación no ejecuta instaladores.
- [Descargar 3.8.9](https://github.com/manuAA11/Atlantic-Software/releases/tag/atlantic-gym-3.8.9-piloto): actualización opcional beta, NO FINAL.
- Core ofrece las dos arquitecturas de ZTATTUZ al gimnasio existente, con canal beta y política OPTIONAL. El snapshot SQL alojado devolvió 3.8.9 para cada arquitectura en pruebas revertidas. No quedaron equipos de prueba. Licencia, configuración y suscripción se conservaron.

La primera ejecución Windows 45286300367 detectó una variable de estado del editor que ocultaba el método nativo de la ventana. Se corrigió en el commit `d8c3bc17f4658daff7a6a2c034db03b430431fcc`, que es la fuente exacta de los instaladores aprobados. Las evidencias originales del fallo se conservan.

### Aplicación móvil publicada

La nueva interfaz está publicada en [Atlantic League](https://atlantic-league.atlanticsoftware11.workers.dev). La ejecución [Cloudflare 45286300321, intento 2](https://github.com/manuAA11/Atlantic-Software/actions/runs/45286300321) aprobó la autorización, el despliegue y la comprobación HTTPS de recursos, rutas SPA, manifiesto, service worker, CORS y autenticación. Cloudflare asignó la versión `c781b2ac-61f4-4a97-b93d-f3eed5fe91ca`; la fuente exacta de la web es `09e454ba2e1870b6ee74e4e0991b7225e169c0de`. Los cambios posteriores del editor Tk no cambian esa web.

Se abrió la aplicación publicada con la sesión existente del propietario: la consulta de membresía, agenda y dos rutinas asignadas cargaron correctamente. El enlace del botón correspondiente apuntó al WhatsApp configurado del gimnasio. La agenda muestra las actividades publicadas y no ofrece creación o edición de eventos al socio. Se activó la actualización del service worker y se comprobó la reapertura de la sesión en el mismo navegador. No se envió ningún mensaje, se registró un pago ni se creó o canceló una reserva/solicitud.

La sesión temporal de Wrangler cerró correctamente después de la publicación. La comprobación del navegador es una aceptación alojada con la sesión existente; no sustituye las pruebas físicas de instalación, reapertura y push en iPhone/Android.

No se habilitaron nuevos socios ni se amplió la lista del piloto. League sigue siendo opcional. Meta/Wompi no se activaron. La aceptación del equipo instalado, Windows32 nativo, lector/relé y teléfonos físicos sigue pendiente. No se declara terminada la salida general a producción.

Los resultados estructurados están en [evidence/league-delivery-3.8.9.json](../evidence/league-delivery-3.8.9.json).
