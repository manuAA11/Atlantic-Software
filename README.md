# Atlantic Software · Multi-Gym

Aplicaciones recuperadas de Atlantic Gym Comercial 3.6.0 y ZTATTUZ 3.6.1 x86/x64, con correcciones posteriores, Atlantic UI Kit y Runtime DigitalPersona original completo. Los paquetes incluyen las fuentes y los recursos necesarios para crear instaladores; la aceptación final de servidor, integraciones y hardware continúa pendiente.

- `GymSoft_Comercial_3.6.0`: Administrador, Recepción y panel privado del propietario; sin relé.
- `GymSoft_ZTATTUZ_3.6.1_x86` y `GymSoft_ZTATTUZ_3.6.1_x64`: Administrador y Recepción ZTATTUZ, con control de puerta y loader de su arquitectura.
- `common`, `backend`, `supabase`, `onboarding`, `deployment`: componentes compartidos, servicios, migraciones y utilidades del operador.
- `assets/atlantic`: referencia de iconos azul/cian recreada a partir de la lámina aprobada, convertida a ICO y copiada a cada edición.
- `evidence`: resultados históricos, fragmentos recuperados y validación actual separados.

Leer [estado y límites](docs/ESTADO_CIERRE.md), [acciones externas y Windows](docs/INTEGRACIONES_Y_WINDOWS.md), [UI Kit](docs/ATLANTIC_UI_KIT.md) y [políticas permanentes](AGENTS.md). Los requisitos del usuario están en `docs/REQUISITOS_CIERRE_MULTIGYM.txt`.

El run Windows `37998368137` aprobó los tres jobs completos con Python 3.14.8: **111 etapas y 484 tests Python**, creación mediante el `.bat` real, **siete programas y ocho instaladores** con iconos PE/diagnósticos correctos. La instalación y desinstalación x64 también aprobaron; ZTATTUZ verificó actualización mediante el instalador completo. La variante x86 se compila y diagnostica, pero su Runtime requiere Windows de 32 bits para instalarse. Los logs y alcances están en [el estado](docs/ESTADO_CIERRE.md) y `evidence/windows-actions`. Las pruebas simuladas no acreditan cuentas reales ni lector/relé físicos. Ambos servidores reportan base y scheduler disponibles en la comprobación pública del 9 de octubre.

## Crear e instalar los programas en Windows

1. Descarga el [paquete completo de tu aplicación](docs/PAQUETES_APLICACION_COMPLETA.md) y extráelo en una carpeta nueva. Para tu Python 3.14 de 64 bits usa Comercial o ZTATTUZ x64. Los Runtime y sus licencias ya están incluidos; no hace falta volver a buscarlos.
2. En el PC que compila, instala CPython 3.14 o 3.13 estándar de la arquitectura correspondiente, Node LTS e Inno Setup 6. Dentro de la edición, ejecuta **`CREAR_INSTALADORES.bat`**. Prepara las dependencias y repite todas las pruebas antes de compilar. Si falta la aceptación final, genera instaladores reales marcados `VALIDACION_NO_FINAL_` en `salida/PRUEBAS_PARA_CONFIGURAR/<identificador>/`; una prueba fallida detiene la publicación.
3. Abre `LEER_PRIMERO.txt` en esa carpeta y ejecuta el instalador para configurar y probar la aplicación. ZTATTUZ ofrece el instalador completo y sus componentes; Comercial mantiene el panel del propietario separado en `PRIVADO_PROPIETARIO`. **El PC donde instalas los EXE no necesita Python, Node ni Inno.** WhatsApp/Wompi se conectan desde Administrador, una vez habilitado el backend según [la guía](docs/INTEGRACIONES_Y_WINDOWS.md).

ZTATTUZ x86 se compila con Python de 32 bits, también desde Windows x64 con Node LTS x64. El PC donde se instala su Runtime necesita Windows de 32 bits: el MSI original rechaza Windows de 64 bits. Los instaladores finales se generan únicamente cuando `release_readiness.json` tiene evidencia válida para todos sus criterios aplicables. El Runtime recuperado no cambia la implementación de huella que ya funcionaba.

## Abrir desde fuentes en Windows

Ejecuta `INICIAR_ADMINISTRADOR.bat` o `INICIAR_RECEPCION.bat` dentro de tu edición con Python de la arquitectura indicada. El preparador conserva entornos incompatibles como respaldo. Los tres archivos de configuración pública están recuperados; consulta [las instrucciones](docs/INTEGRACIONES_Y_WINDOWS.md#abrir-los-programas-con-python-314-o-313) si utilizas una configuración propia. Estos accesos conservan autenticación y permisos normales.

## Desarrollo cloud

Desde `/workspace/Atlantic-Software`, ejecutar `bash tools/setup_cloud.sh` con Python 3.13/Tk, uv y Node disponibles. Luego `bash tools/start_display.sh :100`; comprobar el mensaje de Tk. Para cada suite paralela usar un display distinto.

```sh
node --test backend/tests/*.test.mjs
DISPLAY=:100 XDG_CACHE_HOME=/workspace/.cache /workspace/.venvs/multigym313/bin/python tools/validate_all.py GymSoft_Comercial_3.6.0 --scope all
```

ZTATTUZ usa el mismo comando con su carpeta y un display propio (:101 x64; :102 x86). El helper conserva resultados y no oculta errores. No reinstalar dependencias mientras haya pruebas en ejecución. Desde una carpeta de edición, `python run_validation.py --data-only` o `--ui-only` usa el runner portable Windows/Linux. Instalar sus requirements y ejecutar `npm ci` previamente.

La configuración cloud de instalación/inicio/red se guardó como borrador; publicarla desde la configuración del entorno conserva el snapshot. Guardar un borrador no ejecuta scripts ni valida futuras instancias.

`tools/backup_complete_sources.py` prepara las aplicaciones completas en desarrollo, con Runtime original incorporado y verificación de todos los hashes. `tools/backup_sources.py` conserva la alternativa de respaldo de fuentes. Ninguno declara aceptación final. No ejecutar esquemas iniciales en una base existente ni sobrescribir migraciones históricas.
