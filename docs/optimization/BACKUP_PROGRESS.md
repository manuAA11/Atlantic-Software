# Preparación del respaldo · 2026-11-26

El usuario autorizó crear el respaldo y aplicar la optimización. Aún no se ha exportado ni restaurado una copia completa; no se aplicó C1 en producción.

La conexión MCP permite SQL/advisors, pero no ofrece descarga pg_dump ni backups. El navegador compartido no pudo iniciarse por un error del entorno. Se preparó Supabase CLI oficial 3.4.0 y su inicio de sesión oficial con token nombrado para esta operación; está pendiente que el usuario complete la verificación de un solo uso. Ninguna contraseña fue solicitada, cambiada o expuesta. No se copian enlaces/códigos de autorización ni claves a este repositorio.

Preparado:

- Directorio privado fuera del repositorio, permisos 0700.
- Clave AES-256-GCM separada, permisos 0600; pruebas sintéticas de cifrado, descifrado y rechazo de manipulación aprobadas. Esto no equivale a respaldo de producción.
- Docker disponible para restauración aislada, sin detener servicios existentes.
- Copia de definición/owner/ACL/search_path de marketing_cron_tick y cron en los dos archivos before-idle-gate.json. Hash de definición en ambos: 94a0b9b659ec24a92de06679be30792e. Esto es respaldo del objeto de código, no de la BD.
- Recuentos de referencia: Comercial 5 clientes, 8 membresías, 1 congelación; ZTATTUZ 249, 443, 13. La actividad legítima puede cambiar estos recuentos; no atribuir variaciones a optimización sin evidencia.

Pasos pendientes después de autenticar:

1. Verificar la cuenta/organización y apuntar exclusivamente a los dos proyectos identificados.
2. Exportar esquema, roles y datos con snapshot coherente; comprobar cobertura de esquemas privados/Auth/Storage y exclusiones de Supabase. Conservar metadata de cron y funciones; los valores Vault cifrados dependen de claves del proyecto y no deben presentarse como portables sin verificación.
3. Cifrar fuera del repositorio, calcular checksums, restaurar aislado y comparar integridad/constraints/RLS/conteos/funciones. Documentar limitaciones reales del respaldo.
4. Entregar copia cifrada y mecanismo seguro de recuperación al propietario. No publicar datos de clientes, biometría, tokens ni claves en GitHub.
5. Sólo con respaldo recuperable verificado, revalidar drift y aplicar C1 primero en Comercial. Conservar API, cron de congelaciones de un minuto y grants; verificar jobs/errores antes de considerar ZTATTUZ.
6. Detener si falla exportación/restauración, mantener producción intacta y explicar el bloqueo.
