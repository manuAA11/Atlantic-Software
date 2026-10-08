# Validación de Gym soft Comercial 3.3.2

**Actualización del 9 de septiembre de 2026:** el registro siguiente corresponde a las correcciones iniciales de la aplicación. La corrección posterior de la prueba de compilación, con límites del monitor y configuración DPI, se detalla en `VALIDACION_PARCHE_COMPILACION_3.3.2.md`.

## Fallo reproducido y corrección

Se reprodujo el contenido oculto de Configuración. El contenedor añadido por el diseño adaptable era hermano del Notebook y se creaba después. `grid(in_=...)` cambiaba su contenedor geométrico, pero no su padre ni su orden de superposición. El contenedor tapaba las pestañas. El mismo defecto afectaba a las tablas con barras de desplazamiento añadidas por el módulo compartido.

La corrección mantiene el control por encima de su contenedor al crearlo y al volver a mostrarlo. Conserva las pestañas, sus formularios, las barras de desplazamiento y la reorganización del contenido.

La nueva comprobación gráfica sitúa un punto sobre la zona visible del control y consulta qué widget recibe allí el ratón. Se comprobó que detecta el contenedor superpuesto al reproducir el comportamiento anterior y que pasa con la corrección. Comprobar únicamente `winfo_viewable()` y las dimensiones no detectaba este fallo.

## Lectura automática

Los clics sobre la casilla anterior sí cambiaron su variable en la reproducción local. El indicador «X» no expresaba el estado con claridad. Ahora se presenta el estado por escrito y se cambia mediante un botón con una acción explícita.

Las pruebas pulsan el botón mediante eventos de ratón y comprueban el estado compartido. Una lectura simulada durante la pausa no identifica al cliente; otra, después de reactivar, sí llega al controlador. Cambiar de sección y volver conserva el estado. Se mantienen las comprobaciones de lectura con y sin Enter, búsqueda manual, repetición, foco y pausa en formularios.

## Resultados locales

- **52 pruebas Python:** correctas.
- **518 comprobaciones gráficas de diseño:** correctas. Incluyen Administración, Recepción y panel del propietario; tamaños de 1366 × 768, 960 × 640 y 800 × 550 en las aplicaciones, y tamaños equivalentes del panel; escalas Tk equivalentes al 100 % y 125 %; pestañas, tablas, selector compacto, navegación de regreso y controles de lectura.
- **Prueba gráfica de ventanas:** correcta. Incluye inicio de sesión, Sí/No, formularios, archivos, pagos, gastos y editor del propietario, con respuesta simulada retrasada para usuarios e invitaciones. Se verifica además la exposición del contenido del editor.
- **Prueba gráfica del lector:** correcta, con clics de pausa/reactivación y códigos emitidos mediante eventos Tk.
- **34 comprobaciones gráficas de fechas, tiqueteras y seguimiento:** correctas al 100 % y 125 %.
- **Revisión de capturas:** Configuración, Estadísticas y Registro de entrada muestran de nuevo su contenido. El control de lectura muestra «activada» y «Pausar lectura».

## Alcance

Las pruebas se ejecutaron con Python y Tk en Linux, mediante Xvfb, sin conectar a la base comercial ni usar cuentas reales. Las escalas se simularon en Tk. No sustituyen una prueba de los ejecutables y del lector físico en Windows.

Esta corrección no modifica SQL ni datos. Los archivos anteriores siguen presentes en las fuentes; los cambios de producto se limitan al diseño compartido, el control de lectura y la versión. ZTATTUZ no fue modificado.

El ZIP contiene las fuentes completas y el generador de instaladores. `CREAR_INSTALADORES.bat` conserva las pruebas gráficas y la comprobación del icono GS antes de producir los instaladores en Windows.
