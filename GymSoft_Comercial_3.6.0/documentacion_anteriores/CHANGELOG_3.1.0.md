# Gym soft 3.1.0

- Editor privado con destino fijo por Gym ID, 13 tablas editables y consulta de auditoría/mensajes.
- Edición de nombre, contacto, plan comercial y zona horaria del gimnasio.
- Asignación de correos de Administración/Recepción, cambio de rol, vista de pendientes y revocación de códigos.
- Respaldo GymSoft-CLOUD-2 con datos operativos y contexto comercial, sin secretos de acceso.
- Restauración JSON transaccional, validación de origen, IDs nuevos y reconstrucción de relaciones.
- Confirmaciones de destino y detección de modificaciones posteriores a la copia.
- Borrado completo del gimnasio separado de cancelación; respaldo local obligatorio en la interfaz.
- Ediciones auditadas y control de versiones para evitar guardar sobre una fila modificada.
- Ajuste de inventario al corregir/eliminar ventas y validación de cupos de clases/reservas.
- Coordinación de escrituras por gimnasio en el servidor, conservando RLS, FK y validación de acceso.
- WhatsApp y correo del creador en Configuración de Administración.
- Conserva los iconos GS, diálogos oscuros y funciones anteriores; actualiza accesos a GymSoft-3.1.0.ico.

Estado del despliegue: preparado y probado localmente. La aplicación SQL en el proyecto real fue bloqueada por revisión automática y está pendiente de autorización del usuario.
