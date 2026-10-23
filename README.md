# Atlantic Software · Atlantic Gym

Atlantic Gym se desarrolla como una sola aplicación de Administración y Recepción.
Hay dos versiones oficiales: **x86 (32 bits) y x64 (64 bits)**, con las mismas
funciones y el mismo código compartido. Se conserva el lector DigitalPersona y
el relé de la referencia funcional recuperada de ZTATTUZ. La versión de desarrollo
es **3.7.0 beta**; las instalaciones actuales continúan operativas.

- `common`: implementación única de la aplicación, acceso a datos, sesiones, interfaz,
  lector, puerta, Core y actualizador. Ver [arquitectura y compatibilidad](docs/ARQUITECTURA_COMERCIAL_CORE.md).
- `GymSoft_ZTATTUZ_3.6.1_x86`, `GymSoft_ZTATTUZ_3.6.1_x64` y `GymSoft_Comercial_3.6.0`:
  directorios históricos de entrada y empaquetado. Usan el mismo código compartido;
  conservan arquitectura, AppId, rutas y configuración de instalaciones existentes.
  La puerta es opcional y requiere configuración local en cualquier perfil.
- `backend`, `supabase`, `onboarding`, `deployment`: servicios compartidos,
  migraciones y herramientas del operador. Core registra los gimnasios por su UUID
  y selecciona actualizaciones generales o dirigidas a un `gym_id`, canal y arquitectura.
- `assets/atlantic`: iconos aprobados de Administrador (azul) y Recepción (cian).
- `evidence`: resultados históricos y validaciones, con su alcance indicado.

Registrar un gimnasio en Core no traslada sus tablas operativas. La compatibilidad
con el proveedor actual permite mantener las instalaciones trabajando durante la
integración. No cambiar conexiones ni eliminar datos de origen como parte de una
actualización de código. Las credenciales privadas y los datos de clientes no se
publican en este repositorio.

Leer [estado y límites](docs/ESTADO_CIERRE.md), [acciones externas y Windows](docs/INTEGRACIONES_Y_WINDOWS.md), [UI Kit](docs/ATLANTIC_UI_KIT.md) y [políticas permanentes](AGENTS.md). Los requisitos del usuario están en `docs/REQUISITOS_CIERRE_MULTIGYM.txt`.

## Referencias de versiones anteriores

Los enlaces de esta sección corresponden a versiones anteriores; no contienen la
actualización 3.7.0. Sus resultados no acreditan la aceptación de la versión nueva.

El run Windows `38001250527`, commit `fe2a95b`, aprobó los tres jobs completos con Python 3.14.8: **111 etapas y 484 tests Python**, creación mediante el `.bat` real, **siete programas y ocho instaladores** con iconos PE/diagnósticos correctos. Comercial y ZTATTUZ x64 aprobaron instalación nueva, actualización conservando directorios/registros y desinstalación; ZTATTUZ utilizó su instalador completo en ambos pasos. La variante x86 se compila y diagnostica, pero su Runtime requiere Windows de 32 bits para instalarse. Los logs y alcances están en [el estado](docs/ESTADO_CIERRE.md) y `evidence/windows-actions`. Las pruebas simuladas no acreditan cuentas reales ni lector/relé físicos. Ambos servidores reportan base y scheduler disponibles en la comprobación pública del 9 de octubre.

