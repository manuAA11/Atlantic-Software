# Verificación · Gym soft Comercial 3.6.0

**PASS: 25 etapas completas; 113 pruebas de Python.**

Interfaz comprobada con Tk real al 100 %, 120 % y 125 %. Se verificaron marcas blancas, foco de teclado y cierre/cancelación de avisos. La suite conserva las pruebas anteriores de distribución, respuesta gráfica, formularios, huellas, tiqueteras, pagos, aislamiento y una jornada simulada completa.

| Etapa | Resultado | Segundos |
|---|---|---:|
| python | PASS | 6.64 |
| contratos_extraidos | PASS | 0.54 |
| fingerprints | PASS | 1.96 |
| security | PASS | 1.95 |
| contracts | PASS | 1.88 |
| owner_flows | PASS | 2.23 |
| owner_editor | PASS | 2.29 |
| ticket_plans | PASS | 1.93 |
| ticket_followup | PASS | 2.12 |
| recorrido_huellas | PASS | 14.27 |
| simulacion_gimnasio | PASS | 13.38 |
| dialog_design_ui_smoke | PASS | 15.54 |
| ui_wait_smoke | PASS | 0.28 |
| access_layout_ui_smoke | PASS | 20.18 |
| client_fingerprint_ui_smoke | PASS | 7.31 |
| fingerprint_ui_smoke | PASS | 9.00 |
| windows_ui_smoke | PASS | 2.34 |
| responsive_ui_smoke | PASS | 61.89 |
| biometric_ui_smoke | PASS | 3.86 |
| ticket_ui_smoke | PASS | 6.69 |
| performance_ui_smoke | PASS | 8.18 |
| popdown_ui_smoke | PASS | 3.84 |
| layout_modes_ui_smoke | PASS | 55.15 |
| review_ui_smoke | PASS | 5.11 |
| layout_consistency_ui_smoke | PASS | 8.47 |

**No se cambió ninguna base real ni archivo SQL de la edición anterior.** Los archivos de DigitalPersona coinciden byte por byte con el paquete íntegro de la versión anterior. En Comercial se restauró una copia incompleta de Data1.cab desde ese paquete verificado; no se cambió la versión del controlador.

**Límites:** no se dispone aquí del Windows del gimnasio, del lector ni del relé físico. Los paquetes contienen código y el generador; no incluyen ejecutables Windows compilados. El PASS no certifica el montaje eléctrico, la posición de la puerta ni garantiza ausencia de todo fallo.

La prueba física se realiza después de instalar. No es un requisito para compilar. Los registros de cada etapa están en `salida/validacion`.
