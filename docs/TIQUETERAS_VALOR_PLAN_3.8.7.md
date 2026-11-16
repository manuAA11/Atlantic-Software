# Tiquetera iniciada: conservar el importe seleccionado

Administración y Recepción conservan el precio del plan al marcar o desmarcar «Tiquetera ya iniciada». Si se editó «Valor pagado», se conserva exactamente ese importe, incluido cero. Seleccionar otro plan vuelve a inicializar su precio. Los planes internos continúan sin cobro.

No cambia el contrato de registro del pago, la idempotencia, el consumo, la fecha de inicio ni el vencimiento. No requiere migración ni modifica pagos históricos. El importe positivo sigue representando dinero recibido al registrar la operación.

La prueba Tk existente cubre los tres perfiles, Administración/Recepción y escalas 100/125 %, con alternancia repetida, valor del plan, edición positiva, cero explícito, reinicialización al seleccionar el plan y conservación de entradas utilizadas. La validación y publicación Windows se registran por el commit exacto antes de ofrecer la actualización.

Candidata 3.8.7 beta opcional NO FINAL. Se conservan los gates físicos/externos y la comprobación pendiente de instalación en Windows nativo de 32 bits.
