# Comprobación de visibilidad durante la compilación

9 de septiembre de 2026. Parche acumulativo de Gym soft Comercial 3.4.0.

## Motivo

El registro recibido indica que la consulta de visibilidad devuelve `None` en el centro de una tabla de Clases y reservas. Las coordenadas informadas están dentro del monitor y de la ventana. El usuario señala que minimizaba las ventanas para trabajar en otras aplicaciones durante la prueba.

La implementación de Tk para Windows consulta `WindowFromPoint` y solo devuelve un control si pertenece al mismo intérprete de Tk. Por tanto, una ventana minimizada o tapada por otra aplicación puede producir ese resultado sin que exista un defecto en el diseño de la tabla. El registro no identifica qué ventana estaba delante en ese momento; no permite asegurar retrospectivamente cuál la tapaba.

Referencias técnicas: [código de Tk para Windows](https://github.com/tcltk/tk/blob/core-8-6-branch/win/tkWinWm.c), [consulta de ventanas de Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-windowfrompoint) y [documentación de winfo](https://www.tcl-lang.org/man/tcl8.6/TkCmd/winfo.htm).

## Cambio

- La preparación de las ventanas de prueba las mantiene delante y restaura las que se minimizan. Los controles secundarios y las ventanas ocultadas deliberadamente con `withdraw()` se conservan en ese estado.
- Una consulta sin resultado se repite durante un máximo de 1,5 segundos, procesando los eventos y recalculando las coordenadas visibles. Solo pasa si la consulta real encuentra el control esperado o un hijo suyo.
- Se mantienen los fallos por controles ocultos, fuera del visor, tapados por otro control o no encontrados después de la espera.
- La compilación y la guía indican que hay que mantener visibles las ventanas de prueba y el escritorio desbloqueado.
- No cambia el comportamiento de minimización del programa instalado ni las reglas de negocio. Incluye también el parche anterior de carga asíncrona.

## Verificación

Las pruebas se ejecutan con Tk en Linux y una pantalla virtual de 1920 × 1080. Usan datos simulados, sin conexión al servidor ni cambios en gimnasios reales.

- 52 pruebas unitarias.
- Ventanas de acceso, formularios, archivos, pagos, gastos y editor del propietario.
- Lectura simulada, pausa, reanudación, foco, duplicados y formularios.
- 34 comprobaciones de fechas, tiqueteras y seguimiento al 100 % y 125 %.
- Carga de las 14 secciones de Administración y Recepción, conservación de selección y desplazamiento y actualización diferencial.
- Navegación, tablas, pestañas y formularios en ventanas de varios tamaños al 100 % y 125 %.
- Casos positivos y negativos de visibilidad: borde del monitor, consulta temporalmente vacía seguida de un control real, superposición durante el reintento, control oculto y consulta permanentemente vacía.

La decisión de restaurar únicamente el estado minimizado se comprueba con un doble de prueba en Linux. Se añade una comprobación de minimización real que se ejecutará en Windows. El entorno local sin gestor de ventanas no permite validar esa operación nativa.

Los ZIP contienen fuentes y pruebas. No contienen ejecutables compilados en Windows. La compilación, la restauración nativa, los iconos y el lector físico requieren la comprobación en el equipo Windows.
