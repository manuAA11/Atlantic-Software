# Atlantic Gym 3.8.3: detección del relé y cierre de sesión

El usuario informó que la instalación de 32 bits no encuentra el relé. En las
capturas COM4 permanece en el selector mientras aparece «No se encontró un
CH340». Ese COM puede ser el valor guardado: la captura no prueba que Windows
identifique actualmente el módulo ni permite conocer el error del controlador.

Se reprodujo un defecto del detector cuando el puerto existe pero sus campos
VID/PID están incompletos. Antes quedaba descartado aunque su identificador de
hardware permitiera reconocerlo. La consulta compartida ahora recupera esos
datos y, en Windows, consulta también HardwareID de dispositivos presentes de
la clase Ports mediante SetupAPI. Las estructuras y firmas de pySerial 3.5
respetan el tamaño de los punteros del proceso x86/x64. No se usa una búsqueda
de dispositivos desconectados en el registro ni se identifica por nombre libre.

Sólo se conservan los identificadores CH340/CH341 ya admitidos: VID 1A86 con
PID 7523 o 5523. Un ID explícito de otro dispositivo no se reemplaza, y una
identificación nativa ambigua no habilita el puerto. Descubrir no abre COM,
no transmite tramas ni cambia el controlador. La comprobación al abrir el
transporte utiliza la misma consulta; continúa exigiendo la identidad guardada.

El selector elimina un COM ausente, conserva la selección actual si existe
y propone el único compatible si hay uno. No activa ni guarda la puerta por
sí solo. Cuando sólo existen puertos sin identidad compatible, explica esa
diferencia en pantalla. Si Windows no presenta el dispositivo o falla su
controlador, el cambio de software no puede certificar una reparación física.

## Cerrar sesión

Administración y Recepción incluyen un botón rojo encima de Configuración.
Antes de salir, se exige terminar ventas, lecturas y formularios. Se detienen
nuevas solicitudes y se espera a las pendientes; el control de puerta se
cancela antes de retirar las credenciales. El cierre usa el alcance local de
Supabase y limpia almacenamiento, memoria y conexiones SDK aun sin red.
Un error al borrar el archivo de sesión no se anuncia como un cierre exitoso;
la instancia tampoco vuelve a cargar automáticamente esas credenciales.

Se destruyen las pantallas anteriores y sus temporizadores, y el mismo proceso
abre una nueva ventana de acceso. No se reutiliza el espacio de otra cuenta.
La configuración del relé se conserva, y las sesiones independientes de otros
equipos permanecen activas. Sin red se acredita la retirada local, no una
revocación confirmada en el servidor. Cerrar normalmente la ventana sigue
conservando la sesión; el botón es la salida explícita solicitada.

## Validación y límites

Los tests de descubrimiento cubren COM4 con metadatos incompletos, HardwareID,
conflictos, ambigüedad, fallback nativo y reapertura con identidad recuperada;
prohíben transmitir durante el escaneo. En Windows se comprueban también las
estructuras nativas y la consulta real sin abrir USB. Los tests de sesión
comprueban salida local, caída de red, error de disco, bloqueo de operaciones
y construcción de un espacio nuevo.

Las pruebas Tk añadidas comprueban ambos botones, orden, color, venta pendiente,
limpieza y formulario vacío a 100/125 %. El diálogo de relé prueba un COM antiguo
y la recuperación del selector sin transmitir. El digest histórico de lector,
ON/OFF, tiempos y exclusión del puerto se mantiene: el test de baseline restaura
sólo el adaptador antiguo de descubrimiento para verificar todo el resto.

La validación automatizada Windows y sus instaladores se publicarán sólo si
aprueban para el commit exacto. La publicación conserva NO FINAL y todos los
gates. Faltan la prueba presencial en Windows32 con el relé afectado y la
aceptación física de OFF, prueba confirmada y entrada autorizada. No se cambian
servicios, datos o permisos de producción para simular esa comprobación.

Resultado local: 897 regresiones de perfiles (318/290/289) y 158 guards
con dos comprobaciones exclusivas de Windows omitidas en Linux. El SDK real
con transporte HTTP simulado aprobó salir, retirar credenciales y volver a
autenticarse. Los módulos de la nueva prueba de interfaz importan correctamente;
la ejecución gráfica y la compilación Windows aún no se han realizado. No hay
instaladores 3.8.3 publicados.
