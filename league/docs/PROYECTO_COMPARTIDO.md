# League dentro de un proyecto existente

Decisión del propietario: no contratar proyectos ni ramas adicionales de Supabase. League puede compartir el proyecto operativo del gimnasio. Una base o proyecto independiente no es un requisito del producto.

## Distribución

- El proyecto actual del gimnasio aloja Auth, tablas `league_*`, funciones privadas `league_private` y `league_source_private`, el catálogo y el bucket privado `league-evidence`.
- Se reutilizan sus tablas de clientes, rutinas, ejercicios, clases y reservas. Las asociaciones usan `gym_id`; una cuenta deportiva no se agrega a `gym_users` por registrarse.
- Atlantic Core conserva las licencias y la habilitación de League en el proyecto de Core que ya existe. No se crea un tercer proyecto.
- La PWA usa únicamente la URL y la clave pública del proyecto del gimnasio. La pasarela puede usar ese mismo proyecto tanto como hub como proveedor.
- La pasarela nueva se publica con nombre independiente `atlantic-league`, sin reemplazar las funciones actuales de Core o marketing.

## Configuración de la pasarela

`LEAGUE_HUB_REF` y el `projectRef` del gimnasio en `LEAGUE_SOURCES_JSON` pueden ser idénticos. Sus transportes reutilizan el mismo proveedor existente; no se crea otra base. `LEAGUE_CORE_REF` apunta al Core existente. Las claves privilegiadas quedan exclusivamente en los secretos del servidor, nunca en Gym ni en las variables EXPO_PUBLIC de la PWA. Las claves públicas de ambos proyectos no sustituyen esos secretos.

Con `LEAGUE_SHARED_PROJECT=true`, el runtime implementado reutiliza `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` para ambos transportes; la integración con Core sigue requiriendo credenciales de servidor configuradas en ese entorno. No leer ni imprimir secretos de Vault para trasladarlos a un cliente.

## Identidad compartida

Eliminar League elimina su perfil, historial deportivo y evidencias privadas. **No elimina el usuario de Supabase Auth**, porque esa identidad puede administrar Atlantic Gym. No revoca roles ni borra clientes o membresías del gimnasio. La pasarela obtiene el identificador desde la sesión validada y exige reautenticación reciente; el navegador no elige la identidad que se borra.

## Piloto limitado

Primero ejecutar las migraciones juntas en pruebas locales, validar permisos y conservar una copia de seguridad antes de desplegar. El piloto debe permanecer limitado explícitamente a la cuenta confirmada del propietario y a su cliente verificado. No activar `allow_all_clients`, no importar todos los socios y no habilitar registros públicos hasta completar el recorrido.

La convivencia en el mismo proyecto no equivale a aislamiento físico: comparte límites de almacenamiento, transferencia, Auth y cómputo del plan existente. No agrega el costo de otro proyecto; el uso debe permanecer dentro de los límites disponibles.

## Estado

Esquema del proyecto actual inspeccionado en modo lectura: están presentes los campos y funciones requeridos; no había tablas League antes del piloto ni triggers de alta en Auth. Ahora se desplegaron únicamente los objetos de League y el piloto limitado. Sus políticas de las tablas operativas requieren rol de gimnasio. La prueba `shared-project.test.mjs` ejecuta hub y adaptador juntos y comprueba que eliminar League conserva Auth, roles y clientes originales. La PWA privada y su pasarela ya se publicaron. El inicio de sesión y el recorrido en el iPhone del propietario siguen pendientes.

La pasarela del piloto usa la clave pública de Core únicamente para `core_league_public_directory`, que devuelve sólo metadatos de gimnasios habilitados. El esquema privado de Core permanece cerrado a `anon`; el directorio tiene un esquema de funciones separado. No se trasladó ninguna clave privilegiada entre proyectos.
