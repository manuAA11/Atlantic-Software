# Publicación de la optimización web · 2026-11-26

## Activo

PWA publicada en https://atlantic-league.atlanticsoftware11.workers.dev, mismo Worker y cuenta, mediante autorización explícita del destino y login temporal por dispositivo. Cloudflare versión **ebcceb44-914d-4b8c-9fd6-fad2b8bfeb17**. Sesión cerrada con éxito después de verificar.

[PR #2](https://github.com/manuAA11/Atlantic-Software/pull/2) integrado en pruebas como **b11487ad8ed20637f3a55e8a145fc797050a3c71**. Fuente funcional **1f7b8e41c2b28c3b646f4cacddccc68575223e41**, mismo árbol que el merge. Main no fue actualizado. Los cambios de esta publicación se prepararon en la rama de optimización y pasaron validaciones antes del merge.

Única mejora funcional activada: compartir lecturas no críticas simultáneas de rutinas, catálogos y configuración push. Sólo memoria durante la solicitud, sin cache persistente ni TTL; separación por endpoint, token y gimnasio. Se preservan contratos, interfaz y servidor de autorización.

Sin cambios en Supabase SQL, cron, RLS, funciones Edge, frecuencias, escritorio, membresías, pagos, biometría o relé. No hay nuevos instaladores de escritorio. La ausencia de modificaciones críticas no constituye prueba física de equipos instalados.

## Validación

- 53 casos web locales aprobados (incluidos seis de B1 y cinco del SQL candidato C1); build TypeScript/Vite aprobado.
- [PWA PR 45860536150](https://github.com/manuAA11/Atlantic-Software/actions/runs/45860536150): PASS.
- [PWA merge 45860940706](https://github.com/manuAA11/Atlantic-Software/actions/runs/45860940706): PASS.
- [Paquete Cloudflare 45860940610](https://github.com/manuAA11/Atlantic-Software/actions/runs/45860940610): PASS de validación; esa ejecución no publicó por no ser commit release. La publicación autorizada se ejecutó con Wrangler 4.136.3 en el entorno cloud.
- [Integración aislada 45860940879](https://github.com/manuAA11/Atlantic-Software/actions/runs/45860940879): PASS, incluidos PostgreSQL concurrente, restauración de fixtures, bundles iOS/Android y navegador.
- Verificación HTTPS posterior: HTML, JS y SW coinciden byte por byte con la compilación publicada. Rutas SPA/auth, iconos/manifiesto, headers SW, CORS del origen autorizado, rechazo de origen ajeno y snapshot sin credenciales = 401: PASS.
- El verificador original necesitó NODE_USE_ENV_PROXY=1 en este entorno; el intento con HTTPS directo dio ECONNREFUSED. Se conservó el proxy y las mismas aserciones; no se desactivó TLS ni controles de seguridad.

La web previa se descargó antes del deploy y su bundle coincide exactamente con la recompilación de la base:

| Artefacto | Antes | Después |
|---|---|---|
| JS | index-DPRvNjcy.js | index-Ct5z0QrF.js |
| Bytes JS sin comprimir | 524.351 | 524.857 |
| SHA256 JS | 38bafcbbda8482947edaa0b89a0e7f28a2e19173a1ea2121f9191c735db94dd8 | 9123db47765e945f835ee592d7f84d0bfd00215efbde7a7d8f588a99fe62d433 |

El bundle aumenta 506 bytes por el coordinador; esta mejora reduce solicitudes duplicadas, no el tamaño de JavaScript. Recursos alojados en Cloudflare, no atribuir sus bytes a Supabase. Ahorro Egress de producción aún sin medir; 20→1 transportes es exclusivamente fixture concurrente.

## Reversión

Copia anterior descargada en /workspace/Atlantic_League_preoptimization_20261126.zip, SHA256 0daeee7901a9694b90695f53108187a9a28488f1d99ec28a1aa5d7e84c9ce0ab. Paquete nuevo en /workspace/Atlantic_League_optimization_20261126.zip, SHA256 fe24cfd2a11a5f60ffbb4b18f134f672da6ae143a3da4d6c362c02b5ee28a925. Son archivos del entorno para descarga, no backups de la BD ni artefactos subidos a GitHub.

Para revertir B1: revertir el commit funcional en desarrollo, compilar con la configuración pública vigente, validar y publicar como versión nueva. Alternativamente republicar el artefacto anterior con el Worker estático y headers anteriores, conservando el origen. Comprobar HTML/SW/bundle y auth después. No borrar sesiones/colas del usuario ni intervenir Supabase.

## Pendiente y bloqueado

El usuario confirmó que no hay respaldo de Supabase. C1 está preparado y probado en proposals/marketing-idle-gate*.sql, sin instalar. Shadow query de sólo lectura a las 16:42 UTC dio would_skip_http=true en ambos proyectos. Falta respaldo cifrado recuperable restaurado en aislado antes de cualquier cambio SQL de riesgo.

La prueba propuesta de C1 no cambia reloj ni intervalos: se omite HTTP sólo con flags/reglas apagados, ausencia de QUEUED/PROCESSING y cron separado de congelaciones activo por minuto. Con trabajo/flags activos o cron modificado vuelve al comportamiento previo. No añade reintentos de mensajes UNCERTAIN. ACL y search_path se conservan. Falta prueba bajo múltiples sesiones reales y revisión previa de drift/usuario del cron.

Biometría incremental, índices y SQL/RLS, cambios Realtime y otras optimizaciones del plan continúan pendientes según riesgo/evidencia. No se afirma que estén implementadas todas las recomendaciones de la auditoría.

Programadas dos revisiones automáticas de sólo lectura: **2026-11-27 y 2026-11-28 a las 16:46 UTC**, para comparar ventanas equivalentes, consultar errores/consumo y verificar la PWA. No son monitorización continua ni prueba de aceptación de iPhone/Android/recepción. No permiten cambios productivos automáticos.
