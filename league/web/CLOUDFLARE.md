# Publicar Atlantic League en Cloudflare Pages

La distribución `Atlantic_League_Cloudflare.zip` contiene únicamente la web ya
compilada. `index.html`, `sw.js`, `_headers`, `_redirects`, el manifiesto, los
iconos y los recursos están directamente en la raíz del ZIP. No contiene claves
administrativas, una base de datos ni una aplicación de escritorio.

## Subida manual

1. Entra en https://dash.cloudflare.com/ y selecciona tu cuenta.
2. Abre **Workers & Pages** y **Create application**. Elige **Pages** y la
   opción **Direct Upload / Drag and drop / Upload assets**, según el panel.
3. Usa `atlantic-league` como nombre si está disponible. Si ya existe un
   proyecto de League creado por ti, abre ese proyecto y crea una nueva
   publicación de producción en lugar de duplicarlo.
4. Sube `Atlantic_League_Cloudflare.zip` completo. Si el panel exige una carpeta,
   descomprime el ZIP y selecciona la carpeta que contiene `index.html`.
5. Pulsa **Deploy site** o **Save and Deploy** y copia la dirección de producción
   que Cloudflare te entregue. No hay que configurar un comando de compilación
   ni instalar Node para esta subida.
6. Envíame la dirección exacta, incluido `https://`. Esa dirección debe
   registrarse en los orígenes permitidos de los servicios de acceso y datos de
   League, y revisarse en las URLs de autenticación y recuperación de Supabase.

## Conexión pendiente después de subir

La pantalla de instalación puede abrirse inmediatamente. El inicio de sesión y
las consultas al gimnasio requieren registrar el nuevo origen en el backend.
El paquete usa los servicios existentes de Supabase; no vuelve a aplicar SQL
ni cambia membresías o rutinas. Hasta registrar y comprobar el nuevo dominio,
el acceso desde Cloudflare puede ser rechazado por los servicios.

El sitio será público. Los datos del gimnasio siguen requiriendo autenticación
y el piloto conserva las cuentas que ya estaban habilitadas. No se habilitaron
otros socios ni se crearon cuentas al preparar esta distribución.

## Actualizaciones

En el mismo proyecto de Pages, usa **Create a new deployment**, selecciona
producción y sube el siguiente ZIP completo. El proyecto debe ser de subida
directa para usar esta opción del panel; Cloudflare no permite convertir ese
proyecto a integración Git posteriormente. Podemos preparar una integración
Git en un proyecto separado si se decide automatizar las publicaciones.

Al cambiar desde la dirección anterior a `pages.dev`, instala la aplicación
desde la nueva dirección. La sesión y el icono anteriores pertenecen a otro
origen; inicia sesión otra vez en la nueva aplicación. La cuenta permanece
vinculada al mismo perfil del gimnasio.

## Comprobación final

- En navegador móvil: bienvenida e instrucciones para instalar.
- Desde el icono instalado: acceso con cédula y contraseña.
- En computador: experiencia web normal.
- Recargar `/agenda` o `/rutinas` debe conservar la navegación sin un 404.
- Los enlaces de autenticación y recuperación deben usar la nueva dirección.
- Probar cierre, reapertura, persistencia de sesión y una actualización real
  en iPhone y Android; estas comprobaciones físicas siguen pendientes.

La compilación y 27 grupos de pruebas automatizadas pasan. Preparar este ZIP no
equivale a haberlo publicado o validado en teléfonos reales.

Documentación oficial consultada:
- https://developers.cloudflare.com/pages/get-started/direct-upload/
- https://developers.cloudflare.com/pages/configuration/headers/
- https://developers.cloudflare.com/pages/configuration/serving-pages/
