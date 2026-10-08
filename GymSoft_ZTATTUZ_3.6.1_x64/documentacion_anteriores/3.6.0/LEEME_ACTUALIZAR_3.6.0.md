# Gym soft ZTATTUZ 3.6.0

Actualización de presentación y controles. Las casillas usan marcas blancas, con estados de selección y teclado conservados. Los avisos tienen iconos dibujados, texto alineado y acciones consistentes; las pestañas y botones siguen el tema oscuro. El acceso inicial muestra «Iniciar sesión» y «Crear cuenta».

## Instalar o actualizar

1. Cierra Administración y Recepción.
2. Extrae este ZIP completo en una carpeta nueva.
3. En el computador donde generas instaladores, ejecuta `CREAR_INSTALADORES.bat`. Utiliza Python 3.13 de 64 bits, Inno Setup 6 y Node.js LTS para las pruebas locales; los archivos de preparación incluidos comprueban las dependencias.
4. Espera a que las comprobaciones terminen. No necesitas conectar el lector ni el relé. Las pruebas gráficas abren ventanas: mantén el escritorio desbloqueado y las pruebas visibles.
5. En `salida`, ejecuta `ZTATTUZ_Instalar_o_Actualizar_3.6.0.exe`. Sirve para instalar y actualizar Administración y Recepción.

## Puerta automática y manual, exclusiva de ZTATTUZ

En Administración: **Configuración → Puerta automática**. Selecciona el COM del LCUS-1 CH340, configura 1 a 10 segundos y guarda la activación. Se conserva por usuario de Windows, computador y gimnasio; Administración y Recepción comparten esos datos locales.

- La huella identificada por DigitalPersona abre automáticamente solo después de que el servidor registre una entrada autorizada. No necesita el cursor en el buscador.
- El botón **Abrir puerta** de Registro de entrada está disponible en Administración y Recepción. Pide confirmación y envía un pulso manual; no crea asistencia ni descuenta tiquetera.
- El código escrito, el registro manual de asistencia y comprobar una huella no activan la apertura automática.
- Una respuesta de red sin confirmar, una huella desconocida o una entrada denegada no envían apertura.
- No hay colas de aperturas retrasadas; el USB se maneja fuera del hilo de interfaz. Los errores se muestran junto al control de puerta.
- El controlador DigitalPersona incluido se conserva. Si Windows no detecta el LCUS-1, instala el CH340 desde el enlace oficial que aparece en el panel.

Lee `GUIA_PUERTA_LCUS1.md` antes del montaje. El botón físico de salida debe cortar el imán independientemente del computador. La prueba del relé se hace **después de instalar**, con una persona presente en la puerta.

## Datos y comprobaciones

No necesitas SQL nuevo para actualizar desde 3.5.3. Esta entrega no cambia la base real, los permisos, los pagos, los clientes ni las plantillas biométricas. Se mantienen las correcciones de distribución estable y márgenes en Registro de entrada.

El ZIP contiene código y el generador de instaladores, no ejecutables Windows precompilados. La entrega se verifica en Linux con Tk real y PostgreSQL local; lector y relé simulados. El informe `VERIFICACION_3.6.0.md` detalla lo que se probó y lo pendiente. La compilación en Windows conserva sus controles de errores. La instalación y el hardware físico deben comprobarse en el equipo del gimnasio; las pruebas automáticas no garantizan que cualquier dispositivo o versión modificada de Windows funcione sin incidencias.

© 2026 Manuel Cuéllar. All rights reserved.
