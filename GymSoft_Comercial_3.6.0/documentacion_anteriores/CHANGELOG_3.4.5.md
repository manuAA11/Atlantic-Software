# Cambios de Gym soft 3.4.5

## Diseño

- Las rejillas conservan columnas, filas, celdas combinadas, alineación y pesos de crecimiento en ambos estados de ventana. Se elimina el cálculo que apilaba bloques según el ancho mínimo de la ventana restaurada.
- Se corrige la pérdida de crecimiento vertical que dejaba los paneles cortos dentro de filas altas, especialmente en Estadísticas.
- Las filas equivalentes de tarjetas mantienen anchos iguales; las distribuciones con proporciones distintas conservan sus pesos originales.
- Las barras horizontales creadas con `pack` conservan su alineación natural, sin convertir cada etiqueta o botón en una columna del mismo ancho.
- El estado de carga comparte la fila del título y no reserva espacio cuando está vacío.

## Contenido accesible y rendimiento

- Los anchos mínimos se calculan a partir de los controles y se conservan en caché. Las tablas aportan el ancho de su visor, sin forzar a toda la página a medir la suma de sus columnas.
- Las columnas conservan mínimos legibles para impedir que una tabla ancha comprima los botones vecinos. En ventanas estrechas, el contenido sigue accesible mediante desplazamiento condicional.
- El foco del teclado puede hacer visible un control tanto horizontal como verticalmente.
- El movimiento y el desplazamiento de páginas estables no recalculan la distribución. Se elimina código del antiguo cálculo de apilado que ya no se utiliza.

## Pruebas

- El recorrido de todas las páginas comprueba que ningún adaptador pierda columnas, celdas combinadas, alineación ni crecimiento vertical.
- Una nueva etapa comprueba el Dashboard y Estadísticas con datos ficticios en ventana mediana, grande, restaurada y estrecha al 100 %, 120 % y 125 %.
- Se mantiene la batería completa de operaciones, seguridad, pagos, lector, ventanas, rendimiento y editor del propietario. El constructor ejecuta también la nueva etapa.

Sin cambios de SQL, dependencias ni reglas de negocio.
