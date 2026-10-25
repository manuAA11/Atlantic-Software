# Atlantic Gym 3.8.2 · Actualización opcional de prueba

Incluye las correcciones de continuidad y reincorporación de sesión en
Administración y Recepción. Es una entrega de prueba, NO FINAL.

## Sesión y conexión

- Una sesión todavía vigente se conserva al abrir el programa.
- Las conexiones utilizan la sesión renovada por el mismo perfil.
- Un corte de red conserva la sesión; la renovación vuelve a intentarse con
  espera limitada. Al reanudar, comprueba de nuevo la vigencia.
- Si la sesión se revoca, permite volver a entrar con la misma cuenta y
  gimnasio. Una contraseña incorrecta vuelve al formulario con el correo
  conservado y la contraseña vacía. Cancelar la reincorporación deja abierta
  la ventana y sigue exigiendo autenticación para operar.
- La reincorporación vuelve a activar la renovación periódica de sesión.
- Una respuesta perdida a una escritura no provoca su repetición automática.

## Instalar o actualizar

1. Cierra Administración y Recepción.
2. Usa el instalador de la arquitectura y el perfil de tu instalación actual.
3. Instala en la misma carpeta y comprueba que el programa muestre 3.8.2.
4. Prueba el acceso de Administración y Recepción con sus cuentas autorizadas.
5. Comprueba en el PC la recuperación tras perder internet y suspender Windows.

Se conservan los identificadores y las carpetas de instalación. Conserva un
respaldo verificado de la configuración y los datos antes de actualizar.
El instalador no aplica migraciones de base de datos ni modifica permisos.
La corrección del rechazo de JWT del proveedor requiere su actualización
administrada de Supabase; se atiende por separado desde el servicio.

## Alcance de la prueba

La instalación del paquete x86 en Windows de 32 bits y la comprobación presencial
del lector, relé y suspensión siguen pendientes para esta versión. Las pruebas
con tiempo, red o hardware simulados no sustituyen la comprobación del PC.
Los criterios de aceptación final permanecen activos.

© Atlantic Tech Software — All rights reserved. By Manuel Cuellar
