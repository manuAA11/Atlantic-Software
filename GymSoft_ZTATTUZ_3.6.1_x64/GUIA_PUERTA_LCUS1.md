# Puerta automática opcional · LCUS-1

La capa compartida se usa en ZTATTUZ x64/x86 y, cuando se habilita, en Atlantic Gym Comercial. Por defecto está desactivada; un gimnasio sin puerta no enumera puertos ni necesita relé.

El huellero y el LCUS-1 se conectan por separado al computador. El driver usa un puerto COM seleccionado por Administración/Propietario, identificación USB CH340 y parámetros seriales guardados (9600/8N1 por defecto). Detectar un COM no confirma un relé ni sus contactos; la prueba real la hace el instalador.

Con el circuito COM/NC acordado: `A0 01 01 A2` activa la bobina, abre NC y libera el imán; `A0 01 00 A1` devuelve el relé a reposo y permite alimentar el imán. El relé no tiene sensor de posición ni confirmación de contactos. El cierre físico de la hoja depende del cierrapuertas.

Huella o código identificado → RPC actual de acceso → respuesta PERMITIDA confirmada → pulso limitado → OFF. No se duplican reglas de membresía en el driver. Vencido, congelado, STAFF inactivo o tiquetera agotada se deniegan por el servidor. Reanudar permite la próxima lectura vigente sin esperar el séptimo día. La deduplicación anterior al RPC evita registros simultáneos; las tiqueteras siguen consumiendo como máximo una entrada por día local.

Administración → Configuración → Puerta automática permite guardar COM, duración de liberación (3 segundos recomendado) y velocidad serial. El panel Propietario tiene una pestaña Puerta para el gimnasio seleccionado y hardware de ese computador, no un control remoto de otros PC. Probar apertura y Liberar puerta requieren permiso administrativo y confirmación. Recepción conserva consulta del estado y restablecimiento OFF; no ofrece bypass manual ni pruebas de liberación. Probar lector usa la comprobación ya existente, sin asistencia ni relé.

Watchdog independiente, finally, cierre normal y cancelación intentan OFF. Una desconexión queda registrada y requiere restablecer, sin aperturas pendientes al reconectar. El software no garantiza retorno físico si USB, módulo, Windows o alimentación fallan; el LCUS-1 no incorpora aquí un temporizador autónomo confirmado. La salida no-touch y liberación de emergencia deben funcionar sin PC. No hay apertura indefinida.

Diagnóstico con hora IANA del gimnasio y sin datos biométricos: `%LOCALAPPDATA%\GymControl\puerta\puerta.log` y `%LOCALAPPDATA%\GymSoft\logs\huellas.log`. La pantalla muestra puerto, estado solicitado, duración, última orden y último error; estos datos no equivalen a posición física.

Los [pasos de prueba presencial](PRUEBA_PUERTA_ZTATTUZ.md) contienen las verificaciones de cableado por terminales, contactos, imán, retorno, lector, membresías, salida independiente y fallos de USB/energía. Nunca identificar cables por color ni declarar conformidad eléctrica sólo por tests de software.

La ampliación de puerta no añade SQL; STAFF/reanudación requieren los dos upgrades y backend descritos en la checklist. Los tests automáticos usan transporte/SDK simulados y PostgreSQL local PGlite; no acreditan hardware ni servidor remoto.

Referencias: [manual LCUS-1](https://images.100y.com.tw/pdf_file/57-LCUS-1.pdf), [contactos COM/NC](https://github.com/andrewintw/usb-powered-relay/blob/master/usbser2relay.sh), [pySerial](https://pyserial.readthedocs.io/en/latest/pyserial_api.html), [controlador WCH CH340](https://www.wch-ic.com/downloads/CH341SER_EXE.html). Confirmar el protocolo y variante del dispositivo real antes de poner la puerta en servicio.
