# Plan priorizado y registro de decisiones

**Estado actualizado:** la PWA B1 se publicó y verificó; SQL C1 y cambios críticos no desplegados. Ver [RELEASE_STATUS.md](RELEASE_STATUS.md) para fuente, versión, pruebas, reversión y revisiones posteriores.
No desplegado. La reducción global de Egress 40–70% es un objetivo condicionado; actualmente no demostrada.

Continuación: autorización de envío recibida, PR #2 publicado y validación de B1 aprobada en GitHub. C1 ahora dispone de SQL propuesto y rollback en proposals/, con cinco pruebas de comportamiento PGlite. Usuario confirmó que no tiene respaldo; SQL productivo y cambios críticos permanecen bloqueados. La propuesta conservadora no cambia intervalos ni reduce revalidaciones de acceso: con cualquier feature/regla activa o mensaje QUEUED/PROCESSING invoca el worker original. No requiere ni introduce clientes/API nuevos.

| ID / problema | Evidencia y causa raíz | Solución / archivos | Impacto / complejidad / riesgo | Antes → después | Ahorro | Pruebas / dependencias / reversión |
|---|---|---|---|---|---|---|
| B1 lecturas simultáneas PWA | Routines montaje + refresh, StrictMode y eventos; sin coordinador de transporte. Duplicación real pendiente | read-flight.ts, api.ts; allowlist de cuatro lecturas no críticas, sólo en curso | Bajo a medio según concurrencia / baja / bajo | Fixture 20 transportes → 1; producción sin cambio | 95% solicitudes y payload en fixture idéntico; global desconocido | seis pruebas de comportamiento y build; sin BD. Revertir ambos archivos y test |
| C1 marketing vacío | Tick alojado HTTP sin gate, flags apagados, 0 mensajes/reglas activas; 1.438/1.439 jobs/día | Preparar gate SQL dentro de private.marketing_cron_tick antes de Vault/HTTP | Alto en invocaciones / media / moderado | ~2.877 jobs/día ambos → potencial 0 mientras sin trabajo | Hasta 86.310 jobs/30 días y ~345.240 RPC en escenario actual; no ahorro de GB demostrado | Respaldo restaurado, fixtures, concurrencia y plan medido. Restaurar función exacta capturada |
| C2 intervalos | Cron cada minuto, notices cada 5 | Evaluar marketing 15 min sólo si latencia de reglas lo admite; no es decisión implementada | Alto invocaciones / media / moderado | 1.440 → 96/día por proyecto en escenario sin gate | 93,3% jobs teóricos, no sumar con C1 | Reglas a hora exacta, lotes/backlog, leases. Restaurar schedule por jobid validado |
| C3 duplicación freezes | runJobs ejecuta RPC completa además de cron local | Revisar eliminación de segunda pasada; mantener cron 1 min y guardas de acceso | Medio API / media / crítico por dependencia temporal | ~1.435–1.439 RPC/día por proyecto → potencial 0 desde marketing | Estimación de llamadas, no ingreso autorizado | Probar límites de tiempo, estado servidor, importación y carreras. Restaurar worker y función |
| C4 memberships SQL | ZTATTUZ sin compuesto que Comercial sí tiene, muchos scans acumulados | Planes bajo RLS y rol real antes de decidir índice; public/private SQL | Indeterminado / media / moderado | No medido → no medido | No cuantificado | Datos representativos, backup, no ANALYZE de RPC que escriben. Índice nuevo sólo concurrente con ventana validada; rollback sin bloquear |
| C5 Realtime | 13 tablas publicadas, listener común gym_events, backoff sin jitter | Mapear versiones históricas, invalidación por entidad y jitter; common/realtime_listener.py, ui_performance.py | Medio / media / moderado | bytes/reconexiones pendientes | No cuantificado | Sesiones múltiples, suspensión, notificaciones; restaurar listener/publicación exportada |
| D1 huellas completas | list full, worker 15 s; 1.276 RPC/día | RPC v2 opcional delta con cursor monotónico, tombstones, snapshot consistente, hash e instancia/tenant; clientes viejos conservan v1 | Potencial alto bytes / alta / crítico | bytes desconocidos → pendiente | No afirmar porcentaje | Hardware x86/x64, revocación sin ventana adicional, cifrado/aislamiento, borrado y recuperación full. Feature flag opt-in y vuelta v1; aprobación explícita |
| B futura payload/listados | select(*) escritorio, list_clients completo | Ver consumidores/campos, medir payload, API paginada nueva compatible; common/cloud_database.py | Potencial medio / media / moderado | Sin medición | No cuantificado | Contrato viejo intacto, totales y filtros cross-tenant; no cambiar a ciegas |
| PWA bundle | build 524,36 kB JS, gzip 154,09 kB | Evaluar lazy loading Routines/Profile manteniendo rutas y SW; league/web/src | Mejora carga / baja-media / bajo | Baseline previa no medida → build de rama | Cloudflare, no atribuir a Supabase | Browser offline/update iOS/Android antes de desplegar |
| Seguridad Advisors | definer anon/authenticated, RLS, password checks | Revisión individual de guards/grants, no revocación masiva | Seguridad / alta / moderado | Sin cambios | No aplica | Gates por rol/gym y compatibilidad; rollback DDL exacto |

## Gate de marketing a preparar y probar (no aplicado)

Excluir HTTP sólo si no existe trabajo que requiera worker: mensajes QUEUED vencidos, PROCESSING caducados que deben pasar UNCERTAIN, reglas temporales habilitadas y operables aunque cola esté vacía, eventos pendientes, leases y pagos con reglas pendientes. No limitarse a EXISTS(marketing_messages). Mantener SQL de congelaciones 1 min y validación síncrona en acceso. Primera versión conservadora puede despertar ante cualquier regla habilitada, aunque aún no venza: ahorro menor, semántica más fácil de preservar.

Probar activación desde todos los flujos, nuevas reglas/gimnasios, importación, reloj/timezone, lease expirado, HTTP timeout, simultaneidad y backlog >100. Locks transaccionales evitan enqueue simultáneo, pero no protegen toda la vida de una ejecución Edge: mantener claims/leases. No introducir reenvío automático de mensajes UNCERTAIN a Meta. Backoff+jitter sólo en errores transitorios seguros; conservar idempotency keys de pagos/eventos.

## Caché por clase de dato

Estáticos públicos: assets versionados/hash y Cache-Control, shell SW existente; branding/config por gym con versión. Operativos: sólo lectura no crítica, TTL corto a definir por pantalla e invalidación tras escritura/Realtime; key endpoint+gym+usuario+claims, limpiar logout/cambio de cuenta. B1 implementa únicamente deduplicación concurrente en memoria, sin TTL ni almacenamiento de respuestas.

Críticos: membresías, autorizaciones, revocaciones, biometría, permisos, congelaciones y tiqueteras siempre servidor según garantías actuales; sin nueva política offline. No sustituir getUser servidor/RLS por getSession local. No compartir cache autenticada en CDN/SW.

## Producción y aceptación

Antes de C/D/E: copia recuperable verificada (incluyendo contenido privado cifrado fuera del repo), restauración aislada, hashes versiones instaladas, fixtures compatibles y hardware. Sin respaldo verificable quedan detenidas operaciones de riesgo. Presentar diff, resultados y rollback; autorización de producción independiente de esta rama. Piloto gradual y monitorización comparable 24–48 h. No instaladores finales ni ampliación del piloto.

Criterios pendientes: pruebas funcionales integrales, bytes facturados y reducción real, latencias críticas iguales o mejores y aceptación física. Cero pérdida funcional no se certifica sólo con tests sintéticos.
