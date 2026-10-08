# Respaldos recuperados

Estos dos ZIP contienen las fuentes de desarrollo de Atlantic Gym y ZTATTUZ por separado. Se conservan aquí para poder descargarlos incluso si se pierde el entorno cloud.

No son instaladores ni paquetes finales: faltan recursos DigitalPersona y aceptación externa/Windows. Los ZIP incluyen las guías de cierre, fuentes, iconos, dependencias declaradas, migraciones y evidencias. Se comprobaron CRC, SHA256, bytes contra las fuentes y funcionamiento de copias extraídas independientes.

`MANIFEST.json` identifica el commit de fuentes y SHA256 de cada archivo. Consultar `docs/ESTADO_CIERRE.md` en el repositorio o dentro del respaldo antes de usar las instrucciones históricas.

Actualización del preparador: admite CPython 3.13/3.14 estándar y conserva entornos incompatibles. Usa los accesos `INICIAR_ADMINISTRADOR.bat`/`INICIAR_RECEPCION.bat` para configurar/probar desde las fuentes; los instaladores finales conservan el gate de aceptación.

`Atlantic_Transferencia_SDK_25MB.zip` es una utilidad separada de transferencia: divide los archivos SDK grandes en partes verificables y conserva los originales. Ejecutar `DIVIDIR_ZIP.bat` y seleccionar los ZIP originales; enviar todas las partes al chat. `TRANSFERENCIA_MANIFEST.json` registra el SHA256 de la utilidad.
