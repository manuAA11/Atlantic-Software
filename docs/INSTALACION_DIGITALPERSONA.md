# Instalación del componente DigitalPersona

Los instaladores de clientes incorporan el runtime original 3.4.0.127 recuperado del SDK del usuario, junto con su EULA íntegra. No distribuyen el SDK de desarrollo. La licencia original se muestra durante la instalación y se conserva en `DigitalPersonaRuntime/Licenses/EULA SDK.rtf`.

El componente de instalación compartido es `common/digitalpersona_install.iss`; cada edición incluye una copia idéntica. Antes de ejecutar el redistribuible, busca las dos bibliotecas del lector, `dpfpdd.dll` y `dpfj.dll`, en las ubicaciones utilizadas por la aplicación. Comprueba su arquitectura PE y una versión de archivo igual o posterior a 3.4.0.127. Una instalación compatible existente se conserva; no se sustituye por el paquete recuperado.

Si falta el runtime compatible, el instalador ejecuta el `setup.exe` original con elevación de Windows y espera su resultado. El usuario debe aceptar la solicitud de Windows para instalar el controlador. Los códigos 0, 3010 y 1641 se consideran exitosos; los dos últimos requieren reiniciar. Después se comprueba de nuevo que estén ambas bibliotecas compatibles. Si se cancela la elevación, falla el redistribuible o faltan las bibliotecas, la instalación muestra un error; no informa un éxito completo. El registro MSI queda en `%LOCALAPPDATA%\AtlanticTechSoftware\logs\DigitalPersona_instalacion.log`.

El runtime se comprueba también al instalar sin interfaz. El actualizador completo ZTATTUZ instala primero ese componente y después Administración y Recepción, con sus identificadores y directorios anteriores. Los instaladores individuales conservan la misma comprobación. El panel privado del propietario comercial no incluye el lector ni el runtime.

## Arquitecturas

- Comercial y ZTATTUZ x64 requieren Windows 10 o posterior en x64 nativo para instalar el runtime del lector. El cliente comercial usa `x64os`, como ZTATTUZ x64. No se acredita soporte del controlador en ARM64.
- ZTATTUZ x86 conserva Windows de 32 bits. El MSI original x86 contiene la condición `NOT VersionNT64` y rechaza Windows de 64 bits. Compilar y probar Python de 32 bits en un runner Windows x64 no acredita instalar este redistribuible allí.
- El panel privado comercial requiere Windows 10 o posterior y conserva `x64compatible` porque no instala el runtime. Esto no acredita pruebas de ejecución en ARM64.

## Compilación técnica

Los `.iss` aceptan `BuildDistRoot` (por defecto `dist`) y `BuildComponentRoot` (por defecto `salida\componentes`) para compilar desde directorios aislados de validación. Definir `BuildValidation` añade `Validación técnica (no final)` al nombre visible de todos los instaladores. Esos parámetros no modifican los identificadores de las instalaciones ni el gate de entrega final.

Las pruebas estáticas de empaquetado comprueban las rutas y reglas existentes. La compilación real de estos scripts con Inno Setup, la ejecución del instalador y las pruebas físicas del lector se registran por separado. La revisión estática no acredita esos resultados.

## Prueba de instalación en un runner efímero

`tools/windows_installation_qa.py --ephemeral-runner` usa exclusivamente el último informe técnico de `windows_packaging_qa.py --installers`. Antes de ejecutar un proceso verifica su estado PASS, la marca NO FINAL, los SHA256 y que sus archivos pertenezcan al directorio aislado de validación. También exige Windows, GitHub Actions alojado por GitHub, una identidad de ejecución y los directorios `RUNNER_TEMP` y `GITHUB_WORKSPACE` válidos. Una ejecución local, en un runner persistente o sin el parámetro explícito se rechaza antes de modificar archivos.

En Windows x64 instala en directorios propios del run, comprueba el runtime real, los EXE instalados, sus iconos, sus diagnósticos sin red y los accesos directos. En ZTATTUZ también ejecuta el actualizador completo y verifica que conserve directorios y registros. Al terminar desinstala las aplicaciones y comprueba la limpieza; el runtime del sistema se conserva hasta destruir el runner. No inicia sesión ni usa huellas, relé o cuentas externas. El informe y los logs quedan bajo `salida/validacion/instalacion-tecnica` y mantienen `final: false`.

Para ZTATTUZ x86, un runner Windows x64 produce `NOT_RUN` con la condición `NOT VersionNT64` del SDK; esto no acredita instalación en Windows de 32 bits. Las pruebas portátiles del helper verifican rechazos y autenticación del paquete. La instalación real solo se acredita con el resultado del run Windows correspondiente.
