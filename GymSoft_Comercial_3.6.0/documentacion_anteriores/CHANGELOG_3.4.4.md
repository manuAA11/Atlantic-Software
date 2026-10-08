# Gym soft Comercial 3.4.4 · Revisión de rendimiento y funcionamiento

## Interfaz

- Sustituidos los temporizadores de distribución de 120, 65, 55, 35 y 16 ms por trabajo agrupado en el ciclo de eventos de Tk. El aviso de operación lenta conserva un umbral propio de 120 ms para evitar que aparezca en consultas instantáneas; no retrasa la entrega del resultado.
- Eliminada la capa que tapaba la aplicación durante los cambios de tamaño. No conservaba una imagen de la vista anterior.
- Los controles que ya usan `grid` permanecen mapeados al cambiar de columnas. La conversión inicial desde `pack` se hace una sola vez.
- Un error en un componente de distribución se informa sin impedir que los demás componentes terminen su actualización.
- Corregido el ajuste de la región desplazable que se aplicaba tarde, al comenzar el scroll.
- El lector biométrico etiqueta cada nuevo control una vez; ya no recorre todo su subárbol por cada evento de aparición.
- El catálogo de Recepción mantiene una distribución por modo de ventana y escala, limpia columnas sobrantes y deja crecer las tarjetas con su contenido.

## Operaciones

- Añadido un adaptador de datos para Administración y Recepción: las llamadas desde Tk ejecutan la operación de datos en un trabajador y conservan la respuesta o el error. Las lecturas que ya usan trabajadores continúan directamente.
- La espera mantiene el bucle de eventos activo y conserva el modal anterior. Se posponen los repintados y la navegación durante una operación; una escritura no se reintenta automáticamente.
- Administración y Recepción guardan el pago antes de cerrar su formulario. Un error conserva importe, fecha, plan, referencia y notas. El envío repetido mientras espera queda bloqueado.
- La consulta inicial de planes y fecha se hace antes de construir el formulario de Administración, evitando dejar una ventana incompleta ante un error de red.
- Eliminadas 16 solicitudes de actualización inmediatamente seguidas de otra actualización general que invalidaba su resultado.
- La verificación de licencia conserva su resultado mientras termina un guardado. Una denegación explícita se aplica al finalizar esa espera; las restricciones del servidor permanecen intactas.

## Validación de datos

- Importe entero estricto compartido por planes, pagos, correcciones, gastos, productos y tarifas de personal. No se eliminan separadores arbitrarios que cambien el importe introducido.
- Caché de fecha del servidor limitada a 60 segundos, con invalidación al cambio local de día del gimnasio y coordinación de lecturas concurrentes. Un fallo de consulta no prolonga una fecha caducada.

## Entrega

- Nueva batería de regresión con formularios de pago reales y red simulada, catálogo poblado, fechas de una sesión larga y cambios de distribución.
- Las nuevas comprobaciones forman parte de la validación obligatoria del generador de instaladores.
- La generación de invitaciones de Recepción desde Configuración también utiliza una espera sin bloquear el dibujo y cuenta con su propia regresión de interfaz.
- Sin cambios de SQL, permisos, dependencias ni credenciales respecto a la 3.4.3.

Created by Manuel Cuéllar  
© 2026 Manuel Cuéllar. All rights reserved.
