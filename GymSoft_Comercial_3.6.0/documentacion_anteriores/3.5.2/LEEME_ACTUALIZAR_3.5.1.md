# Gym soft / ZTATTUZ 3.5.1 - Huella dentro del formulario de clientes

La huella es opcional y ahora se gestiona dentro de Nuevo cliente y Editar cliente, en Administración y Recepción.

## Uso

1. Completa los datos del cliente o abre uno existente para editarlo.
2. En **Huella digital (opcional)** pulsa **Registrar huella** o **Reemplazar huella**.
3. Confirma la identidad y su autorización. Se guardan primero los datos del cliente y comienza la lectura en el mismo formulario.
4. Sigue las instrucciones colocando y levantando el mismo dedo hasta confirmar el registro.
5. Pulsa **Guardar cliente** para guardar cambios adicionales y cerrar. No se crea otro cliente al guardar después de registrar la huella.

Puedes guardar al cliente sin huella. Cancelar la lectura conserva los datos ya guardados; al reemplazar se mantiene la huella anterior hasta confirmar la nueva. **Eliminar huella** conserva al cliente, sus pagos y asistencias.

Para el ingreso automático, cierra el formulario y deja la lectura activada. No hace falta enfocar el buscador. Se mantienen las verificaciones de plan y los permisos del gimnasio. Si no se confirma una escritura por un problema de conexión, revisa los datos antes de repetirla.

## Controlador DigitalPersona

Se instala una vez en cada computador Windows de 64 bits donde se conecte el U.are.U 4500. Es un componente adicional al programa; el instalador completo de Gym soft ya permite instalarlo al finalizar.

También está en **DigitalPersonaRuntime/setup.exe** dentro de este paquete. Extrae toda la carpeta antes de abrirlo. Conserva junto al EXE los archivos setup.msi, Data1.cab, Setup.ini, el archivo de idioma y la carpeta ISSetupPrerequisites. Sigue el asistente, acepta el permiso de administrador y reinicia si lo solicita. No copies solamente setup.exe, pues necesita los demás archivos.

Si ya instalaste correctamente el componente DigitalPersona 3.4.0 x64, no necesitas reinstalarlo por este cambio del formulario. El componente funciona con ambas ediciones; basta con una instalación por equipo. Solo una aplicación puede controlar el mismo lector a la vez.

## Generar los instaladores

Estos ZIP contienen código y generador de instaladores; no contienen los ejecutables de Gym soft ya compilados.

Extrae en una carpeta nueva y ejecuta **CREAR_INSTALADORES.bat** en Windows con Python 3.13 x64, Node.js LTS e Inno Setup 6. Los resultados estarán en `salida`:

- Comercial: `GymSoft_Instalar_o_Actualizar_3.5.1.exe`.
- ZTATTUZ: `ZTATTUZ_Instalar_o_Actualizar_3.5.1.exe`.
- El instalador del propietario de Comercial es privado y se instala solo en tu equipo.

Las pruebas de compilación usan un lector simulado. No necesitas conectar el dispositivo ni instalar su controlador para generar los instaladores. Mantén visibles las ventanas durante las pruebas gráficas.

## Base de datos y verificación

No hay SQL nuevo en 3.5.1. Ambas bases ya tienen la actualización de huellas 3.5.0 aplicada. No vuelvas a instalar la base. La nube comparte la plantilla únicamente entre equipos autorizados del mismo gimnasio.

Pasaron las pruebas locales indicadas en **VERIFICACION_3.5.1.md**. La lectura con el sensor físico, su controlador real y Windows 10 Mini siguen pendientes de comprobar en el gimnasio. Esta entrega requiere Windows de 64 bits y los componentes del sistema necesarios para DigitalPersona.

La guía PDF incluida describe los pasos de instalación y uso del formulario actualizado.
