# Gym soft Comercial 3.4.0

Actualización de fluidez y distribución para Administración, Recepción y el panel privado del propietario.

## Corrección de la carga y las pruebas gráficas

**Revisión del 10 de septiembre: carga de Recepción.** Se corrigió el caso en que `ReceptionApp / access` quedaba en «Cargando información…» con ambas respuestas recibidas, la página visible y ningún temporizador. La sección seleccionada mantiene la reanudación mientras termina de mostrarse y solo completa la carga después de presentar todos sus resultados. Se reproduce ese orden de eventos en la prueba y se conserva el límite de seis segundos.

Esta entrega incorpora el parche para `performance_ui_smoke.py` cuando informaba «La respuesta de prueba no llegó a tiempo». Se corrigió la reanudación de una respuesta que llega antes de que la página se haga visible, y el temporizador de las cargas encadenadas. La prueba conserva el límite de seis segundos y ahora identifica la página y el estado de la carga.

Si ya tienes la carpeta 3.4.0 con sus dependencias, puedes aplicar `GymSoft_3.4.0_PARCHE_CARGA.zip`: copia su contenido dentro de **GymSoft_Comercial_3.4.0**, acepta reemplazar archivos y vuelve a ejecutar **CREAR_INSTALADORES.bat**. Conserva `.venv`. El paquete completo también incluye esta corrección. No necesita SQL nuevo.

Descarga de nuevo el parche para obtener esta revisión. Es acumulativo: no necesitas aplicar antes los parches anteriores. Al comenzar la prueba de rendimiento, aparecerá **COORDINADOR DE CARGA: f1be40c96930**, que identifica el código corregido.

El parche incluye también la recuperación de las ventanas de prueba al minimizarlas. La comprobación de visibilidad necesita una ventana realmente visible en el escritorio: taparla, minimizarla o bloquear la sesión puede provocar «No se encontró un control en el punto visible». La prueba mantiene su ventana delante, la restaura si se minimiza y vuelve a consultar el control mientras Windows termina de mostrarla. Sigue rechazando controles ocultos, superpuestos y consultas que no encuentran el control.

**Durante las pruebas automáticas, deja sus ventanas visibles y el escritorio desbloqueado hasta que terminen.** Minimizar solo CMD no afecta a la comprobación si las ventanas de prueba permanecen visibles. Esta recuperación se aplica a las pruebas; la aplicación instalada conserva su comportamiento normal al minimizarla.

## Instalar para probar

1. Cierra las tres aplicaciones.
2. Extrae `GymSoft_Comercial_3.4.0_COMPLETO.zip` en una carpeta nueva.
3. Ejecuta `CREAR_INSTALADORES.bat`. Requiere Python 3.13 de 64 bits e Inno Setup 6.
4. Instala `salida/GymSoft_Instalar_o_Actualizar_3.4.0.exe` para Administración y Recepción.
5. En tu computador, instala también `salida/GymSoft_Propietario_PRIVADO_3.4.0.exe` si utilizas el panel del propietario.
6. Abre los accesos directos instalados y confirma que indiquen **3.4.0**.

El paquete contiene el código completo y el generador de instaladores. Los ejecutables se generan en Windows; no vienen compilados en este ZIP. El aviso de actualización de pip no impide compilar.

**Si ya utilizas 3.3.2, no necesitas ejecutar SQL.** Esta actualización conserva las cuentas, gimnasios, registros, planes y tiqueteras. No ejecutes `INSTALAR_BASE_NUEVA.sql` sobre la base existente.

El instalador de Administración y Recepción se entrega al gimnasio. El instalador del propietario y este paquete de fuentes son privados del proveedor.

## Qué cambia

