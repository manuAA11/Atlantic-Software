# Tiquetera iniciada: conservar el importe seleccionado

Administración y Recepción conservan el precio del plan al marcar o desmarcar «Tiquetera ya iniciada». Si se editó «Valor pagado», se conserva exactamente ese importe, incluido cero. Seleccionar otro plan vuelve a inicializar su precio. Los planes internos continúan sin cobro.

No cambia el contrato de registro del pago, la idempotencia, el consumo, la fecha de inicio ni el vencimiento. No requiere migración ni modifica pagos históricos. El importe positivo sigue representando dinero recibido al registrar la operación.

La prueba Tk existente cubre los tres perfiles, Administración/Recepción y escalas 100/125 %, con alternancia repetida, valor del plan, edición positiva, cero explícito, reinicialización al seleccionar el plan y conservación de entradas utilizadas. La validación y publicación Windows se registran por el commit exacto antes de ofrecer la actualización.

Candidata 3.8.7 beta opcional NO FINAL. Se conservan los gates físicos/externos y la comprobación pendiente de instalación en Windows nativo de 32 bits.

## Publicación verificada · 16 de noviembre de 2026

3.8.7 publicada y habilitada para ZTATTUZ en beta/OPTIONAL, x86 y x64. Windows [43934689954](https://github.com/manuAA11/Atlantic-Software/actions/runs/43934689954) y publicación [43934690287](https://github.com/manuAA11/Atlantic-Software/actions/runs/43934690287) PASS sobre `34f78aaf56bd9df0d7993db922537ed581123eb3`. Los tres perfiles aprobaron 86 comprobaciones gráficas de tiqueteras, con Administración/Recepción a 100/125 %. Python: Comercial 322, ZTATTUZ x64 294 y x86 293 pruebas; además, 177 guardas por perfil.

Se descargaron íntegros los tres instaladores y se comprobaron tamaños y SHA256 contra el manifiesto, SHA256SUMS y los digests de GitHub. El actualizador de producción seleccionó y verificó los paquetes, también usando las filas filtradas de Core. Se conservaron configuración, licencia, suscripción y los 11 registros anteriores de distribución. No se modificaron datos operativos ni contratos del servidor.

El primer intento se bloqueó por los metadatos 3.8.6 de los instaladores; se corrigieron los ocho scripts y las instrucciones por perfil antes de la ejecución aprobada. No se alteraron tests ni gates para forzar la entrega. La instalación nativa Windows32 y la aceptación física/externa siguen pendientes.

[Descargas de la actualización opcional](https://github.com/manuAA11/Atlantic-Software/releases/tag/atlantic-gym-3.8.7-piloto). Evidencia: `evidence/ticket-plan-value-3.8.7.json`.
