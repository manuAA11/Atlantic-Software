# Clases, reservas y rutinas — diagnóstico y alcance

La aplicación comparte `common/app.py`, `cloud_database.py`, `ui_performance.py`
y el UI Kit en todos los perfiles x86/x64. Las tablas operativas son `routines`,
`exercises`, `classes`, `reservations`, `trainers` y `clients`, siempre por gym_id.
League ya lee estas mismas rutinas/clases y conserva snapshots de entrenamientos.
Existe un catálogo global y por gimnasio en `league_exercise_catalog`; no se crea
otro catálogo. Se ampliará el catálogo existente con baja lógica, medios y orden.

Faltan filtros, edición, historial de asignación y reserva, parámetros de descanso,
plantillas, asignación grupal y un selector de ejercicios completo. El panel actual
League abre un diálogo por ejercicio, requiere provisionar perfiles y no sirve
como editor de trabajo diario. El escritorio tiene lecturas en segundo plano,
búsqueda con debounce y tablas incrementales: se reutilizarán.

La nueva RPC de entrenamiento opera sobre las mismas tablas, sin exigir activación
League ni aprovisionar deportistas. Requiere instalar los adaptadores existentes en
el mismo proyecto Supabase (modalidad piloto actual). Para ejercicios personalizados
se registra la identidad real del gimnasio en el directorio con League deshabilitado;
no se activan licencias ni se crean miembros, vínculos o pagos. La autoridad para
activar League continúa siendo Core. Un despliegue con hub remoto necesita una
réplica de catálogo validada; no se fingirá compatibilidad con esa topología.

La edición de rutinas crea una revisión y archiva el plan previo, sin borrar sus
ejercicios. Los registros móviles y snapshots anteriores permanecen. Las clases
reutilizan el trigger de aforo compartido. Se ampliará su cobertura a edición,
cancelación, condiciones y asistencia, con un historial separado de reservas.

Apariencia está duplicada en Sistema y avisos y como acceso directo en Recepción.
Se retira esa duplicación y se añade Configuración en Recepción, sólo con apariencia.
No se conceden privilegios administrativos al rol de recepción.

No se aplican migraciones ni semillas en producción en esta tarea. Se validará con
fixtures aislados. Windows físico y lector/puerta quedan fuera de las pruebas locales.
