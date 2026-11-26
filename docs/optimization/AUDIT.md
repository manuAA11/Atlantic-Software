# Auditoría Atlantic · 2026-11-26

**Estado actualizado:** la PWA B1 se publicó y verificó; SQL C1 y cambios críticos no desplegados. Ver [RELEASE_STATUS.md](RELEASE_STATUS.md) para fuente, versión, pruebas, reversión y revisiones posteriores.
Fase A de solo lectura completada para las fuentes accesibles. Auditoría integral aún abierta: Egress facturable, CPU/RAM, instalaciones y hardware requieren evidencia adicional. No hubo escrituras en Supabase, borrado, reinicio, despliegue ni reset de estadísticas. No se consultaron plantillas, secretos Vault ni datos personales. Capturas agregadas en `evidence/`.

## Correspondencia comprobada

Organización ZTATTUZ `fxrdfzrsxtslwpnuepzw`, plan Free confirmado por API. Ambos proyectos ACTIVE_HEALTHY, us-east-1, PostgreSQL 17.

| Proyecto | Uso demostrado en código | Versiones/fuentes |
|---|---|---|
| bawrakwhzkxmhmgkczqu | Comercial, Atlantic Core, directorio central League | Configuración Comercial y Core de ambos perfiles ZTATTUZ |
| srmquhwpawgipncmvfjf | ZTATTUZ x86/x64, League y servicios de socios | Configuración de ambos perfiles y Edge Functions alojadas |

Repositorio canónico `manuAA11/Atlantic-Software`: main `9c2d175adb32ebb4ae34624f2a578eacc35c4953`; desarrollo pruebas `347dbcbc95613816c7edd7c806a1884f63b975f4`. Rama local autorizada `optimization/supabase-20261126`, basada en pruebas. `ztattuzapp` `8a3a729542f589f8c1d4675bc43f718e5f2b0edd` es escritorio Python histórico, no la PWA. No se modifica.

Según `docs/LEAGUE_ENTREGA_20261123.md`, escritorio 3.8.9 opcional proviene de d8c3bc17f4658daff7a6a2c034db03b430431fcc; web publicada de 09e454ba2e1870b6ee74e4e0991b7225e169c0de en Cloudflare Workers. Es evidencia documental, no comprobación actual del binario instalado ni del despliegue HTTP. Main no incluye League: no usarlo como fuente única. Revisar manifiestos y hash de cada PC antes de compatibilidad final.

## Hallazgos confirmados

1. `private.marketing_cron_tick()` hace HTTP incondicional si está configurado. En ambos proyectos: WhatsApp, chatbot, automatizaciones y pagos deshabilitados, cero reglas activas y cero mensajes en la captura. ZTATTUZ conserva siete reglas deshabilitadas. La ventana de 24 h registra 1.438/1.439 jobs y aproximadamente cuatro RPC por job. Causa: no hay comprobación de trabajo antes de HTTP. `backend/core/worker.mjs:runJobs` además completa congelaciones, ya atendidas por cron SQL. No basta con comprobar cola vacía: preservar reglas temporales, eventos, leases, pagos y PROCESSING vencidos.
2. `common/fingerprint_service.py` sincroniza cada 15 s; `fingerprint_store.py` usa acción list. La definición SQL alojada devuelve todas las plantillas base64 y revisiones del gimnasio tras verificar usuario/rol. 1.276 RPC/24 h; 81.310 llamadas acumuladas. Otras acciones comparten queryid: no atribuir todas a list. No se descargó ninguna plantilla. Memoria local, no archivos crudos. No modificar frecuencia, revocaciones ni algoritmo en fase B.
3. `membership_freezes`: índice parcial `freezes_due` ya existe en ambos. EXPLAIN sin ANALYZE: Comercial usa índice, ZTATTUZ seq scan con coste 1.12 para tabla diminuta. No justifica nuevo índice. La causa exacta de millones de scans de memberships aún requiere planes bajo roles reales y correlación temporal.
4. ZTATTUZ no tiene el índice `(gym_id,client_id,end_date DESC)` que sí tiene Comercial. Es candidato, no recomendación automática; faltan planes representativos y selectividad.
5. Realtime publica 13 tablas públicas en ZTATTUZ y tres en Comercial. El listener común escucha solo gym_events filtrado por gimnasio, evita start duplicado y cierra canales/socket; backoff sin jitter. list_changes es trabajo interno, no mensajes enviados ni Egress. No reducir publicación sin inventario de clientes históricos.
6. PWA `league/web/src/main.tsx`: refresh en montaje, cambio de gimnasio, online y visibilitychange. React StrictMode y eventos próximos pueden solapar lecturas. `Routines.tsx` carga tres lecturas al montar y contentVersion las reinicia. Hay guardas para no aplicar respuestas antiguas, pero no evitan transferencias duplicadas. La frecuencia real de duplicación no está medida.
7. Auth: cliente único por módulo web; escritorio usa managed_client con renovación central y cliente async separado para socket sin refresh token. get_session en listener cada segundo no demuestra HTTP cada segundo. 69 /auth/v1/user y seis /auth/v1/token en ZTATTUZ/24 h; sin evidencia de tormenta de renovación en esta ventana.
8. Storage: cero objetos en ambas capturas. Service worker sólo cachea shell/estáticos versionados del mismo origen, excluye autorización y query string. Push conserva mensaje genérico. No hay evidencia de Egress Storage significativo. Recursos Cloudflare ya externos a Supabase.

