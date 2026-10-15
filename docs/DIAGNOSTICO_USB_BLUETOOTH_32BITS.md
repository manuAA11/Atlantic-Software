# Diagnóstico USB / Bluetooth en ZTATTUZ de 32 bits

El usuario reportó que la primera apertura de puerta funciona, la música Bluetooth se corta y después la asistencia sigue registrándose, pero la puerta queda bloqueada. El relé se conecta mediante un adaptador USB cuyo tipo está por confirmar; no se ha confirmado el tipo de conexión del dispositivo Bluetooth. Todavía no se ha confirmado una causa física ni se ha reproducido el problema en ese computador.

La revisión de código no encontró llamadas para controlar Bluetooth, deshabilitar dispositivos ni cambiar la energía de Windows. El controlador abre únicamente el COM CH340 seleccionado y comprueba VID/PID e identidad guardada. Un fallo USB o de cierre, o la desaparición del puerto, bloquea nuevos pulsos hasta un restablecimiento OFF satisfactorio. Ese bloqueo conserva la asistencia registrada y evita reenviar una apertura retrasada; quitarlo automáticamente ocultaría el fallo original.

El colector permite comparar Windows antes y después del incidente sin tocar el relé. No identifica por sí solo si existe un problema de alimentación, interferencia eléctrica, controlador, adaptador o conexión USB.

## Uso en el computador afectado

1. Copie juntos [DIAGNOSTICAR_RELE_USB.bat](../tools/DIAGNOSTICAR_RELE_USB.bat) y [diagnose_relay_usb.ps1](../tools/diagnose_relay_usb.ps1) a una carpeta local. Ejecútelos desde esa carpeta, sin privilegios de Administrador. Requieren Windows 10 y Windows PowerShell 5.1; no requieren Python ni instalar módulos.
2. Abra `DIAGNOSTICAR_RELE_USB.bat`. El programa toma la fotografía **ANTES** y se queda esperando ENTER.
3. Reproduzca por separado, desde ZTATTUZ, únicamente la operación normal que iba a realizar. El colector no inicia pruebas, no libera la puerta ni repite asistencias. Observe si la música se corta y en qué momento respecto de la operación.
4. Cuando aparezca el fallo o termine la operación, vuelva a la ventana del colector y pulse ENTER. Se toma **DESPUÉS**, se consultan los últimos 20 minutos del registro System y se filtra el log local de puerta. Conserve el estado del fallo mientras se recoge esta evidencia.
5. Abra la carpeta indicada y lea `RESUMEN.txt`. Conserve juntos los ocho archivos de la colección para la revisión técnica. No hace falta adjuntar la configuración de Supabase, archivos de puerta ni el log original.

La carpeta nueva se crea debajo de `%LOCALAPPDATA%\Atlantic Tech Software\DiagnosticoUSB`. El lanzador elige PowerShell de la arquitectura nativa de Windows cuando está disponible; en Windows de 32 bits usa PowerShell de 32 bits. La arquitectura registrada es la del **colector**, además de la del sistema operativo: no demuestra la arquitectura del ejecutable instalado de ZTATTUZ.

`-ExecutionPolicy Bypass` se aplica únicamente al proceso que abre el lanzador; no modifica una política persistente ni evita las directivas de grupo. Si la organización bloquea el script, su responsable debe autorizarlo mediante el procedimiento habitual. El colector no pide elevación ni cambia esas políticas.

Para una carpeta alternativa, abra Windows PowerShell y ejecute el script con `-OutputDirectory 'C:\RutaLocal\CarpetaNueva'`. La carpeta debe ser nueva y local. El parámetro opcional `-DoorLogPath` permite indicar otro `puerta.log` local; su contenido original nunca se copia.

## Qué se guarda

| Archivo | Contenido |
| --- | --- |
| `antes.json` | Estado PnP previo de USB, puertos, Bluetooth y audio. |
| `despues.json` | Los mismos datos después de la operación. |
| `cambios.json` | Dispositivos añadidos, ausentes o con cambios de estado, problema, COM, controlador o relación de bus. |
| `sistema.json` | Versión/build de Windows, bits de Windows y del colector, versión de PowerShell. |
| `eventos_system.json` | Hora UTC, proveedor técnico, ID/nivel del evento y campos numéricos permitidos de estado o error de los últimos 20 minutos. |
| `puerta_sanitizada.json` | Hasta 500 líneas recientes del log de puerta, conservando solo eventos y campos técnicos expresamente permitidos. |
| `resumen.json` | Recuentos, disponibilidad de las consultas y limitaciones. |
| `RESUMEN.txt` | Resumen legible y advertencias de la colección. |

