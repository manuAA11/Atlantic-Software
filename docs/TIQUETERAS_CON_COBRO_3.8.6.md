# Tiqueteras ya iniciadas con cobro opcional

En Administración y Recepción, Tiquetera ya iniciada conserva las entradas utilizadas y permite editar Valor pagado. El valor inicial es cero; un valor positivo representa dinero recibido al registrar la operación, no un pago histórico ni un saldo pendiente. Los planes internos mantienen su comportamiento sin pago.

La RPC nueva register_ticket_carryover_with_payment se instaló en los dos proveedores existentes. La RPC anterior conserva su contrato sin cobro para los clientes antiguos. Se verificaron permisos sin acceso anónimo y ausencia de cambios en los registros financieros previos. Sólo se realizó DDL en producción; sin clientes o cobros de prueba.

La operación nueva comprueba gimnasio, rol, cliente, plan comercial activo, vigencia, cupo y superposiciones. El mismo identificador y contenido devuelve la misma membresía; cambiar el cobro, método, referencia, nota o entradas con ese identificador exige revisar la ficha. Un reintento no crea otro ingreso. El cobro positivo usa la hora del servidor al registrar, aunque la tiquetera haya empezado antes.

Validación local: 25 comprobaciones SQL por fixture, seis pruebas Python del formulario por perfil y 177 guardas generales (dos omisiones existentes). La prueba Tk se amplió para valor positivo y cero en Administración/Recepción, con 100/125% de escala; requiere ejecución Windows antes de publicar.

Distribución prevista: 3.8.6 opcional por el actualizador para x64/x86, conservando las identidades de instalación. Los gates de aceptación física y Windows nativo de 32 bits no se modifican ni se consideran aprobados por estas pruebas.
