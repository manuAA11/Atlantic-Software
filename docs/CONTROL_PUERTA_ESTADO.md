# CONTROL DE PUERTA — ESTADO

Correcciones de software completas y pruebas locales aprobadas; compilación/pruebas Windows y aceptación física documentadas por separado. Requisitos originales: `REQUISITOS_PUERTA_ZTATTUZ_20261014.txt`. No se modificó el circuito eléctrico desde el software.

## DRIVER LCUS-1

Driver común en Comercial y ZTATTUZ x64/x86. Selección COM/identidad USB CH340, 9600/8N1 por defecto, tiempos de escritura acotados, pulso con watchdog independiente/finally, cancelación de escritura y OFF al cerrar. Errores quedan latentes hasta restablecer; no reenvía aperturas al reconectar. Puerto presente no equivale a relé físicamente validado.

## CONFIGURACIÓN WINDOWS

Administración → Configuración → Puerta automática; Propietario → gimnasio seleccionado → Puerta. Ajustes locales por gimnasio/PC: `automatic_door_enabled`, `door_unlock_seconds` (3 por defecto), puerto, identificación y velocidad serial. Conserva configuración schema1; guarda schema2 sin tocar membresías. Desactivada no descubre USB.

## LÓGICA NC / FAIL-SAFE

ON `A0 01 01 A2` activa bobina/abre NC/libera el imán. OFF `A0 01 00 A1` restaura reposo/NC. La alimentación del imán asegura; no mueve la hoja. El contacto, cableado y fail-safe se comprueban físicamente. El software no reemplaza salida no-touch ni liberación de emergencia.

## LECTOR DE HUELLA

Se conserva DigitalPersona U.are.U 4500/5160, almacenamiento/sincronización y comprobación sin asistencia. El lector va al computador, separado del relé. Encontrar huella no abre: se necesita el RPC de acceso. Probar lector reutiliza la pantalla existente; el panel Propietario ofrece diagnóstico de presencia sin captura/inscripción.

## MEMBRESÍAS

El resultado del servidor determina el acceso. No se recalculan vencimientos ni estados en el driver. Respuesta inválida, pérdida de backend o cliente no identificado no envían ON. La pérdida de backend cancela un pulso que siga activo.

## CONGELACIÓN / REANUDACIÓN

Congelación deniega. Reanudación del servidor permite la próxima identificación vigente, sin esperar los siete días originales ni reutilizar una denegación cacheada del lector. Se conservan días completos, idempotencia, máximo siete, DATE/TIMESTAMPTZ y zona del gimnasio.

## STAFF

INTERNAL activo permite sin pago/vencimiento por defecto, con asistencia separada; inactivo deniega. El driver no calcula esa regla ni altera estadísticas/contabilidad.

## TIQUETERA

Decisión y consumo los resuelve el servidor. Una entrada como máximo por día local; reentrada del mismo día no vuelve a descontar. Agotada sin consumo válido del día deniega.

## DEBOUNCE

Exclusión por cliente/gimnasio durante toda la llamada RPC y ledger SQLite con transacción antes del RPC: lecturas simultáneas del mismo cliente/gimnasio se suprimen durante 0,75 s, sin cachear autorización. El bloqueo entre procesos se libera al terminar la llamada o al cerrarse el proceso. Respuestas con más de dos segundos de espera conservan la asistencia del servidor pero no solicitan una liberación retrasada. El lector conserva el control de dedo retirado y debounce de accesos permitidos. Relé: un ciclo a la vez, sin cola ni extensión por otra lectura; exclusión entre procesos y deduplicación de órdenes existente.

## LOGS / DIAGNÓSTICO

Hora IANA del gimnasio para lector y puerta. Eventos de lector/código, identificación, backend, decisión, inicio/fin del pulso, desconexión/restablecimiento y error serial. Sin huellas, nombres, documentos ni credenciales. Pantalla: conexión serial, COM, estado solicitado, duración, última orden/error y Copiar diagnóstico. Logs de puerta limitados por rotación.

## TESTS EJECUTADOS

