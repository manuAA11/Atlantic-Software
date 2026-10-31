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
