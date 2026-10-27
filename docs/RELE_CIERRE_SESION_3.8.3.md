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

La validación Windows [40421628845](https://github.com/manuAA11/Atlantic-Software/actions/runs/40421628845)
aprobó los tres perfiles del commit 5f4eda366fa19b02635660aa39edeaa24843a46b.
Cada perfil aprobó 158 guards, 106 comprobaciones de login, 64 de Cerrar sesión,
93 de puerta con USB simulado y su ejecutable congelado. Las regresiones por
perfil aprobaron 318 tests en Comercial, 290 en ZTATTUZ x64 y 289 en ZTATTUZ x86.
Los dos perfiles x64 aprobaron instalación, actualización y desinstalación en
Windows desechable. El perfil x86 comprobó proceso y API nativa de 32 bits en
un host x64; su instalación se mantiene NOT_RUN porque el MSI requiere Windows32.

La [publicación 3.8.3](https://github.com/manuAA11/Atlantic-Software/releases/tag/atlantic-gym-3.8.3-piloto)
se completó en el run 40421628798. Se descargaron los tres paquetes mediante
HTTPS y se verificaron sus tamaños y SHA256 contra el manifiesto del commit
validado. Resumen reproducible en `evidence/relay-logout-3.8.3-validation.json`.

La publicación conserva NO FINAL y todos los gates. Faltan la prueba presencial
en Windows32 con el relé afectado y la aceptación física de OFF, prueba confirmada
y entrada autorizada. Las pruebas sintéticas no acreditan el hardware del cliente.
Los identificadores y registros operativos de distribución permanecen privados.