Suites locales completas en las tres ediciones (39 etapas Comercial, 38 cada ZTATTUZ); tests adicionales del driver, lector, UI, SQL/driver y empaquetado. Evidencia original y fallos corregidos en `evidence/door-access-20261014` y `evidence/closure-validation-20261008/*/all-door-20261014-v1`. Windows repite las 37 etapas habituales por edición, que incluyen ahora el flujo adicional de puerta. Se mantienen gates y aceptación externa pendiente.

## RESULTADOS

Software aprobado con transporte/SDK simulados y SQL real en PGlite: autoriza/rechaza, respeta congelación/reanudación/STAFF/tiquetera, evita doble escritura/pulso, limita apertura, retorna OFF en timeout/excepción/cierre y maneja desconexión. PGlite no acredita concurrencia de dos sesiones PostgreSQL reales. Comercial incorpora pySerial a dependencias y al empaquetado. Su antiguo criterio de relé no aplicable deja de usarse: pasa a pendiente para esta ampliación opcional, sin marcar hardware aprobado.

## ARCHIVO PRUEBA_PUERTA_ZTATTUZ.md

[Checklist de 16 pasos](../PRUEBA_PUERTA_ZTATTUZ.md): COM, driver, relé/retorno, lector autorizado/denegado, vencida/congelada/reanudada, STAFF, tiquetera, repetición, botón físico, USB, reinicio y prueba final. Identificar terminales por nombre, sin colores inventados. Incluida por edición.

## LO ÚNICO QUE QUEDA PARA PROBAR FÍSICAMENTE MAÑANA

La cadena real LCUS-1/CH340, contactos COM/NC, imán/fuente, retorno tras pérdidas de USB/energía y cierre/reinicio, huellero real y salida independiente. El servidor debe tener primero los upgrades/backend descritos en la checklist; no se desplegaron remotamente en esta tarea. El watchdog del PC no garantiza contacto físico si USB/Windows/hardware dejan de operar. No declarar seguridad eléctrica, evacuación o normativa a partir de estos tests.

Revisión independiente adicional: 55 pruebas específicas de puerta aprobadas, incluidas seis de orden ON/OFF y tres de petición lenta/en curso. El fallo de sincronización original x86 y los dos jobs Windows aprobados del run `38499829306` se conservan sin marcar la matriz como aprobada. La siguiente ejecución Windows valida las correcciones y el diagnóstico congelado de pySerial/puerta también en Comercial.

## Entrega Windows comprobada

Run [38555801086](https://github.com/manuAA11/Atlantic-Software/actions/runs/38555801086), commit `7a44de83f1aa6e1e7616a82f917ac3907d695568`: tres jobs success, 111 etapas y 599 tests Python, siete EXE y ocho instaladores reales. Comercial cliente/Propietario y ZTATTUZ x64 aprobaron instalación, actualización y desinstalación; x86 compilación/diagnósticos aprobados, instalación NOT_RUN en el host x64. Evidencia nativa y hashes en `evidence/windows-actions/38555801086`.

[Instaladores publicados](https://github.com/manuAA11/Atlantic-Software/releases/tag/configuracion-pruebas-7a44de8) para Administrador/Recepción de las tres ediciones. Los tres ZIP fueron descargados y verificados por CRC, tamaños, hashes internos/digest GitHub y commit/run; recibo `evidence/installer-downloads-door-20261014.json`. [Propietario](https://github.com/manuAA11/Atlantic-Software/actions/runs/38555801086/artifacts/11890383860) se entrega por separado, requiere iniciar sesión en GitHub y caduca el 12 de enero de 2027. Tiene pruebas nativas y hashes de instalador/copia, pero el almacenamiento bloqueó la descarga desde la nube; no se acredita verificación de bytes descargados. Hash original, metadata y alcance en `evidence/owner-installer-download-20261014.json`.

Para habilitar STAFF/reanudación se necesitan los dos SQL y el backend actualizado; no se aplicaron remotamente. Los archivos se incluyen en la release. Siguen siendo instaladores NO FINAL para configuración/prueba física; no se aprobaron hardware, cuentas reales ni concurrencia PostgreSQL por simulación.
