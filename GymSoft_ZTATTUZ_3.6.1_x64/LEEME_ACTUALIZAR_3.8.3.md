# Atlantic Gym 3.8.3 — actualización opcional de prueba, NO FINAL

Instala el archivo correspondiente al proveedor y a Windows x86 o x64 de este equipo.
Cierra Administración y Recepción antes de ejecutar el instalador.

## Cambios

- Detección del relé: recupera VID/PID desde el identificador de hardware y, cuando Windows entrega información incompleta, consulta los dispositivos presentes mediante SetupAPI. No confunde un COM guardado con un relé conectado y conserva la selección explícita entre varios módulos.
- Cerrar sesión: botón rojo encima de Configuración en Administración y Recepción. Retira las credenciales locales y vuelve al formulario; no reutiliza las pantallas de la cuenta anterior. Las sesiones independientes de otros dispositivos permanecen activas.
- El cierre de sesión local funciona aunque el servidor no responda. Una operación o venta pendiente debe terminar antes de salir.

El detector no instala controladores ni envía ON/OFF. La configuración del relé y las funciones anteriores se conservan. Encontrar un CH340 no certifica los contactos ni la apertura física: comprobar Restablecer (OFF), prueba confirmada y una entrada autorizada en el equipo afectado. La instalación del controlador x86 necesita Windows de 32 bits; un proceso x86 en Windows x64 no acredita esa instalación. No se han completado los pilotos externos ni se presenta esta publicación como final.