## Advisors y seguridad

Ver detalles en snapshots. Comercial: 91 funciones definer ejecutables authenticated; ZTATTUZ: 75 y tres anon. Esto exige revisar autorización interna, no revocar en bloque. RLS enabled/no-policy (35/39) incluye tablas privadas con denegación por defecto; no equivale a exposición. Protección de contraseñas filtradas deshabilitada y extensión en public en ambos. Sin cambios de seguridad en esta tarea.

Rendimiento: FK sin índice 18/30; índices sin uso 54/69; políticas permisivas múltiples 4/7; Comercial dos auth_rls_initplan. No eliminar índices por contador cero ni consolidar políticas sin probar semántica de roles.

[Guía Advisors](https://supabase.com/docs/guides/database/database-linter), [definer anon](https://supabase.com/docs/guides/database/database-linter?lint=0028_anon_security_definer_function_executable), [definer authenticated](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable), [auth initplan](https://supabase.com/docs/guides/database/database-linter?lint=0003_auth_rls_initplan), [password security](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## Inventario y límites

Snapshots metadata: tablas/tamaños/RLS, firmas de todas las funciones public/private/league_member_private, triggers, políticas, índices y estadísticas. Snapshot principal: cron actual sin secretos, Edge summaries, top statements, publicaciones, colas, Storage y logs agregados. Fuente SQL de marketing, freezes y huellas inspeccionada; fuentes alojadas de marketing, members y jobs recuperadas para revisión. Contratos de otras RPC inventariados pero no todos auditados línea por línea. No se invocaron RPC operativas.

Pendientes: bytes reales de huellas (Content-Length ausente en 1.273/1.276), Egress diario/mensual oficial por servicio, CPU/RAM, conexiones por cliente, backups recuperables, retención logs completa, versiones instaladas, tráfico móvil representativo, pruebas físicas y bajo múltiples sesiones reales. Los logs agregados no son factura ni cobertura garantizada.

## Documentación vigente consultada

Changelog oficial descargado 2026-11-26: CLI v3 local por defecto, config.jsonc desde 3.4, merge de ramas exige permiso producción; no se usó CLI ni ramas de BD. Sin cambios SDK ni upgrade de PostgreSQL. [Egress](https://supabase.com/docs/guides/platform/manage-your-usage/egress): Free 5 GB uncached y 5 GB cached independientes por organización. [Backups](https://supabase.com/docs/guides/platform/backups): Free requiere exportaciones propias; archivos Storage no están en backup BD. No se ha verificado un respaldo restaurable.
