# Actualización Gym soft 3.1.0

Esta entrega añade el editor del propietario y el contacto en **Administración → Configuración**:

> Created by Manuel Cuéllar. Instagram: @manuelcuellar11  
> WhatsApp: +57 3162990884 · Correo: manuel411cm@hotmail.com

## Estado de la base comercial

La actualización SQL está preparada en `ACTUALIZAR_EDITOR_PROPIETARIO_3.1.0.sql`.

**Todavía no está instalada.** La revisión automática rechazó aplicarla directamente en `bawrakwhzkxmhmgkczqu` porque modifica funciones/permisos y añade controles de escritura sobre múltiples tablas de una base real, incluidas operaciones de importación y borrado. Su aplicación requiere tu autorización específica. No se modificaron ni eliminaron gimnasios reales.

El SQL completo se adjunta para revisión. La actualización instala las funciones y controles; las acciones de importar o borrar se ejecutan después, sólo cuando tú las solicitas desde el panel. El editor comprueba que la base tenga la versión adecuada antes de abrirse.

**No vuelvas a ejecutar `INSTALAR_BASE_NUEVA.sql` ni `HABILITAR_PROPIETARIO.sql` en la base ya instalada.**

## Después de autorizar y aplicar la actualización SQL

1. Cierra los programas de Gym soft. Extrae `GymSoft_Comercial_3.1.0_COMPLETO.zip` en una carpeta nueva.
2. Puedes abrir tu panel desde `ABRIR_PANEL_PROPIETARIO.bat` dentro de esa carpeta.
3. Para actualizar los programas instalados y sus accesos, ejecuta `CREAR_INSTALADORES.bat` en Windows con Python 3.13 de 64 bits e Inno Setup 6.
4. Espera a que terminen las pruebas y la compilación. Se abrirán ventanas de prueba que se cierran solas; no usan cuentas ni datos reales.
5. Instala `salida/GymSoft_Instalar_o_Actualizar_3.1.0.exe` para Administración/Recepción y `salida/GymSoft_Propietario_PRIVADO_3.1.0.exe` para tu panel.
6. Abre los accesos nuevos y confirma versión 3.1.0. El panel del propietario, su ZIP y este código completo son privados; al gimnasio se entrega únicamente el instalador de clientes.

**El ZIP contiene código completo y el constructor de instaladores; no contiene EXE ya compilados.** Los iconos de los EXE y la interfaz Windows se comprueban al compilar en tu equipo.

## Uso del editor

Selecciona un gimnasio en el panel y pulsa **Editor del propietario**.

| Pestaña | Acciones |
| --- | --- |
| Gimnasio y correos | Editar nombre/contacto/zona/plan, asignar correo a Administración o Recepción, cambiar rol y revocar invitaciones pendientes. |
| Registros | Buscar, editar y eliminar registros operativos con motivo e historial. Los IDs están protegidos y las dependencias bloquean eliminaciones incompletas. |
| Base de datos y eliminación | Descargar JSON, importar/restaurar datos operativos y eliminar completamente el gimnasio. |

Para asignar correos, una cuenta confirmada recibe el rol elegido conservando su contraseña. Para un correo nuevo se genera un código de activación. Entrégalo a esa persona; debe crear/confirmar su cuenta y usarlo. Su equipo sigue necesitando autorización. No se envían invitaciones por correo automáticamente.

Antes de importar o eliminar completamente, suspende o cancela el gimnasio desde el panel principal. Guarda la copia que el editor solicita y escribe exactamente el nombre del destino. **Cancelar conserva datos; Eliminar los borra.** Las identidades globales de inicio de sesión quedan sin gimnasio y sin acceso; la copia descargada queda en tu PC.

La importación admite respaldos JSON de Gym soft de hasta 20 MB / 25.000 filas. Reemplaza datos operativos conservando el Gym ID, contrato y cuentas del destino. El historial previo se conserva. WhatsApp queda pausado. Consulta `README_COMERCIAL.md` para los límites y la recuperación desde respaldos.
