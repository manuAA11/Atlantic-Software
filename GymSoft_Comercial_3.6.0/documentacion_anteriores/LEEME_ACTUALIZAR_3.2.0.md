# Gym soft Comercial 3.2.0

Esta entrega contiene Administración, Recepción y el panel privado del propietario, con diseño adaptable, huella opcional y tiqueteras configurables.

## Instalar o actualizar en Windows

1. Cierra las tres aplicaciones y extrae el ZIP en una carpeta nueva.
2. Ejecuta `CREAR_INSTALADORES.bat` con Python 3.13 de 64 bits e Inno Setup 6 instalados.
3. El proceso ejecuta las pruebas de Python, las comprobaciones gráficas y la verificación del icono GS de cada ejecutable.
4. En `salida`, ejecuta `GymSoft_Instalar_o_Actualizar_3.2.0.exe` para Administración y Recepción.
5. Instala `GymSoft_Propietario_PRIVADO_3.2.0.exe` sólo en tu computador. Conserva privado este paquete de fuentes y entrega a los gimnasios únicamente el instalador de clientes.

Si ya usas la base comercial 3.1.1, **no ejecutes SQL nuevo ni reinstales la base**. Los cambios utilizan los campos y permisos existentes.

El ZIP contiene las fuentes y el generador de instaladores. No incluye ejecutables ya compilados. La comprobación final de los ejecutables y del lector físico debe realizarse en Windows.

## Ventanas y escala de pantalla

Puedes usar Windows al 100 % o 125 % y cambiar el tamaño de la ventana. Las tarjetas, los controles y los formularios se reorganizan según el espacio disponible, sin reducir el tamaño de texto configurado en el sistema.

Cuando falta altura, utiliza la rueda del ratón o la barra de desplazamiento. Las tablas tienen desplazamiento horizontal y vertical. Si los títulos de las pestañas no caben, aparece un selector con todas las secciones. La barra lateral también permite desplazarse hasta Configuración.

Administración y Recepción comienzan con **Dashboard → Registro de entrada → Clientes y pagos**. Las funciones del panel del propietario conservan su organización comercial.

## Clientes y lectura automática de huella

El campo **Código de huella (opcional)** se puede dejar vacío al crear o editar clientes. No es necesario disponer de un lector.

Para utilizarlo, asocia al cliente el identificador que envía un lector compatible. El lector debe funcionar como teclado y enviar su código completo; no todos los dispositivos biométricos tienen este modo.

Con Gym soft activo:

- Una lectura rápida compatible intenta registrar la entrada aunque el foco esté fuera del buscador. Admite lecturas con Enter y sin Enter, de al menos tres caracteres.
- En el buscador de **Registro de entrada**, escribir o pegar un código exacto también intenta registrar el ingreso tras una pausa de 0,7 segundos. Enter permite realizar la consulta inmediatamente.
- Se comprueba el código exacto dentro del gimnasio de la cuenta y se valida la membresía. Una huella desconocida o una membresía sin acceso no autoriza el ingreso.
- La misma lectura se ignora durante cinco segundos para evitar consumos repetidos en ese equipo. Una operación pendiente no se reintenta automáticamente.
- La captura se pausa mientras hay un formulario abierto o Gym soft deja de ser la aplicación activa. El buscador de códigos de barras de Tienda conserva su función de venta.
- Puedes desactivar **Lectura automática de huella** desde Registro de entrada. Recepción también muestra el control en Dashboard. Al volver a abrir la aplicación queda activado.

## Crear una tiquetera de 15, 20 u otra cantidad de entradas

En **Administración → Configuración → Planes → Nuevo plan**:

1. Escribe el nombre, por ejemplo, «Tiquetera 20 entradas».
2. En **Tipo de plan**, selecciona **Tiquetera / por entradas**.
3. Define **Vigencia en días**, **Cantidad de entradas** y **Precio**.
4. Guarda el plan. Ya estará disponible al registrar pagos en Administración y Recepción.

Cada ingreso autorizado consume una entrada. La tiquetera termina al agotar el cupo o al vencer su vigencia, como en las tiqueteras anteriores. Una renovación usa el cupo del plan comprado y conserva el historial de la compra anterior.

Para modificar el cupo, selecciona el plan y pulsa **Editar plan**. El cambio se aplica a las compras siguientes; las tiqueteras ya vendidas conservan sus entradas contratadas. Si un plan ya tiene compras, crea otro para cambiar entre la modalidad por días y por entradas.

Para una mensualidad normal, selecciona **Mensualidad / por días**. Mantiene la duración en días y no limita la cantidad de ingresos durante su vigencia.

## Contacto

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
Correo: manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
