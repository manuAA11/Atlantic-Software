# ZTATTUZ 3.6.1 · Windows de 64 bits

Esta edición habilita el lector **DigitalPersona U.are.U 5160** y conserva el **U.are.U 4500**. La detección es automática mediante el controlador DigitalPersona: no hay que seleccionar el modelo ni colocar el cursor en el buscador.

Incluye Administración, Recepción, el registro opcional de huella dentro de Nuevo cliente y Editar cliente, la lectura automática de entrada y el control de puerta LCUS-1 de ZTATTUZ. Se conserva la corrección de WinError 32 de la entrega anterior.

## Preparar el instalador en tu computador

El ZIP contiene el código completo, las pruebas, el generador de instaladores y el instalador original del runtime DigitalPersona de 64 bits. **No contiene los ejecutables de ZTATTUZ ya compilados.**

1. Extrae todo el ZIP en una carpeta nueva. No copies la carpeta `.venv` de otra versión.
2. Utiliza CPython 3.13 o 3.14 de **64 bits**, Inno Setup 6 y Node.js. Tanto Windows como Python deben ser de 64 bits (x64, Intel/AMD).
3. Ejecuta `CREAR_INSTALADORES.bat`.
4. Las pruebas usan lectores y relé simulados: **no conectes hardware para compilar**. Durante las pruebas gráficas, mantén sus ventanas visibles y el escritorio desbloqueado.
5. Al terminar, entrega al gimnasio **`salida/ZTATTUZ_Instalar_o_Actualizar_3.6.1_x64.exe`**.

Si ya compilaste la edición anterior de 64 bits en ese computador, puedes utilizar las mismas herramientas instaladas. El entorno de esta carpeta se prepara de nuevo.

## Instalar en ZTATTUZ

1. Cierra Administración y Recepción antes de actualizar.
2. Ejecuta el instalador completo en el computador del gimnasio con Windows 10 de **64 bits**.
3. Instala el componente **DigitalPersona** que ofrece el instalador si aún no está instalado. Si Windows pide reiniciar, hazlo antes de abrir ZTATTUZ.
4. Conecta el U.are.U 5160 por USB y abre una sola aplicación para usar el lector: Administración o Recepción.
5. Inicia sesión y entra en **Registro de entrada**. El estado del lector mostrará **DigitalPersona U.are.U 5160 listo** cuando el controlador lo haya detectado y abierto. Un error de controlador o conexión se mostrará en ese mismo estado.

El runtime también está completo en `DigitalPersonaRuntime/setup.exe`: ejecútalo desde esa carpeta, conservando los archivos MSI y CAB que lo acompañan. No copies únicamente `setup.exe`.

El computador del gimnasio no necesita Python, Node.js ni Inno Setup. Esta actualización desde 3.6.0 **no requiere SQL nuevo** ni volver a cargar clientes, pagos o huellas.

## Registrar y comprobar una huella

1. Abre **Nuevo cliente** o **Editar cliente** y completa los datos de la persona.
2. En **Huella digital (opcional)**, pulsa **Registrar huella**. Si ya tiene una, aparecerá **Reemplazar huella**.
3. Sigue las indicaciones: apoya el mismo dedo, espera la confirmación de cada muestra y retíralo entre lecturas.
4. Cuando el programa lo indique, coloca el dedo una vez más para verificarlo.
5. Espera el mensaje **Huella registrada y verificada correctamente**. Ese mensaje aparece después de comprobar el guardado en la base del gimnasio. Que el lector alumbre no confirma por sí solo el registro.
6. **Comprobar huella** permite verificar la identidad; esa acción no registra asistencia ni abre la puerta.
7. Guarda los demás cambios y cierra el formulario.

Las plantillas existentes se conservan; esta versión utiliza el mismo formato biométrico. La lectura de una huella real registrada con otro dispositivo debe comprobarse en el gimnasio; si no coincide, reemplázala desde el cliente después de confirmar su identidad.

## Entrada automática y puerta

Con la lectura automática activada, la aplicación abierta y el formulario de huella cerrado, colocar el dedo inicia la comprobación sin hacer clic en el buscador. Se abre **Registro de entrada** y se muestra **INGRESO REGISTRADO** o **INGRESO NO AUTORIZADO** según la respuesta del servidor.

- Una mensualidad vigente o una tiquetera vigente con saldo permite registrar la entrada.
- Una huella desconocida, un cliente inactivo, un plan vencido o una tiquetera sin saldo no autorizan la apertura automática.
- Las lecturas repetidas tienen protección contra duplicados. Retira el dedo entre personas.
- Si la puerta LCUS-1 está configurada y activada, solo una entrada biométrica autorizada envía el pulso automático.
- **Abrir puerta** conserva la apertura manual con confirmación. No crea asistencia ni descuenta entradas.
- Si no se confirma la respuesta del servidor, no se envía apertura automática. Revisa el historial antes de reintentar.

La configuración y la comprobación física del relé se explican en `GUIA_PUERTA_LCUS1.md`.

## Si el lector no aparece

Abre **Registro de entrada → Huellas / lector**. Puedes usar **Instalar controlador DigitalPersona** y **Copiar diagnóstico**. Comprueba también que Windows reconozca el lector y que otra aplicación no lo esté utilizando. El controlador DigitalPersona es distinto del CH340 del relé.

Este paquete es para Windows 10 x64 (Intel/AMD). Para un Windows de 32 bits utiliza la edición x86; esta entrega no es para Windows ARM64. Una edición MiniOS puede carecer de servicios o controladores; eso debe comprobarse en el computador donde se instalará.

## Alcance de las pruebas

Consulta `VERIFICACION_3.6.1_x64.md`. Las comprobaciones automáticas utilizan datos ficticios, PostgreSQL local, un SDK DigitalPersona simulado y un relé simulado. No modifican el gimnasio real y no requieren dispositivos USB.

Queda pendiente compilar e instalar esta entrega en Windows y comprobar el lector 5160 y la puerta físicos. Las pruebas simuladas verifican los flujos del programa, no la calidad de captura del sensor ni los componentes de una instalación concreta de MiniOS.

© 2026 Manuel Cuéllar. All rights reserved.
