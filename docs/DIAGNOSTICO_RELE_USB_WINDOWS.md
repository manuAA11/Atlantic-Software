# Diagnóstico del relé USB en Windows

## Incidencia comunicada el 14 de octubre de 2026

En el computador de 32 bits, el usuario informa que Recepción registra entradas
permitidas y el botón no-touch libera el imán. El relé no hace clic ni enciende
su indicador durante la prueba de apertura. Las capturas muestran el CH340
presente, control activado, 9600 baudios, estado «Desconocido», última orden `—`
y fallo USB incluso al pulsar «Restablecer relé (OFF)».

Esto sitúa el fallo antes de confirmar en el registro la transmisión inicial OFF;
no demuestra que ningún byte haya llegado al módulo.
Todavía no identifica si falla la apertura/configuración del puerto, la escritura
o el vaciado de transmisión. Tampoco comprueba físicamente el cableado del relé.
La autorización del servidor y el botón de salida no verifican esa comunicación.

El cliente publicado con `7a44de8` conserva únicamente el tipo de excepción y
muestra un aviso genérico. Una entrada posterior puede sustituirlo por el aviso
de restablecimiento pendiente. Las capturas no contienen el error nativo de Windows.

## Comprobar la apertura del puerto sin transmitir

Con la puerta abierta y el botón de salida operativo, cerrar Administración,
Recepción y cualquier utilidad que utilice el puerto serie. Mantener el relé
conectado por USB. Abrir **Win+R → powershell** y pegar:

```powershell
$puertoRele = Read-Host 'Puerto del rele, por ejemplo COM6'
$pruebaRele = New-Object System.IO.Ports.SerialPort
$pruebaRele.PortName = $puertoRele.Trim().ToUpperInvariant()
$pruebaRele.BaudRate = 9600
try {
    $pruebaRele.Open()
    'OK: Windows pudo abrir el puerto'
} catch {
    'ERROR: ' + $_.Exception.GetBaseException().Message
} finally {
    $pruebaRele.Dispose()
}
```

Introducir el puerto observado para el LCUS-1 en ese computador. Esta prueba usa
el componente serie de Windows/.NET, disponible en Windows 10 de 32 bits; no
requiere Python ni cambia la configuración guardada del programa. Abre y cierra
el puerto con 9600/8N1, sin enviar ON, OFF ni otra trama. No certifica la transmisión,
los contactos o la apertura física del relé. La ejecución en el equipo real sigue
pendiente hasta recibir su resultado.

Conservar la línea `OK` o `ERROR`. Un resultado correcto permite continuar con
la investigación del transporte pySerial y la escritura; un error proporciona
el motivo que Windows devuelve al intentar abrir/configurar el puerto.

## Comprobación posterior

Después de resolver la causa del puerto, abrir solo Administración con el mismo
usuario de Windows y el mismo gimnasio que Recepción. Confirmar la configuración
guardada, ejecutar un único Restablecer y comprobar el mensaje OFF enviado. Con
la puerta abierta, la prueba de apertura requiere la confirmación administrativa
existente. Finalmente comprobar una entrada por huella/código autorizada.

Los contactos NC y los comandos del programa conservan la lógica documentada en
[la checklist presencial](../PRUEBA_PUERTA_ZTATTUZ.md). La recuperación del USB no
debe repetir asistencias ni enviar aperturas pendientes. La salida independiente
permanece operativa durante estas comprobaciones.

## Mejora del diagnóstico en las fuentes

La corrección posterior distingue validación/apertura del puerto, escritura y
vaciado del OFF inicial, ON, OFF final y cierre. Conserva el tipo permitido y los
códigos numéricos Windows/errno, con mensajes fijos; no imprime mensajes libres
de excepciones. Una entrada posterior bloqueada conserva la causa USB original.
El fallo solo se limpia tras completar satisfactoriamente el restablecimiento.

La regresión local aprobó 650 pruebas Python (Comercial 231, ZTATTUZ x64 210,
x86 209), incluidas 60 de puerta por edición. La prueba gráfica existente aprobó
78 comprobaciones por edición de configuración, confirmación, roles y escalas.
Son CPython/Tk en Linux con USB simulado; ejecutar el código x86 en este host no
acredita Windows32. [Evidencias y hashes](../evidence/relay-usb-diagnostics-20261014/summary.json).

El instalador publicado `7a44de8` no incorpora esta mejora; requiere una nueva
compilación Windows. En esta sesión la API de GitHub/Actions rechazó la credencial
disponible y no se generó esa compilación. No se modificaron los criterios de
aceptación ni se acreditó el funcionamiento del hardware. El usuario pidió
esperar mientras revisa las conexiones; el resultado de la prueba del puerto
de Windows sigue pendiente.
