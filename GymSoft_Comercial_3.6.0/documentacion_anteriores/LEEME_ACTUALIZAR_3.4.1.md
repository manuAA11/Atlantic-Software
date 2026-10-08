# Gym soft Comercial 3.4.1

Actualización de pagos, operaciones y distribución de ventanas. Incluye Administración, Recepción y el panel privado del propietario.

## Instalar o actualizar

1. Cierra las aplicaciones de Gym soft y extrae `GymSoft_Comercial_3.4.1_COMPLETO.zip` en una carpeta nueva.
2. Ejecuta `CREAR_INSTALADORES.bat`. En el computador de compilación se necesitan Python 3.13 de 64 bits, Node.js LTS e Inno Setup 6. El preparador reconoce instalaciones de Python aunque no exista el comando `py`.
3. Mantén las ventanas de prueba visibles y el escritorio desbloqueado durante la comprobación gráfica. Las pruebas de datos crean gimnasios ficticios en una base local, sin modificar tus cuentas ni tus gimnasios.
4. Cuando termine correctamente, instala `salida/GymSoft_Instalar_o_Actualizar_3.4.1.exe`. Este mismo instalador sirve para instalar o actualizar Administración y Recepción.
5. Para tu panel privado, instala `salida/GymSoft_Propietario_PRIVADO_3.4.1.exe` únicamente en tu computador.
6. Abre los accesos directos y confirma que la versión sea **3.4.1**.

El ZIP contiene las fuentes y el generador de instaladores. Los EXE se generan en Windows; no vienen compilados en este paquete. Los computadores de los gimnasios solo necesitan el instalador de clientes: no requieren Python, Node.js ni el código fuente.

**Si ya usas 3.4.0, no ejecutes SQL.** Esta corrección cambia el programa y sus pruebas; conserva la base comercial existente. No ejecutes `INSTALAR_BASE_NUEVA.sql` sobre una base en uso.

## Correcciones

- **Registro de pagos:** las listas desplegables internas de Tk ya no provocan `KeyError: 'popdown'`. Una actualización espera mientras está abierto el formulario. Los avisos oscuros recuperan correctamente el control del formulario al cerrarse.
- **Rutinas, ejercicios y clases:** se retiraron campos antiguos de las llamadas de guardado que no existen en la base comercial. La simulación crea los registros y comprueba sus relaciones.
- **Ventana normal y maximizada:** cada modo conserva su distribución de tarjetas. Arrastrar la ventana por su título no vuelve a calcular las columnas. Al restaurarla, recupera su distribución normal.
- **Escala de pantalla:** se mantiene el tamaño de texto elegido en Windows. Hay pruebas al 100 %, 120 % y 125 %. Los textos ajustan sus líneas después de estabilizar el tamaño disponible; no se encoge la fuente para ocultar contenido.
- **Desplazamiento:** las barras aparecen cuando el contenido excede el espacio. Al hacer una ventana más pequeña que su distribución normal, se mantiene esa distribución y se puede desplazar lo que no cabe. Las listas conservan su propio desplazamiento.
- **Fluidez:** se conservan las consultas en segundo plano, las tablas que actualizan solo las filas modificadas, las pantallas reutilizadas y la agrupación de notificaciones. Las vistas ocultas no quedan recalculando su distribución.

Recepción continúa sin Dashboard. Se mantienen la huella opcional, Activar/Pausar lectura, planes mensuales, tiqueteras editables, saldos iniciales, corrección y anulación de pagos, gastos desde Recepción, seguimiento de sesiones y el editor del propietario.

## Simulación de un gimnasio

Ejecuta `SIMULAR_GIMNASIO.bat` para repetir todas las etapas de validación sin crear instaladores. El mismo conjunto se ejecuta automáticamente antes de compilar.

El informe queda en `salida/validacion/RESUMEN_PRUEBAS.txt`. Cada etapa conserva su archivo `.log`, y `simulacion_gimnasio.json` enumera las comprobaciones de la jornada. Si algo falla, la ejecución se detiene e identifica la etapa; no se debe distribuir un instalador anterior como si fuera el resultado de esa ejecución.

La jornada usa las clases de datos de Administración y Recepción contra PostgreSQL local con el SQL comercial. Crea cuentas y dos gimnasios ficticios, registra clientes, planes, pagos, entradas, ventas, gastos, turnos, rutinas y reservas; comprueba estadísticas, contactos, exportación, restauración y permisos. Otras suites amplían la validación del editor, cancelaciones, eliminación, conflictos, cupos y errores.

Consulta **VALIDACION_3.4.1.md** para la cobertura y los resultados de esta entrega. Las pruebas locales no sustituyen la comprobación del instalador en Windows, el lector físico, los correos ni la conexión real entre equipos. WhatsApp automático requiere tener activo su servicio de envío. No se afirma que una ejecución sin fallos garantice la ausencia de cualquier error futuro.

## Comprobación después de instalar

1. Abre Registrar pago, despliega Plan y Medio de pago, selecciona valores y guarda un pago de prueba. Confirma el registro en el historial antes de intentar repetirlo.
2. Cambia entre ventana normal y maximizada, y muévela arrastrando su título. Los cuadros deben conservar su distribución y permanecer visibles.
3. Repite con la escala de Windows que utilices. Comprueba también las pestañas de Configuración y Registro de entrada.
4. Desde otro equipo del mismo gimnasio, confirma que aparezca el pago. Prueba una entrada y revisa su resultado y el saldo de la tiquetera.

Created by Manuel Cuéllar  
WhatsApp: +57 3162990884  
manuel411cm@hotmail.com  
© 2026 Manuel Cuéllar. All rights reserved.
