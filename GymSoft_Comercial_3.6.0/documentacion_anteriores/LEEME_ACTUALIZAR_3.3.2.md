# Gym soft Comercial 3.3.2

Entrega completa de Administración, Recepción y el panel privado del propietario.

## Corrección de compilación del 9 de septiembre de 2026

Esta entrega incluye la corrección de la prueba que informaba `Control tapado ... financepage ... el ratón encuentra None`. Las pruebas ahora usan la misma configuración DPI que la aplicación, ajustan sus ventanas al área útil del monitor y consultan puntos dentro del área visible. Siguen deteniendo la compilación si un control está realmente tapado o no se encuentra en el punto visible.

Si ya tienes la carpeta **GymSoft_Comercial_3.3.2** y sus dependencias instaladas, puedes aplicar **GymSoft_3.3.2_PARCHE_COMPILACION.zip**: copia su contenido dentro de esa carpeta, acepta reemplazar los archivos y vuelve a ejecutar **CREAR_INSTALADORES.bat**. El archivo `LEEME_PARCHE_COMPILACION.txt` incluye los pasos. El paquete completo ya incorpora la corrección.

## Qué corrige

La adaptación del diseño colocaba un contenedor por encima de las pestañas y de algunas tablas. Los controles existían, pero quedaban tapados. Esta versión corrige su orden de presentación, también después de cambiar de sección o tamaño. Configuración vuelve a mostrar sus pestañas y Estadísticas conserva el acceso a asistencia, frecuencia y seguimiento de sesiones.

La lectura de huella ahora muestra **Lectura automática de huella: activada** o **pausada**, junto al botón correspondiente. Sustituye la casilla cuyo indicador «X» resultaba confuso. El estado se comparte entre las pantallas de cada aplicación.

**Esta actualización no requiere SQL nuevo.** Conserva la base comercial y las funciones de 3.3.0 y 3.3.1. No ejecutes `INSTALAR_BASE_NUEVA.sql` para actualizar un gimnasio existente.

## Instalar o actualizar en Windows

1. Cierra Administración, Recepción y el panel del propietario.
2. Extrae el ZIP completo en una carpeta nueva.
3. Ejecuta **CREAR_INSTALADORES.bat**. Requiere Python 3.13 de 64 bits e Inno Setup 6.
4. Instala `salida/GymSoft_Instalar_o_Actualizar_3.3.2.exe` para Administración y Recepción.
5. Solo en tu computador de propietario, instala `salida/GymSoft_Propietario_PRIVADO_3.3.2.exe`.
6. Abre los accesos directos instalados y comprueba que la versión sea **3.3.2**.

El ZIP contiene las fuentes completas y el generador de instaladores; no incluye ejecutables ya compilados. El instalador de Administración y Recepción es el que se entrega a los gimnasios. El panel del propietario es privado.

La compilación conserva las pruebas de acceso, formularios, editor, diseño, huella y tiqueteras, y la comprobación del icono GS de los ejecutables. Si falla alguna prueba, se detiene antes de generar los instaladores. El aviso de actualización de pip no es un fallo de la aplicación.

## Lectura automática

- Al iniciar la aplicación, la lectura automática está activada.
- **Pausar lectura** cambia el estado a «pausada» e impide los intentos automáticos de registro.
- **Activar lectura** vuelve a habilitar esos intentos. El estado se conserva al navegar mientras la aplicación permanece abierta.
- Un lector compatible que escriba el código como un teclado puede identificar al cliente sin seleccionar el buscador, mientras Gym soft tenga el foco.
- También puedes escribir el código exacto en el buscador de Registro de entrada. La aplicación intenta identificarlo después de terminar de escribir.
- La huella debe estar asociada a un cliente del gimnasio. Al encontrarlo, el sistema valida su membresía y registra el resultado del ingreso. Las lecturas repetidas del mismo código se filtran durante cinco segundos.
- La captura automática se pausa temporalmente al abrir formularios o trabajar en otra aplicación. El registro manual sigue disponible aunque pauses la lectura.

El código de huella sigue siendo opcional al crear un cliente. Esta función no configura el lector físico ni controla directamente un torniquete.

## Planes, tiqueteras y seguimiento

En **Administración → Configuración → Planes**, usa **Nuevo plan** o **Editar plan**. Una mensualidad conserva la vigencia por días. Una tiquetera permite indicar el número de entradas y elegir su vigencia por días o meses calendario. Las compras anteriores conservan el cupo y vencimiento con los que se registraron.

Para trasladar una tiquetera ya iniciada, entra a **Clientes y pagos → Registrar pago**, elige la tiquetera, escribe la fecha original y marca **Tiquetera ya iniciada (sin nuevo cobro)**. Indica las entradas ya utilizadas y revisa el saldo y el próximo número de entrada. El traslado no crea visitas ficticias ni un nuevo ingreso de dinero.

Dashboard conserva los bloques **Sin entradas**, **1–5**, **6–10**, **11–15**, **16–20** y **Más de 20**. Cada bloque permite revisar los clientes y sus contactos.

En **Estadísticas → Seguimiento de sesiones**, puedes consultar los últimos **7, 14 o 30 días**. Se incluyen quienes solo asistieron por sesión en el período elegido, con su teléfono, correo y plan actual para el seguimiento manual. El listado no envía mensajes.

## Recorrido de comprobación en tu computador

1. Abre Configuración y comprueba que aparezcan la tabla de planes y sus botones. Cambia de pestaña y vuelve a Planes.
2. Abre Estadísticas y recorre las tres pestañas. Si el ancho es pequeño, utiliza el selector que sustituye la fila de pestañas.
3. Cambia a Clientes y pagos y regresa a las pantallas anteriores: sus tablas deben seguir visibles.
4. Reduce y amplía la ventana. Repite con la escala de Windows al 100 % y 125 %. Si el contenido excede el alto, debe poder desplazarse con la barra o la rueda.
5. En Registro de entrada, pulsa Pausar lectura y comprueba el texto «pausada». Cambia de sección y regresa; el estado debe mantenerse.
6. Pulsa Activar lectura. Con un cliente de prueba y un lector compatible, comprueba que identifique el código y muestre el resultado del ingreso. Esta prueba sí registra un intento real de entrada.

Las comprobaciones locales y sus límites se describen en `VALIDACION_3.3.2.md`. La prueba final de los ejecutables, la instalación y el lector físico debe realizarse en Windows.

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
