# Atlantic Software · Multi-Gym

Fuentes recuperadas de Atlantic Gym Comercial 3.6.0 y ZTATTUZ 3.6.1 x86/x64, con correcciones posteriores y Atlantic UI Kit. Estado de desarrollo; no es una entrega final ni un instalador.

- `GymSoft_Comercial_3.6.0`: Administrador, Recepción y panel privado del propietario; sin relé.
- `GymSoft_ZTATTUZ_3.6.1_x86` y `GymSoft_ZTATTUZ_3.6.1_x64`: Administrador y Recepción ZTATTUZ, con control de puerta y loader de su arquitectura.
- `common`, `backend`, `supabase`, `onboarding`, `deployment`: componentes compartidos, servicios, migraciones y utilidades del operador.
- `assets/atlantic`: referencia de iconos azul/cian recreada a partir de la lámina aprobada, convertida a ICO y copiada a cada edición.
- `evidence`: resultados históricos, fragmentos recuperados y validación actual separados.

Leer [estado y límites](docs/ESTADO_CIERRE.md), [acciones externas y Windows](docs/INTEGRACIONES_Y_WINDOWS.md), [UI Kit](docs/ATLANTIC_UI_KIT.md) y [políticas permanentes](AGENTS.md). Los requisitos del usuario están en `docs/REQUISITOS_CIERRE_MULTIGYM.txt`.

La validación local final reúne 114 etapas PASS, incluidas 450 pruebas Python y 56 pruebas del backend por edición; también SQL, UI, branding y un flujo HTTP/backend/SQL con transportes externos simulados. El resumen enlaza sus logs en `evidence/closure-validation-20261008/summary.json`. Se conservan los fallos del primer run y sus rechecks explícitos.

Pendientes: runtime DigitalPersona excluido del ZIP, pilotos reales Meta/Wompi y aceptación Windows/hardware/servidor actual. Los instaladores finales siguen sujetos a `release_readiness.json`.

## Abrir desde fuentes en Windows

CPython 3.13 o 3.14 estándar: 64 bits para Comercial/ZTATTUZ x64; 32 bits para ZTATTUZ x86. Ejecuta `INICIAR_ADMINISTRADOR.bat` o `INICIAR_RECEPCION.bat` dentro de la carpeta de tu edición. El preparador conserva entornos incompatibles como respaldo. Hace falta la configuración pública del servidor; consulta [instrucciones](docs/INTEGRACIONES_Y_WINDOWS.md#abrir-los-programas-con-python-314-o-313).

La suite de 450 tests también pasa con Python 3.14.7. Evidencia adicional de UI, wheels Windows y empaquetado de prueba Linux en `evidence/closure-validation-20261008/python-compatibility.json`. La ejecución Windows/hardware sigue pendiente.

## Desarrollo cloud

Desde `/workspace/Atlantic-Software`, ejecutar `bash tools/setup_cloud.sh` con Python 3.13/Tk, uv y Node disponibles. Luego `bash tools/start_display.sh :100`; comprobar el mensaje de Tk. Para cada suite paralela usar un display distinto.

```sh
node --test backend/tests/*.test.mjs
DISPLAY=:100 XDG_CACHE_HOME=/workspace/.cache /workspace/.venvs/multigym313/bin/python tools/validate_all.py GymSoft_Comercial_3.6.0 --scope all
```

ZTATTUZ usa el mismo comando con su carpeta y un display propio (:101 x64; :102 x86). El helper conserva resultados y no oculta errores. No reinstalar dependencias mientras haya pruebas en ejecución. Desde una carpeta de edición, `python run_validation.py --data-only` o `--ui-only` usa el runner portable Windows/Linux. Instalar sus requirements y ejecutar `npm ci` previamente.

La configuración cloud de instalación/inicio/red se guardó como borrador; publicarla desde la configuración del entorno conserva el snapshot. Guardar un borrador no ejecuta scripts ni valida futuras instancias.

`tools/backup_sources.py` prepara dos respaldos de fuentes en desarrollo tras comprobar el resumen local y sincronización. No produce paquetes finales, runtimes ausentes ni instaladores. No ejecutar esquemas iniciales en una base existente ni sobrescribir migraciones históricas.