Los [instaladores ya compilados](https://github.com/manuAA11/Atlantic-Software/releases/tag/configuracion-pruebas-fe2a95b) están publicados para configurar y probar. Se descargaron y verificaron CRC/SHA256 de los tres ZIP y sus digests de GitHub. Extrae el ZIP de tu edición y ejecuta el EXE; el PC no necesita Python. La entrega mantiene la marca **NO FINAL** hasta completar la aceptación real pendiente.

## Crear e instalar los programas en Windows

1. Para compilar la versión de desarrollo, descarga o clona el repositorio actual completo. Los [paquetes históricos](docs/PAQUETES_APLICACION_COMPLETA.md) sirven como referencia y recuperación de versiones anteriores. Para tu Python 3.14 de 64 bits usa Comercial o ZTATTUZ x64. Los Runtime y sus licencias ya están incluidos; no hace falta volver a buscarlos.
2. En el PC que compila, instala CPython 3.14 o 3.13 estándar de la arquitectura correspondiente, Node LTS e Inno Setup 6. Dentro de la edición, ejecuta **`CREAR_INSTALADORES.bat`**. Prepara las dependencias y repite todas las pruebas antes de compilar. Si falta la aceptación final, genera instaladores reales marcados `VALIDACION_NO_FINAL_` en `salida/PRUEBAS_PARA_CONFIGURAR/<identificador>/`; una prueba fallida detiene la publicación.
3. Abre `LEER_PRIMERO.txt` en esa carpeta y ejecuta el instalador para configurar y probar la aplicación. ZTATTUZ ofrece el instalador completo y sus componentes; Comercial mantiene el panel del propietario separado en `PRIVADO_PROPIETARIO`. **El PC donde instalas los EXE no necesita Python, Node ni Inno.** WhatsApp/Wompi se conectan desde Administrador, una vez habilitado el backend según [la guía](docs/INTEGRACIONES_Y_WINDOWS.md).

ZTATTUZ x86 se compila con Python de 32 bits, también desde Windows x64 con Node LTS x64. El PC donde se instala su Runtime necesita Windows de 32 bits: el MSI original rechaza Windows de 64 bits. Los instaladores finales se generan únicamente cuando `release_readiness.json` tiene evidencia válida para todos sus criterios aplicables. El Runtime recuperado no cambia la implementación de huella que ya funcionaba.

## Abrir desde fuentes en Windows

Ejecuta `INICIAR_ADMINISTRADOR.bat` o `INICIAR_RECEPCION.bat` dentro de tu edición con Python de la arquitectura indicada. El preparador conserva entornos incompatibles como respaldo. Los tres archivos de configuración pública están recuperados; consulta [las instrucciones](docs/INTEGRACIONES_Y_WINDOWS.md#abrir-los-programas-con-python-314-o-313) si utilizas una configuración propia. Estos accesos conservan autenticación y permisos normales.

## Desarrollo cloud

Desde `/workspace/Atlantic-Software`, ejecutar `bash tools/setup_cloud.sh` con Python 3.13/Tk, uv y Node disponibles. Luego `bash tools/start_display.sh :100`; comprobar el mensaje de Tk. Para cada suite paralela usar un display distinto.

```sh
node --test backend/tests/*.test.mjs
DISPLAY=:100 XDG_CACHE_HOME=/workspace/.cache XDG_DATA_HOME=/workspace/.local/share /workspace/.venvs/multigym314/bin/python tools/validate_all.py GymSoft_Comercial_3.6.0 --scope all --run-label "cloud-$(date -u +%Y%m%dT%H%M%SZ)-$$"
```

ZTATTUZ usa el mismo comando con su carpeta y un display propio (:101 x64; :102 x86). El helper conserva resultados y no oculta errores. No reinstalar dependencias mientras haya pruebas en ejecución. Desde una carpeta de edición, `python run_validation.py --data-only` o `--ui-only` usa el runner portable Windows/Linux. Instalar sus requirements y ejecutar `npm ci` previamente.

La configuración cloud de instalación/inicio/red se guardó como borrador; publicarla desde la configuración del entorno conserva el snapshot. Guardar un borrador no ejecuta scripts ni valida futuras instancias.

`tools/backup_complete_sources.py` prepara las aplicaciones completas en desarrollo, con Runtime original incorporado y verificación de todos los hashes. `tools/backup_sources.py` conserva la alternativa de respaldo de fuentes. Ninguno declara aceptación final. No ejecutar esquemas iniciales en una base existente ni sobrescribir migraciones históricas.
