# Cambios · 2026-11-26

- Auditoría remota de sólo lectura en ambos proyectos, metadata y contadores preservados.
- Inventario de repositorio main/pruebas y repositorio histórico; rama optimization/supabase-20261126 desde 347dbcbc95613816c7edd7c806a1884f63b975f4.
- Documentación y snapshots agregados sin datos de clientes, credenciales ni plantillas.
- B1: coordinador temporal de lecturas en la PWA web. Allowlist: gym.routines, gym.templates, gym.catalog y push.config. Todas las demás acciones ejecutan transporte independiente y limpian vuelos pendientes.
- Limpieza al cambiar sesión/auth, al empezar/terminar operaciones no compartidas, ante éxito/error. Fin de vuelo antiguo no elimina reemplazo.
- Sin modificación SQL, cron, escritorio, biometría, relé, RLS, UI, API server ni despliegue. No se añadieron dependencias ni se cambiaron lockfiles.
- Moderadas/críticas quedan como propuestas hasta respaldo, pruebas y autorización correspondiente.
