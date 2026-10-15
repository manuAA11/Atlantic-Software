# PRUEBA DE PUERTA ZTATTUZ EN WINDOWS

Revisión de software: 14 de octubre de 2026. Esta checklist requiere un instalador de puerta para las comprobaciones eléctricas y mecánicas. Los tests de software no prueban el equipo, el cableado ni el cumplimiento normativo.

## Antes de empezar

- Tener salida independiente: botón no-touch y liberación de emergencia donde corresponda, operativos sin aplicación ni computador. Mantener a una persona junto a la puerta durante cada prueba.
- El instalador confirma en las etiquetas/documentación de cada equipo los terminales **COM, NC, +12V y GND**; no asignar funciones por colores de cables. Confirmar tensión, corriente y alimentación apropiadas, aislamiento del contacto y características del módulo real.
- Circuito previsto, que debe confirmar el instalador: fuente **+12V → COM relé → NC relé → COM botón → NC botón → electroimán +**; electroimán − a GND. El botón recibe además su propia alimentación +12V/GND. El huellero y el LCUS-1 son USB independientes al computador; el huellero NO se conecta eléctricamente al relé.
- COM/NC en reposo permite alimentar el imán; activar la bobina del LCUS-1 abre NC y libera. El imán no mueve la hoja: el cierre depende del cierrapuertas y de su alineación. Confirmar físicamente la variante real del relé antes de conectar el imán.
- Para STAFF/reanudación nuevas en el servidor actual, aplicar primero `ACTUALIZAR_PLANES_INTERNOS.sql`, después `ACTUALIZAR_REANUDACION_MEMBRESIAS.sql`, sobre una base que ya tenga los upgrades previos; desplegar el backend actualizado. No reinstalar el esquema inicial. Esta tarea no modificó el servidor remoto.
- Usar Windows y paquete de la arquitectura correcta: x64 en Windows64; x86 sólo en Windows32. El PC instalado no requiere Python. El runtime DigitalPersona viene incorporado; CH340 puede requerir el controlador oficial de WCH.

## Pasos de prueba

