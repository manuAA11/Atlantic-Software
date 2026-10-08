# Multi-Gym: cierre de recuperación, 8 de octubre de 2026

**Estado: desarrollo recuperado, pruebas automáticas aprobadas; actualización final pendiente de aceptación externa y recursos Windows.** Este informe sustituye las afirmaciones de estado del informe histórico, que se conserva como evidencia de aquella ejecución.

## Recuperación verificada

El ZIP original se conserva fuera del checkout, con SHA256 `28ed79ae1d1a9d67c2612e3a44f6b5dc5d845b1c77b59e81dfe4abec0e4ea19b`. Se importaron todas sus fuentes de Comercial 3.6.0 y ZTATTUZ 3.6.1 x86/x64 a Git. El primer checkpoint se publicó en main como `abe9dda6063c7dda10966cbb45d0674ea6762a6f`.

Se compararon fuentes originales, manifiestos/evidencias adjuntas y el historial accesible de los chats anteriores. Los cuatro scripts de migración originales mantienen sus bytes. Un documento de estado ya difería del manifiesto dentro del ZIP original; no se considera un cambio perdido de código.

Del hilo `01a1195a-6aa3-7056-a174-ffd75dd140d7` se recuperaron cambios posteriores al ZIP:

- Turno `01a11cb7-12ca-735d-98f0-b7815a9d679d`: resolución de `extensions.gen_random_bytes` y generador de migración correctiva del scheduler.
- Turno `01a11cc2-48af-717e-9838-1b3d5d3fcbf2`: rutas del gateway Edge, dos regresiones HTTP adicionales, índices de Marketing/congelación y script completo de pruebas aisladas de concurrencia PostgreSQL con sus tres correcciones posteriores.

Los dos archivos de evidencia remota del último turno se recibieron truncados. Sus fragmentos y procedencia están en `evidence/history-recovered-20261008.json`; no se reconstruyeron inventando contenido. Esos fragmentos registran migraciones/cron y concurrencia posteriores al informe adjunto, pero no acreditan una consulta actual de esos servidores. **No se puede garantizar que el material disponible contenga cada byte del último entorno perdido.** Los cambios reconstruibles identificados fueron conservados.

## Ediciones y sincronización

- **Atlantic Gym Comercial 3.6.0:** Administrador, Recepción y panel privado del propietario; licencias, suscripciones, invitaciones y equipos aprobados son exclusivos de Comercial. Se conserva su ausencia de relé/apertura de puerta.
- **Atlantic Gym · ZTATTUZ 3.6.1 x86/x64:** Administrador y Recepción, compatibilidad con la base ZTATTUZ anterior y control del relé. La arquitectura del loader nativo, Python/build e instalador se conserva por edición.
- Backend, UI Kit, iconos y nuevas correcciones compartidas sincronizados: 30 comparaciones de archivos PASS; 30 de 44 módulos Python con el mismo nombre son idénticos en las tres ediciones. Las diferencias de app/cloud/licencia, arquitectura y puerta se conservan. El inventario completo está en `evidence/closure-validation-20261008/parity.json`.

## Atlantic UI Kit, branding e iconos

Políticas permanentes en `AGENTS.md`, especificación en `docs/ATLANTIC_UI_KIT.md` y tokens compartidos en `common/atlantic_ui.py`, copiados a cada edición independiente. Se conservan el diseño oscuro aprobado, navegación, tarjetas, formularios, diálogos, inputs, estados y componentes existentes. La fuente es nativa: Segoe UI en Windows, system en macOS; no se distribuye SF Pro.

Administrador utiliza el G azul y Recepción el G cian de la referencia aprobada. Se recrearon assets aislados de la lámina visible: no son los archivos maestros originales ni recortes exactos. La procedencia está en `assets/atlantic/README.md`. Se aplican a ventanas principales, login/diálogos, selección del icono PyInstaller, metadatos PE y recursos/accesos directos de los futuros instaladores. Firma discreta: `© Atlantic Tech Software — All rights reserved. By Manuel Cuellar`. IDs, nombres técnicos y directorios de actualización se conservan.

Se corrigieron el desbordamiento de la barra lateral al 125 % y un icono de acceso directo de Recepción declarado pero no instalado en Comercial. Las pruebas Tk y recursos de instaladores pasan; la compilación del PE e instalación efectiva se verifican en Windows.

## Funciones recuperadas

Congelación por siete días, extensión de vencimiento, una por membresía salvo excepción con motivo, denegación de acceso mientras está congelada, reactivación y conservación de cupos permanecen en el servidor. Las tiqueteras descuentan una vez por día del gimnasio. Las pruebas cubren límites de fecha, cancelación, excepción y renovación durante congelación.

Calendario DATE, instantes TIMESTAMPTZ, zona del gimnasio y America/Bogota de ZTATTUZ se conservan. Importación, auditoría y presentación no inventan horas de medianoche. Scheduler, recordatorios y chatbot consultan estados del servidor. La nueva migración del scheduler es aditiva; no reescribe la original.

