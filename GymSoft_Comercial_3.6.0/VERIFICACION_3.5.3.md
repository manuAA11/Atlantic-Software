# Verificación de Gym soft Comercial 3.5.3

**PASS: 24 etapas completas; 113 pruebas de Python.**

Corrección de texto con márgenes y del ancho variable de las columnas en Registro de entrada. La regresión falla con el cálculo anterior y pasa con la corrección.

La suite completa conserva las pruebas de datos, seguridad, pagos, tiqueteras, huellas, formularios, carga, popdown y diseño. No se retiraron pruebas para conseguir un PASS.

| Etapa | Resultado | Segundos |
|---|---|---:|
| python | PASS | 6.75 |
| contratos_extraidos | PASS | 0.57 |
| fingerprints | PASS | 1.90 |
| security | PASS | 2.18 |
| contracts | PASS | 1.92 |
| owner_flows | PASS | 2.07 |
| owner_editor | PASS | 2.32 |
| ticket_plans | PASS | 2.04 |
| ticket_followup | PASS | 2.01 |
| recorrido_huellas | PASS | 14.12 |
| simulacion_gimnasio | PASS | 13.27 |
| ui_wait_smoke | PASS | 0.25 |
| access_layout_ui_smoke | PASS | 19.95 |
| client_fingerprint_ui_smoke | PASS | 7.16 |
| fingerprint_ui_smoke | PASS | 8.91 |
| windows_ui_smoke | PASS | 2.22 |
| responsive_ui_smoke | PASS | 61.57 |
| biometric_ui_smoke | PASS | 3.85 |
| ticket_ui_smoke | PASS | 6.61 |
| performance_ui_smoke | PASS | 8.27 |
| popdown_ui_smoke | PASS | 3.75 |
| layout_modes_ui_smoke | PASS | 54.98 |
| review_ui_smoke | PASS | 4.95 |
| layout_consistency_ui_smoke | PASS | 8.34 |

La etapa de diseño de ingreso contiene 270 comprobaciones; el recorrido gráfico de huellas, 124, y el registro integrado en clientes, 80. La prueba de datos biométricos recorre 28 casos contra PostgreSQL local.

**Entorno:** Linux con Tk real y PostgreSQL local. Dispositivo biométrico y respuestas del servicio simulados. No se dispone aquí de Windows ni del lector físico.

**No se modificaron la base real, SQL, permisos, pagos ni plantillas biométricas.** Se comprobó que los archivos del controlador coinciden byte por byte con la entrega base.

Los ejecutables deben compilarse e instalarse en Windows. Falta la comprobación visual en el Windows concreto del gimnasio y con el lector físico. Un PASS no garantiza ausencia de todos los errores.

Consulta los registros en `salida/validacion` y los hashes de los cambios en `VERIFICACION_3.5.3.json`.
