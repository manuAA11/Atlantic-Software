# Interfaz 0.2.0

Diseño adaptado de la referencia aprobada `Atlantic_League_ZTATTUZ_Prototipo.html`: cabecera compacta, tarjetas blancas, Inicio/League/Agenda/Rutinas/Perfil y modo oscuro azul guardado por dispositivo. Los datos de progreso siguen procediendo de la cuenta actual. Iconos web SVG sin fuentes externas.

Corregidos: barra inferior y altura visible en celular, búsqueda de ejercicios sin tildes, guardado ordenado de borradores y eliminación al retirar todas las series, salida de sesión limitada al dispositivo, carga que no termina si falla el almacenamiento, adjuntos web y reintentos de verificación con identificador estable. Historias con estadísticas pequeñas, texto blanco/oscuro o tarjeta discreta, selección de gimnasio/XP y enlaces directos de descarga/apertura.

Validación: TypeScript y compilación PWA; 21 grupos automáticos locales; revisión de las cinco secciones en navegador a 320×640, 390×844 y 430×932, sin desbordamiento ni iconos de fuente; modo oscuro conservado al reabrir. Se comprobó la preparación de una historia y la disponibilidad de sus enlaces. No se verificó la descarga del archivo en el entorno HTTP de revisión. Las nuevas pruebas Playwright están preparadas y no se les atribuye PASS sin ejecución.

La captura enviada por el propietario acredita que pudo abrir la PWA y consultar la rutina y el catálogo en su iPhone. Siguen pendientes el recorrido físico completo, cámara/guardar/compartir y suspensión/reanudación en el dispositivo real. Esta actualización no cambia el esquema, membresías ni licencias del gimnasio.

# Piloto publicado

La PWA privada está publicada en https://atlantic-league-piloto.ablebeech7.chatgpt.site. El acceso del sitio requiere la cuenta propietaria de ChatGPT; el acceso deportivo utiliza la cuenta existente de Atlantic Gym. Sólo una cuenta confirmada está habilitada en el piloto y vinculada a su propio registro de ZTATTUZ. No hay altas masivas ni mensualidades creadas.

League utiliza el proyecto Supabase existente de Gym, y el módulo de Core utiliza el proyecto de Core ya existente. Se aplicaron las migraciones aditivas de League, con RLS en todas sus tablas públicas, Storage privado y comprobación de que clientes y membresías permanecieron intactos. Se habilitó el módulo para ZTATTUZ y se creó una rutina identificada como prueba, sólo para el propietario.

Verificado: 18 grupos de pruebas locales; perfil, vínculo y catálogo mediante el rol autenticado de base de datos dentro de una transacción revertida; RPC pública limitada del directorio real de Core; rechazo HTTP de sesiones ausentes y de orígenes CORS ajenos; publicación privada del sitio confirmada. No se utilizó la contraseña ni se inició una sesión HTTP en nombre del usuario.

Pendiente: que el propietario inicie sesión y complete el recorrido en su propio iPhone; instalación física PWA, cámara, compartir y reapertura sin internet en el dispositivo real; publicación de la nueva compilación de escritorio con el catálogo. La versión Windows 3.7.1 previamente publicada no incluye este panel. Las reservas seguirán comprobando una membresía válida. Los pasos anteriores de laboratorio se conservan más abajo como historial.

# Estado y piloto

## Implementado en esta fase

- Aplicación Expo/TypeScript con navegación, acceso, registro libre y confirmación de correo, recuperación de contraseña, sesiones nativas cifradas, configuración y eliminación de cuenta.
- Perfil personal independiente del gimnasio; invitaciones seguras y solicitudes que necesitan aprobación.
- Aprovisionamiento controlado de referencias deportivas sobre clientes originales. Se limita a una lista explícita del piloto y está deshabilitado por defecto.
- Catálogo universal inicial y ejercicios personales/propios del gimnasio. Máquinas por gimnasio.
- Asignación individual o grupal desde Gym, checkboxes y configuración de series, repeticiones, peso, descanso y día.
- Consulta de rutinas y registro de series con snapshot del servidor e historial inmutable.
- Clases y reservas sobre las tablas originales, bloqueo del último cupo, cancelación y revisión administrativa.
- XP personal, objetivo semanal, constancia y asistencia oficial sin duplicar la misma fecha/gimnasio.
- Solicitudes de verificación y revisión con motivo. Clasificaciones oficiales separadas por ejercicio y categoría.
- Creador local de historias con fotos propias, cuatro plantillas y verificación de tamaño.
- Control opcional del módulo en Core sin cambios de pagos/licencias.
- Pruebas SQL/HTTP/seguridad, persistencia Unicode, cola tras respuesta perdida, PostgreSQL con dos conexiones y recorrido de interfaz simulado.

