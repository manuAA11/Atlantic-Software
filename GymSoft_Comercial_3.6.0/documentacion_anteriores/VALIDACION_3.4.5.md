# Validación de Gym soft Comercial 3.4.5

Revisión del 14 de septiembre de 2026 sobre la entrega 3.4.4. Se corrigió la distribución compartida y se ejecutó la batería completa con datos ficticios. No se modificaron datos de gimnasios reales ni funciones o permisos del servidor.

**Resultado: PASS en las 18 etapas — nueve de datos y nueve de interfaz.**

## Problema corregido

La reorganización anterior cambiaba columnas, quitaba el crecimiento vertical de las filas y sustituía la alineación completa de sus paneles por una alineación horizontal. Por eso una ventana mediana apilaba tarjetas y, en Estadísticas, quedaba un hueco entre el gráfico y los indicadores inferiores.

La nueva regla conserva las columnas, las celdas combinadas, la alineación y los pesos de crecimiento originales. Los anchos mínimos se calculan por control y se guardan en caché. Las barras de acciones conservan su alineación natural y los encabezados no reservan una fila vacía para avisos.

## Resultados por área

| Área | Comprobación ejecutada |
| --- | --- |
| Lógica Python | 64 pruebas de formularios, importes, fecha, concurrencia, licencia y otras reglas. |
| Seguridad | 54 comprobaciones en PostgreSQL local. |
| Contratos | Extracción y comprobación de 61 llamadas RPC y 15 contratos de tablas. |
| Operaciones del propietario | 35 comprobaciones. |
| Editor del propietario | 159 comprobaciones de permisos, conflictos, registros, importación, inventario y eliminación aislada. |
| Huella opcional y cupos | 27 comprobaciones de registro, consumo, renovación, mensualidad y aislamiento. |
| Tiqueteras y seguimiento | 70 comprobaciones de fechas, saldos, seguimiento, roles e idempotencia. |
| Jornada de un gimnasio | 107 comprobaciones con las clases Python y el SQL comercial. |
| Inicio y ventanas | Acceso, Sí/No, formularios, mensajes oscuros, archivos, pagos, gastos y editor. |
| Espacio disponible | 503 comprobaciones de tamaños, navegación y formularios al 100 % y 125 %; recorrido de pestañas y pruebas del detector de controles tapados. |
| Lector automático | Lectura con y sin Enter, búsqueda manual, repetición, foco fuera del buscador, formularios, pausa y respuestas pendientes. |
| Fechas y planes en interfaz | 34 comprobaciones al 100 % y 125 %. |
| Carga y actualización | 14 páginas, consultas fuera del hilo de dibujo, respuestas vigentes, ráfagas agrupadas, modales, selección, barras condicionales y reutilización. |
| Desplegables nativos | 40 comprobaciones del problema popdown, pagos, avisos y recuperación. |
| Distribución de todas las páginas | 396 comprobaciones en ventana normal, maximizada y movida al 100 %, 120 % y 125 %. Se añadió la comprobación de columnas, celdas, alineación y ocupación vertical. |
| Regresiones de rendimiento y pagos | 71 comprobaciones de transiciones, desplazamiento, guardados lentos o fallidos, doble envío, invitaciones y catálogo con productos. |
| Dashboard y Estadísticas | 120 comprobaciones nuevas de columnas estables y ausencia del hueco intermedio, con datos ficticios al 100 %, 120 % y 125 %. |

Los números indican comprobaciones ejecutadas, no un porcentaje de cobertura de todas las combinaciones posibles. El número de controles visibles varía con la distribución; no se eliminaron etapas para obtener el resultado.

## Comprobaciones específicas de diseño

- Dashboard: cuatro indicadores, cuatro acciones rápidas y cuatro tarjetas de vencimiento en sus filas; tiqueteras en dos filas de tres; cumpleaños en una fila de tres.
- Ventana mediana de 1280 × 800, grande de 1560 × 900, restaurada y estrecha de 900 × 620, con las tres escalas.
- El Dashboard cabe horizontalmente en las ventanas mediana y grande de la prueba. Una ventana menor conserva controles legibles y permite desplazarse cuando sea necesario.
- El gráfico y la tabla de Estadísticas llenan su fila; el espacio hasta los indicadores inferiores corresponde al margen previsto, de 12 píxeles.
- El recorrido de las páginas de Administración, Recepción y Propietario comprueba que el adaptador no pierda filas, columnas, celdas combinadas ni capacidad de crecimiento.
- Mover la ventana y desplazar contenido estable no vuelve a distribuir tarjetas.
- Se inspeccionaron capturas finales del Dashboard mediano, Estadísticas grande y el panel del propietario al 125 % en el escritorio virtual.

## Operaciones simuladas

La jornada de prueba cubre altas y consultas de clientes; cumpleaños y huella opcional; planes, tiqueteras y pagos; entradas y consumo de cupos; corrección y anulación de pagos con auditoría; ventas e inventario; gastos y conciliación; personal, turnos y rutinas; clases y reservas; estadísticas y seguimiento; marketing y autorización de contactos; Excel, respaldos y restauración; roles, licencia y aislamiento entre gimnasios.

El motor de pruebas es PostgreSQL local mediante PGlite. El transporte de pruebas conecta las clases Python con ese motor. Esto verifica reglas y resultados del SQL, pero no equivale a utilizar Internet, Auth o Realtime de un gimnasio real.

## Rendimiento observado

En esta ejecución, despachar una consulta al trabajador tomó **0,05 ms**. Aplicar una respuesta idéntica a una tabla de **1.000 filas** tomó **2,05 ms**, con **cero borrados y cero inserciones**. Son mediciones puntuales de este entorno, no tiempos garantizados en Windows ni mediciones de la latencia del servidor.

Las pruebas conservan las comprobaciones de que una operación lenta permite que avance el bucle de eventos, un error de pago mantiene los campos del formulario y otro envío durante la espera no repite la escritura. No se reintentan pagos automáticamente.

## Entorno y límites

Se utilizó **Linux, Python 3.12.14 y Tk 9.0**, con Xvfb. Cuando no hay gestor de ventanas se emula el estado normal/maximizado; la geometría, los controles y los eventos que se inspeccionan son reales de Tk.

**El ZIP contiene fuentes; no contiene ejecutables compilados o probados en Windows.** El constructor utiliza Python 3.13 de 64 bits, PyInstaller e Inno Setup y vuelve a ejecutar la batería completa. Comprueba también los recursos del icono GS antes de generar los instaladores.

Queda por comprobar en el equipo Windows de uso: instalación/actualización, iconos, dibujo durante desplazamiento y maximización, cambio entre monitores, lector físico, correo de acceso, conexión entre equipos y servicio de WhatsApp si se ofrece. Las pruebas automatizadas no garantizan ausencia absoluta de errores.

## Reproducir

Ejecuta `SIMULAR_GIMNASIO.bat` o `CREAR_INSTALADORES.bat`. Mantén el escritorio desbloqueado y las ventanas de prueba visibles. Los registros se guardan en `salida/validacion`; una etapa fallida detiene la compilación.

El paquete de resultados incluye `resultado_pruebas_all.json`, el resumen y los registros de las 18 etapas, además de la salida completa y un manifiesto con la huella SHA-256 del paquete de fuentes correspondiente.

Created by Manuel Cuéllar  
© 2026 Manuel Cuéllar. All rights reserved.
