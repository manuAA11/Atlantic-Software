# Despliegue compartido: decisión actual

El propietario decidió no contratar otro proyecto ni rama de pago. Usar [proyecto compartido](PROYECTO_COMPARTIDO.md): Gym y League conviven en el proyecto existente; Core conserva su proyecto actual. La separación en tres proyectos descrita más abajo queda como alternativa, no como requisito. Validar primero localmente, respaldar y desplegar sólo un piloto limitado.

# Pruebas, respaldo, despliegue y reversión

## Límites de esta entrega

Los proyectos operativos existentes no son destinos de despliegue de League. No se han ejecutado allí estas migraciones. Crear un entorno aislado antes de probar usuarios reales. Los paquetes de actualización de Atlantic Gym 3.7.1 no contienen estos cambios.

## Entorno aislado

Preparar tres bases/proyectos con configuración explícita:

1. **Proveedor Gym QA:** esquema original de Atlantic Gym y datos totalmente sintéticos. Reutilizar los scripts de instalación y migraciones operativas que correspondan al proveedor. No copiar documentos, biometría, fotografías, pagos ni clientes reales.
2. **Core QA:** esquema original de Core, un propietario de pruebas y un gimnasio QA registrado contra ese proveedor.
3. **Hub League QA:** proyecto separado para cuentas deportivas y almacenamiento privado.

La pasarela puede alojarse como Edge Function del hub QA. Registrar sólo las referencias de QA en LEAGUE_SOURCES_JSON. Guardar las claves secretas en variables privadas de servidor; las de las aplicaciones son exclusivamente publicables.

## Respaldo previo

En una estación autorizada con Supabase CLI 2.122.0 y las herramientas PostgreSQL/Docker necesarias, conservar por cada destino:

- Dump del esquema.
- Dump de datos del módulo y las tablas de negocio involucradas.
- Backup de Storage y configuración Auth/URLs/permisos de función.
- SHA256 de los archivos y una prueba de restauración en otra base aislada.

Comandos descubiertos en la CLI de esta entrega:

    supabase db dump --project-ref QA_PROJECT_REF --schema public,private --file schema-before.sql
    supabase db dump --project-ref QA_PROJECT_REF --data-only --file data-before.sql

El respaldo contiene información privada. No subirlo al repositorio ni a un artefacto público de CI. Usar el flujo de contraseña/autenticación de la CLI sin imprimir secretos en registros. Un archivo creado sin prueba de restauración no acredita recuperación.

## Migraciones

Cada grupo tiene su propio historial de migraciones. Inspeccionar el destino y ejecutar primero con --dry-run. No emplear --include-all en un proveedor operativo cuyo historial sea distinto sin revisar el plan completo.

    supabase db push --workdir league/hub --project-ref QA_HUB_REF --skip-vault --dry-run
    supabase db push --workdir league/source --project-ref QA_GYM_REF --skip-vault --dry-run
    supabase db push --workdir league/core --project-ref QA_CORE_REF --skip-vault --dry-run

Después de verificar copias, restauración, destino y plan, el operador aplica el mismo comando sin --dry-run en los proyectos aislados. La historia de Supabase evita volver a ejecutar una versión aplicada; no ejecutar los archivos iniciales repetidamente como SQL suelto.

Los nombres de las migraciones fueron generados por supabase migration new. Cambios posteriores a un despliegue deben crear una nueva migración; no editar una versión que ya se haya aplicado.

## Configuración del piloto QA

Por defecto league_gym_settings.enabled=false, allow_all_clients=false. Habilitar exclusivamente IDs sintéticos explícitos mediante SQL del operador en QA. Aprovisionar esos clientes desde el escritorio usando league_staff/provision. No habilitar allow_all_clients.

El propietario de Core QA puede activar el módulo con core_league_owner. Se genera un código deportivo independiente del join_code histórico de personal. Nunca publicar el código de personal ni reutilizarlo como credencial de un deportista.

Configurar las variables de league/backend/.env.example en los secretos del servidor y desplegar:

    supabase functions deploy atlantic-league --workdir league/backend --project-ref QA_HUB_REF --use-api --no-verify-jwt

El verificador de JWT de la puerta Edge se desactiva porque hay varios emisores. La función NO es anónima: valida cada JWT contra /auth/v1/user de la fuente registrada, exige correo confirmado y permisos actuales, y comprueba Core. CORS sólo permite los orígenes web indicados; los clientes nativos no requieren Origin.

El empaquetado Deno, Auth, Storage y los avisos de seguridad deben comprobarse en Supabase QA real antes de habilitar el piloto. No se ha acreditado aún ese despliegue.

En la compilación de pruebas de Gym configurar league_endpoint con la URL HTTPS exacta de la pasarela QA. Para desarrollo se admite ATLANTIC_LEAGUE_ENDPOINT. No cambiar la conexión operativa de un gimnasio real para reutilizar la demo.

## Pruebas

    cd league
    npm ci
    npm run typecheck
    npm test

Para concurrencia real usar exclusivamente PostgreSQL local desechable:

    LEAGUE_TEST_DATABASE_ALLOW_LOCAL=1 LEAGUE_TEST_DATABASE_URL=postgres://postgres:postgres@127.0.0.1:5432/postgres npm run test:postgres

El test crea su propia base temporal y comprueba backends distintos, espera de bloqueo, un único ganador del cupo final y reintento duplicado. El guard sólo permite loopback y habilitación explícita/CI. No proporcionar una URL de producción. Los roles Auth necesarios se crean si no existen en el cluster desechable.

La interfaz compartida se revisa con:

    npm exec --workspace @atlantic/league-mobile -- expo export --platform web --output-dir dist-web
    npx playwright install chromium
    npm run test:ui

Esto usa datos simulados y no acredita un iPhone. Probar también importación/arranque de las funciones y políticas de Storage en Supabase QA, seguida de cámara, guardado y compartir en dispositivos.

## Reversión

La primera medida es deshabilitar **sólo League** en Core y en league_gym_settings, retirar la configuración opcional del escritorio y detener la pasarela. Conservar cuentas e historial. No suspender Atlantic Gym ni sus licencias.

Los scripts en reversals/ sólo deshabilitan el módulo y son idempotentes. No eliminan clientes, membresías, pagos, rutinas, clases ni entrenamientos. El guard de cupos se conserva mientras puedan existir reservas escritas por esta fase.

Para una reversión estructural completa en QA, restaurar el respaldo verificado en una base nueva, cambiar las aplicaciones de QA a ese destino y conservar el original hasta comparar recuentos y hashes. No usar DROP CASCADE o una migración inversa que pierda entrenamientos recibidos después del respaldo. Corregir una función desplegada mediante una nueva migración versionada cuando sea viable.

No migrar clientes reales ni activar League en ZTATTUZ operativo hasta completar la tabla de aceptación y recibir autorización específica para el cambio productivo.
