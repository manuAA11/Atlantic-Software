# Corrección de carga de Recepción

10 de septiembre de 2026. Gym soft Comercial 3.4.0. Coordinador `f1be40c96930`.

## Fallo reproducido

El registro del usuario mostraba `ReceptionApp / access`, ventana normal, estado «Cargando información…», ambas respuestas recibidas, página visible y temporizador `None`.

Se reprodujo el mismo estado utilizando la página real de Recepción y datos simulados. Durante la llegada de las respuestas se retrasó deliberadamente la señal `winfo_viewable`; luego se permitió que devolviera su valor real, sin generar otro evento Map. Antes de la corrección, ambas respuestas quedaban almacenadas y la página nunca completaba la carga.

La prueba controla ese orden de eventos para reproducirlo de forma determinista en Linux. No representa una ejecución nativa de Windows ni depende de minimizar ventanas.

## Corrección

El coordinador mantiene un único temporizador para la sección seleccionada mientras termina de hacerse visible. Al mostrar los datos elimina la respuesta pendiente y completa el estado de carga. Las páginas apartadas y las ventanas minimizadas o retiradas permanecen en reposo; su regreso permite presentar los resultados conservados.

Se conserva la protección de formularios modales, la invalidación de respuestas antiguas, la reutilización de filas y el trabajo de consulta fuera del hilo de Tk. No cambia SQL, dependencias, cuentas ni registros.

## Comprobaciones

- La página real Registro de entrada de Recepción recibe las dos respuestas antes de que el coordinador la considere visible. Conserva su temporizador y las presenta sin recibir otro Map ni repetir las consultas.
- El aviso de carga completa se ejecuta después de presentar ambas respuestas.
- Navegar a otra sección deja de sondear la página apartada. Volver presenta lo recibido sin repetir la consulta.
- Una nueva consulta de la misma clave iniciada durante el renderizado continúa pendiente hasta completar su propia presentación.
- Se conservan las pruebas de respuestas anteriores al primer Map, restauración, formularios modales, solicitudes reemplazadas e invalidación.
- El recorrido completo incluye las 14 secciones de Administración y Recepción, con el mismo límite de seis segundos por espera.

El conjunto de validación incluye también las 52 pruebas unitarias y las pruebas gráficas de acceso, formularios, propietario, lector simulado, fechas, tiqueteras, seguimiento, navegación y tamaños al 100 % y 125 %. Se ejecuta con datos de prueba, sin usar gimnasios reales.

## Entrega

El parche es acumulativo sobre la 3.4.0 original e incluye las correcciones anteriores de visibilidad. Reemplaza su contenido dentro de `GymSoft_Comercial_3.4.0`, conserva `.venv` y ejecuta `CREAR_INSTALADORES.bat`. La prueba de rendimiento imprime `COORDINADOR DE CARGA: f1be40c96930` para identificar esta revisión.

Los ZIP contienen código y pruebas; no incluyen ejecutables compilados. La compilación y comprobación nativa de Windows siguen realizándose en el computador del usuario.
