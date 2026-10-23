# Desarrollo e instalación en iPhone

El proyecto tiene perfiles EAS, pero todavía no existe un build firmado ni una instalación probada en un iPhone real.

## Preparación

1. Crear el entorno Supabase aislado descrito en DESPLIEGUE.md y probar la pasarela con datos sintéticos.
2. Copiar mobile/.env.example a mobile/.env. Las tres variables de conexión son publicables; nunca usar service_role/sb_secret en Expo.
3. En Auth del hub habilitar confirmación de correo, configurar SMTP de pruebas y permitir atlanticleague://auth en las URLs de retorno. Establecer contraseña mínima de 12 caracteres.
4. Entrar en la cuenta Expo del propietario, crear/enlazar el proyecto Atlantic League y completar EXPO_PUBLIC_EAS_PROJECT_ID. No compartir contraseñas ni códigos de verificación con el código fuente.
5. Confirmar que com.atlantictech.league sea el identificador disponible y deseado en la cuenta Apple antes del primer registro; puede ajustarse en app.json antes de publicarlo.

## Desarrollo local

    cd league
    npm ci
    npm run mobile

La demostración no necesita servicios. La función de captura usa módulos nativos; probarla con un development build del SDK indicado. El navegador sirve para revisar el mismo código de interfaz y los flujos simulados; no acredita cámara, SecureStore ni compartir de iOS.

## Build de desarrollo

Con EAS CLI disponible en su versión verificada al ejecutar, autenticar la cuenta y registrar el iPhone:

    cd league/mobile
    eas build:configure
    eas device:create
    eas build --platform ios --profile development

La distribución interna a un iPhone físico necesita firma y un perfil que incluya el dispositivo. No confundirlo con el perfil simulator, que sólo sirve para el simulador de iOS.

## TestFlight

Se necesita acceso a Apple Developer y App Store Connect del propietario, identificador registrado y un registro de app. Introducir los valores publicables del entorno aislado en el entorno preview de EAS:

    eas build --platform ios --profile testflight
    eas submit --platform ios --profile testflight --latest

Aceptar y revisar el build en TestFlight desde el propio iPhone. No enviar todavía a revisión pública ni cambiar el entorno de producción. La configuración de cifrado debe revisarse para la distribución final; en esta fase sólo se utilizan las bibliotecas estándar del sistema y HTTPS.

## Android

    eas build --platform android --profile preview

El perfil preview genera APK para pruebas. production prepara la distribución en tiendas una vez superados el piloto, privacidad, permisos y revisión de publicación.

La aprobación de vinculaciones, membresía y reservas requiere conexión al servidor. Los entrenamientos se conservan localmente cuando se pierde Internet y se reintentan con la misma identidad.
