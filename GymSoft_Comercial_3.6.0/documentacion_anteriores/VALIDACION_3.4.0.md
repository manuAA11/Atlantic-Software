# Validación local · Gym soft Comercial 3.4.0

9 de septiembre de 2026. Pruebas en Linux con Tk y pantalla virtual; sin conexión a gimnasios reales. No se modificaron funciones SQL, permisos ni datos del servidor.

## Resultados

- **52 pruebas de Python:** correctas.
- **Ventanas:** acceso, preguntas Sí/No, formularios, avisos oscuros, archivos, pagos, gastos y editor del propietario correctos. Se conserva la espera por condición de usuarios e invitaciones y el detector de controles tapados.
- **Diseño:** 515 comprobaciones de tamaños, navegación y formularios al 100 % y 125 %. Se recorrieron Administración, Recepción y Propietario, sus pestañas y regresos a pantallas ya abiertas.
- **Huella simulada:** lectura con y sin Enter, búsqueda manual, repetición, foco fuera del buscador, pausa, formularios y respuestas pendientes correctas.
- **Tiqueteras y fechas:** 34 comprobaciones gráficas de formato de cumpleaños, cupos, vigencia, traslado de tiqueteras y seguimiento correctas.
- **Carga de páginas:** las 14 secciones de Administración y Recepción cargaron usando consultas ejecutadas fuera del hilo de Tk. Volver a pulsar la sección visible no hizo otra consulta ni reconstruyó sus controles.
- **Esperas de red simuladas:** la ventana siguió atendiendo eventos durante la consulta. La búsqueda más reciente reemplazó a la pendiente y la respuesta vieja no llegó al renderizador. Las respuestas invalidadas se descartaron.
- **Modales y navegación:** no se aplicaron resultados sobre una sección oculta ni mientras estaba abierto un modal; se presentaron al volver o cerrar el modal.
- **Actualización:** una ráfaga de 20 eventos se agrupó en un refresco de la sección visible. No se consultaron las secciones ocultas por esa ráfaga.
- **Tablas:** al actualizar 1.000 filas idénticas hubo cero borrados y cero inserciones; se conservaron la selección y la posición. También se comprobó añadir y retirar registros reales de la lista de prueba.
- **Tienda:** cambiar un producto conservó las otras tarjetas. Las barras de una lista vacía se ocultaron, aparecieron con desbordamiento y volvieron a ocultarse al retirar los registros.
- **Redibujado:** mover una ventana construida no hizo consultas ni creó controles nuevos. Se comprobó que un evento Map de un control no reaplique el estilo nativo de toda la ventana ni fuerce `update_idletasks()`.
- **Inspección visual:** Registro de entrada de Recepción encaja en la ventana de prueba de 960 × 640 al 100 %, mostrando las cuatro columnas y sin barra exterior. Los tamaños menores o la escala mayor conservan desplazamiento cuando el contenido ya no cabe.

En la última medición local de la prueba de fluidez, despachar una consulta al trabajador tomó aproximadamente **0,05 ms**, y actualizar la tabla sin cambios de 1.000 filas tomó **2,09 ms**. Son mediciones de esta máquina con datos simulados: no representan la latencia de Supabase ni el rendimiento gráfico de Windows.

## Alcance y comprobación pendiente

El paquete conserva el control de compilación de ventanas y añade `tests/performance_ui_smoke.py`; no se eliminaron comprobaciones para permitir la entrega. Los nombres y versiones de fuentes, metadatos e instaladores corresponden a 3.4.0.

No se compilaron ni ejecutaron EXE en Windows en este entorno. Falta comprobar en el computador de destino la composición de ventanas al arrastrar o redimensionar, los iconos de los accesos instalados y el lector físico. Las consultas de prueba no usan red; el tiempo real del servidor depende de la conexión.

La optimización cubre las lecturas de las páginas principales, su navegación, diseño y actualización. Las operaciones que escriben pagos, entradas, importaciones o cambios continúan confirmándose con el servidor. No se garantiza ausencia absoluta de demoras de red ni de limitaciones del equipo.
