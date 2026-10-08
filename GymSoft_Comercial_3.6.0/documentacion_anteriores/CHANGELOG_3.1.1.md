# Gym soft Comercial 3.1.1

## Presentación

- Se unifican títulos y botones en español: Resumen, Consultar y editar pagos, Corregir el pago seleccionado, Logotipo y Copia de seguridad.
- Los estados de los registros y las acciones del historial del propietario se presentan con nombres comprensibles. La traducción se limita a la interfaz y conserva los valores del servidor.
- Se mantienen los créditos y datos de contacto. Se añade el aviso «© 2026 Manuel Cuéllar. All rights reserved.» y una descripción de cada aplicación en las propiedades del ejecutable.
- Los instaladores usan el icono GS en una ruta permanente con la versión 3.1.1. Se conserva la verificación de los recursos de icono en Administración, Recepción y Propietario.

## Errores y estados

- Los errores del servidor se muestran sin el diccionario técnico de respuesta. Se conservan las indicaciones útiles para recuperar la operación.
- Una pérdida de conexión no se presenta como garantía de que los cambios fueron revertidos. Se pide revisar datos e historial antes de repetir una operación.
- Los fallos de eventos de interfaz muestran un aviso con referencia de soporte; dejan un registro de ubicaciones del código, sin valores de registros, contraseñas o tokens.
- WhatsApp sólo muestra «En servicio» cuando hay actividad reciente del servicio. Una configuración incompleta, pausada o sin actividad se informa con su estado correspondiente. Se retira la promesa de envíos automáticos sin un servicio activado.

## Compatibilidad

Se conservan las funciones de 3.1.0: aislamiento entre gimnasios, licencias, equipos, usuarios, mensualidades, pagos corregibles, gastos de Recepción y editor del propietario con importación y eliminación. La aplicación 3.1.1 utiliza la base comercial 3.0.0 y el editor SQL 3.1.0; no requiere una migración nueva.

## Comprobaciones

Pasaron 38 pruebas Python, 54 comprobaciones de seguridad y operación, 60 contratos RPC, 14 contratos de tablas, 35 flujos de propietario y pagos, y 159 comprobaciones del editor. La base comercial remota coincide con las 124 funciones de la versión local, normalizando los saltos de línea. Consulta los límites de validación en `VALIDACION_3.1.1.md`.
