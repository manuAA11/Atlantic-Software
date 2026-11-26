# Línea base · 2026-11-26

**Estado actualizado:** la PWA B1 se publicó y verificó; SQL C1 y cambios críticos no desplegados. Ver [RELEASE_STATUS.md](RELEASE_STATUS.md) para fuente, versión, pruebas, reversión y revisiones posteriores.
Captura BD 16:17:18–16:17:21 UTC, sin reset. Logs: 2026-11-25 16:00:00 a 2026-11-26 16:00:00 UTC. No sumar edge_logs con function_edge_logs como si fueran usuarios: son capas y tráfico interno entre servicios.

| Métrica | Comercial | ZTATTUZ |
|---|---:|---:|
| BD bytes | 44.608.659 | 53.302.963 |
| Conexiones en captura | 9 | 10 |
| Deadlocks acumulados | 0 | 0 |
| pg_stat_database.stats_reset | NULL | NULL |
| pg_stat_statements reset UTC | 2026-10-03 03:53:31.868718 | 2026-10-25 00:49:10.896229 |
| Arranque PostgreSQL UTC | 2026-10-03 03:53:53.260867 | 2026-10-25 00:50:50.297655 |
| edge_logs eventos/24 h | 6.183 | 9.171 |
| function_edge_logs eventos/24 h | 1.508 | 1.725 |
| marketing/jobs 200/24 h | 1.438 | 1.439 |
| jobs p50/p95 ejecución ms | 1.488,5 / 3.077,3 | 1.499 / 3.055,1 |
| marketing/jobs Content-Length total | 63.272 | 63.316 |
| gym_fingerprints/24 h | no aparece en top | 1.276 |
| RPC fingerprints acumulado | no aparece en top | 81.310 |
| list_changes acumulado | no aparece en top | 1.369.662 |
| Reglas activas / mensajes | 0 / 0 | 0 / 0 |
| Objetos Storage | 0 | 0 |

p50/p95 aquí son ejecución Edge de logs, no latencia extremo a extremo. Un campo ausente no se interpreta como cero de latencia. Los Content-Length son parciales, pueden diferir de bytes de red comprimidos y no equivalen a Egress facturado. En huellas sólo 3/1.276 respuestas tienen longitud; no estimar bytes desde 201 bytes observados. En BD, los contadores SQL normalizados agrupan acciones y fechas distintas.

ZTATTUZ: memberships 443 filas estimadas, 4.220.648 seq scans; freezes 13, 1.377.003; clients 249, 69.071. Son contadores de trabajo interno. La fecha de arranque no reemplaza stats_reset desconocido de tablas.

## Cron preservado

Comercial: marketing * * * * *, freezes * * * * *. ZTATTUZ: los mismos más notices */5 * * * * y app_clock 0 5 * * * (día Bogotá). Comandos exactos sin secretos en evidence/*.json → detail[0].snapshot.jobs. No se modificó ninguno.

## Repetición comparable

Ejecutar baseline.sql una sola vez al inicio y al cierre de una ventana equivalente de 24–48 h; conservar timestamps, queryids y reset de ambas muestras. Si hay reset/dealloc/cambio de versión, separar series. Comparar deltas por hora abierta, usuarios y dispositivos activos; fines de semana no son control de día laboral. Registrar despliegue y commit del cohort.

Exportar Usage por organización y por proyecto desde [Usage ZTATTUZ](https://supabase.com/dashboard/org/fxrdfzrsxtslwpnuepzw/usage), separando cached/uncached y Database/Auth/Storage/Functions/Realtime/Pooler. Herramientas conectadas no ofrecen ese endpoint; consumo facturable actual NO MEDIDO. No se accedió al Dashboard autenticado.

Medir bytes cliente con Resource Timing/DevTools o transporte instrumentado sin payloads/tokens: action normalizada, bytes, duración y cache/dedupe hit. No sumar bytes de dos capas. Recopilar en fixtures primero y muestra acotada después de autorización. No instalar telemetría ni cron de monitorización en producción en esta fase.
