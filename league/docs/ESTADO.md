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
- Vincular Expo/EAS y Apple Developer/App Store Connect; producir build firmado.
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
