# Atlantic Gym 3.8.5 · Notas, motivos de acceso y vencimientos

Petición del usuario del 30 de octubre de 2026: avisos por cliente y notas al registrar la mensualidad, visibles durante el chequeo. El usuario excluyó expresamente abonos, saldos y reglas de deuda.

- Clientes y pagos → seleccionar persona → **Notas y avisos**: aviso general de hasta 2000 caracteres. Administración y Recepción pueden consultar, editar y borrar el texto guardando. Permanece entre renovaciones hasta su edición explícita.
- Registrar plan: conserva el campo de nota de la membresía y su guardado existente. La ficha muestra por separado el aviso general y la nota de la membresía seleccionada por el servidor; una renovación futura no reemplaza prematuramente la nota vigente.
- Ingreso permitido o denegado: muestra motivo del servidor, aviso de vencimiento hoy/mañana/en 2–7 días y ambas notas en un panel desplazable. Un vencimiento próximo sigue permitido conforme a la autorización del servidor. Se limpia el panel al cambiar de persona o identificar una huella desconocida.
- Todos los grupos de vencimiento del dashboard se muestran por fecha ascendente, nombre como desempate y registros sin fecha al final. Se ordenan las fechas recibidas; no se recalculan grupos, días, congelaciones ni autorización en el equipo.

El almacenamiento del aviso general está en `private.client_staff_notes`, sin acceso directo para anon/authenticated, con RLS y RPC que validan usuario y rol del gimnasio. El guardado usa bloqueo del cliente y revisión esperada: un cambio concurrente produce aviso y conserva el texto en pantalla. Repetir un guardado idéntico es idempotente. Ediciones auditadas, notas sólo para el personal: el snapshot genérico usado por League/marketing/chat no recibe estos campos.

Migración aditiva generada con Supabase CLI 2.122.0: `20261030235749_client_staff_notes.sql`, sincronizada con `ACTUALIZAR_NOTAS_CLIENTES.sql` en los tres perfiles. Conserva wrappers comerciales y permisos/licencias, filtros de búsqueda, autorización, congelación, escritura de asistencia y consumo diario. En registro sólo envuelve el JSON ya autorizado y registrado para añadir presentación. No modifica controlador, pulsos ni recuperación del relé.

Verificación local: 64 comprobaciones PGlite por proveedor (ZTATTUZ/Comercial), incluidas permisos, aislamiento, revisión obsoleta, reintento idéntico, límite, borrado, nota vigente/futura, persistencia entre renovaciones, fecha Bogotá frente UTC, permiso/denegación, congelación y reingreso diario; comparación de definiciones protegidas y datos financieros. No acredita dos sesiones PostgreSQL simultáneas ni hardware real. Pruebas de UI verifican notas largas desplazables, escritura fallida sin perder texto, sustitución al cambiar cliente y Admin/Recepción al 100/125% en Windows.

Estado de entrega: candidato beta opcional, NO FINAL. Validación Windows, aplicación de la migración y publicación se documentan con sus resultados reales al completarse; los gates externos de `release_readiness.json` permanecen pendientes.

Servidor: migración aplicada correctamente en los proveedores ZTATTUZ y Comercial. Comprobaciones posteriores: RLS activo, acceso directo de authenticated denegado, RPC anon denegado y RPC del personal habilitado. El hash del snapshot genérico de cada proveedor sigue idéntico. Al retirar sólo el envoltorio de presentación del registro, su definición conserva exactamente el hash anterior. Sin usuarios de prueba ni tokens impersonados en producción.

## Publicación verificada

La ejecución Windows **41150693184**, commit `15318a4653f5dc8ab25b4eadfe93e623fae32fdf`, aprobó Comercial x64, ZTATTUZ x64 y ZTATTUZ x86. Cada perfil aprobó 177 guards, 64 comprobaciones SQL de notas y 56 comprobaciones de UI de notas. Las regresiones Python fueron 322/294/293 respectivamente. Instalación, actualización y desinstalación x64 PASS; instalación Windows32 nativa NOT_RUN (el runner es x64). Se conservan los fallos iniciales de 41148446276 y sus correcciones de prueba en el historial.

La publicación **41150693251** creó `atlantic-gym-3.8.5-piloto`, release **429627552**, opcional y prerelease. Se descargaron íntegramente los tres paquetes, verificando SHA256/tamaño con el actualizador real. Core ofrece los dos paquetes ZTATTUZ únicamente al gimnasio autorizado; selección real de metadatos y código del actualizador PASS en ambas arquitecturas. No se creó actualización global ni se modificó licencia, configuración o suscripción; se conservaron las dos entradas 3.8.4.

Uso: Sistema y avisos → Buscar actualizaciones. Clientes y pagos → seleccionar persona → Notas y avisos. La nota general y la nota de la membresía se muestran por separado durante el chequeo. Sin abonos, saldos ni cambios de autorización por el texto.

Evidencia: `evidence/notes-release-3.8.5.json`. Permanecen pendientes los gates externos, hardware físico y Windows32 nativo. Esta publicación no acredita una entrega final.
