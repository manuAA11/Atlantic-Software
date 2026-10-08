# Comercial 3.5.1 - Resultado de las pruebas

PASS: 78 pruebas unitarias Python, 64 comprobaciones de los formularios con huella integrada, 28 comprobaciones del gestor de huellas y la prueba de ventanas/formularios/pagos/gastos.

Los formularios se comprobaron en Administración y Recepción a escalas 100 % y 125 %. Se ejercitaron alta con y sin huella, validación de datos, guardado sin INSERT duplicado, edición después de capturar, reemplazo, eliminación sin borrar al cliente, cancelación y bloqueo de reintentos ante una respuesta de guardado incierta.

La escritura se ejecuta fuera del hilo de Tk. El lector se simuló; las pruebas no cargan sus DLL ni requieren USB. Las pruebas previas de SQL no se repitieron: 3.5.1 no modifica el SQL, los permisos ni la lógica de validación de entradas de 3.5.0.

Pendiente: generar y ejecutar los instaladores en Windows y comprobar DigitalPersona con el dispositivo físico, incluido el computador Windows 10 Mini. No se garantiza ausencia de todo error.

El archivo run_validation.py incorpora la nueva comprobación de formularios a las pruebas de compilación existentes. El informe JSON de esta revisión está en salida/validacion.
