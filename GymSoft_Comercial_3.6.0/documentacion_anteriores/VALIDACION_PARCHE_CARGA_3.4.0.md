# Corrección de carga de páginas · 3.4.0

9 de septiembre de 2026.

## Fallo reproducido

Con el coordinador original, una consulta se completó antes de mostrar el contenedor de la página. La respuesta quedó almacenada, la página todavía no era visible y el temporizador se detuvo. Al mostrar el contenedor, la página se volvió visible pero no presentó los datos: `_view_loaded` permaneció falso. Esto provoca que la comprobación de carga llegue a su límite de tiempo.

La reproducción se hizo con Tk y una respuesta local inmediata, sin Supabase ni cuentas reales. No fue necesario simular una conexión lenta ni aumentar el límite del test.

## Corrección

- El coordinador recibe el evento de presentación de las páginas que tienen consultas. Cuando una página aparece o su ventana se restaura, presenta la respuesta que ya recibió.
- No vuelve a consultar para recuperar esa respuesta ni mantiene un sondeo continuo de las páginas ocultas.
- Un renderizador que inicia otra lectura mantiene un único temporizador de sondeo. Los controles individuales no disparan trabajo adicional del coordinador al aparecer.
- La prueba gráfica configura DPI antes de crear el primer Tk. Si falla una carga, identifica aplicación, sección, visibilidad, solicitudes pendientes y temporizador; también muestra la excepción de un renderizador.

## Verificación local

La reproducción que fallaba con la versión anterior muestra los datos después del cambio. Las pruebas fuerzan además la restauración de una ventana, el regreso a una página oculta y una segunda consulta iniciada desde un renderizador. Se verifica que solo exista un temporizador para las consultas encadenadas.

Se mantienen los controles de selección, tablas estables, búsqueda vigente, pausa en modales, barras condicionales y las 14 páginas de Administración y Recepción. La comprobación conserva el límite de seis segundos; no se omite para permitir la compilación.

Las 52 pruebas de Python y las pruebas gráficas locales de ventanas, lector simulado, tiqueteras, fluidez y diseño al 100 % y 125 % pasan. La prueba de diseño recorre 515 comprobaciones, y la de fechas y tiqueteras mantiene sus 34 comprobaciones.

No cambia SQL, configuración de conexión, iconos, reglas de pagos ni datos de gimnasios. La compilación de EXE y su comprobación nativa todavía deben realizarse en Windows. Este entorno valida el caso de orden de eventos con Tk en Linux y pantalla virtual; no constituye una ejecución del instalador de Windows.
