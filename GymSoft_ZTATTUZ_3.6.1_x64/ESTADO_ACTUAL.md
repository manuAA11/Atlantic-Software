# Atlantic Gym · ZTATTUZ 3.6.1 x64: estado actual

Estado revisado el **9 de octubre de 2026**. Administrador y Recepción están recuperados, con Atlantic UI Kit, iconos G azul/cian, control del relé y Runtime DigitalPersona x64 original completo. Se conserva el loader de 64 bits y la compatibilidad con la base ZTATTUZ anterior.

Hay correcciones y actualizaciones SQL posteriores a los LEEME históricos. Consulta [estado y evidencia](../docs/ESTADO_CIERRE.md) y [configuración e instalación](../docs/INTEGRACIONES_Y_WINDOWS.md) antes de seguir instrucciones antiguas.

## Crear e instalar

1. Extrae el paquete de aplicación completa en una carpeta nueva, conservando las carpetas de esta edición, `tools` y `docs`. El SDK ya está recuperado; MSI, CAB, bootstrapper y EULA están incluidos en la aplicación.
2. En el PC que compila, instala **CPython 3.14 o 3.13 estándar de 64 bits**, Node LTS e Inno Setup 6. Ejecuta **`CREAR_INSTALADORES.bat`**. Prepara el entorno y las dependencias; si falta aceptación final, repite todas las pruebas y compila los instaladores para configuración.
3. Abre `salida/PRUEBAS_PARA_CONFIGURAR/<identificador>/LEER_PRIMERO.txt` y ejecuta el instalador `VALIDACION_NO_FINAL_…`. El instalador completo incluye Administrador y Recepción; **COMPONENTES** conserva los instaladores individuales. Configura COM/relé desde la aplicación. El PC donde instalas los programas no necesita Python, Node ni Inno. WhatsApp/Wompi se conectan desde Administrador después de habilitar el backend según la guía.

Una prueba o compilación fallida detiene la publicación de una nueva entrega. El modo de configuración conserva autenticación y permisos, y no cambia `release_readiness.json`. El aviso `Entrega bloqueada. Falta comprobar: …` indica aceptación final pendiente; el batch actualizado continúa por el modo de configuración. La entrega final se genera únicamente con evidencia válida para todos sus criterios aplicables.

## Abrir desde fuentes y alcance comprobado

Puedes ejecutar `INICIAR_ADMINISTRADOR.bat` o `INICIAR_RECEPCION.bat`.  La configuración pública está recuperada. `PREPARAR_PYTHON.bat` conserva una `.venv` incompatible como respaldo y crea otra sin cambiar esa configuración. No guardes claves privadas de Meta/Wompi ni service_role en el escritorio.

El run Windows `37998368137` aprobó las 37 etapas actuales de cada edición y la creación mediante el `.bat` real, con diagnósticos e iconos PE verificados. ZTATTUZ x64 comprobó instalación nueva de los componentes, actualización mediante el instalador completo y desinstalación. Las comprobaciones actuales de disponibilidad del backend y conexión pública se conservan en `../evidence/live-health-20261009.json` y `../evidence/network-diagnostic-20261009`. Continúan pendientes los pilotos de cuentas reales y el lector/relé físico de una instalación nueva. El código de huella que ya funcionaba se conserva.
