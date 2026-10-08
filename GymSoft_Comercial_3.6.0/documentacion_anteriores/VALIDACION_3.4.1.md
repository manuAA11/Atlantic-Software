# Validación de Gym soft Comercial 3.4.1

Preparación: 13 de septiembre de 2026. Resultado de las suites locales: **APROBADAS**. Esta entrega corrige el error del desplegable de pagos, los campos antiguos de guardado en rutinas, ejercicios y clases, y establece dos distribuciones de ventana.

## Qué se ejecutó

| Conjunto | Resultado verificado |
| --- | --- |
| Pruebas Python | 54 pruebas aprobadas: formularios, fechas, biometría, datos del propietario, empaquetado, manejo de errores y detención de la validación ante fallos. |
| Seguridad y operación SQL | 54 comprobaciones con roles, permisos y aislamiento. |
| Contratos de la aplicación | 61 llamadas RPC y columnas esperadas de 15 tablas. Incluye campos literales enviados al guardar. |
| Operaciones del propietario y pagos | 35 comprobaciones usando los parámetros de los formularios Python. |
| Editor del propietario | 159 comprobaciones de las 13 tablas editables, permisos, conflictos, correos, importaciones, ajuste de stock y eliminación aislada. |
| Planes y tiqueteras | 27 comprobaciones de huella opcional, consumo, renovación, mensualidad y aislamiento; otras 70 de meses calendario, saldos iniciales, seguimiento e idempotencia. |
| Jornada de gimnasio | 107 comprobaciones usando las clases de datos de Python y el SQL comercial reales. Se ejercitan 68 métodos públicos de Administración y Recepción. |
| Ventanas y formularios | Acceso, Sí/No, formularios, diálogos oscuros, archivos, pagos, gastos y editor del propietario. |
| Visibilidad y navegación | 510 comprobaciones al 100 % y 125 %, más controles ocultos, superpuestos y consultas de posición sin resultado. |
| Lector simulado | Lectura con y sin Enter, búsqueda manual, repetición, foco fuera del buscador, pausa en formularios y respuestas pendientes. |
| Fechas y seguimiento en pantalla | 34 comprobaciones de fechas, tiqueteras y seguimiento al 100 % y 125 %. |
| Rendimiento | Las 14 páginas de Administración y Recepción cargan fuera del hilo de Tk; se conservan selección, filas y datos durante las actualizaciones. |
| Regresión del pago | 40 comprobaciones con desplegables reales de ttk, avisos, guardado del formulario y recuperación ante fallos de lectura. |
| Ventana normal y maximizada | 387 comprobaciones al 100 %, 120 % y 125 %: cambios de modo, texto visible y movimiento sin recalcular tarjetas. |

Las cifras representan comprobaciones de alcance distinto; no son un porcentaje de cobertura ni una garantía de ausencia de errores.

## Recorrido de la jornada

Se crean dos gimnasios y cuentas ficticias de propietario, Administración y Recepción. Se autoriza el equipo y se comprueba que las cuentas vean únicamente su gimnasio.

| Área | Operaciones y resultados comprobados |
| --- | --- |
| Clientes | Alta sin huella y con huella; cumpleaños; búsquedas por nombre, documento y huella; contacto editado desde ambos roles; duplicados rechazados; baja y eliminación de un registro temporal. |
| Planes | Crear mensualidad, sesión y tiqueteras de 15/20 entradas; editar precio, nombre, vigencia y cupo; activar/desactivar; conservar el cupo de compras anteriores; impedir cambiar el tipo de un plan ya utilizado. |
| Pagos | Registrar desde ambos roles; renovación anticipada; corregir importe/medio/referencia; rechazar una revisión desactualizada; anular conservando evidencia; consultar historial y conciliar ingresos. |
| Tiqueteras existentes | Fecha original y entradas utilizadas; traslado sin nuevo cobro; repetición de la misma solicitud sin duplicarla; saldo conservado al exportar e importar. |
| Entradas | Entrada manual y por código de huella; descuento de una entrada; rechazo sin plan, por inactividad y al agotar una sesión; autorización excepcional administrativa; historial en ambos roles. |
| Tienda | Crear/editar producto; buscar SKU; vender desde Recepción; descontar stock; impedir cantidades inválidas y venta sin existencias; activar/desactivar y consultar historial e informe financiero. |
| Gastos | Registrar desde Administración y Recepción; corregir importe; eliminar un gasto temporal y comprobar el total guardado. |
| Personal | Alta, edición y desactivación; entrada/salida del turno; rechazo de turnos duplicados o inexistentes; consulta del informe. |
| Rutinas | Crear rutina con cliente y entrenador; añadir ejercicios; comprobar relaciones y orden. |
| Clases | Crear clase; reservar; impedir sobrepasar el cupo en el recorrido secuencial; cancelar y reactivar sin duplicar la reserva. |
| Dashboard y estadísticas | Clientes y entradas del día; próximos vencimientos; saldos de tiqueteras; asistencia y seguimiento de sesiones de 7/14/30 días. |
| Marketing | Guardar configuración; consultar contactos; activar y revocar autorización; consultar actividad. No se envían mensajes externos. |
| Excel y respaldos | Exportar archivos reales; leer la vista previa; restaurar JSON y Excel en el segundo gimnasio; reconstruir relaciones e IDs; conservar saldos; rechazar JSON corrupto; revertir una importación con relaciones rotas. |
| Accesos y licencia | Deshabilitar/reactivar usuario; rechazar operaciones sin permiso o de otro gimnasio; suspender/reactivar; mensualidad comercial con reintento sin duplicación; respaldo e historial del propietario. |