1. **Identificar COM.** En Administrador de dispositivos → Puertos (COM y LPT), conectar/desconectar el LCUS-1 y comprobar qué puerto CH340 aparece. Confirmar el módulo, VID/PID y ubicación; la existencia de COM no acredita el relé. No escoger otro CH340. Anotar COM, modelo y arquitectura Windows.
2. **Configurar.** Iniciar sesión en Administración → Configuración → Puerta automática → Configurar puerta / relé. Pulsar **Detectar relé**, escoger el COM observado, 9600/8N1 salvo que la documentación del módulo real indique otra velocidad, duración **3 segundos**, activar y guardar. La configuración se guarda para el gimnasio y PC actual. Restablecer envía sólo OFF; confirmar presencialmente el contacto en reposo.
3. **Relé sin huella.** Con el instalador, comprobar primero el contacto y el circuito de forma controlada. Pulsar **Probar apertura**, leer y aceptar la confirmación. Esperado: trama `A0 01 01 A2` activa bobina/abre NC; el imán pierde alimentación y libera. No registrar asistencia ni probar un botón de mantener abierto.
4. **Retorno.** Tras unos 3 segundos comprobar OFF `A0 01 00 A1`, retorno COM↔NC y alimentación del imán. La puerta sólo se asegura con hoja cerrada y alineada. Repetir cerrando la ventana de configuración y cerrando normalmente la aplicación durante el pulso: comprobar retorno. Los logs confirman transmisión, no posición física ni recepción por el módulo.
5. **Huella autorizada.** Con lector conectado directamente al PC, pulsar **Probar lector**. Comprobar una huella desde la ficha del cliente sin generar asistencia. Después, en modo de acceso, un cliente mensual vigente: identificación → respuesta PERMITIDA del servidor → una asistencia → un pulso → reposo.
6. **Huella rechazada.** Probar una huella desconocida: sin cliente identificado, sin asistencia y sin pulso. Probar cliente inactivo: respuesta denegada del backend y ninguna activación.
7. **Vencida.** Probar cliente comercial vencido. Esperado: DENEGADA; nunca ON. No usar autorización excepcional para esta comprobación.
8. **Congelada.** Congelar una membresía autorizada. Probar huella y código: DENEGADA/FROZEN; ningún pulso. El acceso no se permite mediante override de congelación.
9. **Reanudada.** Desde Administración reanudar la anterior. Confirmar días completos usados y nuevo vencimiento en servidor; retirar/volver a colocar dedo. Si vigente, permitir sin esperar al séptimo día original. Antes de 24 horas de congelación, extensión 0.
10. **STAFF.** Asignar plan INTERNAL activo ($0, ilimitado, sin vencimiento por defecto). Esperado: permitir, registrar asistencia de personal separada, sin cobro/deuda/descuento. Desactivar esa membresía: denegar, nunca ON. Reactivar y repetir.
11. **Tiquetera.** Con entradas vigentes, permitir y descontar una según el día local del gimnasio. Reentrada el mismo día conserva el descuento único. Una tiquetera sin saldo y sin entrada ya consumida ese día debe denegar. No confundir saldo cero tras ingreso del día con prohibición de reentrada del mismo día.
12. **Lectura repetida/código.** Dos lecturas casi simultáneas: una escritura de asistencia, un consumo y un pulso; sin timers que alarguen apertura. Probar el código exacto identificado por la aplicación: usar la misma autorización del servidor. Una nueva persona durante un pulso no acumula otra apertura; revisar resultado/estado y atenderla sin repetir asistencia.
13. **Botón no-touch.** Instalador: TLEB102 libera mediante su contacto NC aun con ZTATTUZ cerrado y computador apagado. El software no tiene que recibir ese evento ni registrar salida. Comprobar también la liberación de emergencia independiente.
14. **Desconectar USB.** Probar antes de acceso y durante un pulso bajo supervisión del instalador. El software debe mostrar error/desconexión, intentar OFF y no repetir asistencia ni reabrir al reconectar. Reponer el USB y pulsar **Restablecer relé (OFF)**; comprobar físicamente reposo antes de reactivar acceso. Un LCUS-1 sin respuesta ni temporizador autónomo puede conservar un estado tras pérdida de comunicación: el watchdog del PC no garantiza contactos en esa situación. No poner la puerta en servicio si el retorno físico falla; el instalador debe resolverlo con hardware/apertura independiente adecuados.
15. **Reiniciar.** Cerrar normalmente/reabrir aplicación: configuración conservada y sólo OFF inicial, sin apertura automática. No existe botón de apertura indefinida. Probar también sin Supabase disponible: ninguna autorización nueva puede liberar; restablecer conexión sin reenviar accesos pendientes.
16. **Prueba final.** Instalador: corte/restablecimiento de 12V, fail-safe sin alimentación libera y al volver permite asegurar con la hoja alineada. Comprobar lector autorizado/denegado, relé, reposo, salida independiente, duración y logs en conjunto. Desactivar puerta automática y verificar asistencia normal sin búsquedas ni errores de relé.

## Diagnóstico para guardar

En Puerta / relé, usar **Copiar diagnóstico**. Guardar hora/zona, COM, duración, última orden y último error. Eventos en `%LOCALAPPDATA%\GymControl\puerta\puerta.log`; lector en `%LOCALAPPDATA%\GymSoft\logs\huellas.log`, con hora IANA del gimnasio. No adjuntar plantillas, imágenes de huella, credenciales ni documentos personales.

| Etapa | Evidencia esperada |
|---|---|
| Lector | `fingerprint_detected`, lector disponible o error nativo sin datos de huella |
| Identificación | `member_identified` con ID técnico; desconocida no genera RPC de entrada |
| Backend | `access_decision` PERMITIDA/DENEGADA o `backend_error`; sin confirmación no ON |
| Membresía | Motivo/estado del servidor, congelación, STAFF o tiquetera |
| Puerto/relé | `relay_unlock_start`, `relay_unlock_end`, `relay_rest_failed`, COM y trama enviada |
| Duplicados | `duplicate_read_ignored`; no segunda escritura ni pulso |

Registrar PASS/FAIL por cada paso con fecha/hora, equipo y observación del instalador. Hasta comprobar físicamente contactos, imán, retorno y salida independiente, la puerta queda **pendiente de aceptación física**. El programa no es un mecanismo de evacuación ni una certificación eléctrica.
