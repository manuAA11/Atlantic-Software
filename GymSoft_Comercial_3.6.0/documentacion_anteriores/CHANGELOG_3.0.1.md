# Gym soft · Correcciones 3.0.1

Esta versión corrige dos problemas de la distribución de Windows:

- PyInstaller y el instalador usan `icono.ico` para Administración, Recepción y el panel del propietario.
- Un error de autenticación, confirmación de correo, invitación, conexión o licencia muestra el motivo y permite reintentar; ya no cierra la aplicación silenciosamente.
- La ventana de inicio de sesión se muestra al frente aunque el root principal esté oculto mientras se comprueba la cuenta.
- Después de crear una cuenta y confirmar el correo, el flujo vuelve directamente al inicio de sesión.
- Los errores de inicio se registran en `%LOCALAPPDATA%\\GymSoft\\logs\\inicio.log` sin guardar contraseñas ni sesiones.

El esquema de Supabase sigue siendo `3.0.0`; no se debe volver a ejecutar la migración SQL por este cambio de aplicación.
