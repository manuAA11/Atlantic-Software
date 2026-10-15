# Prueba presencial de Tienda / POS

Estado: **pendiente de ejecutar con lector físico y la nueva versión instalada**. Las pruebas automáticas usan teclado/HID simulado y una base local; no completan este checklist.

Usa un gimnasio de prueba o productos y operaciones controlados identificados como pruebas. Registra fecha, edición, versión/commit, usuario/rol, Windows/arquitectura y modelo del lector. El lector debe funcionar como teclado USB y terminar cada lectura con ENTER. No necesita un controlador propio del POS. Conserva el historial; anula las ventas de prueba con motivo en lugar de borrarlas.

Antes de empezar, el responsable debe aplicar `ACTUALIZAR_TIENDA_POS.sql` a la base existente, con las actualizaciones previas instaladas, y desplegar una versión del programa que incluya este POS. Los instaladores anteriores no incluyen estos cambios. Habilita Tienda desde su configuración administrativa. Para el equipo de 32 bits utiliza la edición ZTATTUZ x86; este documento no acredita su instalación en Windows.

## Recorrido de 20 pasos

- [ ] 1. En Administrador → Tienda → Nuevo producto, crear **Coca-Cola**, con SKU propio, categoría Bebidas, precio $4.000, costo conocido $2.000, stock inicial 10 y mínimo 5.
- [ ] 2. Pulsar **Escanear** junto a Código de barras y leer la etiqueta real. Confirmar que el código aparece completo, incluidos los ceros iniciales. Mantener SKU y barcode como campos distintos.
- [ ] 3. Guardar. Intentar crear otro producto del mismo gimnasio con ese barcode: debe rechazarse con un aviso claro.
- [ ] 4. Cerrar el editor y el programa; volver a abrir e iniciar sesión.
- [ ] 5. Editar Coca-Cola y confirmar que barcode, SKU, costo, categoría, mínimo e imagen si se agregó persisten.
- [ ] 6. Abrir Punto de venta y escanear sin volver a hacer clic en la búsqueda. Comprobar la coincidencia exacta y que no registra una entrada ni solicita apertura de puerta.
- [ ] 7. Comprobar que Coca-Cola aparece en el carrito: cantidad 1, precio $4.000, subtotal $4.000.
- [ ] 8. Volver a escanear la misma etiqueta una sola vez.
- [ ] 9. Comprobar una sola fila con cantidad **2**, subtotal $8.000. Un ENTER adicional sin código no debe sumar otra unidad.
- [ ] 10. Buscar y agregar manualmente otro producto; probar nombre, SKU y categoría. Probar también sin lector conectado.
- [ ] 11. Pulsar **COBRAR**, elegir EFECTIVO y escribir una cantidad recibida suficiente. Una cantidad inferior al total debe impedir confirmar.
- [ ] 12. Verificar el cambio antes y después de confirmar y comparar el comprobante con el dinero recibido.
- [ ] 13. Confirmar el descuento exacto de stock y un movimiento SALE por cada producto, con antes/después, usuario, referencia e instante.
- [ ] 14. Consultar Historial y volver a abrir el comprobante: número V-…, productos, cantidades, total, método, empleado/rol y estado. Verificar que la fecha corresponde a America/Bogota.
- [ ] 15. Registrar una venta con TRANSFERENCIA y referencia; repetir con TARJETA. Verificar ambos métodos en historial y finanzas de Tienda.
- [ ] 16. Intentar una cantidad mayor al stock disponible: debe impedirse. Desde dos equipos intentar comprar las últimas unidades; sólo deben confirmarse las realmente disponibles.
- [ ] 17. Repetir el recorrido en **Recepción**. No debe permitir costos, edición de productos, ajustes o anulaciones administrativas. Mis ventas debe respetar el alcance del usuario.
- [ ] 18. En **Administrador**, probar editar precio/costo, consultar estadísticas y anular una venta con motivo: debe conservarse como VOID y devolver stock exactamente una vez. Repetir la solicitud no vuelve a sumar.
- [ ] 19. Usar **Recibir / agregar inventario**, escanear Coca-Cola y recibir 24 unidades con costo opcional: comprobar que se eligió ese producto y que 10 + 24 = 34 si no hubo ventas intermedias. Consultar movimiento PURCHASE. Probar un ajuste con conteo físico, motivo obligatorio y stock esperado.
- [ ] 20. Vender hasta llegar al mínimo y a cero: verificar **stock bajo** y **agotado**. Deshabilitar Tienda y comprobar que el resto del gimnasio sigue funcionando; reactivar desde Administrador.

## Recuperación y límites de la comprobación

- [ ] Interrumpir la conexión después de enviar un cobro, sin repetirlo con una referencia nueva. Cerrar/reabrir, consultar el cobro pendiente y reconciliar por su referencia exacta; reintentar el mismo cobro debe devolver una sola venta/pago/descuento.
- [ ] Repetir la interrupción con una entrada de inventario: consultar o reintentar el mismo movimiento sin duplicar unidades.
- [ ] Abrir un formulario, un diálogo y otra página: escribir/pegar nombres, comentarios y precios no debe agregar productos ni disparar acceso. Cambiar de pestaña durante una lectura no debe completar una lectura anterior.
- [ ] Comparar ingresos por membresías y Tienda: separados. Una compra de un cliente STAFF debe contar normalmente como venta de Tienda, sin convertir su membresía en un cobro.
- [ ] Exportar un respaldo nuevo completo y restaurarlo en un gimnasio de prueba. Comparar productos/barcodes, ventas, pagos, movimientos y fechas. Un archivo antiguo incompleto debe rechazarse antes de reemplazar un historial POS existente.
- [ ] Repetir en Atlantic Gym Comercial Admin/Recepción y en ZTATTUZ x64/x86 donde corresponda. El ensayo de dos equipos PostgreSQL y el lector real requieren registro presencial; no marcarlos por pruebas simuladas.

Resultado presencial: ____________________  Evidencia/referencias: ____________________

© Atlantic Tech Software — All rights reserved. By Manuel Cuellar