Las suites del propietario amplían el recorrido con cambios de contrato, días de gracia, equipos, asignación/revocación de correos, edición de registros, importación y eliminación completa de un gimnasio de prueba. Verifican que el otro gimnasio conserve sus datos.

## Correcciones encontradas durante esta revisión

1. `focus_get()` y `grab_current()` intentaban resolver como objetos Python las ventanas internas `.popdown` de Tcl/ttk. Se utiliza su ruta Tcl y se resuelve el control propietario cuando corresponde. El desplegable se cierra de forma ordenada antes del aviso oscuro y se restaura el control del formulario.
2. Los guardados de rutinas, ejercicios y clases enviaban `objective`, `sort_order` y `active`, respectivamente, aunque el esquema comercial usa `goal`, `position` y `status`. Se corrigieron las llamadas, sin alterar las tablas del servidor.
3. Los ajustes pendientes de distribución de vistas ocultas y controles destruidos se cancelan o esperan a que la vista vuelva a mostrarse. Los textos se ajustan después de estabilizar el ancho, conservando las columnas del modo normal o maximizado.
4. La validación detecta también errores de callbacks de Tk escritos en la consola aunque el proceso termine con código cero. Una prueba específica comprueba que ese caso se marque como fallo y detenga las etapas siguientes.

## Entorno y límites

- Pruebas realizadas en Linux con Python 3.12, Tk y pantalla virtual Xvfb, además de PostgreSQL en memoria mediante PGlite. Los desplegables, controles, geometría, foco y consultas de visibilidad son reales de Tk.
- La simulación ejecuta las clases Python de la aplicación y las funciones/tablas/RLS del SQL comercial. Un adaptador local traduce las consultas; **no sustituye una prueba real de HTTP/PostgREST, Auth ni Realtime en red**.
- En Xvfb se simula el estado normal/maximizado del sistema operativo, porque no hay gestor de ventanas. La prueba incluida usa el estado nativo al ejecutarse en Windows. Se revisaron imágenes de las tres aplicaciones en ambas distribuciones.
- Medición local de referencia: despacho de una consulta de lectura de 0,06 ms; actualización de una tabla sin cambios de 1.000 filas de 1,76 ms, con cero borrados y cero inserciones. Son mediciones de este entorno, no una promesa de latencia de Internet ni de fluidez en cualquier computador.
- El recorrido cubre las áreas conectadas a los menús comerciales actuales. Los caminos heredados de importación SQLite/restauración antigua que no están conectados a esos menús no forman parte del recorrido. No se han probado todas las combinaciones posibles de datos ni una carga concurrente de múltiples equipos.
- No se compilaron ni ejecutaron EXE de Windows aquí. El generador realiza las pruebas en Windows y luego verifica los iconos embebidos antes de crear instaladores. Quedan por comprobar en el equipo de destino: instalación/actualización, accesos directos, movimiento nativo, lector físico, correo de acceso y sincronización real entre computadores.
- WhatsApp automático requiere su servicio y plantillas activos. Los envíos externos no se prueban ni se presentan como aprobados.
- No se modificaron gimnasios reales ni el SQL de esta entrega. Desde 3.4.0, no se necesita aplicar una migración.

## Repetir y revisar

`SIMULAR_GIMNASIO.bat` ejecuta todas las suites sin compilar. `CREAR_INSTALADORES.bat` exige esas mismas suites antes de crear los instaladores. Las ventanas de prueba deben estar visibles y el escritorio desbloqueado durante la parte gráfica.

Los resultados de cada ejecución se guardan en `salida/validacion`: resumen de texto, informe JSON, log por etapa y casos de la jornada. Un fallo detiene la validación y debe revisarse antes de distribuir la versión. El archivo `GymSoft_3.4.1_RESULTADOS_PRUEBAS.zip` conserva los resultados locales de esta preparación.

Created by Manuel Cuéllar  
© 2026 Manuel Cuéllar. All rights reserved.
