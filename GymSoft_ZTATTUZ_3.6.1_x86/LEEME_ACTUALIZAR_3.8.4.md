# Atlantic Gym 3.8.4 · Actualización opcional

- Conserva la sesión, los botones de cierre de sesión y la detección CH340 de 3.8.3.
- Ante un fallo al enviar el OFF final, comprueba el cierre real del puerto y la identidad USB. Intenta una sola reconexión para restablecer OFF.
- No repite ON, asistencias, consumos ni solicitudes al servidor. Si no completa el restablecimiento, conserva el bloqueo y el diagnóstico.
- No cambia automáticamente de COM, dispositivo ni configuración. Un fallo al abrir, enviar ON o cerrar el puerto no inicia esta recuperación.
- Se distribuye desde Sistema y avisos → Buscar actualizaciones. Cerrar Administración y Recepción antes de aplicar la actualización.

La transmisión OFF no confirma los contactos del módulo ni la posición de la puerta. La comprobación del relé instalado y de Windows32 nativo permanece pendiente; paquete de prueba opcional, NO FINAL.
