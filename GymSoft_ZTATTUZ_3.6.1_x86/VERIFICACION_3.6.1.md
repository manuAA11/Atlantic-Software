# Verificación · ZTATTUZ 3.6.1 x86

Fecha: 30 de septiembre de 2026. Origen: paquete completo ZTATTUZ 3.6.0 x86.

## Cambios de esta versión

- El adaptador DigitalPersona habilita los modelos U.are.U 4500 y 5160 enumerados por el SDK. Otros modelos no se habilitan implícitamente.
- El estado de conexión muestra el modelo abierto. La ventana de huellas informa de ambos lectores compatibles.
- La exclusión de uso del lector conserva su identificador anterior para evitar que otra versión capture al mismo tiempo.
- Se mantienen el formato de las plantillas, el umbral de comparación, la verificación antes de guardar, la consulta del plan y el control de puerta de ZTATTUZ.
- Versión del producto e instaladores: 3.6.1. Destino: Windows 10 de 32 bits. Compilación: Python 3.13 x86.
- Los archivos SQL y los ocho archivos del runtime DigitalPersona coinciden byte a byte con la entrega 3.6.0 x86. No se ejecutó SQL ni se modificó el gimnasio real.

## Resultado automatizado

**25 etapas aprobadas** mediante `run_validation.py`, en Linux con Python 3.12, Tk sobre Xvfb y PostgreSQL local (PGlite). Duración acumulada de las etapas: 259 segundos.

- **127 pruebas Python aprobadas**, incluidas siete nuevas de compatibilidad de modelos: descriptores, selección del lector, captura, registro y comparación por el adaptador nativo, ausencia de lector, otros modelos y errores de apertura. También se comprueban la selección de DLL según arquitectura y los instaladores de 32 bits.
- **88 comprobaciones del recorrido biométrico**: 4500 y 5160, Administración y Recepción, utilizando el adaptador `NativeReader` real con las llamadas a las DLL simuladas. Incluyen guardado y lectura en PostgreSQL, registro y verificación separados de la asistencia, mensualidad, tiquetera, plan vencido, cliente inactivo, huella desconocida, borrado, protección contra duplicados y relé simulado.
- Pruebas SQL de permisos, aislamiento, contratos, actualización, planes y seguimiento; simulación de una jornada de gimnasio.
- Pruebas gráficas de registro de huellas, resultado automático, puerta, diálogos, pagos, navegación, distribución, rendimiento y desplegables. Las pruebas aplicables incluyen escalas de 100 %, 120 % y 125 %.
- Tras añadir la guía al instalador, se repitieron las cinco comprobaciones de empaquetado: aprobadas.

Los resultados por etapa y sus registros están en `verificacion/3.6.1_linux/`. Al compilar en Windows, la misma validación genera registros nuevos en `salida/validacion/`.

## Qué no prueban estas comprobaciones

El SDK simulado sustituye la carga de `dpfpdd.dll` y `dpfj.dll`; no se cargaron DLL Windows en Linux. Las muestras son sintéticas y la comparación simulada no mide precisión biométrica. Las pruebas no requieren ni intentan utilizar un lector USB o relé físico.

Quedan pendientes: compilación de los ejecutables e instaladores en Windows, instalación en el MiniOS del gimnasio, detección del 5160 por su controlador, calidad de captura e identificación del dedo real y funcionamiento físico del relé. No se incluye un ejecutable ZTATTUZ precompilado ni se afirma ausencia total de errores.

Después de instalar, comprueba una huella registrada y verificada, una entrada permitida, una denegada y, con el relé configurado, la apertura y el retorno al estado de reposo. Esta comprobación física no forma parte del proceso de compilación.

## Etapas

| Etapa | Resultado | Tiempo |
|---|---|---|
| `python` | PASS | 15.11 s |
| `contratos_extraidos` | PASS | 0.51 s |
| `fingerprints` | PASS | 1.73 s |
| `upgrade_compatibility` | PASS | 1.77 s |
| `security` | PASS | 1.77 s |
| `contracts` | PASS | 1.73 s |
| `ticket_plans` | PASS | 1.78 s |
| `ticket_followup` | PASS | 1.85 s |
| `recorrido_huellas` | PASS | 16.68 s |
| `simulacion_gimnasio` | PASS | 12.87 s |
| `door_ui_smoke` | PASS | 8.44 s |
| `dialog_design_ui_smoke` | PASS | 15.38 s |
| `ui_wait_smoke` | PASS | 0.26 s |
| `access_layout_ui_smoke` | PASS | 20.01 s |
| `client_fingerprint_ui_smoke` | PASS | 7.27 s |
| `fingerprint_ui_smoke` | PASS | 9.10 s |
| `windows_ui_smoke` | PASS | 1.21 s |
| `responsive_ui_smoke` | PASS | 58.40 s |
| `biometric_ui_smoke` | PASS | 3.92 s |
| `ticket_ui_smoke` | PASS | 6.60 s |
| `performance_ui_smoke` | PASS | 8.19 s |
| `popdown_ui_smoke` | PASS | 3.79 s |
| `layout_modes_ui_smoke` | PASS | 47.29 s |
| `review_ui_smoke` | PASS | 5.11 s |
| `layout_consistency_ui_smoke` | PASS | 8.38 s |
