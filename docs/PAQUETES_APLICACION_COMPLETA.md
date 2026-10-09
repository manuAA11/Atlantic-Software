# Paquetes de aplicación completa en desarrollo

`tools/backup_complete_sources.py` genera dos aplicaciones completas independientes: Atlantic Gym Comercial y ZTATTUZ x64/x86. Además de las fuentes y recursos recuperados, cada edición incorpora su Runtime DigitalPersona original en código objeto, con su EULA intacta y términos que incorporan expresamente esa licencia. No se distribuye un Runtime independiente, SDK fuentes, headers ni samples. El paquete conserva la aplicación y la integración que utiliza el componente.

La redistribución se basa en §1.2(c) de la EULA original: Runtime objeto incorporado a la aplicación, avisos intactos y términos no menos restrictivos. Los binarios no se publican por separado en Git; si se conserva el ZIP de aplicación completo, debe mantenerse completo y con sus avisos. La EULA original acompaña cada edición y la instalación debe presentar sus términos.

```console
py tools\backup_complete_sources.py --output "C:\ruta\entregas" --label 20261008
py tools\backup_complete_sources.py --verify-archive "C:\ruta\entregas\AtlanticGym_APLICACION_COMPLETA_EN_DESARROLLO_20261008.zip"
```

El preparador necesita el checkout de fuentes y los Runtime originales ya restaurados. El ZIP resultante no requiere que el usuario reconstruya partes ni busque archivos MSI/CAB. Contiene las carpetas de cada edición, launchers para abrir desde las fuentes, dependencias declaradas, backend, migraciones, recursos Atlantic, pruebas, configuración **publicable** y documentación. CPython 3.13/3.14 de 64 bits corresponde a Comercial/ZTATTUZ x64; ZTATTUZ x86 requiere Windows y Python de 32 bits porque su MSI original rechaza Windows de 64 bits.

Para validar en CI los mismos recursos de una aplicación completa se admite `--verify-package` como alias de verificación. `--restore-runtime-from-package ZIP --edition EDICION --expected-sha256 HASH` comprueba el hash externo del ZIP completo, CRC, inventario, aplicación, licencias y arquitectura antes de copiar únicamente sus archivos Runtime originales al checkout. Nunca sustituye un recurso existente distinto y requiere el hash conocido del paquete incorporado autorizado, no una descarga Runtime independiente.

El empaquetado rechaza rutas privadas/temporales, enlaces, claves privadas, JWT `service_role`, archivos Runtime que no pertenecen al inventario o bytes que difieren del original. Verifica CRC de todo el ZIP, SHA-256 de cada archivo, contenido obligatorio de la aplicación y Runtime/EULA de la arquitectura correspondiente. Un manifiesto exterior autentica el ZIP y `APP_MANIFEST.json` describe cada archivo y conserva una copia informativa de los requisitos de aceptación sin modificarlos. No sobrescribe paquetes existentes.

Estas son aplicaciones completas **desde las fuentes y en desarrollo**, no instaladores EXE finales ni una acreditación de pruebas externas/hardware. Los recursos incorporados resuelven el faltante de archivos, pero `CREAR_INSTALADORES.bat` y los criterios reales de aceptación se conservan. Las dependencias de terceros se instalan mediante los preparadores de cada aplicación. No se incluyen secretos de Meta/Wompi ni datos de clientes; su configuración privada pertenece al backend.
