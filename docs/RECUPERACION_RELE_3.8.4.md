# Atlantic Gym 3.8.4 · Recuperación acotada del OFF final

El usuario aportó el registro completo y pidió un segundo chequeo que permita
recuperarse sin reiniciar. El archivo contiene 429 ciclos con ON registrado:
415 registran OFF final y 14 fallan al escribirlo tres segundos después del ON.
Hay 13 errores Windows 5 y un tiempo de espera agotado; cinco fallos corresponden
al 27 de octubre. Dos fallos ocurren durante la prueba manual y hay incidencias
en COM3 y COM4. Cada ciclo fallido produce dos eventos de error en el log anterior;
no se cuentan como dos fallos distintos. No se publica el registro del cliente.

Estos datos sitúan el fallo en la transmisión del OFF final. No identifican el
conector USB físico, la versión del controlador, la causa del error nativo ni
el estado de los contactos. Las desconexiones anotadas posteriormente pueden
corresponder a intervención manual; no prueban que una desconexión causara el
fallo inicial. Tampoco prueban que otro programa ocupara el puerto.

## Comportamiento de la actualización

La UI compartida utiliza `RecoveringDoorController`, que amplía el controlador
existente sin cambiar `common/door_access.py`, sus comandos, tiempos, watchdog,
limpieza, autorización, deduplicación o bloqueo exclusivo del equipo. Se
conservan las huellas históricas de la base oficial y todas sus comprobaciones.

Después de un fallo de escritura/vaciado del OFF final de un acceso, apertura
manual o prueba, se permite una sola recuperación:

1. El ciclo anterior y su cierre nativo deben haber terminado satisfactoriamente.
   Un cierre bloqueado o fallido impide una nueva apertura del puerto.
2. La configuración y su generación deben seguir vigentes, con puerta habilitada,
   mismo COM/VID/PID/serial/ubicación guardados y sin cierre de la aplicación.
3. Tras una espera cancelable de 200 ms se vuelve a comprobar la identidad USB.
4. El restablecimiento usa directamente el camino `secure` existente, en un
   puerto nuevo y bajo su bloqueo no bloqueante compartido entre aplicaciones.
   Sólo transmite OFF; nunca vuelve a ejecutar el acceso original.
5. Sólo completar las escrituras, su vaciado y el cierre permite limpiar el fallo.
   Si falta el puerto, otra ventana lo está usando o hay otro error, se conserva
   el bloqueo. La recuperación no entra en bucle y no crea una cola de aperturas.

El siguiente acceso exige una nueva respuesta permitida del servidor y las
reglas normales. El acceso original conserva su asistencia/consumo: no se llama
otra vez al RPC ni se reenvía ON aunque el restablecimiento funcione.

Fallos al enviar ON, comprobar/abrir el puerto o cerrar, y errores de programación
no inician esta política. El control desactivado y el modo offline no consultan
USB. La configuración, cables de 12V, DTR/RTS y controlador Windows no se cambian.

## Diagnóstico y validación

Los eventos nuevos `relay_off_recovery_start`, `relay_off_recovery_succeeded`,
`relay_off_recovery_failed` y `relay_off_recovery_skipped` conservan únicamente
los campos técnicos ya permitidos. El error original permanece en el registro.
La recuperación exitosa informa OFF enviado y necesidad de comprobar la puerta;
no afirma recepción, posición física ni solución del controlador/cable/módulo.

Las pruebas reproducen el bloqueo de la base 3.8.3 y comparan la recuperación
con transporte simulado: error Windows 5, representación pySerial, tiempo agotado,
fallo del vaciado, watchdog real, fallo persistente, cierre pendiente/fallido,
cambio de identidad/configuración, cierre de aplicación y competencia entre
ventanas. Comprueban una sola reconexión, ausencia de ON adicional/RPC repetido
y conservación de las restricciones para accesos denegados/congelados.

La validación Windows x86/x64 y de paquetes debe corresponder al commit exacto
antes de publicar. `release_readiness.json` conserva las aceptaciones externas
pendientes, incluida la del relé instalado. Windows x86 sobre host x64 no
acredita instalación Windows32 nativa. La distribución es una actualización
opcional de prueba desde la app; no se acredita una entrega final.

La prueba presencial debe observar tanto la recuperación como el retorno real
al reposo y la salida independiente según `PRUEBA_PUERTA_ZTATTUZ.md`. Si el
fallo persiste, se conservan ambos errores para investigar Windows y el módulo;
esta política no sustituye la resolución de un fallo físico o de controlador.
