# Guía rápida del propietario

Para actualizar la versión existente, lee primero `LEEME_ACTUALIZAR_3.1.1.md`. El editor SQL 3.1.0 ya está instalado en el proyecto comercial; esta entrega de la aplicación no necesita ejecutar SQL nuevo.

1. Solo si la base comercial está vacía y es la primera instalación: ejecuta `INSTALAR_BASE_NUEVA.sql`. Si ya funciona, NO lo repitas.
2. Crea y confirma tu usuario de Supabase.
3. Ejecuta `HABILITAR_PROPIETARIO.sql` con tu correo.
4. Abre el panel y pulsa **Nuevo gimnasio**.
5. Entrega el código al correo del administrador del gimnasio.
6. Cuando abra Gym soft por primera vez, el equipo aparecerá como **Pendiente**.
7. Entra al gimnasio desde el panel, abre **Equipos** y pulsa **Autorizar equipo**.
8. En **Registrar mensualidad** indica meses y valor. Puedes conservar la referencia generada o escribir el comprobante (mínimo 3 caracteres). Si se reintenta la misma referencia con los mismos datos, no duplica la mensualidad. No registra cobros bancarios: registra dinero que ya recibiste.
9. Para ampliar el contrato usa **Contrato**; para retirar acceso usa **Suspender**, **Desautorizar equipo** o **Deshabilitar usuario**.

La aplicación de cliente no incluye el panel ni las funciones de propietario.

**Reactivar** no regala tiempo: una suscripción vencida necesita una mensualidad o días de gracia. La gracia no levanta una suspensión o cancelación. Los motivos requieren al menos 3 caracteres y los límites deben ser suficientes para los equipos y usuarios activos.

Para un acceso directo con icono propio instala `salida/GymSoft_Propietario_PRIVADO_3.1.1.exe`, generado mediante `CREAR_INSTALADORES.bat`. Es solo para ti; nunca lo entregues al gimnasio.

En **Editor del propietario → Gimnasio y correos** puedes editar el nombre y los datos del gimnasio, asignar el correo de Administración o Recepción y revocar invitaciones pendientes. En **Registros** corriges datos con motivo e historial. En **Base de datos y eliminación** descargas/restauras respaldos JSON y eliminas completamente un gimnasio. Cancelar el contrato mantiene sus datos; eliminar requiere respaldo, suspensión/cancelación y confirmación del nombre.
