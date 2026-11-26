# Respaldo y reversión

**Estado actualizado:** la PWA B1 se publicó y verificó; SQL C1 y cambios críticos no desplegados. Ver [RELEASE_STATUS.md](RELEASE_STATUS.md) para fuente, versión, pruebas, reversión y revisiones posteriores.
Base de desarrollo: pruebas 347dbcbc95613816c7edd7c806a1884f63b975f4. Main independiente: 9c2d175adb32ebb4ae34624f2a578eacc35c4953. PR #2 integrado en pruebas como b11487ad8ed20637f3a55e8a145fc797050a3c71; ninguna migración aplicada en producción.

Actualización: B1 publicado en rama optimization/supabase-20261126, PR #2. El usuario confirmó ausencia de respaldo. C1 permanece bloqueado para producción. Propuesta y rollback de función en proposals/marketing-idle-gate*.sql, validados con cinco pruebas locales. No son respaldo de la base ni migración aplicada. Antes de aplicar, además del respaldo restaurado, comprobar en vivo owner/ACL y que el cron de congelaciones y su usuario siguen operativos.

## Estado de respaldo

La documentación de Free no garantiza backups diarios/PITR de planes pagos. Directorios backups/recovery contienen material histórico; no se ha probado que restauren las BD actuales. Los snapshots aquí son metadata, no respaldo de clientes. Ninguna operación de riesgo está habilitada por su existencia.

Antes de SQL de riesgo: obtener backup cifrado fuera del repositorio público, registrar fecha/ref/checksum/retención, incluir roles/grants/funciones/cron y objetos privados pertinentes; restaurar aislado y comprobar recuentos/constraints/tenant y contratos. Evitar exportar credenciales Vault a docs. Storage requiere copia independiente. No probar restore en producción.

## Revertir esta rama

En un commit futuro, git revert <commit-de-optimización> sobre desarrollo y ejecutar build/tests antes de publicación autorizada. Hoy, revisar git diff y retirar sólo cambios de esta tarea: api.ts vuelve a la base, eliminar read-flight.ts y su test; documentación puede conservarse. No usar reset --hard ni limpiar archivos ajenos.

No hay rollback SQL que ejecutar en producción porque no hubo cambios allí. Baseline conserva schedule, jobid, jobname, command y active de los cuatro jobs ZTATTUZ y dos Comercial, sin secretos. Capturar definición exacta de la función inmediatamente antes de un cambio autorizado; detener si drift desde auditoría.

Para un eventual gate: restaurar definición y grants/search_path/owner exactos en transacción con timeout/lock timeout; validar hashes y cron. Para schedule: cron.alter_job sólo tras volver a validar jobid+nombre+proyecto y usar schedule previo; no recrear jobs a ciegas ni duplicarlos. La propuesta SQL de C y su rollback están preparados en proposals/, pero no deben aplicarse sin respaldo restaurable verificado.

Para PWA publicada en el futuro: conservar artefacto anterior y su manifest/SW, publicar rollback como versión nueva para invalidar shell coherentemente; verificar auth y rutas al reabrir. No borrar almacenamiento de sesiones ni colas offline. No tocar plantillas biométricas, historial o configuración de lector/puerta.

## Disparadores para detener piloto

Error de acceso válido, revocación ignorada, cambio de saldo/pagos, contaminación entre gimnasios, duplicación de mensaje/cobro, pérdida de push, aumento sostenido de errores/p95 o backlog. Detener progresión, restaurar sólo componente cambiado y verificar función crítica; no reiniciar servidores como remedio genérico.
