# Puerta automática de ZTATTUZ 3.6.1 · Edición de 32 bits

El lector DigitalPersona identifica al cliente, ZTATTUZ consulta su plan y registra la asistencia en la nube. Solo una entrada autorizada provoca una orden de apertura al LCUS-1. No hace falta colocar el cursor en el buscador. Mantén abierta Administración o Recepción, con la lectura automática activada y sin un formulario de registro de huella en curso.

## Equipo y preparación

- Lector DigitalPersona U.are.U 4500 o 5160, con el controlador y el reconocimiento incluidos en `DigitalPersonaRuntime`. Si ya registra e identifica huellas, no hace falta reinstalarlo.
- LCUS-1 de un canal, variante **CH340**, conectado por USB al mismo computador que lee las huellas.
- Controlador del CH340, si Windows no crea el puerto COM al conectarlo: [descarga oficial de WCH](https://www.wch-ic.com/downloads/CH341SER_EXE.html). En el programa está el botón **Controlador CH340 · fabricante**. Este controlador es diferente del de DigitalPersona; su instalador no se incluye en este ZIP.
- Electroimán de 12 V, fuente adecuada a su corriente, soporte y botón físico de salida con contacto **normalmente cerrado (NC)**.
- Windows 10 de 32 bits para esta edición x86. Una edición modificada de Windows debe conservar los servicios y controladores USB. La compilación y la instalación del programa no necesitan el lector ni el relé conectados.

La descripción del vendedor no confirma qué contactos trae el botón de salida. El instalador debe comprobar que dispone de NC; si solo tiene NO, no se debe montar esta conexión tal cual. La especificación de 350 libras es fuerza de retención, no consumo eléctrico.

## Conexión de 12 V para revisar con el instalador

Trabajar con la fuente desconectada. Esta tabla describe únicamente la parte de **12 V CC**; la alimentación de red de la fuente debe realizarla personal competente según las instrucciones del fabricante.

| Origen | Destino |
|---|---|
| USB del computador | USB del LCUS-1 |
| Positivo de la fuente de 12 V | COM del botón físico de salida |
| NC del botón de salida | COM del relé LCUS-1 |
| NC del relé LCUS-1 | Positivo del electroimán |
| Negativo del electroimán | Negativo de la fuente de 12 V |

El contacto NO del relé queda sin conectar en este esquema. Los 12 V no se conectan a los circuitos USB del módulo. El instalador debe verificar polaridad, corriente admisible en CC, protección de la carga inductiva según el fabricante del electroimán, cableado y fijación.

Con el relé desactivado, COM–NC alimenta el imán. Durante el pulso, el relé interrumpe esa alimentación. Al terminar, vuelve a enviar OFF. Pulsar el botón de salida debe interrumpir la alimentación del imán **sin depender del programa, del USB ni de Internet**. No se debe utilizar la puerta si esta salida independiente no funciona. Revisa también con el instalador los requisitos de evacuación del local.

## Activar la puerta

1. Instala la actualización ZTATTUZ 3.6.1 x86 y conecta el lector y el relé al computador del gimnasio.
2. En Administración, abre **Configuración → Puerta automática → Configurar puerta / relé**. También puedes entrar desde **Registro de entrada → Puerta / relé**.
3. Pulsa **Buscar puertos**. Selecciona el COM del LCUS-1. La lista filtra CH340; si hay varios, desconecta y reconecta solo el relé para identificarlo. No pruebes sobre otro equipo CH340.
4. Marca **Activar puerta automática en este computador** y elige una duración de **1 a 10 segundos**; el valor inicial es 3.
5. Pulsa **Guardar configuración**. El programa envía una orden OFF de preparación. Esto no abre la puerta.
6. Con una persona junto a la puerta, pulsa **Probar apertura** y confirma. Comprueba que el imán libere durante el tiempo seleccionado y vuelva a sujetar después. La prueba no registra asistencia.
7. En **Crear cliente** o **Editar cliente**, registra y verifica la huella. Asigna un plan vigente. En Registro de entrada, confirma que **Lectura automática de huella** está activada.
8. Coloca el dedo: se mostrará el resultado de acceso. Si es **INGRESO REGISTRADO**, se envía el pulso. Retira el dedo antes de una nueva lectura.

La configuración es local a este usuario de Windows, computador y gimnasio; la comparten Administración y Recepción. Las huellas y la asistencia siguen en la nube. Si usas otro usuario de Windows o cambias el puerto/conexión del relé, revisa y guarda su configuración allí. Usa una aplicación para leer el lector; el control impide que los dos ejecutables se disputen simultáneamente el relé dentro del mismo usuario.

## Abrir la puerta manualmente

En **Registro de entrada**, pulsa **Abrir puerta** y confirma. Está disponible en Administración y Recepción. Usa la duración guardada y se registra como apertura manual en el registro técnico local. No consulta el plan, no crea asistencia y no descuenta tiquetera. Si la puerta aún no está configurada, el programa te indica dónde activarla. Un fallo USB debe revisarse y restablecerse antes de otra apertura.

## Qué abre y qué no abre

| Situación | Asistencia | Puerta |
|---|---|---|
| Huella reconocida y mensualidad vigente | Se registra | Envía apertura |
| Huella reconocida y tiquetera vigente con saldo | Registra y consume una entrada | Envía apertura |
| Cliente inactivo, plan vencido, sin plan o sin saldo | Se muestra el rechazo | No envía apertura |
| Huella desconocida o eliminada | No identifica al cliente | No envía apertura |
| Registrar, cambiar o comprobar una huella | No registra asistencia | No envía apertura |
| Código escrito/HID, ingreso manual o autorización manual | Conserva el flujo existente | No envía apertura automática |
| No se recibe confirmación del servidor | Resultado sin confirmar | No envía apertura |
| USB falla después de registrar la asistencia | La asistencia permanece registrada | Muestra el problema; no repite el cobro/consumo |
| Abrir puerta, confirmado por Administración o Recepción | No registra asistencia | Envía un pulso manual |
| Probar apertura, confirmado por Administración | No registra asistencia | Envía un pulso de prueba |

Las lecturas repetidas no generan otra orden durante 10 segundos. No se acumulan aperturas para ejecutarlas más tarde. Si llegan otras personas durante un ciclo, revisa su resultado en pantalla; el programa no alarga automáticamente el pulso.

## Si ocurre un problema

- **No aparece un COM:** revisa cable USB y controlador CH340 en el Administrador de dispositivos de Windows. No hace falta instalar Python en el computador donde solo se usará el programa instalado.
- **Puerto distinto o equipo movido:** selecciona de nuevo el relé en Administración. El programa rechaza un puerto cuyo identificador/conexión no coincide con el guardado.
- **Orden USB incompleta o desconexión:** revisa físicamente la puerta y el cable; después pulsa **Restablecer relé (OFF)**. Esa acción no abre la puerta. No se reenvía una apertura pendiente al reconectar.
- **Se registró la asistencia, pero el USB falló:** no repitas el registro para intentar abrir. Atiende a la persona y utiliza la salida/control físico del establecimiento; un administrador puede realizar una prueba de apertura deliberada desde el panel.
- **Cierre inesperado, pérdida de USB o corte eléctrico:** el estado depende del cableado y del módulo. El programa intenta enviar OFF al terminar y al cerrar normalmente, pero no puede garantizarlo si Windows o el hardware se detienen. El botón de salida independiente debe permitir salir siempre.

Los mensajes **Orden de apertura enviada** y **Orden OFF enviada** confirman transmisión desde el programa; este LCUS-1 no aporta un sensor de puerta ni una confirmación de posición del imán. No deben interpretarse como una comprobación física. El registro técnico sin nombres ni huellas está en `%LOCALAPPDATA%\GymControl\puerta\puerta.log`.

## Validación de esta entrega

Pruebas automatizadas con lector y relé simulados; permisos, planes y asistencia comprobados contra PostgreSQL local. No se utiliza ni se modifica el gimnasio real. La validación del instalador no exige hardware. Después de instalar, deben comprobarse el lector real, el pulso, el regreso al estado de reposo, una entrada denegada y el botón de salida con el computador apagado antes de poner la puerta en servicio.

No se necesita SQL nuevo para actualizar desde 3.5.3.

## Referencias técnicas

- [Manual LCUS-1, comandos de apertura y cierre](https://images.100y.com.tw/pdf_file/57-LCUS-1.pdf). Ese manual muestra una variante PL2303; esta integración selecciona la variante CH340 descrita para tu compra. El protocolo de cuatro bytes es el mismo documentado: `A0 01 01 A2` y `A0 01 00 A1`.
- [Implementación de referencia LCUS-1 y contactos COM–NO / COM–NC](https://github.com/andrewintw/usb-powered-relay/blob/master/usbser2relay.sh).
- [Documentación oficial pySerial](https://pyserial.readthedocs.io/en/latest/pyserial_api.html): comunicación 9600, 8N1 y tiempos de escritura acotados.
- [Controlador oficial WCH CH340/CH341](https://www.wch-ic.com/downloads/CH341SER_EXE.html).
