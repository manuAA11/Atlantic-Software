# Paquetes de aplicación completa en desarrollo

`tools/backup_complete_sources.py` genera dos aplicaciones completas independientes: Atlantic Gym Comercial y ZTATTUZ x64/x86. Además de las fuentes y recursos recuperados, cada edición incorpora su Runtime DigitalPersona original en código objeto, con su EULA intacta y términos que incorporan expresamente esa licencia. No se distribuye un Runtime independiente, SDK fuentes, headers ni samples. El paquete conserva la aplicación y la integración que utiliza el componente.

## Descargar y crear los instaladores

Los paquetes completos publicados en `main` están en [backups/20261008](../backups/20261008/). Sus nombres conservan la fecha de la recuperación; el manifiesto identifica el commit de fuentes incluido y el SHA-256 de cada ZIP.

- [Atlantic Gym Comercial completo](https://github.com/manuAA11/Atlantic-Software/raw/refs/heads/main/backups/20261008/AtlanticGym_APLICACION_COMPLETA_EN_DESARROLLO_20261008.zip): Administrador, Recepción y panel privado del propietario.
- [ZTATTUZ completo x64/x86](https://github.com/manuAA11/Atlantic-Software/raw/refs/heads/main/backups/20261008/ZTATTUZ_APLICACION_COMPLETA_EN_DESARROLLO_20261008.zip): Administrador y Recepción, con sus variantes y componentes del relé.
- [Manifiesto de integridad](../backups/20261008/MANIFEST_APLICACIONES_COMPLETAS.json).

1. Descarga el ZIP de tu aplicación y extráelo en una carpeta nueva, conservando juntos las carpetas de edición, `tools` y `docs`. No hace falta descargar el SDK ni unir sus partes de nuevo.
2. En el PC que compila, instala CPython 3.14 o 3.13 estándar de la arquitectura correcta, Node LTS e Inno Setup 6. Abre Comercial o ZTATTUZ x64 para Python de 64 bits. ZTATTUZ x86 se compila con Python de 32 bits, también desde Windows x64 con Node LTS x64; el PC donde se instala su Runtime debe usar **Windows de 32 bits**. Ejecuta **`CREAR_INSTALADORES.bat`** dentro de la edición.
3. Mientras falte aceptación final, el batch repite la validación completa y produce instaladores reales marcados `VALIDACION_NO_FINAL_` en `salida/PRUEBAS_PARA_CONFIGURAR/<identificador>/`. Abre allí `LEER_PRIMERO.txt` e instala para configurar y probar. El PC donde se instalan los EXE no necesita Python, Node ni Inno; la configuración por gimnasio se hace desde la aplicación y su backend, como indica [la guía](INTEGRACIONES_Y_WINDOWS.md).

Si alguna prueba o compilación falla, no se publica una nueva carpeta completa. El panel Comercial queda en `PRIVADO_PROPIETARIO` y no se entrega a clientes. Este flujo permite configurar las cuentas antes de completar los pilotos; no modifica ni acredita la aceptación final pendiente.

## Contenido y verificación

La redistribución se basa en §1.2(c) de la EULA original: Runtime objeto incorporado a la aplicación, avisos intactos y términos no menos restrictivos. Los binarios no se publican por separado en Git; si se conserva el ZIP de aplicación completo, debe mantenerse completo y con sus avisos. La EULA original acompaña cada edición y la instalación debe presentar sus términos.

```console
py tools\backup_complete_sources.py --output "C:\ruta\entregas" --label 20261008
py tools\backup_complete_sources.py --verify-archive "C:\ruta\entregas\AtlanticGym_APLICACION_COMPLETA_EN_DESARROLLO_20261008.zip"
```

El preparador necesita el checkout de fuentes y los Runtime originales ya restaurados. El ZIP resultante no requiere que el usuario reconstruya partes ni busque archivos MSI/CAB. Contiene las carpetas de cada edición, launchers para abrir desde las fuentes, dependencias declaradas, backend, migraciones, recursos Atlantic, pruebas, configuración **publicable** y documentación. CPython 3.13/3.14 de 64 bits corresponde a Comercial/ZTATTUZ x64; ZTATTUZ x86 se compila con Python de 32 bits y su Runtime necesita Windows de 32 bits porque el MSI original rechaza Windows de 64 bits.

Para validar en CI los mismos recursos de una aplicación completa se admite `--verify-package` como alias de verificación. `--restore-runtime-from-package ZIP --edition EDICION --expected-sha256 HASH` comprueba el hash externo del ZIP completo, CRC, inventario, aplicación, licencias y arquitectura antes de copiar únicamente sus archivos Runtime originales al checkout. Nunca sustituye un recurso existente distinto y requiere el hash conocido del paquete incorporado autorizado, no una descarga Runtime independiente.

El empaquetado rechaza rutas privadas/temporales, enlaces, claves privadas, JWT `service_role`, archivos Runtime que no pertenecen al inventario o bytes que difieren del original. Verifica CRC de todo el ZIP, SHA-256 de cada archivo, contenido obligatorio de la aplicación y Runtime/EULA de la arquitectura correspondiente. Un manifiesto exterior autentica el ZIP y `APP_MANIFEST.json` describe cada archivo y conserva una copia informativa de los requisitos de aceptación sin modificarlos. No sobrescribe paquetes existentes.

Estas son aplicaciones completas **desde las fuentes y en desarrollo**. Los recursos incorporados resuelven el faltante de archivos y permiten generar instaladores de configuración; los criterios reales de aceptación final se conservan. Las dependencias de terceros se instalan mediante los preparadores de cada aplicación. No se incluyen secretos de Meta/Wompi ni datos de clientes; su configuración privada pertenece al backend. El manifiesto del paquete describe sus fuentes y requisitos, sin acreditar pruebas externas/hardware ni certificar servidores actuales.
