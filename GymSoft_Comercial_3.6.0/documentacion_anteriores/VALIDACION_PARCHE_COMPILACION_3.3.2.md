# Corrección de la compilación de Gym soft 3.3.2

Fecha: 9 de septiembre de 2026.

## Incidencia

La compilación en Windows se detenía en la prueba gráfica de Finanzas con `Control tapado ... financepage ... el ratón encuentra None`, después de superar las 52 pruebas Python y la prueba inicial de ventanas.

La revisión encontró dos diferencias entre las pruebas y la aplicación: las pruebas omitían la configuración DPI previa a crear Tk y solicitaban ventanas de tamaño fijo sin limitarse al área útil del monitor. Además, la comprobación recortaba las coordenadas por los padres lógicos, pero no por el monitor ni por el contenedor geométrico de `grid(in_=...)`.

Estos defectos permitían consultar un punto fuera de la zona visible. `None` no identifica por sí solo un control superpuesto: Tk devuelve un resultado vacío cuando no encuentra una ventana de la aplicación en el punto consultado. Se consultó la [documentación oficial de winfo](https://www.tcl-lang.org/man/tcl8.6/TkCmd/winfo.htm).

No se reprodujo el equipo Windows del usuario. Se reprodujo y verificó el caso de una ventana parcialmente fuera del monitor con Tk en Linux; por ello, la compilación final en Windows sigue siendo necesaria.

## Cambios

- Las cuatro pruebas gráficas activan la misma configuración DPI de las aplicaciones antes de crear la primera ventana.
- Las ventanas principales de prueba se ajustan al área útil del monitor mediante la función de ajuste del programa.
- El punto consultado se limita al monitor, al visor y a los contenedores geométricos. Las ventanas secundarias se tratan como ventanas independientes de sus dueños lógicos.
- Una consulta sin resultado sigue deteniendo la compilación. El mensaje distingue este caso de un control superpuesto e incluye las dimensiones, la escala y la sección probada.
- Se añadió una comprobación del propio método de verificación: ventana en el borde de la pantalla, contenedor que tapa deliberadamente una pestaña o tabla, y consulta que devuelve `None`. Los controles superpuestos y las consultas sin resultado siguen rechazándose.

## Resultados

- 52 pruebas Python: correctas.
- Pantalla virtual de 1024 × 640: 533 comprobaciones de diseño, navegación y formularios, con escalas equivalentes al 100 % y 125 %: correctas.
- Pantalla virtual de 1600 × 1000: 518 comprobaciones con las mismas escalas: correctas.
- Verificación de los límites del monitor y detección de pestañas y tablas superpuestas: correcta en ambas pantallas.
- Prueba gráfica de acceso, formularios, archivos, pagos, gastos y editor del propietario: correcta.
- Prueba gráfica de lectura automática, pausa/reactivación y formularios: correcta.
- 34 comprobaciones de fechas, tiqueteras y seguimiento: correctas.

## Entrega

El parche contiene únicamente los archivos de pruebas corregidos, instrucciones, informes y la lista de comprobación de las fuentes. Está destinado a la carpeta completa 3.3.2 y reutiliza su entorno de Python. La entrega completa 3.3.2 también incluye estos cambios.

La aplicación mantiene la versión 3.3.2. No se modificaron sus operaciones, el SQL ni los datos comerciales. No se conectó a Supabase para estas pruebas y no se modificó ZTATTUZ.

Las pruebas locales se ejecutaron con Python, Tk y Xvfb en Linux. Los ejecutables se generan y verifican en Windows mediante `CREAR_INSTALADORES.bat`, que conserva todas las comprobaciones.
