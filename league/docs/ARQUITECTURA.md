# Arquitectura y decisiones

## Una aplicación Gym

Atlantic Gym comparte app.py, recepción, UI Kit, sesión, hardware y plataforma en common/. x86/x64 son arquitecturas del mismo producto. Los perfiles existentes conservan sus proveedores y carpetas para que las instalaciones actuales sigan trabajando. No se fusionan bases de clientes mediante copias ni se reemplazan IDs.

League usa un perfil deportivo independiente dentro de un hub lógico. Ese hub puede compartir el proyecto, Auth y la base de datos con Atlantic Gym; no requiere un tercer proyecto. El perfil deportivo se conserva separado de los roles de administración. Al cambiar de gimnasio, el deportista conserva su cuenta y entrenamientos. Core conserva el directorio de gimnasios y la autorización del módulo; la aplicación personal no depende de esa autorización.

La pasarela recibe un JWT de deportista del hub o un JWT de personal del proveedor original. Lo valida en Auth, exige correo confirmado y consulta permisos actuales en gym_users/league_coaches. Las URLs y claves de proveedores proceden de la configuración privada del servidor; ningún cliente puede suministrar un servidor arbitrario.

## Modelo

| Modelo | Datos y reglas |
|---|---|
| league_profiles | Propietario auth.users.id, nombre visible, consentimiento de clasificación y objetivo semanal |
| league_gym_directory | Ruta y nombre públicos del gimnasio, código deportivo y habilitación certificada por Core durante 60 s |
| league_client_profiles, en proveedor Gym | Referencia deportiva opaca sobre el cliente existente. No crea membresías ni pagos |
| league_links | Cuenta del hub → gimnasio → referencia deportiva del proveedor, con aprobación y unicidad |
| league_join_requests | Solicitudes pendientes; el código nunca concede acceso privado |
| league_private.invites | Hash SHA256 del token aleatorio de 256 bits, correo exacto confirmado, caducidad 24 h, un solo uso |
| league_exercise_catalog | Ejercicios globales, propios del gimnasio y personales con acceso por propietario o vínculo |
| league_machines, en proveedor | Equipamiento propio; FK compuesta evita asignar una máquina de otro gimnasio |
| routines/exercises, existentes | Se reutilizan. Sólo se añaden referencias a catálogo/máquina y descanso |
| league_workout_drafts | Snapshot de rutina creado en servidor antes de registrar las series |
| league_workouts | Registro inmutable de las series realizadas y copia del snapshot, independiente de ediciones futuras |
| league_xp_events | Libro de puntos con claves únicas; las escrituras directas del cliente están revocadas |
| league_strength_requests | Ejercicio, peso, repeticiones, división/categoría, evidencia opcional y decisión |
| league_private.verification_history | Revisor, fecha y motivo; el revisor no puede aprobar una marca de su propio correo |
| classes/reservations, existentes | Se reutilizan para calendario, cupos, cancelación y administración |
| private.core_league_modules | Habilitación independiente de licencias, precios y cobros |

## Seguridad

Todas las tablas nuevas expuestas tienen RLS. No se conceden escrituras directas de deportistas. Los wrappers públicos son SECURITY INVOKER; las funciones privilegiadas permanecen en esquemas privados y validan identidad/rol o se conceden sólo al servidor. No se usan user_metadata ni roles remitidos en el cuerpo para autorizar.

El hub no replica documentos, teléfonos, biometría, historiales médicos ni datos de pago. El personal recibe sólo los datos necesarios de su gimnasio. Las clasificaciones exponen nombres visibles con consentimiento, nunca documentos ni correos.

Las evidencias están en un bucket privado de 6 MB máximo con JPG/PNG/WebP. El deportista sólo puede insertar/leer su carpeta. No puede reemplazar una evidencia enviada. El personal obtiene enlaces de 120 segundos después de validar gimnasio y rol. Las fotos para historias permanecen en el dispositivo.

La pasarela comprueba Core antes de cada operación oficial. La autorización almacenada por el hub caduca en 60 segundos para RPC directos. Una caída o deshabilitación del módulo del gimnasio no borra historial ni impide el uso personal.

## Consistencia

Cada entrenamiento conserva UUID y cuerpo exactos en una cola local cifrada. Una respuesta perdida no provoca duplicación al reintentar. Los datos de otra cuenta usan otro espacio de almacenamiento. SecureStore se fragmenta por caracteres Unicode sin superar el límite por entrada y cambia el manifiesto después de completar la escritura.

Las reservas usan un bloqueo de la fila de clase antes de comprobar/insertar/reactivar. Un trigger sobre reservations aplica el mismo límite a escritores del escritorio. La restricción única existente evita dobles reservas. La prueba PostgreSQL usa conexiones independientes y verifica que la segunda espere el bloqueo del último cupo. PGlite sólo verifica lógica y permisos.

Una vinculación aprobada y una membresía activa son estados diferentes. Para reservar se reutiliza private.membership_snapshot_json, incluidas sus reglas de congelación. League no recalcula vigencia, deuda, saldo, consumo diario ni reloj de Gym.

## XP y fuerza

Actividad personal: 20 XP una vez por día UTC; 10 XP desde el tercer día consecutivo, con una sola recompensa por fecha; 50 XP al completar el objetivo semanal, una vez por semana. El servidor determina las fechas y no acepta fecha de finalización del cliente.

Asistencia oficial: 25 XP por gimnasio/fecha local de checkin PERMITIDA, con una clave única que evita repetir la misma asistencia. Los rankings XP oficiales sólo incluyen estos puntos. El XP de actividad personal no altera las posiciones oficiales.

Fuerza: sólo las solicitudes aprobadas influyen en la clasificación. Se compara la mejor estimación de 1RM por atleta (Epley, 1–12 repeticiones) dentro del mismo ejercicio, división y categoría de peso. Las categorías las declara el deportista y el revisor debe comprobarlas al decidir. No hay comparación agregada entre ejercicios ni un título de fuerza universal basado en peso absoluto. La calibración de rangos de fuerza por ejercicio queda pendiente del piloto.

## Historias

Cuatro plantillas: entrenamiento, marca verificada, racha y clasificación. Cámara/galería del usuario, composición local y exportación PNG. Se comprueban 1080 × 1920 antes de guardar o abrir la hoja de compartir del sistema. Instagram/WhatsApp dependen de las opciones instaladas y compatibles. Sin feed, seguidores, comentarios ni likes.

En modo de proyecto compartido, eliminar League nunca elimina el usuario de Auth: se borra sólo el perfil deportivo y sus dependencias. Esto conserva el acceso y los registros de Atlantic Gym asociados a la misma identidad.
