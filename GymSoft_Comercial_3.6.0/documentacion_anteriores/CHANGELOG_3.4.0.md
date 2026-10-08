# Gym soft Comercial 3.4.0

9 de septiembre de 2026.

- Recepción inicia en Registro de entrada y deja de mostrar Dashboard.
- Registro de entrada separa el formulario y el historial en pestañas; mantiene visible el resultado de la última lectura durante los refrescos.
- Barras condicionales en listas, catálogos y selectores. Columnas y alturas flexibles antes de recurrir al desplazamiento de la página.
- Tamaño de Notebook según la pestaña activa, conservando la corrección de controles tapados y la comprobación del área útil del monitor.
- Coordinador de lecturas con dos trabajadores, solicitudes agrupadas, descarte de respuestas antiguas y renderizado en el hilo de Tk.
- Se reutilizan las páginas al navegar. Solo se consulta la página visible al recibir cambios; las restantes se invalidan para su siguiente apertura.
- Actualización diferencial de tablas: se mantienen filas, selección y posición. Se reutilizan las tarjetas y las imágenes sin cambios de la tienda.
- Menos trabajo en eventos de tamaño; se limita el ajuste del contenedor y se agrupan los dibujos de las gráficas.
- El estilo DWM de Windows solo se aplica a eventos de la ventana principal, sin forzar `update_idletasks()` por cada control que aparece.
- Se conservan los cambios locales de formularios de Configuración y Marketing durante una lectura de actualización.
- Nuevas comprobaciones gráficas de consultas lentas, navegación, respuestas obsoletas, modales, barras condicionales y estabilidad de registros.
- No modifica SQL, políticas de acceso, reglas comerciales ni datos del servidor.

## Parche de reanudación de carga

- Se reproducía una espera indefinida si la respuesta llegaba antes del primer Map de la página. Al mostrarse la página o restaurarse su ventana, ahora se presentan los datos recibidos sin repetir la consulta.
- Se mantiene un solo temporizador cuando un renderizador inicia otra consulta; no se sondean continuamente las pantallas ocultas.
- Las pruebas fuerzan respuestas anteriores al primer Map, ocultación, restauración y consultas encadenadas.
- La prueba de fluidez inicia con la configuración DPI antes del primer Tk, imprime cada sección y muestra el contexto de un error. Conserva el límite de seis segundos y los controles de carga.

## Parche de visibilidad durante la compilación

- Las ventanas de las pruebas automáticas permanecen delante y recuperan su estado visible si se minimizan. La aplicación instalada sigue pudiendo minimizarse normalmente.
- La consulta de visibilidad espera hasta 1,5 segundos si Windows todavía no devuelve un control y repite la consulta real con las coordenadas actuales. Nunca acepta una consulta sin resultado.
- Se conserva la detección de tablas, pestañas y controles ocultos o tapados. Se comprueba también una superposición aparecida durante el reintento.
- El generador y la guía indican que las ventanas de prueba deben permanecer visibles y el escritorio desbloqueado.
- Incluye la corrección anterior de cargas recibidas antes de mostrar una página. No cambia datos, SQL ni dependencias.

## Revisión del 10 de septiembre: carga de Recepción

- Se reprodujo el estado de `ReceptionApp / access` con la ventana normal, las dos respuestas recibidas, la página visible y el coordinador sin temporizador. El fallo se produce cuando el último sondeo observa la página todavía no visible y después no recibe otro evento Map.
- La sección seleccionada mantiene la reanudación hasta presentar los resultados. Las secciones apartadas y las ventanas retiradas o minimizadas permanecen en reposo.
- Una solicitud sigue pendiente hasta que se presenta o se informa su error. Los avisos de carga completa esperan todas las respuestas, y una consulta nueva iniciada durante el renderizado conserva su estado pendiente.
- Volver a pulsar la sección activa permite reanudar resultados listos sin reconstruir la página ni repetir consultas.
- La prueba fuerza la llegada de las dos respuestas antes de confirmarse la visibilidad, sin un segundo Map; también verifica navegación durante la espera y consultas encadenadas con la misma clave.
- El límite de seis segundos y las comprobaciones de las 14 secciones se conservan. La prueba imprime el identificador del coordinador para detectar mezclas de archivos de parches anteriores.
