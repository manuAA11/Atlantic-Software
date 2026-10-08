# Gym soft Comercial 3.5.0 · Verificación

Fecha: 25 de septiembre de 2026. Resultado local: **PASS**.

| Grupo | Resultado |
| --- | --- |
| Pruebas unitarias Python | 78 aprobadas; incluyen 14 de huellas |
| Permisos y concurrencia de huellas en PostgreSQL local | 16 comprobaciones aprobadas |
| Ventana de huellas, registro, eliminación y resultado de entrada | 28 comprobaciones con lector simulado, escalas 100 % y 125 % |
| Simulación de gimnasio con clases Python y PostgreSQL | 107 comprobaciones aprobadas |
| Etapas gráficas | 10 aprobadas, incluida la nueva ventana de huellas |
| Contratos, permisos, tiqueteras y seguimiento | Aprobados; detalle en los informes |

La simulación abarca clientes, pagos, correcciones, entradas, vencimientos, tiqueteras, gastos, inventario, ventas, clases, rutinas, personal, estadísticas, exportaciones e importaciones. No constituye una prueba exhaustiva de toda combinación posible.

La integración nueva prueba identificación conocida, desconocida y ambigua; pausa; lecturas repetidas; registro y cancelación; conservación de la huella anterior; eliminación remota; conflictos de edición y aislamiento entre gimnasios. Se evita repetir automáticamente una entrada cuya respuesta se perdió.

Se ejecutaron las suites de datos e interfaz por separado; `resultado_pruebas.json` combina los dos informes originales conservados en `salida/validacion`. Tras el ajuste final del texto y del directorio de trabajo del instalador se repitieron las pruebas unitarias. En Comercial también se repitió la prueba gráfica de huellas.

## Base real

ZTATTUZ: actualización aplicada. Consulta posterior confirmó RLS activa, sin permisos de ejecución anónima, sin lectura directa para usuarios autenticados y cero plantillas guardadas. No se usaron registros reales para probar operaciones biométricas.

Gym soft Comercial: proyecto pausado; migración pendiente de reactivación y ejecución del SQL incluido. Las comprobaciones funcionales se hicieron en una base local aislada.

## Límites de la comprobación

- Entorno utilizado: Linux, Python 3.12, Tk/Xvfb y PostgreSQL local mediante PGlite.
- Se contrastaron las declaraciones de la interfaz nativa con las cabeceras del SDK proporcionado. No se ejecutaron sus DLL de Windows ni se capturó una huella física.
- No se compilaron ni instalaron los ejecutables de Gym soft en Windows desde este entorno.
- Quedan pendientes Windows 10 Mini, el lector real, sincronización física entre dos equipos y servicios externos de correo y WhatsApp.
- Las pruebas de compilación no necesitan lector USB. No se han desactivado las comprobaciones funcionales existentes.

El componente DigitalPersona conserva sus archivos y licencia del proveedor en `DigitalPersonaRuntime/LICENSE.rtf`. No se incluye código de ejemplo del SDK.
