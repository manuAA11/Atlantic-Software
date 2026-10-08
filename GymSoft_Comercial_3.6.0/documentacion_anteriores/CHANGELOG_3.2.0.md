# Gym soft 3.2.0

- Diseño adaptable compartido en páginas, formularios, avisos y panel del propietario. Ajuste de columnas y filas, texto en varias líneas, límites del área visible y desplazamiento de respaldo.
- Menús accesibles en ventanas reducidas; selector para pestañas cuyo ancho excede el disponible y barras de desplazamiento en tablas.
- Dashboard como primera sección, seguida de Registro de entrada y Clientes y pagos. Dashboard de Recepción con acciones y entradas recientes.
- Corrección del envío de huella vacía en Administración: se envía texto vacío, conforme al esquema comercial, en lugar de NULL.
- Captura de lectores que emiten códigos como teclado en la ventana activa, consulta exacta, pausa durante formularios y protección contra lecturas repetidas. Tienda conserva su lector de productos.
- Consulta automática del código escrito o pegado en Registro de entrada.
- Planes con tipo explícito, vigencia, precio y cupo de entradas configurable; el nombre del plan ya no decide su cupo. Los pagos anteriores conservan el cupo comprado.
- Corrección de una espera de visibilidad que podía bloquear un formulario de Recepción al ajustar su tamaño.
- Se mantienen los iconos GS, los créditos, el contacto, el editor, los permisos y la auditoría existentes. Sin migración SQL para actualizar desde 3.1.1.