## Validación

Comprobado localmente: TypeScript sin errores, exportación de bundles JavaScript para iOS/Android y 13 grupos de pruebas de integración/seguridad. Consultar la ejecución CI del commit para PostgreSQL real y navegador; no atribuirles PASS antes de que termine.

No se ha modificado un proyecto productivo de League, migrado clientes reales, enviado correos reales ni instalado en un iPhone. Las evidencias del escritorio/hardware existentes corresponden a Atlantic Gym y no prueban este piloto móvil.

## Pendientes y bloqueos

- Crear/configurar hub, Core y proveedor de Gym aislados con el esquema operativo y datos sintéticos.
- Validar en Supabase real Auth, políticas de Storage, empaquetado Deno de la pasarela y avisos de seguridad.
- Alojar la PWA en HTTPS y registrar su origen en CORS y las redirecciones de Auth. EAS y Apple Developer dejan de ser requisitos del piloto PWA.
- Probar cámara/galería, exportación exacta, guardar/compartir y recuperación de sesión en iPhone y Android físicos.
- Identificar la cuenta y membresía propias del propietario para el piloto; no deducirlas de fotos ni habilitar listas masivas.
- Publicar el panel de administración en una compilación de pruebas de Atlantic Gym después de validar todo el flujo. No está incluido en la actualización 3.7.1 de apariencia.
- Revisión funcional de rangos de fuerza por ejercicio, categorías y evidencia con un entrenador. En esta fase se muestran marcas verificadas y rankings comparables, sin inventar umbrales universales.
- Listas de espera, recordatorios y proveedor de envío automático de invitaciones: preparados por separación de estados, aún no implementados. El administrador recibe un enlace privado para compartir.
- Inicio por cédula: se usa correo verificado en esta fase; no se expone un buscador público de documentos.
- Revisión final de privacidad, retención y publicación de tiendas. Sin precios ni cobros de League.

## Prueba controlada de aceptación

Cada paso requiere una evidencia de la cuenta del propietario; los registros siguientes siguen PENDIENTES.

| Paso | Evidencia necesaria | Estado |
|---|---|---|
| Perfil vinculado | Aprobación sobre el cliente correcto sin crear membresía | Pendiente |
| Acceso iPhone | Build firmado, correo confirmado, entrar/cerrar/reabrir | Pendiente |
| Rutina desde Gym | Asignación visible y ejercicios correctos | Pendiente |
| Completar ejercicios | Series guardadas, repetir envío sin duplicación, historial tras editar plan | Pendiente |
| Solicitar marca | Peso/reps/categoría y evidencia privada opcional | Pendiente |
| Aprobar desde Gym | Revisor autorizado, motivo e inclusión sólo después de aprobar | Pendiente |
| Reservar clase | Cupo confirmado, cancelar/reintentar; dos solicitudes por último cupo | Pendiente |
| Historia propia | Foto real, PNG 1080×1920 y compartir desde iOS | Pendiente |

Sólo después de aprobar estos pasos y recibir autorización se preparará el despliegue operativo y una ampliación de clientes.

## Cambio solicitado: PWA y catálogo de escritorio

Implementados localmente el empaquetado PWA, sesión persistente cifrada de navegador, aviso de actualización, cola al recuperar internet e historias PNG con Web Share/descarga. Catálogo de escritorio con búsqueda, creación y selección de ejercicios; asignación reutiliza rutinas y ejercicios existentes mediante la pasarela, con copia de la prescripción. Diez ejercicios iniciales en la migración de QA aún no aplicada. No se ha desplegado esta fase ni acreditado conexión con la cuenta real.

Conexión del piloto: se seleccionaron la organización actual y el correo manuel411cm@hotmail.com. La creación del proyecto QA fue rechazada por el límite de dos proyectos gratuitos; no se creó ningún proyecto ni se pausaron los existentes. Cotización de rama de desarrollo: USD 0.01344/h, la creación de la rama fue declinada en la confirmación. No se creó ni se generó ese cargo. Tres pruebas de transporte y veinte comprobaciones Tk del catálogo pasaron localmente. Las pruebas nuevas de navegador siguen pendientes de CI.

## Mismo proyecto, sin contratación adicional

El propietario seleccionó reutilizar los proyectos existentes. Implementado `LEAGUE_SHARED_PROJECT=true`: hub y proveedor utilizan las credenciales internas del mismo proyecto, mientras Core conserva su proyecto actual. Se corrigió la eliminación de League para conservar la identidad compartida de Auth. Pasaron 15 grupos de pruebas locales, incluida convivencia de migraciones, preservación de clientes/roles/Auth y transporte compartido. La inspección del proveedor operativo fue de sólo lectura; esta adaptación no se ha desplegado ni acredita aún acceso desde el celular.
