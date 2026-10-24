# Candidata Atlantic Gym 3.8.0 y despliegue de entrenamiento

## Estado comprobado

El 24 de octubre de 2026 se consultaron únicamente metadatos del servidor Gym
actual: PostgreSQL 17.6, catálogo League y adaptador source instalados, protección
activa de cupos y restricción única de clase/cliente. La RPC de entrenamiento y
sus tablas nuevas todavía no están instaladas. El comprobador devuelve
`ready_for_migration`, sin bloqueos de compatibilidad. Esto no certifica un
respaldo ni autoriza una modificación productiva.

Evidencia sin datos de clientes: `evidence/training-preflight-20261024.json`.
La consulta no lee filas de socios, membresías, huellas, contraseñas o archivos.

La nueva versión compartida de escritorio es **3.8.0**, para x86 y x64. El
marcador `deployment/pilot_update.json` mantiene `publish: false` y `final: false`.
No se modifica la versión oficial instalada ni se envía un aviso a los gimnasios.
Los registros de aceptación corresponden a 3.8.0 y siguen sin aprobar: no se
heredan aceptaciones de 3.7.1. La versión debe ser mayor que la instalada para
que el actualizador pueda ofrecerla correctamente.

## Comprobación de servidor

Desde `league`:

```sh
node scripts/training-preflight.mjs --help
node scripts/training-preflight.mjs --snapshot metadata.json --output report.json
```

El archivo de metadatos procede de `league/source/training-preflight.sql`. Para
consultar una conexión directa autorizada, configurar `ATLANTIC_TRAINING_DB_URL`
en el entorno privado y ejecutar el comprobador sin `--snapshot`. No pasar la
contraseña como argumento ni guardarla en Git. La conexión usa una transacción
`READ ONLY`, tiempo limitado y `ROLLBACK`. Los errores no imprimen credenciales.
La consulta también puede ejecutarse con el conector/SQL Editor, dentro de una
transacción de sólo lectura, sin disponer de una contraseña directa en este equipo.

Estados posibles:

- `ready_for_migration`: se cumplen los requisitos del esquema previo.
- `installed`: objetos nuevos presentes, RLS y permisos previstos.
- `disabled`: objetos conservados y RPC deshabilitada para autenticados.
- `blocked`: falta de requisitos, instalación parcial o permisos incompatibles.

Código de salida 0 para los tres primeros estados, 2 si hay bloqueos, 1 si la
comprobación no pudo realizarse. Un JSON incompleto no se considera compatible.
El reporte enlaza la migración y el comprobador mediante SHA-256; se vuelve a
consultar antes del despliegue, no se utiliza una captura antigua como prueba actual.

## Ensayo reproducible de respaldo y reversión

`league/tests/training-restore-postgres.mjs` utiliza `pg_dump` y `pg_restore`
reales contra bases temporales creadas por la propia prueba. Sólo acepta un
PostgreSQL local desechable habilitado expresamente y rechaza parámetros de URL
que puedan cambiar el destino. En CI utiliza los clientes PostgreSQL 17 del
contenedor ya existente; no crea proyectos Supabase ni servicios contratados.

Comprueba el respaldo previo, su restauración, la aplicación repetida de la
migración y la carga idempotente. Después guarda actividad deportiva, una rutina,
una clase y una reserva sintéticas, respalda y restaura de nuevo. Compara conteos
y huellas de las tablas, verifica permisos, secuencias e idempotencia, consulta
League, deshabilita la RPC sin borrar datos y vuelve a habilitarla. Un archivo
corrupto debe detener la restauración. Los archivos temporales se eliminan al final.

Este ensayo de PostgreSQL ordinario **no es un respaldo del proyecto real de
Supabase**. Sus roles ya existen en el clúster de pruebas; no certifica restaurar
contraseñas de roles, proveedores Auth, Vault, fotos ni objetos de Storage.
El resultado del ensayo se conserva en el artefacto de CI
`training-restore-evidence.json`.

## Antes de habilitar en clientes

1. Obtener un respaldo completo por el procedimiento oficial de Supabase y
   restaurarlo en un entorno aislado compatible. Incluir los esquemas privados
   de Gym/League y los datos de identidad necesarios. Conservar los respaldos
   reales en almacenamiento privado protegido, fuera del repositorio. Los
   objetos de Storage, Edge Functions, ajustes de Auth y secretos requieren su
   procedimiento específico. El conector SQL disponible aquí no ha descargado
   un respaldo completo del proyecto.
2. Repetir el preflight del servidor y comparar el SHA de la migración revisada.
   Aplicar sólo `training/supabase/migrations/20261024013933_gym_training_workspace.sql`
   en el proyecto autorizado. No volver a instalar el esquema completo de Gym.
3. Comprobar `installed`, permisos, operaciones existentes y el piloto con la
   cuenta autorizada. Los ejemplos se cargan primero en el entorno aislado;
   no se añaden socios, membresías ni pagos ficticios.
4. Probar la instalación x86 en Windows de 32 bits y el equipo del gimnasio,
   incluida la huella y el relé. Completar los requisitos vigentes de
   `release_readiness.json` con evidencia de 3.8.0. La instalación x64 anterior
   de 3.7.1 no se presenta como aceptación de la candidata nueva.
5. Revisar los destinatarios y el canal en Core, publicar el candidato aprobado
   y probar el aviso y la actualización desde el cliente. El marcador permanece
   desactivado hasta ese punto; no se publica automáticamente con este desarrollo.

Para una reversión funcional, utilizar el cliente anterior y
`training/rollback/disable_workspace.sql`, que conserva la información. No
restaurar un respaldo antiguo sobre actividad nueva sin conciliar esos registros.

Referencias oficiales revisadas:

- https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore
- https://supabase.com/docs/guides/self-hosting/restore-from-platform
- https://supabase.com/changelog.md