- **Recepción inicia en Registro de entrada.** Su menú contiene Registro de entrada, Clientes y pagos y Tienda. Dashboard se conserva en Administración.
- Registro de entrada tiene dos pestañas: **Registrar entrada** e **Historial de entradas**. Una lectura identificada abre el panel de registro para mostrar su resultado.
- Las listas ajustan su altura y sus columnas. Las barras solo aparecen si sus filas o columnas exceden el espacio. Las páginas adaptan sus textos y distribución; cuando todavía falta espacio, permiten desplazarse.
- Las pestañas usan la altura del contenido seleccionado. Una pestaña larga ya no obliga a que las demás tengan su misma altura. En ventanas estrechas, un selector permite acceder a todas las pestañas.
- Las consultas principales de las 14 secciones de Administración y Recepción se ejecutan en segundo plano. La pantalla mantiene sus datos durante la actualización.
- Las tablas conservan las filas que no cambian, la selección y la posición de lectura. La tienda de Recepción reutiliza las tarjetas y fotos de productos que siguen iguales.
- Navegar a una sección ya cargada reutiliza la pantalla. Las notificaciones próximas se agrupan y actualizan la sección visible; las demás quedan pendientes para cuando se abran.
- Se evita volver a aplicar el estilo nativo de Windows por cada control que aparece. El diseño agrupa ajustes de tamaño y evita redibujados que no cambian el contenido.
- Las respuestas de búsquedas anteriores no sustituyen a la búsqueda actual. Los formularios conservan sus cambios locales durante la actualización.

La aplicación muestra «Cargando información…» o «Actualizando…» mientras espera la consulta. Si una carga falla, el mensaje permite pulsar para reintentar. El tiempo de respuesta del servidor sigue dependiendo de la conexión.

## Funciones conservadas

La huella sigue siendo opcional al crear clientes. **Activar lectura / Pausar lectura** mantiene el estado al cambiar de sección. Los lectores compatibles que escriben como un teclado pueden identificar un código mientras Gym soft tiene el foco; la captura se pausa en formularios y al trabajar en otra aplicación. Se filtran las lecturas repetidas del mismo código durante cinco segundos.

En **Administración → Configuración → Planes**, puedes crear o editar mensualidades por días y tiqueteras con un cupo de entradas y vigencia por días o meses calendario. Para trasladar una tiquetera iniciada, usa **Clientes y pagos → Registrar pago → Tiquetera ya iniciada (sin nuevo cobro)** e indica la fecha original y las entradas utilizadas.

Dashboard de Administración conserva los bloques de entradas restantes. **Estadísticas → Seguimiento de sesiones** conserva los períodos de 7, 14 y 30 días y los contactos para seguimiento manual. Se conservan la corrección de pagos, los gastos de Recepción y el editor del propietario.

## Comprobación en tu computador

1. Mueve la ventana arrastrando su título y cambia su tamaño varias veces. Comprueba que los paneles permanezcan visibles.
2. Repite con Windows al 100 % y al 125 %. Las barras deben aparecer solo si hay contenido fuera del espacio disponible.
3. En Recepción, abre Registro de entrada y cambia entre sus dos pestañas. Comprueba Activar/Pausar lectura.
4. Abre una lista con suficientes registros, desplázate y selecciona una fila. Pulsa Actualizar: debe conservar la posición si el registro sigue en el listado.
5. Cambia entre secciones mientras cargan los datos. La aplicación debe permitir seguir navegando; una búsqueda anterior no debe reemplazar a la actual.
6. Revisa Configuración → Planes, Estadísticas y los accesos del propietario.

La compilación ejecuta pruebas automáticas de ventanas, escalado, lector simulado, tiqueteras y fluidez. También puedes ejecutarlas con `VERIFICAR_INTERFAZ.bat`, después de preparar las dependencias. Estas pruebas usan datos locales simulados, sin cuentas ni cambios en gimnasios reales.

Las pruebas locales se describen en `VALIDACION_3.4.0.md`. El movimiento nativo de Windows, los iconos instalados y el lector físico necesitan la comprobación en tu computador. Las operaciones que guardan datos siguen esperando la confirmación del servidor; no se presenta un pago o una entrada como guardados antes de confirmarlos.

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
