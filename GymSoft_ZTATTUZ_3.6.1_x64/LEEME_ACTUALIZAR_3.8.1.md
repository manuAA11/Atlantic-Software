# Atlantic Gym 3.8.1 · Actualización opcional de prueba

Esta actualización corrige el regreso al formulario de acceso en Administración
y Recepción. Es una entrega de prueba, NO FINAL.

## Corrección del acceso

Si falla la sesión guardada o la contraseña es incorrecta, vuelve a aparecer
el formulario de inicio de sesión, con el correo conservado y la contraseña
vacía. El error se muestra dentro del formulario. Puedes escribir de nuevo
la contraseña y continuar; cerrar el formulario cancela el inicio.

Ante el error temporal «JWT issued at future», el programa espera brevemente
antes de devolver el error al formulario. Si persiste, espera unos segundos
y vuelve a iniciar sesión; contacta al soporte si el servicio sigue rechazando
el acceso.

## Instalar o actualizar

1. Cierra Administración y Recepción.
2. Usa el instalador de la arquitectura y el perfil de tu instalación actual.
3. Instala en la misma carpeta y abre el programa; verifica que muestre 3.8.1.
4. Comprueba el acceso de Administración y Recepción con sus cuentas autorizadas.

Se conservan los identificadores y las carpetas de instalación. Conserva un
respaldo verificado de la configuración y los datos antes de actualizar.
Esta corrección de acceso sobre 3.8.0 no requiere cambios de base de datos.

## Alcance de la prueba

La instalación del paquete x86 en Windows de 32 bits y la comprobación presencial
del lector y del relé siguen pendientes. Las pruebas con hardware simulado
no sustituyen esa comprobación en el equipo del gimnasio.

© Atlantic Tech Software — All rights reserved. By Manuel Cuellar
