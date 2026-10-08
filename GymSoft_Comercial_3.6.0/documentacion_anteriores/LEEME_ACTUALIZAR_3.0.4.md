# Instalar la corrección Gym soft 3.0.4

1. Cierra Administración, Recepción y el panel anterior. Si siguen en el Administrador de tareas, finaliza únicamente `GymSoftAdmin.exe`, `GymSoftRecepcion.exe` y `GymSoftControl.exe`.
2. Extrae este ZIP en una carpeta nueva. No uses `dist`, `build` ni ejecutables de versiones anteriores.
3. Ejecuta `CREAR_INSTALADORES.bat`. Requiere Python 3.13 de 64 bits e Inno Setup 6. Aparecerán varias ventanas de prueba que se cierran solas; no las cierres manualmente. No usan cuentas ni conectan a gimnasios reales.
4. Al terminar sin errores, abre `salida/GymSoft_Instalar_o_Actualizar_3.0.4.exe`. Instala o actualiza Administración y Recepción y vuelve a crear sus accesos directos con el icono GS.
5. Para TU panel, abre `salida/GymSoft_Propietario_PRIVADO_3.0.4.exe`. Crea el acceso directo **Gym soft Propietario**. Es privado: no lo envíes al gimnasio.
6. Abre las aplicaciones desde los accesos nuevos. Confirma versión 3.0.4 en la ventana o el pie del programa.

No tienes que volver a ejecutar `INSTALAR_BASE_NUEVA.sql` ni `HABILITAR_PROPIETARIO.sql`. Conserva la configuración comercial, tus cuentas y tus gimnasios; no se cambia la base de ZTATTUZ.

## Dónde están las funciones

- **Administración → Clientes y pagos → selecciona cliente → Ver / modificar pagos → selecciona pago.** Puedes corregir el valor, método y referencia, anularlo o consultar cambios. El motivo es obligatorio y el registro se conserva.
- **Administración → Finanzas y auditoría → selecciona movimiento de membresía → Editar / corregir pago seleccionado.** Abre los pagos del cliente. En **Gastos** puedes crear, editar y eliminar gastos.
- **Recepción → Clientes y pagos → Crear gasto.** El gasto se guarda en el gimnasio del usuario y queda identificado en auditoría.
- **Propietario → selecciona gimnasio → Registrar mensualidad.** Introduce meses y valor; conserva la referencia generada o usa tu comprobante. Si hay un fallo de conexión, revisa Mensualidades antes de repetir; para reintentar el mismo pago usa la misma referencia y los mismos datos.

## Si un icono antiguo sigue apareciendo

El instalador usa un archivo nuevo `GymSoft-3.0.4.ico` en la carpeta permanente de instalación, no en Descargas ni en una carpeta temporal. Las propiedades del acceso deben apuntar a los EXE instalados, no a Python ni a la carpeta de desarrollo.

Si tienes accesos duplicados, elimina solo los accesos antiguos de Gym soft y vuelve a ejecutar el instalador 3.0.4 para recrearlos. No elimines carpetas del programa, datos ni cachés globales de Windows. Los iconos anclados antiguos en la barra de tareas se pueden desanclar y volver a anclar desde la nueva aplicación.

## Qué se entrega al gimnasio

Solo `GymSoft_Instalar_o_Actualizar_3.0.4.exe`. No entregues este ZIP de código, el instalador privado ni el ZIP del panel. Después invita al correo de Administración/Recepción y autoriza su equipo desde tu panel.

## Verificación pendiente en tu PC

Este ZIP contiene código completo y el constructor de instaladores, no EXE ya compilados. Las pruebas Python y PostgreSQL se ejecutaron durante la preparación. La prueba gráfica y los recursos de iconos del EXE se comprueban al compilar en Windows. El instalador se debe probar en tu equipo antes de venderlo.
