# Gym soft Comercial 3.1.1 · Instalación y actualización

Esta entrega contiene el código completo de Administración, Recepción y Control comercial, el icono GS, los archivos SQL y el generador de instaladores para Windows. Los ejecutables se generan en tu equipo; no vienen compilados dentro de este ZIP.

## Actualizar tu instalación

1. Cierra Administración, Recepción y el panel del propietario.
2. Extrae el ZIP en una carpeta nueva llamada `GymSoft_Comercial_3.1.1`.
3. Ejecuta `CREAR_INSTALADORES.bat`. Necesitas Python 3.13 de 64 bits, Inno Setup 6 y conexión a internet. El proceso instala las dependencias y realiza las comprobaciones automáticas antes de compilar.
4. Abre `salida/GymSoft_Instalar_o_Actualizar_3.1.1.exe` para actualizar Administración y Recepción.
5. En tu equipo, instala también `salida/GymSoft_Propietario_PRIVADO_3.1.1.exe` para actualizar el panel y su acceso directo.
6. Abre las aplicaciones desde los accesos que crea el instalador. Comprueba que indiquen la versión 3.1.1.

El instalador conserva la carpeta de instalación anterior y actualiza los accesos directos. El icono se guarda como `GymSoft-3.1.1.ico` en una ruta permanente y también se integra en los tres ejecutables. La comprobación de compilación se detiene si falta el icono de alguno.

No copies un EXE suelto desde `dist`: necesita los archivos que lo acompañan. Entrega el instalador de `salida` al gimnasio.

## Base comercial

El 7 de septiembre de 2026 se comprobó que el proyecto `bawrakwhzkxmhmgkczqu` ya tiene el editor SQL 3.1.0. Las firmas, cuerpos de código y configuración de las 124 funciones comerciales coinciden con la base incluida en esta entrega, tras normalizar los saltos de línea.

**Esta actualización de la aplicación a 3.1.1 no necesita ejecutar SQL nuevo en ese proyecto. No vuelvas a ejecutar `INSTALAR_BASE_NUEVA.sql`.** La comprobación remota fue de lectura: no se crearon pagos ni se borraron datos de tus gimnasios.

El archivo `ACTUALIZAR_EDITOR_PROPIETARIO_3.1.0.sql` se conserva para instalaciones comerciales anteriores que todavía no tengan el editor. `INSTALAR_BASE_NUEVA.sql` se utiliza únicamente al preparar otro proyecto nuevo y vacío.

## Qué entregar a un gimnasio

Entrega únicamente `GymSoft_Instalar_o_Actualizar_3.1.1.exe`, junto con el correo y el código de activación que hayas asignado. El identificador del gimnasio se crea desde tu panel y se obtiene al iniciar sesión; el cliente no tiene que escribirlo ni modificar la conexión.

Conserva para ti el ZIP de código y el instalador privado del propietario.

## Cambios de esta entrega

- Textos, títulos, estados y botones revisados en las tres aplicaciones.
- Avisos claros cuando una operación no se pudo confirmar, con indicaciones para revisar el resultado antes de repetirla.
- Registro de fallos de interfaz con una referencia para soporte, sin incluir el contenido de los registros o las credenciales.
- Se mantienen las correcciones de pagos, los gastos de Recepción, el editor del propietario, los respaldos, las importaciones, las asignaciones de correo y la eliminación de gimnasios.
- Se conserva «Created by Manuel Cuéllar» con Instagram, WhatsApp y correo. Se añade «© 2026 Manuel Cuéllar. All rights reserved.» en Configuración, en las propiedades de los EXE y en `COPYRIGHT.txt`.

## Validación antes de la primera venta

Las suites locales pasaron. El detalle está en `VALIDACION_3.1.1.md`. La compilación y la prueba gráfica en Windows deben completarse en tu equipo; este entorno no permite certificar cómo se ven los accesos directos o las ventanas instaladas.

Con un gimnasio de prueba, valida en dos equipos el inicio de sesión de Administración y Recepción, la autorización de los equipos, un cliente, un pago y su corrección, un gasto, la actualización entre aplicaciones y una mensualidad desde tu panel. Descarga un respaldo y prueba su restauración en otro gimnasio de prueba suspendido. Confirma los iconos al finalizar la instalación y después de actualizar una versión anterior.

**WhatsApp automático requiere activación independiente.** El proyecto comercial no tiene desplegado un servicio de envío. Las pantallas permiten preparar la configuración, pero no acreditan que los mensajes se estén enviando. Antes de ofrecer esa función se necesitan el servicio, las credenciales y las plantillas correspondientes. Los lectores físicos también requieren una prueba con el equipo que usará cada gimnasio.

Created by Manuel Cuéllar. Instagram: @manuelcuellar11  
WhatsApp: +57 3162990884 · Correo: manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
