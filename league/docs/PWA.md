# Atlantic League para celulares

La entrega principal es una PWA. El código React Native Web reutiliza la lógica existente y se exporta a archivos estáticos. Los proyectos nativos se conservan como alternativa futura; no se necesita EAS, TestFlight ni una cuenta de Apple Developer para instalar la PWA.

## Compilar y alojar

Desde `league`, ejecutar `npm ci`, `npm run typecheck`, `npm test` y `npm run build:pwa`. Servir `mobile/dist-web` en la raíz de un dominio HTTPS. No utilizar el servidor de desarrollo como enlace de instalación. Conservar las cabeceras de `_headers` o configurarlas en el proveedor equivalente. `/sw.js` e `/index.html` deben revalidarse. El manifiesto, el icono y el service worker se generan junto al bundle.

Configurar las tres variables públicas de `mobile/.env.example` con proyectos de QA. Registrar el origen HTTPS exacto en CORS de la pasarela y la raíz del sitio en las URLs de redirección de Supabase Auth. Configurar el enlace de invitación del backend como `https://DOMINIO-PWA/` en lugar del esquema nativo. Nunca incluir una clave privilegiada en el bundle.

## Instalar

- iPhone: abrir el enlace HTTPS en Safari, Compartir, Añadir a pantalla de inicio.
- Android: abrir el enlace HTTPS en Chrome y elegir Instalar aplicación o Añadir a pantalla de inicio según el navegador.

Las fotos se seleccionan mediante las capacidades del navegador. Las historias se dibujan localmente en un lienzo PNG de 1080 × 1920. Compartir utiliza archivos del sistema si el navegador lo permite; en caso contrario descarga la imagen para que el usuario la comparta manualmente. Los botones web de confirmación ya no dependen de Alert de React Native.

## Sesión, desconexión y actualización

IndexedDB conserva la sesión, borradores y cola por usuario con AES-GCM y una clave local no exportable. Esto protege los bytes almacenados; no constituye una barrera frente a scripts maliciosos del mismo origen. El almacenamiento del navegador puede borrarse por el usuario o el sistema; se debe sincronizar regularmente. Safari y la PWA instalada pueden tener almacenes separados: iniciar sesión dentro de la PWA.

El service worker almacena exclusivamente archivos estáticos de la aplicación. No guarda respuestas de Auth, APIs, membresías, evidencias ni reservas. Permite volver a abrir la interfaz sin conexión después de la primera carga. Los entrenamientos se conservan pendientes y la cola se reintenta al recuperar internet. Una reserva, aprobación o marca oficial requiere la respuesta del servidor. La actualización nueva muestra un aviso y espera confirmación para no reiniciar durante un entrenamiento.

## Estado verificable

Compilación web y pruebas TypeScript/SQL/HTTP locales ejecutadas. La revisión visual en el preview HTTP no puede probar WebCrypto ni instalación: ambas necesitan HTTPS. Las pruebas de navegador del repositorio incluyen reapertura del borrador, carcasa sin internet y dimensiones reales del PNG; no atribuir PASS hasta ejecutarlas en CI. Sigue pendiente el piloto físico en iPhone/Android y la conexión con la cuenta del propietario sobre infraestructura aislada.

El piloto limitado ya aplica las migraciones aditivas en los proyectos existentes y vincula únicamente la cuenta confirmada del propietario. El sitio privado está publicado; el recorrido físico de aceptación sigue pendiente.

## Apariencia y revisión 0.2.0

Perfil permite activar el modo oscuro y conserva la preferencia al volver a abrir. Los iconos se dibujan con SVG en web; no necesitan descargar una fuente. La altura sigue el viewport visible y la navegación mantiene Inicio, League, Agenda, Rutinas y Perfil. Las historias ofrecen enlaces directos para descargar el PNG o abrir la imagen cuando el navegador no completa el guardado automático. En iPhone, abrir la imagen permite usar las opciones de guardado del sistema.