Los identificadores de instancia y de dispositivo padre se sustituyen por SHA-256 estable. VID/PID, COM, clase, estado y código de problema ayudan a distinguir el CH340 de los dispositivos Bluetooth y de audio cuando Windows los informa. Un hash permite correlacionar el mismo dispositivo entre fotografías; es un identificador seudónimo, no una garantía de anonimato frente a alguien que ya conozca el identificador original.

No se exportan nombres de usuario o equipo, nombres amistosos de dispositivos, seriales, identificadores de miembro/gimnasio, mensajes libres de eventos, contenido de configuraciones ni credenciales. El log de puerta se reconstruye con una lista explícita de eventos, etapas, tipos de error, números de Windows y comandos conocidos; se descartan textos libres y líneas incompatibles. Los archivos originales no se modifican. La ruta local mostrada en pantalla puede contener el nombre del perfil de Windows; no se agrega a los JSON ni al resumen guardado.

El colector solo escribe sus archivos nuevos. No abre puertos COM, no envía ON/OFF, no reinicia o deshabilita dispositivos, no modifica ahorro de energía, servicios, registro, controladores ni Bluetooth, y no sube información a la red.

## Cómo interpretar la evidencia

- Un dispositivo que desaparece o cambia de código de problema, junto con eventos USB/Bluetooth/PnP de la misma hora, ayuda a localizar la interrupción. No demuestra por sí solo una caída de voltaje ni un fallo eléctrico.
- Los hashes de dispositivo padre permiten comparar relaciones de bus cuando Windows las informa. Compartir un padre o cambiarlo es información de topología, no una prueba de causa.
- Dos fotografías iguales no descartan una desconexión breve y posterior reconexión. Los eventos pueden aportar evidencia del intervalo.
- Una colección `partial` conserva lo disponible e identifica lo que faltó. Puede ocurrir por cmdlets ausentes, permisos de eventos, propiedades no disponibles o falta del log. No hay que ejecutarla como Administrador para ocultar esa limitación.
- Si alguna consulta PnP no está disponible, la comparación se marca como no disponible y los recuentos de cambios quedan nulos: no se inventan desconexiones a partir de una fotografía fallida.
- System se limita a 3000 eventos recientes para acotar el trabajo. Si alcanza ese límite, se indica que los 20 minutos pueden estar incompletos. Si se espera más de 20 minutos antes de ENTER, también se informa la pérdida de cobertura inicial.

La revisión también confirmó que desactivar el control de flujo serial no equivale a mantener DTR/RTS bajos: pySerial conserva sus valores iniciales. Eso requiere conocer el hardware conectado para evaluar su relevancia; esta herramienta no cambia esas señales. El cierre del controlador y la recuperación del fallo se investigan por separado sin asumir que Bluetooth sea controlado por la aplicación.

Un OFF enviado no confirma la posición física de la puerta. La comprobación de instalación y cualquier restablecimiento presencial siguen el procedimiento de [PRUEBA_PUERTA_ZTATTUZ.md](../PRUEBA_PUERTA_ZTATTUZ.md); el colector no los ejecuta.

## Validación disponible

Los archivos se revisaron estáticamente para PowerShell 5.1. Además, PowerShell portable **7.4.13 en Linux** aprobó **97 comprobaciones** de parser, funciones, PnP y eventos simulados, tratamiento de errores, forma de los JSON y filtrado de identificadores, nombres y credenciales ficticios. La prueba reutilizable es [test_diagnose_relay_usb.ps1](../tools/tests/test_diagnose_relay_usb.ps1): extrae funciones por AST y no ejecuta el bloque principal ni la reproducción del incidente.

La prueba Linux sustituye expresamente la validación de rutas de Windows para usar únicamente su carpeta temporal; no acredita las API de unidades o puntos de reanálisis de Windows. Tampoco verifica Windows PowerShell 5.1 real, Windows x86/x64, permisos o cmdlets PnP reales, el lanzador BAT, Bluetooth, CH340 ni puerta física. Esos alcances siguen pendientes hasta obtener una ejecución en el computador afectado. No se contactó ni abrió ningún dispositivo durante las pruebas simuladas.

El código de salida es `0` si las consultas terminaron sin advertencias, `2` si se guardó una colección parcial y `1` si no se completó. Una interrupción antes de DESPUÉS puede dejar únicamente los archivos previos; no debe presentarse como una colección completa.

© Atlantic Tech Software — All rights reserved. By Manuel Cuellar