WhatsApp, chatbot, automatizaciones y Wompi tienen pantallas conectadas al backend, autorización, Vault, consentimiento, verificación de identidad, firma de eventos, reintentos/estados y operaciones idempotentes. La prueba adicional conecta el handler HTTP y estas funciones con SQL migrado: pregunta por membresía, verifica identidad, informa congelación, genera enlace y aplica un pago firmado sin renovación duplicada. Meta/Wompi y Vault son fixtures de esa prueba. **Las integraciones no se declaran terminadas sin el piloto real.**

El actualizador manual de Marketing fallaba al reaplicarse por políticas y triggers existentes. Se corrigieron los scripts compartidos/de las tres ediciones; el generador conserva migraciones históricas. La prueba adicional de recompilación/reaplicación pasa. Se debe respetar el orden de actualizaciones; no reaplicar un script antiguo después de uno nuevo que redefine funciones.

## Pruebas de esta instancia

Python 3.13.5, Tk 8.6.16, Node 24.19.0 y PGlite 0.5.8. Dependencias instaladas con lockfiles; setup repetido y arranque de display con Tk comprobados. No se usaron datos ni cobros reales.

| Edición | Etapas datos | Etapas gráficas | Total etapas | Tests Python | Tests backend | Congelación SQL | Tiempo SQL | Marketing SQL | Flujo HTTP/SQL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Comercial | 20 PASS | 18 PASS | 38 PASS | 132 PASS | 56 PASS | 52 PASS | 55 PASS | 90 PASS | 28 PASS |
| ZTATTUZ x86 | 19 PASS | 19 PASS | 38 PASS | 147 PASS | 56 PASS | 52 PASS | 55 PASS | 87 PASS | 28 PASS |
| ZTATTUZ x64 | 19 PASS | 19 PASS | 38 PASS | 148 PASS | 56 PASS | 52 PASS | 55 PASS | 87 PASS | 28 PASS |

**114 etapas aprobadas y 427 pruebas Python.** Las columnas internas están incluidas en las etapas y no se suman como casos únicos. El backend es compartido; sus 56 tests se ejecutan por edición. Se ejecutaron contratos, migraciones, seguridad, permisos, clientes/pagos, importación, huellas, simulación de jornada, fechas/logs, freeze, tiqueteras, Marketing, pruebas gráficas y branding.

El primer run completo detectó iconos ausentes y desbordamiento gráfico. Se conserva su resultado FAIL. Tras corregirlos se repitió Python y toda la UI, además de las suites SQL afectadas y comprobaciones nuevas. El resumen final combina estos resultados explícitamente y enlaza cada log: `evidence/closure-validation-20261008/summary.json`. No se borraron ni transformaron los FAIL originales en PASS.

## Bloqueos concretos y entrega

1. El proxy de esta instancia bloqueó las consultas públicas de health a ambos Supabase antes de llegar al servicio. Las dos entradas de red se guardaron en el borrador del entorno; necesitan aplicación/publicación desde su configuración y una nueva comprobación de conexión.
2. No hay cuentas/número Meta ni Wompi Sandbox disponibles aquí para acreditar los pilotos. La habilitación de plataforma, conexión desde la app y prueba conjunta están detalladas en `docs/INTEGRACIONES_Y_WINDOWS.md`. Los secretos se introducen únicamente en el host/Vault o formulario privado; no por chat.
3. Falta el árbol autorizado `DigitalPersonaRuntime/setup.exe` con sus archivos para las arquitecturas correspondientes; fue excluido del ZIP. Hace falta el paquete completo original o el redistribuible autorizado del proveedor.
4. Falta validar Windows, lector real y relé ZTATTUZ, así como aceptación de la versión y concurrencia/scheduler contra el servidor actual. La evidencia histórica parcial no sustituye esa validación.

Se comprobaron respaldos extraídos en carpetas independientes: imports aislados y flujo HTTP/SQL PASS, instalando node_modules en cada una. Los hashes de las fuentes runtime coinciden con el checkout; evidencia en `evidence/closure-validation-20261008/independent-backups.json`.

Se preparan respaldos independientes de las **fuentes en desarrollo** de Atlantic Gym y ZTATTUZ, con fuentes recuperadas, nuevos assets, tests, requirements, migraciones, .env.example y guías. No contienen venv/node_modules ni recursos Windows ausentes; las dependencias se instalan con sus manifests. No se entregan como paquetes finales completos ni contienen instaladores. `release_readiness.json` conserva los criterios externos pendientes. Las instrucciones de build exactas y procedimientos de aceptación están en la guía enlazada.

El entorno de desarrollo Linux/Tk/PGlite está comprobado. `install_script` y `start_skill` se guardaron como borrador; esa persistencia no equivale a publicar el snapshot ni valida una máquina futura. El usuario debe revisar/publicar en la configuración del entorno para conservarlo.
