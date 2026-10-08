# Validación de Gym soft Comercial 3.4.2

Esta entrega amplía la 3.4.1 con una transición visual estable al maximizar/restaurar, reintento de acceso directo al formulario de credenciales y tolerancia a interrupciones temporales de red durante la comprobación de licencia.

Resultado local: **PASS**.

| Suite | Resultado |
| --- | --- |
| Pruebas Python | 56 pruebas aprobadas. |
| Simulación de una jornada | 107 comprobaciones con clientes, planes, pagos, entradas, tienda, gastos, personal, clases, estadísticas, respaldos y permisos. |
| Interfaz responsive | 510 comprobaciones al 100 % y 125 %. |
| Distribución normal/maximizada | 387 comprobaciones al 100 %, 120 % y 125 %, incluido movimiento sin redistribución. |
| Pagos y desplegables | 40 comprobaciones de formularios, errores y recuperación. |
| Rendimiento | 14 páginas con consultas fuera del hilo de Tk y actualización incremental de tablas. |

También se probó que **Reintentar** vuelva directamente a correo y contraseña y que un fallo transitorio de red del monitor de licencia no cierre la aplicación.

Las comprobaciones locales no sustituyen la instalación nativa del EXE en Windows, la conexión real de Supabase, el lector biométrico físico ni una prueba con varios computadores conectados. Un resultado PASS significa que no se detectaron fallos en los escenarios incluidos, no una garantía de ausencia de cualquier error futuro.

Created by Manuel Cuéllar  
© 2026 Manuel Cuéllar. All rights reserved.
