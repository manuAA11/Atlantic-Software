# Validación · 2026-11-26

**Estado actualizado:** la PWA B1 se publicó y verificó; SQL C1 y cambios críticos no desplegados. Ver [RELEASE_STATUS.md](RELEASE_STATUS.md) para fuente, versión, pruebas, reversión y revisiones posteriores.
No desplegado. Estas pruebas no certifican recepción instalada, hardware, tráfico real ni aceptación integral.

Continuación: validación GitHub Actions 45859830145 aprobada para B1. C1 tiene cinco casos adicionales PGlite aprobados directamente con node tests/marketing-idle-gate.test.mjs: veinte ticks vacíos sin HTTP/Vault/escrituras; cualquier feature o regla activa despierta worker; QUEUED futuro/PROCESSING vencido mantienen procesamiento; si falta o cambia el cron de congelaciones conserva invocación previa; contrato, ACL/search_path y rollback conservados. Es una propuesta SQL, sin aplicación en servidores.

| Comprobación | Resultado | Alcance |
|---|---|---|
| node tests/read-flight.test.mjs | 6/6 PASS | Concurrencia 20→1, aislamiento sesión/claims/endpoint/gym/filtros, errores, frescura secuencial, escrituras, logout y vuelo antiguo |
| league/web npm test | 14/14 archivos PASS | PGlite de eventos/admin, acceso socios, bridge, DB, HTTP, jobs, balances, SW estático, renovación e instalación PWA |
| league/web npm run build | PASS | tsc estricto, Vite y SW; 95 módulos; JS 524.362 bytes, gzip 154,09 kB; CSS 6.931 bytes |
| node --test backend/tests/*.test.mjs | 6/6 archivos PASS | Marketing/core HTTP, congelaciones simuladas, planes internos, onboarding, plataforma |
| league npm test | 10/12 inicialmente | Dos fallos del entorno: dependencia PGlite de perfiles no instalada y spawnSync EPERM |
| Repetición de los dos archivos fallidos | 5/5 casos PASS | Tras npm ci con lockfile en Comercial/x86 y permisos de subproceso; training-preflight y training-providers sin modificar tests |
| JSON evidencia / diff | PASS | JSON válido, sin patrones JWT/private key/sb_secret; git diff --check |
| Supabase read-only | PASS | Queries en BEGIN READ ONLY, timeouts 5–8 s; advisors, metadata y logs agregados; sin llamadas funcionales |
| EXPLAIN freezes SELECT | PASS | Sin ANALYZE; índice ya existe; Comercial Index Scan, ZTATTUZ Seq Scan en tabla pequeña |

Advertencia Vite: chunk JS >500 kB y directiva use client de react-router ignorada al empaquetar. No se ocultó warning ni se cambió límite. Pendiente code splitting con prueba de navegador. No se midió bundle anterior con esta misma compilación; no afirmar reducción de bundle.

El primer npm ci web falló por cache npm fuera del sandbox; se completó usando --cache /tmp/atlantic-npm-cache. No se cambiaron versiones ni lockfiles. El runner node --test reporta archivos como unidades; la ejecución directa de read-flight acredita los seis casos.

La mejora 95% (20 lecturas concurrentes idénticas → una transferencia) es sintética: mismo payload compartido entre consumidores. No son bytes de producción ni porcentaje global. Sin despliegue, métrica posterior de producción = no disponible.

## Matriz funcional pendiente de aceptación

| Flujos requeridos | Evidencia local de esta tarea | Pendiente |
|---|---|---|
| Login/logout, auth suspend/resume | HTTP/access y aislamiento del coordinador | Sesión real, reloj/JWT, cambio de cuenta y reanudación en dispositivos |
| Registro/edición clientes, pagos | Esquemas/contratos de proveedores en training fixtures; ninguna operación real | CRUD/pagos completos en staging y compatibilidad con binarios instalados |
| Activación/vencimiento/congelación/reactivación | backend freeze_time y balances fixtures | Límite temporal exacto, dos sesiones PostgreSQL, recepción real |
| Tiqueteras / Staff Pass | Tests internos y balances, no jornada real | Consumo único diario, días locales, suspensión y dos recepciones |
| Huellas / puertas / lector / relé | Sólo inspección, ninguna modificación | Pruebas físicas Windows32/64, identificar/revocar, reconectar USB/COM, suspensión/reanudación y OFF seguro; aprobación explícita |
| Dashboard / recepción | Inspección de código y baseline | Recorrido manual con cuentas de prueba y versión instalada |
| Eventos / clases / reservas / rutinas | Suites PGlite/HTTP con aislamiento de tenant y permisos | Navegador real y teléfonos iOS/Android |
| Rankings / récords | League DB/security existentes PASS | Datos representativos, paginación, carga y comparación visual |
| Push | Jobs/SW/HTTP locales PASS | Entrega y apertura en dispositivos físicos, reintento/expiración real |
| Multi-tenant / retrocompatibilidad | Fixtures comerciales/legacy y key por token/gym | Binarios anteriores reales y sesiones PostgreSQL independientes |
| Backups / rollback | Plan y metadata conservados | Restore cifrado aislado de respaldo actual, no realizado |

No se registró pago, asistencia, reserva, socio ni notificación real para validar esta tarea. Ninguna prueba física puede ejecutarse desde este entorno. Estado final: propuesta B1 validada localmente, despliegue y criterios integrales pendientes.
