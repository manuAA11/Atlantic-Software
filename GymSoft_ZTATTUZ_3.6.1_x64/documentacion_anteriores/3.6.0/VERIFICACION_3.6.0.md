# Verificación · Gym soft ZTATTUZ 3.6.0

**PASS: 25 etapas completas; 116 pruebas de Python.**

Interfaz comprobada con Tk real al 100 %, 120 % y 125 %. Se verificaron marcas blancas, foco de teclado y cierre/cancelación de avisos. La suite conserva las pruebas anteriores de distribución, respuesta gráfica, formularios, huellas, tiqueteras, pagos, aislamiento y una jornada simulada completa.

| Etapa | Resultado | Segundos |
|---|---|---:|
| python | PASS | 14.92 |
| contratos_extraidos | PASS | 0.57 |
| fingerprints | PASS | 1.70 |
| upgrade_compatibility | PASS | 1.85 |
| security | PASS | 1.77 |
| contracts | PASS | 1.65 |
| ticket_plans | PASS | 1.82 |
| ticket_followup | PASS | 1.85 |
| recorrido_huellas | PASS | 14.38 |
| simulacion_gimnasio | PASS | 12.95 |
| door_ui_smoke | PASS | 8.45 |
| dialog_design_ui_smoke | PASS | 15.50 |
| ui_wait_smoke | PASS | 0.27 |
| access_layout_ui_smoke | PASS | 20.10 |
| client_fingerprint_ui_smoke | PASS | 7.26 |
| fingerprint_ui_smoke | PASS | 8.97 |
| windows_ui_smoke | PASS | 1.20 |
| responsive_ui_smoke | PASS | 58.33 |
| biometric_ui_smoke | PASS | 3.92 |
| ticket_ui_smoke | PASS | 6.64 |
| performance_ui_smoke | PASS | 8.25 |
| popdown_ui_smoke | PASS | 3.91 |
| layout_modes_ui_smoke | PASS | 47.40 |
| review_ui_smoke | PASS | 5.04 |
| layout_consistency_ui_smoke | PASS | 8.39 |

El control de puerta añade 32 pruebas unitarias con transporte simulado y 78 comprobaciones de interfaz. El recorrido completo de huella y puerta incluye 42 comprobaciones con el SQL real contra PostgreSQL local.

Se verificaron: mensualidad y tiquetera autorizadas; inactivo, vencido, sin plan, sin saldo; inscripción y verificación sin abrir; lectura repetida; pérdida de respuesta; puerto equivocado; desconexión; escritura incompleta; transmisión bloqueada con tiempo acotado; OFF al cerrar; órdenes caducadas; exclusión entre aplicaciones; activación por configuración; apertura manual con confirmación sin registrar asistencia ni consumir tiquetera.

**No se cambió ninguna base real ni archivo SQL de la edición anterior.** Los archivos de DigitalPersona coinciden byte por byte con el paquete íntegro de la versión anterior. En Comercial se restauró una copia incompleta de Data1.cab desde ese paquete verificado; no se cambió la versión del controlador.

**Límites:** no se dispone aquí del Windows del gimnasio, del lector ni del relé físico. Los paquetes contienen código y el generador; no incluyen ejecutables Windows compilados. El PASS no certifica el montaje eléctrico, la posición de la puerta ni garantiza ausencia de todo fallo.

La prueba física se realiza después de instalar. No es un requisito para compilar. Los registros de cada etapa están en `salida/validacion`.
