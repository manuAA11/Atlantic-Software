# Gym soft y ZTATTUZ 3.5.2 — Registro y entrada por huella

Esta actualización corrige el manejo del lector DigitalPersona U.are.U 4500, añade confirmación visible y comprueba que la huella se haya guardado. El registro sigue siendo opcional y está dentro de **Nuevo cliente** y **Editar cliente**, tanto en Administración como en Recepción.

## Actualizar

1. Extrae el paquete correspondiente en una carpeta nueva.
2. Ejecuta **CREAR_INSTALADORES.bat** en Windows con Python 3.13 de 64 bits, Node.js LTS e Inno Setup 6.
3. Instala el archivo generado en `salida`: **GymSoft_Instalar_o_Actualizar_3.5.2.exe** para Comercial o **ZTATTUZ_Instalar_o_Actualizar_3.5.2.exe** para ZTATTUZ.
4. Comprueba que la aplicación muestre **3.5.2**. Cierra la otra aplicación que pueda estar utilizando el mismo lector.

El ZIP incluye código, pruebas y generador; no contiene los ejecutables de Gym soft ya compilados. La compilación no necesita un lector conectado ni su controlador: las pruebas utilizan un dispositivo simulado. Mantén visibles las ventanas de las pruebas gráficas.

**No ejecutes SQL nuevamente.** Las dos bases ya tienen las funciones biométricas. No se modificaron gimnasios, clientes, pagos ni permisos en las bases reales durante esta corrección.

## Registrar la huella

1. Abre **Clientes y pagos → Nuevo cliente** o edita al cliente existente.
2. Completa sus datos. En **Huella digital (opcional)** pulsa **Registrar huella** o **Reemplazar huella**.
3. Confirma su identidad y autorización. Primero se guardan los datos del cliente.
4. Apoya la yema del mismo dedo en el centro del sensor y mantenla hasta ver **Muestra aceptada**. Después retíralo y vuelve a colocarlo. El número de muestras lo determina el SDK; no se promete una cantidad fija.
5. Cuando aparezca **Muestras completas**, retira el dedo y colócalo una vez más. Esta lectura comprueba que la huella se puede reconocer antes de guardarla.
6. Espera el aviso **Huella registrada y verificada correctamente**. Solo aparece después de comparar la huella y volver a consultar la base para confirmar que quedó guardada.
7. Pulsa **Guardar cliente** o **Guardar** para guardar cambios adicionales y cerrar. No necesitas volver a crear al cliente.

La luz del lector indica actividad, no un guardado confirmado. **Guardar** no sustituye los pasos de captura. Si intentas guardar durante una lectura, el formulario pide terminarla o cancelarla. **Cancelar lectura** conserva los datos del cliente y su huella anterior, si existía.

## Comprobar una huella sin descontar entradas

En el formulario del cliente pulsa **Comprobar huella** y coloca el dedo registrado. Aparece **Huella reconocida correctamente** si coincide con la guardada en la nube. Esta comprobación no registra asistencia, no genera un pago y no consume entradas de tiquetera. El mismo botón está disponible en **Huellas / lector**.

## Registrar una entrada automáticamente

1. Cierra el formulario del cliente y la ventana **Huellas / lector**.
2. Deja activada **Lectura automática de huella**. Mantén abierta y con la sesión iniciada una sola aplicación que utilice el lector.
3. El cliente coloca el dedo. No hace falta seleccionar el buscador ni colocar allí el cursor; puedes estar en otra sección de Administración o Recepción.
4. La aplicación consulta el plan y abre **Registro de entrada**, mostrando **INGRESO REGISTRADO** o **INGRESO NO AUTORIZADO**.
   Si la huella no se reconoce, también se abre el resultado correspondiente; no se registra una entrada sin identificar al cliente.
5. Una entrada permitida con tiquetera descuenta una unidad. Un plan vencido, sin cupos o un cliente inactivo se rechaza. Las lecturas repetidas inmediatas no generan otra entrada.
6. Retira el dedo después de cada resultado. Si el controlador tarda en detectar el retiro, déjalo retirado unos segundos antes de la siguiente persona.

La lectura se pausa mientras se editan formularios o se gestiona el lector. Al cerrarlos continúa según el estado del botón de lectura automática. La identificación no depende del foco del buscador; requiere que la aplicación esté abierta y conectada. No hay modo de validación de planes sin conexión.

Si se pierde la respuesta al registrar una entrada, la lectura se pausa y pide revisar el historial. No repite automáticamente una escritura cuyo resultado se desconoce, para evitar consumir otra entrada.

## Controlador y diagnóstico

El componente **DigitalPersona Runtime 3.4.0 x64** sigue incluido en `DigitalPersonaRuntime/setup.exe`. Instálalo una sola vez en cada computador que use el lector, conservando todos los archivos de esa carpeta. Si ya está instalado correctamente, esta actualización no exige reinstalarlo. El asistente puede pedir permisos de administrador y reinicio.

Si no termina una lectura, aparece un aviso de error o de tiempo agotado, no una confirmación falsa. Abre **Huellas / lector → Copiar diagnóstico** y pega ese informe al solicitar soporte. Incluye versión, fases y códigos del controlador; no incluye imágenes, plantillas de huella, nombres ni contraseñas. También queda en `%LOCALAPPDATA%\GymSoft\logs\huellas.log`.

Windows 10 Mini debe conservar los componentes y servicios necesarios para el controlador y ser de 64 bits. La compatibilidad con esa instalación concreta y el dispositivo físico debe comprobarse en el gimnasio después de instalar.

## Qué se comprobó

Se probaron el adaptador nativo con llamadas simuladas, formularios y mensajes en Tk al 100 % y 125 %, lectura sin foco en el buscador, guardado con consulta de confirmación, cancelación, reemplazo, conflictos entre equipos, borrado, fallos de conexión y prevención de entradas repetidas.

El recorrido de entrada usa el servicio de huellas, las clases Python y las funciones SQL reales contra PostgreSQL local con datos ficticios: mensualidad, tiquetera, saldo agotado, sin plan, inactivo, vencido, huella desconocida y revocada. También se ejecuta la simulación general de una jornada de gimnasio. Los resultados detallados están en `salida/validacion` y `VERIFICACION_3.5.2.md`.

No se dispone aquí del lector físico ni de Windows para compilar los EXE. Las pruebas locales no sustituyen esa comprobación final; ningún resultado de simulación se presenta como una prueba física del sensor.
