# Gym soft · Edición comercial 3.4.5

Empieza por **LEEME_ACTUALIZAR_3.4.5.md**. El paquete contiene Administración, Recepción y el panel privado del propietario, con sus fuentes y generador de instaladores para Windows.

Esta actualización conserva las mismas columnas en ventana mediana y maximizada. Los paneles, gráficos y tablas aprovechan el alto disponible, sin los huecos que dejaba la reorganización anterior. Los encabezados y las barras de acciones conservan su alineación natural. El desplazamiento aparece únicamente cuando el contenido legible excede el espacio disponible. Se mantienen las mejoras de consultas y guardados, la validación de importes y la conservación del formulario de pago ante errores. El Dashboard conserva cuatro rangos prioritarios, sin la tarjeta de más de 30 días. Desde 3.4.0 no requiere ejecutar SQL. La copia original de ZTATTUZ permanece separada.

## Qué incluye el editor

Selecciona un gimnasio y pulsa **Editor del propietario**.

- **Gimnasio y correos:** nombre, contacto, zona horaria, nombre del plan comercial y motivo de modificación. Asigna correos a Administración o Recepción, cambia su rol y consulta las invitaciones pendientes. Puedes revocar un código pendiente.
- **Registros:** búsqueda y paginación de clientes, planes, pagos/membresías, entradas, personal, jornadas, rutinas, ejercicios, clases, reservas, productos, ventas y gastos. Los campos de identidad y relación están protegidos. Mensajes y auditoría son de consulta.
- **Base de datos:** descarga un respaldo JSON completo del gimnasio; importa/restaura los datos operativos desde una copia compatible; elimina completamente un gimnasio con una confirmación diferente de Cancelar contrato.

La edición registra motivo, autor y valores anteriores/nuevos en el historial del propietario. Los pagos conservan su ID e incrementan su revisión. Cambiar la cantidad de una venta ajusta las existencias; eliminar una venta las devuelve. Un registro con dependencias no se borra en cascada desde el editor: resuelve primero sus relaciones o desactívalo.

## Correos de Administración y Recepción

1. Selecciona el gimnasio → **Editor del propietario → Gimnasio y correos → Asignar correo y rol**.
2. Escribe el correo exacto, el rol y el motivo. Confirma el gimnasio y la persona.
3. Si la cuenta ya está confirmada y disponible, se vincula. La persona conserva su contraseña e inicia sesión de nuevo.
4. Si no existe o falta confirmar el correo, el panel genera un código de siete días. Entrégalo a esa persona para crear/confirmar su cuenta y activar su acceso. No se envían correos automáticamente desde el panel.
5. En el panel principal, autoriza su equipo cuando aparezca como pendiente.

Un correo asociado a otro gimnasio no se traslada. La cuenta propietaria no se convierte en una cuenta del gimnasio. Los límites de usuarios se comprueban en el servidor. Habilitar/deshabilitar personas y equipos sigue disponible en las pestañas del panel principal.

## Respaldo e importación

El respaldo **GymSoft-CLOUD-2** incluye tablas operativas, marca, configuración de marketing, auditoría, datos del gimnasio, contrato, mensualidades, usuarios, equipos e historial del propietario. No incluye contraseñas, sesiones, claves de acceso, hashes de equipos ni códigos de invitación. Los archivos externos del PC, como fotos referidas por una ruta, deben conservarse por separado.

La importación admite JSON **GymSoft-CLOUD-1** y **GymSoft-CLOUD-2**, hasta 20 MB y 25.000 filas. No ejecuta archivos SQL. La importación/exportación Excel original sigue disponible en Administración.

Para reemplazar los datos, suspende o cancela primero el gimnasio. El panel muestra origen y destino, valida el archivo, exige guardar una copia del destino y pide escribir su nombre. Se conserva el Gym ID del destino. Se crean nuevos IDs para las filas importadas y se reconstruyen las relaciones. No se copian cuentas, equipos, contratos, mensualidades ni la auditoría del archivo: estos datos permanecen como información de respaldo. El historial existente del destino se conserva y se registra la importación.

Si falta una relación o falla una validación, se revierte toda la importación. Si el destino cambió después del respaldo, se cancela el reemplazo y se pide una copia nueva. Revisa los datos antes de reactivar. WhatsApp queda pausado y los mensajes pendientes importados se marcan para no reenviarse automáticamente.

## Cancelar y eliminar

**Cancelar contrato** retira el acceso y conserva los datos para una posible reactivación.

**Eliminar gimnasio completamente** borra sus tablas operativas, contrato, mensualidades, historial, invitaciones, equipos y asignaciones de usuarios. Requiere gimnasio suspendido/cancelado, respaldo guardado, motivo, nombre exacto y confirmación final. La operación se hace en una transacción. La copia guardada por ti queda fuera de Supabase.

Las identidades globales de Authentication quedan sin gimnasio y sin permiso para acceder a sus datos; no se borran cuentas globales. Recuperar datos operativos requiere crear/seleccionar un gimnasio e importar tu copia. Los accesos y el contrato deben configurarse de nuevo.

## Instaladores y seguridad

`CREAR_INSTALADORES.bat`, en Windows con Python 3.13 de 64 bits, Node.js LTS e Inno Setup 6, genera:

- `salida/GymSoft_Instalar_o_Actualizar_3.4.5.exe`: Administración y Recepción; éste se entrega al gimnasio.
- `salida/GymSoft_Propietario_PRIVADO_3.4.5.exe`: tu panel privado con acceso directo propio.
- `salida/GymSoft_Control_Propietario_3.4.5.zip`: distribución privada alternativa de tu panel.

El constructor integra el icono GS en los tres ejecutables. Los accesos directos usan `GymSoft-3.4.5.ico` en una ruta permanente. Se comprueban los recursos del icono de cada EXE antes de generar el instalador. Se conservan los arreglos de ventanas visibles, diálogos oscuros, pagos editables y gastos de Recepción.

Las acciones de propietario requieren su rol en el servidor. No basta con ocultar botones. Los gimnasios mantienen RLS, relaciones por `gym_id` y comprobaciones de licencia, usuario y equipo. La actualización incorpora coordinación de escrituras por gimnasio para proteger importaciones y eliminaciones simultáneas. El archivo `gymsoft_config.json` sólo lleva URL y clave publicable.

## Primera instalación en otro proyecto comercial vacío

Sólo para una base nueva y vacía: `INSTALAR_BASE_NUEVA.sql` contiene la base completa con el editor 3.1.0. Después crea/confirma la cuenta propietaria y configura su correo en `HABILITAR_PROPIETARIO.sql`. Para una base existente se revisa/aplica únicamente la actualización correspondiente; no se repite la instalación completa.

## Verificación de esta entrega

Consulta **VALIDACION_3.4.5.md** para la cobertura y los resultados. `SIMULAR_GIMNASIO.bat` ejecuta los escenarios de operación, permisos, editor, importación y pantallas usando datos ficticios. El constructor exige que todas estas etapas pasen antes de generar instaladores.

La simulación no contacta gimnasios reales. El motor local ejecuta el SQL comercial y sus reglas; la capa de transporte de pruebas adapta las consultas de Python. La conexión real de red, el correo, el lector físico y los instaladores se comprueban además en Windows. WhatsApp automático requiere activar su servicio y las plantillas.

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
