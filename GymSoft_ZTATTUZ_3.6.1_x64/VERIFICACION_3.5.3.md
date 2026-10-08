# Verificación de Gym soft ZTATTUZ 3.5.3

**PASS: 23 etapas completas; 84 pruebas de Python.**

Corrección de texto con márgenes y del ancho variable de las columnas en Registro de entrada. La regresión falla con el cálculo anterior y pasa con la corrección.

La suite completa conserva las pruebas de datos, seguridad, pagos, tiqueteras, huellas, formularios, carga, popdown y diseño. No se retiraron pruebas para conseguir un PASS.

| Etapa | Resultado | Segundos |
|---|---|---:|
| python | PASS | 6.57 |
| contratos_extraidos | PASS | 0.51 |
| fingerprints | PASS | 1.77 |
| upgrade_compatibility | PASS | 1.98 |
| security | PASS | 1.80 |
| contracts | PASS | 1.81 |
| ticket_plans | PASS | 1.87 |
| ticket_followup | PASS | 1.85 |
| recorrido_huellas | PASS | 14.18 |
| simulacion_gimnasio | PASS | 12.77 |
| ui_wait_smoke | PASS | 0.25 |
| access_layout_ui_smoke | PASS | 20.02 |
| client_fingerprint_ui_smoke | PASS | 7.06 |
| fingerprint_ui_smoke | PASS | 8.94 |
| windows_ui_smoke | PASS | 1.21 |
| responsive_ui_smoke | PASS | 58.24 |
| biometric_ui_smoke | PASS | 3.86 |
| ticket_ui_smoke | PASS | 6.62 |
| performance_ui_smoke | PASS | 8.24 |
| popdown_ui_smoke | PASS | 3.79 |
| layout_modes_ui_smoke | PASS | 47.43 |
| review_ui_smoke | PASS | 4.95 |
| layout_consistency_ui_smoke | PASS | 8.29 |

La etapa de diseño de ingreso contiene 270 comprobaciones; el recorrido gráfico de huellas, 124, y el registro integrado en clientes, 80. La prueba de datos biométricos recorre 28 casos contra PostgreSQL local.

**Entorno:** Linux con Tk real y PostgreSQL local. Dispositivo biométrico y respuestas del servicio simulados. No se dispone aquí de Windows ni del lector físico.

**No se modificaron la base real, SQL, permisos, pagos ni plantillas biométricas.** Se comprobó que los archivos del controlador coinciden byte por byte con la entrega base.

Los ejecutables deben compilarse e instalarse en Windows. Falta la comprobación visual en el Windows concreto del gimnasio y con el lector físico. Un PASS no garantiza ausencia de todos los errores.

Consulta los registros en `salida/validacion` y los hashes de los cambios en `VERIFICACION_3.5.3.json`.
