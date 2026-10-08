# Gym Soft y ZTATTUZ: actualización en desarrollo

Revisión: 8 de octubre de 2026. Este paquete conserva código fuente, migraciones, pruebas y capturas. No es un instalador final. Las versiones permanecen en Comercial 3.6.0 y ZTATTUZ 3.6.1 x86/x64.

## Resultado y límites actuales

Se continuó WhatsApp oficial, automatizaciones, chatbot y Wompi. La congelación y el reloj del gimnasio están integrados en sus motores compartidos, sin una segunda lógica de membresía. Las Edge Functions marketing se desplegaron en ambos proyectos. Las cuatro migraciones nuevas aún no aparecen aplicadas en los servidores: sus comandos no devolvieron respuesta incluso con 120 segundos de espera, y se comprobó después que no había transacciones de migración activas o bloqueadas ni tablas nuevas instaladas. El entorno local se desconectó temporalmente; el acceso se recuperó para guardar este avance.

No se activaron campañas ni se realizaron cobros reales. Las pruebas locales no sustituyen un piloto con Meta, un pago Wompi externo, dos sesiones PostgreSQL reales o el lector/relay físico. No se marca la actualización como terminada.

## Pruebas ejecutadas

| Edición | Etapas datos | Etapas UI | Python | Congelación SQL | Tiempo SQL | Contratos Marketing |
| --- | --- | --- | --- | --- | --- | --- |
| Comercial | 17 PASS | 16 PASS | 132 PASS | 52 PASS | 55 PASS | 90 PASS |
| ZTATTUZ x86 | 16 PASS | 17 PASS | 147 PASS | 52 PASS | 55 PASS | 87 PASS |
| ZTATTUZ x64 | 16 PASS | 17 PASS | 148 PASS | 52 PASS | 55 PASS | 87 PASS |

Las suites completas suman 99 etapas PASS. Los casos de Python y SQL están incluidos en esas etapas; las columnas no deben sumarse como casos únicos. Backend compartido: 54 tests PASS en cada edición. Los últimos cambios afectados se volvieron a verificar: contratos Marketing 90/87, ocho pantallas Marketing 76 comprobaciones por edición, congelación UI 48 comprobaciones y pipeline SQL 55. Los resultados JSON y sus logs se conservan en evidence/tests; los rechecks finales están en evidence/tests/rechecks.

Los ensayos de SQL usan PGlite. Promise.all comparte una sesión de ese motor y no acredita dos PCs concurrentes. La huella y el relé se prueban con adaptadores simulados. Los smoke tests de Tk se ejecutan en Linux con pantalla de prueba, incluso los que se llaman windows_ui_smoke; la compilación y ejecución Windows físicas siguen pendientes.


Migraciones, proveedores, concurrencia real y hardware pendientes. No generar builds finales.
