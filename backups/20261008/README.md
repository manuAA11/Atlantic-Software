# Descargas completas de Atlantic Gym y ZTATTUZ

Los ZIP `APLICACION_COMPLETA_EN_DESARROLLO` incluyen el código íntegro recuperado, recursos Atlantic, configuración pública, pruebas, dependencias declaradas y todos los archivos DigitalPersona originales de cada arquitectura, con EULA y condiciones incorporadas. Extrae en una carpeta nueva; no necesitas reconstruir MSI/CAB ni copiar recursos desde otro paquete.

- [Atlantic Gym Comercial completo](AtlanticGym_APLICACION_COMPLETA_EN_DESARROLLO_20261008.zip): Administrador, Recepción y fuentes del panel privado. No entregar el panel propietario a clientes.
- [ZTATTUZ completo x64/x86](ZTATTUZ_APLICACION_COMPLETA_EN_DESARROLLO_20261008.zip): Administrador y Recepción de ambas arquitecturas. Con Python 3.14 de 64 bits usa la carpeta x64.

Son aplicaciones completas desde las fuentes, **en desarrollo**: no EXE finales ni aceptación de integraciones/hardware. `INICIAR_ADMINISTRADOR.bat` y `INICIAR_RECEPCION.bat` abren los programas para configurar y probar. `CREAR_INSTALADORES.bat` conserva la aceptación final. El empaquetado técnico se verifica aparte en Windows. Consulta `docs/ESTADO_CIERRE.md` y `docs/INTEGRACIONES_Y_WINDOWS.md` incluidos.

Los hashes externos están en `MANIFEST_APLICACIONES_COMPLETAS.json`; dentro, `APP_MANIFEST.json` autentica cada archivo. DigitalPersona se distribuye exclusivamente incorporado a Atlantic con su EULA, nunca como Runtime independiente. No se incluyen secretos ni datos de clientes.

---

# Respaldos recuperados

Estos dos ZIP contienen las fuentes de desarrollo de Atlantic Gym y ZTATTUZ por separado. Se conservan aquí para poder descargarlos incluso si se pierde el entorno cloud.

No son instaladores ni paquetes finales: faltan recursos DigitalPersona y aceptación externa/Windows. Los ZIP incluyen las guías de cierre, fuentes, iconos, dependencias declaradas, migraciones y evidencias. Se comprobaron CRC, SHA256, bytes contra las fuentes y funcionamiento de copias extraídas independientes.

`MANIFEST.json` identifica el commit de fuentes y SHA256 de cada archivo. Consultar `docs/ESTADO_CIERRE.md` en el repositorio o dentro del respaldo antes de usar las instrucciones históricas.

Actualización del preparador: admite CPython 3.13/3.14 estándar y conserva entornos incompatibles. Usa los accesos `INICIAR_ADMINISTRADOR.bat`/`INICIAR_RECEPCION.bat` para configurar/probar desde las fuentes; los instaladores finales conservan el gate de aceptación.

`Atlantic_Transferencia_SDK_25MB.zip` es una utilidad separada de transferencia: divide los archivos SDK grandes en partes verificables y conserva los originales. Ejecutar `DIVIDIR_ZIP.bat` y seleccionar los ZIP originales; enviar todas las partes al chat. `TRANSFERENCIA_MANIFEST.json` registra el SHA256 de la utilidad.
