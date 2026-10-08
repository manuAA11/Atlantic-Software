# Verificación · ZTATTUZ 3.6.1 x64

Fecha: 30 de septiembre de 2026.

Edición exclusiva de ZTATTUZ para Windows 10 de 64 bits (x64, Intel/AMD). Conserva el soporte de los lectores DigitalPersona U.are.U 4500 y 5160, Administración, Recepción y el control de puerta LCUS-1.

## Cambios respecto al paquete 3.6.1 x86

- Preparación y compilación con Python 3.13 de 64 bits. El preparador selecciona explícitamente esa arquitectura, incluso si también está instalado Python de 32 bits.
- Se rechaza una compilación con Python de 32 bits antes de generar los ejecutables. Se comprueba que el resultado de PyInstaller tenga arquitectura AMD64 (PE 0x8664).
- Los tres instaladores se destinan a Windows x64 nativo y utilizan el modo de instalación de 64 bits. Se conservan sus identificadores y directorios para actualizar instalaciones existentes de ZTATTUZ.
- Se incluyen los nueve archivos originales del runtime DigitalPersona x64 de la entrega anterior de 64 bits. Se comprobó que el MSI declara `Template: x64;1033` y que sus archivos coinciden byte a byte con esa entrega. El ejecutable de arranque del fabricante es de 32 bits; instala el MSI y los componentes de 64 bits, por lo que su cabecera no identifica la arquitectura final del runtime.
- Instalador completo de salida: `salida/ZTATTUZ_Instalar_o_Actualizar_3.6.1_x64.exe`.
- Guías de actualización y uso adaptadas a esta edición.

Se verificó que el código de las dos aplicaciones, el adaptador y servicio de huella, el registro dentro del cliente y el control de puerta coinciden byte a byte con 3.6.1 x86. Los archivos SQL también permanecen idénticos. No se modificó la edición comercial ni se ejecutaron operaciones contra el gimnasio real.

## Pruebas realizadas en esta copia

Entorno: Linux con Python 3.12 de 64 bits, Tk sobre Xvfb y PostgreSQL local (PGlite). Los dispositivos se simulan.

| Comprobación | Resultado |
|---|---|
| Pruebas Python, incluidos modelos 4500/5160, selección de DLL y rechazo de compilación con Python de 32 bits | 128 aprobadas |
| Recorrido por el adaptador nativo y el servicio: huella, guardado, entradas, tiqueteras y puerta, con ambos modelos y roles | 88 aprobadas |
| Registro de huella y presentación automática del resultado en Administración y Recepción, escalas 100 % y 125 % | 124 aprobadas |
| Arquitectura del runtime y conservación de código funcional y SQL | Conforme |

Registros de esta copia: `verificacion/3.6.1_x64_linux/`.

La validación completa anterior de 25 etapas corresponde a la base 3.6.1 x86 y se conserva como antecedente en `verificacion/3.6.1_x86_linux/`. No se presenta como una ejecución de Windows de esta edición. El generador de instaladores mantiene las 25 etapas locales, las comprobaciones de iconos y el diagnóstico de los ejecutables para cuando lo ejecutes en Windows.

## Comprobación pendiente en Windows

El ZIP contiene código, runtime y generador; no contiene los ejecutables de ZTATTUZ precompilados. Quedan pendientes la compilación e instalación en Windows x64 y la prueba con el lector y relé físicos. Las DLL Windows no se cargaron en Linux, y las muestras sintéticas no prueban la precisión biométrica del sensor real.

No se exige conectar el lector ni el relé durante la compilación. La lectura real, el resultado de entrada y la apertura de puerta se comprueban después de instalar en el gimnasio.

No se necesita SQL nuevo para actualizar desde ZTATTUZ 3.6.0. Para Windows de 32 bits debe utilizarse el paquete x86; esta entrega no es para ARM64.

Referencia de empaquetado: https://jrsoftware.org/ishelp/topic_setup_architecturesallowed.htm (selección de arquitectura nativa cuando se incluyen controladores).
