# Gym soft Comercial 3.0.4

## Cambios

- Panel del propietario: los formularios validan antes de cerrarse y conservan los datos cuando son inválidos. La mensualidad recibe una referencia automática; reintentar la misma referencia mantiene la clave de idempotencia.
- Importes con formatos habituales de miles/decimales; meses 1–120, gracia 1–30, equipos 1–100 y usuarios 1–1000. Motivos de al menos tres caracteres. Roles elegidos mediante lista.
- Un error de presentación no detiene el procesamiento de acciones. Cambiar de gimnasio invalida los accesos anteriores hasta cargar los del nuevo gimnasio.
- Se explica que reactivar no renueva automáticamente un vencimiento ni la gracia levanta una suspensión.
- Icono GS y barras oscuras también en login, formularios y mensajes del propietario. Avisos y selectores de archivos propios oscuros en las aplicaciones.
- Tres EXE con iconos embebidos verificados al compilar; accesos directos con icono versionado permanente. Instalador privado nuevo para el propietario.
- Acceso explícito **Ver / modificar pagos** desde Clientes y pagos. Se conserva el gestor de corrección/anulación con auditoría y control de revisión concurrente.
- Acceso a pagos desde Finanzas; Crear gasto en Recepción; validación de gastos rechaza importes negativos y fechas mal formadas.

## Compatibilidad

El esquema sigue siendo 3.0.0. No se ejecuta ninguna migración nueva ni se reinstala la base. ZTATTUZ no se modifica. Cada gimnasio conserva su UUID, cuentas y datos; el control de acceso continúa en el servidor.

## Comprobaciones

24 pruebas Python, 54 verificaciones de seguridad, 35 de operaciones y 49 contratos RPC / 14 de tablas. La prueba gráfica y comprobación de recursos PE se ejecutan en Windows al compilar; no se afirma haber probado el escritorio del cliente desde el entorno de preparación.

El empaquetado usa las opciones oficiales de [accesos directos de Inno Setup](https://jrsoftware.org/ishelp/topic_iconssection.htm) y la notificación de actualización de [Windows Shell](https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shchangenotify).
