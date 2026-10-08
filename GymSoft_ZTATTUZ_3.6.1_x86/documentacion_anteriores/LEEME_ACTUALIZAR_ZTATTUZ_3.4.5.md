# Gym soft para ZTATTUZ · 3.4.5

Entrega del 24 de septiembre de 2026. Incorpora a Administración y Recepción las mejoras operativas y de interfaz de Gym soft Comercial 3.4.5, usando el proyecto original de ZTATTUZ.

## Cómo instalar la actualización

1. Extrae `GymSoft_ZTATTUZ_3.4.5_COMPLETO.zip` en una carpeta nueva de tu computador de preparación.
2. Necesitas Python 3.13 de 64 bits, Node.js LTS e Inno Setup 6 para generar los ejecutables. Ejecuta `CREAR_INSTALADORES.bat` y mantén el escritorio visible durante las pruebas gráficas.
3. Cuando termine, copia únicamente `salida/ZTATTUZ_Instalar_o_Actualizar_3.4.5.exe` al computador del gimnasio.
4. Cierra las aplicaciones anteriores y ejecuta ese instalador con la misma cuenta de Windows que utilizabas para ZTATTUZ. Actualiza Administración y Recepción y conserva sus rutas e identificadores de instalación anteriores.
5. Abre el acceso directo nuevo de Administración o Recepción. Inicia sesión con el correo y contraseña de siempre.

**La actualización de la base ya se aplicó y verificó en el proyecto original `srmquhwpawgipncmvfjf`. No necesitas ejecutar SQL, importar un Excel ni crear otra cuenta.** El SQL incluido documenta la actualización; no es un instalador de base nueva.

El ZIP contiene fuentes, pruebas y el generador de instaladores. No contiene ejecutables compilados en Windows. La compilación y la prueba en el Windows Mini del gimnasio siguen pendientes.

## Mejoras incluidas

- Huella opcional al crear clientes y lectura automática mediante un lector compatible que envíe códigos como teclado. Funciona dentro de la aplicación, con pausa y protección frente a lecturas repetidas.
- Recepción abre Registro de entrada; no incluye Dashboard.
- Dashboard administrativo con vencimientos, saldos de tiqueteras y cumpleaños. Conserva las columnas de la ventana maximizada al usar una ventana mediana; scroll solo cuando el contenido lo requiere.
- Distribución corregida de Estadísticas y otros paneles, evitando huecos intermedios. Escalas comprobadas en las pruebas gráficas: 100 %, 120 % y 125 %.
- Consultas fuera del hilo de la interfaz, agrupación de actualizaciones y reutilización de tablas para reducir refrescos visibles.
- Tiqueteras con entradas y vigencia por meses editables. Traslado de una tiquetera anterior con fecha de inicio y entradas consumidas, sin inventar pagos ni asistencias.
- Seguimiento de visitas por sesión a 7, 14 y 30 días.
- Fecha de cumpleaños con avance del cursor después de la barra.
- Corrección y anulación de pagos con auditoría; registro de gastos desde Recepción.
- Conserva tienda, inventario, personal, rutinas, clases, marketing y exportación/importación de Excel y JSON.
- Formularios y avisos oscuros, corrección del error de desplegables `popdown`, y Reintentar devuelve al formulario de credenciales.
- Iconos GS en ejecutables y accesos. Conserva el logo local anterior y permite compartirlo entre equipos al guardarlo desde Configuración.

El panel comercial del propietario sigue perteneciendo a la edición comercial. Esta edición utiliza los permisos originales de ZTATTUZ, sin contratos ni licencias comerciales añadidos a su cuenta.

## Windows 10 Mini

Preparado para Windows 10 de **64 bits**, la misma arquitectura de los instaladores anteriores. Los ejecutables generados incluyen Python, Tk, Excel, certificados y dependencias: no necesitas instalar Python, Node.js, Office ni Microsoft Store en el computador del gimnasio.

Windows Mini no tiene una única composición. Si esa instalación eliminó componentes necesarios de Windows, debe comprobarse en el equipo. Incluí `Inicio → ZTATTUZ → Diagnóstico de ZTATTUZ Administración`. Su informe queda en `%LOCALAPPDATA%\GymControl\logs\diagnostico.json`. Consulta `LEEME_WINDOWS_MINI.txt`.

Referencias: [Python 3.13 en Windows](https://docs.python.org/3.13/using/windows.html) y [requisitos de PyInstaller](https://pyinstaller.org/en/stable/requirements.html). La compatibilidad documentada del intérprete no certifica una imagen modificada de Windows.

## Qué se comprobó y qué falta

`salida/validacion` contiene los resultados locales. La simulación utiliza las clases Python reales y PostgreSQL local con la estructura de ZTATTUZ; registra pagos y entradas ficticios, prueba límites de tiqueteras, restaura respaldos y comprueba permisos. No agrega registros de prueba a la base real.

Las pruebas gráficas se ejecutaron en Linux con Tk y una pantalla virtual. Los tests de maximización simulan el estado de Windows cuando ese entorno no lo proporciona. Antes de usarlo durante la jornada, comprueba en el Windows Mini: instalación, inicio de sesión, pago, entrada, impresión/exportación que utilices y lector físico. No se promete ausencia absoluta de errores.

La compilación repite las pruebas en Windows y abre los dos ejecutables en modo diagnóstico antes de generar el instalador completo. Se detiene si una etapa falla; no elimina esas comprobaciones.

WhatsApp automático conserva la configuración existente y requiere que el servicio de envío esté activo. Esta actualización no realiza envíos ni activa un proveedor externo.

## Soporte

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
Correo: manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
