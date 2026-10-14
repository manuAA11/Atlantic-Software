# El panel no pudo actualizarse

El 14 de octubre de 2026 el usuario informó que Dashboard mostraba ceros y
«No se pudo actualizar», mientras **Clientes y pagos sí mostraba sus clientes**.
Ese mensaje indica un fallo de consulta; los ceros iniciales no eran un resultado
válido del servidor. No se observó ni se realizó un borrado de datos en esta revisión.
El usuario mostró también estadísticas cargadas (8 entradas del día, 195 del mes)
y confirmó que solo instaló el programa, sin ejecutar los dos upgrades nuevos.

## Causa identificada en el cliente

El panel nuevo consulta `membership_population`, agregada por
`ACTUALIZAR_PLANES_INTERNOS.sql`. Los instaladores actualizan los programas del PC;
no instalan estas migraciones en Supabase. La carga anterior agrupaba membresías,
tiqueteras y cumpleaños en una sola petición: cualquier error impedía presentar
todo el panel. Además consultaba dos veces la población de membresías.

La ausencia de esa función es una explicación probable en un proyecto sin el
upgrade, pero **no se ha confirmado el error exacto de la sesión del usuario**.
Un permiso, sesión vencida o timeout también puede interrumpir una consulta.
En esta revisión la conexión pública de diagnóstico fue rechazada por el proxy
del entorno; no se accedió a la sesión del usuario ni se modificó Supabase.

## Comprobar el proyecto existente

1. En el panel de Supabase, abrir el proyecto utilizado por la aplicación.
   Para ZTATTUZ es `srmquhwpawgipncmvfjf`; conservar el gimnasio y las cuentas existentes.
2. Abrir **SQL Editor → New query** y ejecutar
   [DIAGNOSTICAR_PANEL.sql](../deployment/DIAGNOSTICAR_PANEL.sql).
   Solo lee metadatos: devuelve `PRESENTE` o `FALTA` sin consultar personas.
3. Si faltan `Panel de membresías y STAFF` / `Editor de planes`, ejecutar completo
   [ACTUALIZAR_SERVIDOR_MEMBRESIAS.sql](../ACTUALIZAR_SERVIDOR_MEMBRESIAS.sql).
   Comprueba requisitos previos antes de escribir y reúne los upgrades de STAFF
   y reanudación en **una sola transacción**. Si cualquier paso falla, se revierte
   toda esa transacción. Actualiza la caché de PostgREST al confirmar.
   No instala el esquema inicial ni aplica migraciones anteriores automáticamente.
   Este archivo es generado desde las fuentes canónicas de
   `ACTUALIZAR_PLANES_INTERNOS.sql` y `ACTUALIZAR_REANUDACION_MEMBRESIAS.sql`, en ese orden;
   no hace falta ejecutarlos por separado si se utiliza el archivo unificado.
4. Si faltan consumo diario, congelación u otras dependencias anteriores, comprobar
   el historial y completar el orden descrito en
   [STAFF y reanudación](MEMBRESIAS_STAFF_REANUDACION.md#base-de-datos-y-despliegue).
   No repetir scripts antiguos sobre funciones más nuevas ni ejecutar el esquema
   inicial para intentar reparar el panel.
5. Volver a ejecutar el diagnóstico y, en la aplicación, pulsar **Actualizar**.
   Si todas las funciones están presentes y continúa el fallo, hace falta el
   diagnóstico de la consulta para distinguir permisos, sesión, timeout o caché.
   No compartir contraseñas, claves privadas ni tokens.

Este diagnóstico verifica presencia, no ejecuta las funciones ni acredita su
versión, permisos, caché PostgREST o rendimiento. No sustituye las pruebas de
acceso, finanzas, congelación ni el despliegue del backend de Marketing.

El preflight del archivo unificado comprueba metadatos, tipos de calendario e
instantes y las funciones previas que necesita actualizar. Si devuelve una lista
de requisitos faltantes o versiones incompatibles, revisar esa lista antes de
continuar. No acredita compatibilidad con cualquier versión histórica o cambios
SQL hechos fuera de estas fuentes. Generación reproducible:
`python common/build_membership_server_upgrade.py`.

## Conexión administrativa desde Codex

El usuario autorizó aplicar los SQL al proyecto real. Para ejecutarlos desde aquí
hace falta una conexión administrativa; la configuración pública del programa no
otorga ese acceso. En Codex de escritorio, añadir una conexión MCP HTTP con esta URL:

`https://mcp.supabase.com/mcp?project_ref=srmquhwpawgipncmvfjf`

Autenticar en Supabase mediante su autorización, con acceso SQL al proyecto. No
pegar contraseñas, claves privadas ni tokens en el chat o en el repositorio. Una
conexión añadida en el escritorio no se considera disponible para esta tarea
cloud hasta que las herramientas de Supabase aparezcan aquí y respondan.

## Corrección del cliente

Las tres ediciones separan las lecturas de membresías, tiqueteras y cumpleaños.
Una respuesta de población sirve para métricas y vencimientos, sin recalcular
estados en la interfaz. Las secciones sin respuesta muestran `—` y las cargas
fallidas conservan el último resultado válido. El aviso permite consultar un
diagnóstico con categoría, código y referencia, y después reintentar.

Esta corrección necesita una compilación posterior a `7a44de8`. Los instaladores
ya publicados con ese commit no se modifican al actualizar el código en Git.
Aplicar un upgrade que falte en Supabase puede resolver ese fallo en el cliente
ya instalado; la corrección visual del cliente no instala funciones en el servidor.

No se generaron instaladores nuevos para esta corrección. En esta sesión, Git
puede acceder al repositorio, pero la API de GitHub/Actions rechaza la credencial
disponible; no se pudo iniciar una nueva compilación Windows. Esto no invalida
las evidencias de los instaladores anteriores ni acredita la corrección nueva
en Windows.

## Verificación de esta corrección

En las tres ediciones aprobaron 15 etapas dirigidas: **635 pruebas Python**
(Comercial 226, ZTATTUZ x64 205, x86 204), carga y navegación Tk, tiqueteras,
fallos/reintentos de listas y flujo SQL de STAFF. Cada edición incluye 58
comprobaciones nuevas del panel y 40 del upgrade unificado. Estas últimas
comprueban falta de requisitos sin escrituras, rollback ante un fallo tardío,
historial poblado conservado, métricas del servidor y reaplicación idempotente.

Son pruebas Linux/Tk/PGlite con datos ficticios. La ejecución del código x86 en
este host no acredita Windows32. Evidencias y hashes de las fuentes verificadas:
[dashboard-20261014/summary.json](../evidence/dashboard-20261014/summary.json).
Las correcciones de fixtures y sus fallos anteriores se identifican en ese informe.
