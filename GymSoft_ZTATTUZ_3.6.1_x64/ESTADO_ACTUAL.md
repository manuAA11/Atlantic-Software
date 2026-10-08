# Atlantic Gym: checkpoint recuperado

Estado de desarrollo: consultar `../docs/ESTADO_CIERRE.md` y `../docs/INTEGRACIONES_Y_WINDOWS.md` antes de usar las instrucciones antiguas de esta carpeta.

Hay correcciones y actualizaciones SQL posteriores a los LEEME históricos. Los iconos azul/cian están incluidos. Faltan el runtime DigitalPersona autorizado y aceptación externa/Windows. No generar instaladores finales ni forzar release_readiness.json.

## Python y apertura desde fuentes

Compatible con CPython 3.13 o 3.14 estándar. Comercial y ZTATTUZ x64 requieren 64 bits; ZTATTUZ x86 requiere 32 bits. `PREPARAR_PYTHON.bat` conserva una `.venv` incompatible en `.venv_respaldo_<fecha>_<id>` y crea otra sin cambiar tu configuración.

Para abrir y continuar la configuración/pruebas ejecuta `INICIAR_ADMINISTRADOR.bat` o `INICIAR_RECEPCION.bat`. Necesitas URL y clave publicable del servidor configuradas. Estos accesos ejecutan las fuentes; no producen instaladores ni desactivan autenticación/permisos.

`Entrega bloqueada. Falta comprobar: …` significa aceptación pendiente, no fallo de instalación de dependencias. El gate se conserva; sigue las instrucciones de `../docs/INTEGRACIONES_Y_WINDOWS.md`.
