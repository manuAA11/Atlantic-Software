# DigitalPersona 3.4.0 recuperado

El SDK original enviado por el usuario se reconstruyó desde sus siete partes y se autenticó con SHA-256. Los recursos de ejecución `RTE/x64` y `RTE/x86` están completos en el entorno de trabajo: Comercial y ZTATTUZ x64 reciben el Runtime x64; ZTATTUZ x86 recibe el Runtime x86. Se preservan todos los archivos originales, incluidos MSI, CAB, INI, BAT y el prerrequisito del proveedor para x64. El cargador de huellas y la implementación existente no cambian.

El inventario reproducible está en [sdk-manifest.json](vendor/digitalpersona/sdk-manifest.json). Cada carpeta `DigitalPersonaRuntime` contiene además el manifiesto de su arquitectura y `Licenses/EULA SDK.rtf`, copia íntegra del original. `setup.exe` es un lanzador InstallShield de 32 bits en ambos árboles; la arquitectura del Runtime se determina por el árbol RTE original y su paquete MSI, no por ese lanzador.

Desde la raíz del repositorio:

```console
py docs\vendor\digitalpersona\preparar_runtime.py "C:\ruta\DigitalPersonaBiometricSDKforWindows_3.4.0.zip"
py docs\vendor\digitalpersona\preparar_runtime.py --verify
```

El preparador verifica el SHA-256 del ZIP, autentica cada archivo antes de copiar y vuelve a comprobar el destino. No sustituye archivos distintos: informa de la diferencia. No descarga paquetes de terceros ni altera los originales.

Para un paquete de fuentes que contenga solo un producto, selecciona sus ediciones con `--edition GymSoft_Comercial_3.6.0` o con los nombres ZTATTUZ x64/x86 correspondientes; la opción se puede repetir. La ejecución sin esa opción espera las tres ediciones del repositorio completo.

La EULA del proveedor, §1.2(c), permite distribuir el Runtime en código objeto incorporado a la aplicación, conservando sus avisos y con términos no menos restrictivos. El §2 restringe otras redistribuciones. Por ello los archivos binarios individuales se mantienen locales e ignorados en Git: no se publica el SDK completo ni un Runtime independiente. Los instaladores Atlantic existentes incluyen esos árboles mediante `DigitalPersonaRuntime\*`; los avisos y la EULA deben acompañar esa distribución y su licencia de instalación debe incorporar los términos del proveedor. Los manifiestos y el preparador permiten reproducir la integración usando el ZIP autorizado que conserva el usuario.

Los respaldos de fuentes anteriores no incluían el Runtime. El nuevo [paquete de aplicación completa](PAQUETES_APLICACION_COMPLETA.md) incorpora el Runtime objeto bajo la propia aplicación Atlantic y conserva sus condiciones/EULA. Esa entrega resuelve la necesidad de un paquete completo sin distribuir un componente Runtime por separado ni incluir fuentes del SDK.

La inspección de las tablas MSI originales confirma `ProductVersion=3.4.0.127`. El ProductCode x64 es `{7FC7AAC6-4A7E-4DA4-92ED-D37FB6BDCA18}`; x86 es `{9C54D120-D3C1-49FF-8160-CE6B1CF4F533}`. El MSI x64 tiene plantilla `x64;1033` e instala DLL de 32 y 64 bits; el MSI x86 tiene plantilla `Intel;1033` y una condición explícita `NOT VersionNT64`, por lo que rechaza Windows de 64 bits. No se altera esa condición. Las DLL `dpfpdd.dll` y `dpfj.dll` originales tienen versión `3.4.0.127`; el registro del proveedor conserva `Software\DigitalPersona\Products\U.are.U RTE` y su `Version`. Estos datos de archivos/paquetes no acreditan funcionamiento físico ni soporte ARM64.

La recuperación e integridad de recursos no acreditan instalación del controlador, lector físico, relé ni una versión final. La instalación que el usuario ya utiliza tiene la huella funcionando; se conserva esa implementación. Las comprobaciones pendientes de una compilación nueva deben aportar su propia evidencia y conservar `release_readiness.json`.
