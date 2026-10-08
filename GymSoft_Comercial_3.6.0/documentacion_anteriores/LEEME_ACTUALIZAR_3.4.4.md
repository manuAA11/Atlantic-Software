# Gym soft Comercial 3.4.4

Esta entrega contiene las tres aplicaciones y el generador de instaladores para Windows. El ZIP es un paquete de código fuente; los ejecutables se generan en tu computador.

## Actualizar

1. Cierra Administración, Recepción y el panel del propietario.
2. Extrae `GymSoft_Comercial_3.4.4_COMPLETO.zip` en una carpeta nueva.
3. Ejecuta `CREAR_INSTALADORES.bat`. Usa Python 3.13 de 64 bits, Node.js LTS e Inno Setup 6, como en la entrega anterior. El script también reconoce una instalación de Python aunque el comando `py` no esté disponible.
4. Durante las pruebas gráficas, deja el escritorio desbloqueado y las ventanas de prueba visibles. El programa moverá y restaurará sus propias ventanas. Espera a que termine antes de utilizar otras aplicaciones que puedan taparlas.
5. Instala `salida/GymSoft_Instalar_o_Actualizar_3.4.4.exe` para Administración y Recepción.
6. Instala `salida/GymSoft_Propietario_PRIVADO_3.4.4.exe` únicamente en tu computador.

**No ejecutes SQL para actualizar desde 3.4.x.** Esta revisión no cambia las tablas, las funciones del servidor ni los permisos. Tus gimnasios, cuentas y registros se conservan.

## Cambios principales

- Distribuciones normal y maximizada, sin las esperas temporizadas ni la capa oscura de la 3.4.3. Se actualiza la posición de los controles existentes, evitando retirarlos y volverlos a mostrar.
- El área desplazable se ajusta al cambiar el contenido. Desplazar una página estable ya no vuelve a calcular su distribución.
- Las consultas y los guardados de Administración y Recepción se ejecutan fuera del hilo que dibuja la ventana. Cuando una operación tarda, aparece un aviso de progreso. Una conexión lenta sigue necesitando tiempo para responder.
- El formulario de pago conserva sus campos si el guardado falla. Se cierra después de recibir confirmación y bloquea otro envío mientras espera. No reintenta pagos automáticamente.
- Validación compartida de importes: acepta pesos enteros, por ejemplo `55000` o `55.000`. Rechaza entradas ambiguas como `15,50`, que antes podían convertirse en otro importe.
- La fecha del servidor se vuelve a consultar al caducar su caché breve o al cambiar de día. No es necesario cerrar el programa cada noche.
- La tienda conserva sus tarjetas cuando los productos no cambian; ajusta su altura al texto y a la escala de pantalla.
- Se mantienen el Dashboard sin «Más de 30 días», Recepción sin Dashboard, la huella opcional, la lectura automática, las tiqueteras editables y los créditos y contactos.

## Comprobar en tu equipo

Prueba Administración y Recepción con la escala habitual de Windows. En el Dashboard y en una tienda con productos, maximiza, restaura y desplaza el contenido. Comprueba también un pago y su aparición en el historial. Si la aplicación indica que **no pudo confirmar** una operación, consulta el historial antes de repetirla: perder la respuesta de la red no demuestra que el servidor haya rechazado el pago.

`SIMULAR_GIMNASIO.bat` ejecuta las pruebas con datos ficticios y guarda el informe en `salida/validacion`. No usa gimnasios reales. La compilación exige que todas las etapas pasen; si falla, conserva esa carpeta para diagnosticar la causa.

El informe `VALIDACION_3.4.4.md` describe los resultados y los límites de la comprobación local. La fluidez visual del ejecutable, el lector físico y la conexión real entre computadores requieren comprobación en Windows. Ninguna batería de pruebas garantiza ausencia absoluta de errores.

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
