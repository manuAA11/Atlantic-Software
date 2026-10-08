# Gym soft · Correcciones 3.0.2

Esta versión corrige el problema de ventanas invisibles durante el arranque en Windows:

- Administración y Recepción mantienen visible su ventana raíz mientras se solicita la cuenta.
- La pantalla de correo y contraseña se muestra al frente y no queda detrás de Visual Studio Code.
- El instalador asigna explícitamente `icono.ico` a los accesos directos de Administración y Recepción.
- La versión sube a 3.0.2 para forzar una actualización limpia sobre instalaciones 3.0.1.

El esquema de Supabase sigue siendo `3.0.0`; no se debe volver a ejecutar la migración SQL por este cambio de aplicación.
