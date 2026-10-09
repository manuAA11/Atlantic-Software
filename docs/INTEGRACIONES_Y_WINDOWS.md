# Configurar, crear instaladores y comprobar la actualización

Las pantallas de Marketing de Administrador ya llaman al backend compartido. Recepción tiene las consultas y vinculación permitidas por su rol. La configuración por gimnasio se hará desde la aplicación instalada; no se deben introducir claves en el código ni enviarlas por chat. El backend necesita la habilitación inicial del operador descrita más abajo. Las pruebas locales de esas funciones usan transportes externos simulados; todavía faltan los pilotos reales.

## Crear instaladores para configurar la aplicación

1. Descarga el paquete de aplicación completa y extráelo en una carpeta nueva, conservando juntos `tools`, `docs` y las carpetas de edición. El paquete ya incorpora DigitalPersona con sus MSI, CAB, bootstrapper, prerrequisitos y EULA originales. No copies una `.venv` de otro paquete ni sustituyas tu configuración propia sin guardarla.
2. En el PC de compilación instala **CPython 3.14 o 3.13 estándar**, con Tk, **Node LTS** e **Inno Setup 6**. Comercial y ZTATTUZ x64 requieren Python/Windows de 64 bits. ZTATTUZ x86 se compila con Python de 32 bits, también desde Windows x64 con Node LTS x64; el PC donde se instala su Runtime debe usar Windows de 32 bits, porque su MSI original rechaza Windows de 64 bits. Abre la carpeta de tu edición y ejecuta **`CREAR_INSTALADORES.bat`**; prepara Python, instala dependencias, comprueba pip y ejecuta la validación completa antes de compilar.
3. Si la aceptación final está pendiente, abre `salida/PRUEBAS_PARA_CONFIGURAR/<identificador>/LEER_PRIMERO.txt` y ejecuta el instalador `VALIDACION_NO_FINAL_…`. ZTATTUZ incluye el instalador completo en esa carpeta y los individuales en `COMPONENTES`; Comercial separa el instalador privado en `PRIVADO_PROPIETARIO`. **El PC donde se instalan los programas no necesita Python, Node ni Inno.** Inicia sesión y configura WhatsApp/Wompi desde Administrador después de habilitar el backend.

La carpeta solo se publica cuando todas las pruebas locales, compilaciones, diagnósticos e integridad de las copias aprueban. Cada ejecución usa una carpeta nueva y conserva las anteriores. Si una etapa falla, revisar el error y sus logs; no entregar salidas parciales. El nombre y los metadatos identifican estos instaladores como validación técnica, porque siguen pendientes las pruebas externas y físicas. El panel Comercial del propietario es exclusivo del dueño del software y no se entrega a clientes.

`CREAR_INSTALADORES.bat` selecciona la entrega final únicamente cuando la aceptación de la versión está aprobada con evidencia válida. No cambiar `release_readiness.json` a true para retirar un aviso. La generación para configuración conserva esos criterios pendientes.

## Entorno cloud

En la configuración de este entorno, revisar y guardar el borrador de instalación/inicio y las dos entradas de red: `bawrakwhzkxmhmgkczqu.supabase.co` (Comercial) y `srmquhwpawgipncmvfjf.supabase.co` (ZTATTUZ). Después publicar el entorno para conservar el snapshot. Guardar el borrador no publica ni aplica automáticamente su red a esta máquina.

Los intentos anteriores de consultar `/functions/v1/marketing/health` fueron bloqueados por el proxy antes de llegar al servicio. El 9 de octubre se comprobó el acceso actual: ambos proyectos responden HTTP 200 con `ready`, `database` y `scheduler_installed` verdaderos. La respuesta original está en `evidence/live-health-20261009.json`; es una comprobación pública de disponibilidad, sin datos privados ni pilotos externos. Comprobar la lista real de migraciones antes de desplegar; el historial parcial registra despliegues posteriores al informe original.

## Habilitación inicial de Meta por Atlantic

Esto corresponde al operador del servicio una sola vez; después cada gimnasio conecta su número desde Marketing.

1. Abrir Meta for Developers → aplicación de empresa → producto WhatsApp. Crear/configurar la app y su portafolio empresarial si aún no existen. Para una conexión comercial mediante Embedded Signup, completar los requisitos vigentes de Meta para el caso de uso y los permisos `whatsapp_business_management` y `whatsapp_business_messaging`; el modo de prueba se limita a los usuarios y números permitidos por Meta.
2. En Facebook Login for Business, crear la configuración de Embedded Signup. Obtener el App ID y Configuration ID; establecer el dominio HTTPS de la página de autorización. Los nombres del panel pueden variar según la versión de Meta.
3. Publicar `onboarding/index.html` en ese dominio HTTPS, en `/conectar/`. El generador seguro está en `backend/core/onboarding.mjs`. Revisar los backends permitidos antes de publicar; deben ser únicamente los dos proyectos autorizados. No poner tokens en el HTML.
4. Obtener App Secret y crear un Verify Token privado. Introducirlos en el host del operador mediante secretos, junto con las variables de `.env.example`: `GSOFT_SUPABASE_URL`, `GSOFT_SERVICE_ROLE_KEY`, `META_APP_ID`, `META_BUSINESS_CONFIG_ID`, `META_APP_SECRET`, `META_VERIFY_TOKEN`, `META_ONBOARDING_URL`. `GSOFT_SERVICE_ROLE_KEY` es privada y solo de servidor. Ejecutar `node deployment/configure_meta.mjs` por cada proyecto para guardar la configuración en Vault.
5. En WhatsApp → Webhooks de Meta, configurar `https://<proyecto>.supabase.co/functions/v1/marketing/webhooks/meta` y el mismo Verify Token. Suscribir los eventos que procesa el backend: mensajes/estados y cambios de plantillas; agregar los eventos de coexistencia cuando se habilite ese flujo. Verificar la suscripción de la app a la WABA.
6. En Atlantic Gym Administrador → Marketing → conexión de WhatsApp, iniciar el flujo oficial, elegir la empresa/WABA/número y autorizar. Comprobar estado conectado. Crear la plantilla desde Marketing, enviar a aprobación y esperar el estado APPROVED antes de habilitar recordatorios que la requieran.

No basta con crear una app: hacen falta un número autorizado, la página HTTPS y la configuración de plataforma para que el botón de conexión pueda funcionar. El programa muestra el requisito pendiente mientras no existe esa habilitación.

## Wompi desde la aplicación

1. Abrir el panel de Wompi → ambiente Sandbox → configuración/desarrolladores. Obtener las cuatro credenciales del mismo ambiente: llave pública `pub_test_…`, privada `prv_test_…`, secreto de eventos `test_events_…` y secreto de integridad `test_integrity_…`.
2. En Administrador → Marketing → pagos online/Wompi, introducirlas en el formulario privado y conectar. El backend las guarda en Vault. No deben ir en `gymsoft_config.json`, un ZIP, logs o el repositorio.
3. Copiar la URL de webhook que devuelve la conexión: `https://<proyecto>.supabase.co/functions/v1/marketing/webhooks/wompi/<gym_id>`. Configurarla en Wompi para los eventos de transacción del ambiente Sandbox.
4. Elegir un plan y usar la acción de pago de prueba. Se crea el cliente reservado PRUEBA Integraciones; no cobrar ni modificar un cliente real para probar Sandbox. Abrir el enlace y realizar la transacción de prueba según los medios de pago oficiales de Wompi.
5. Verificar webhook confirmado, transacción APPROVED, una sola renovación y registro de auditoría. Reenviar el mismo evento desde Wompi si el panel lo permite y comprobar que no renueva otra vez. Probar también rechazo y firma inválida en un entorno aislado. Un pago Sandbox no debe registrarse como ingreso real.

## Piloto conjunto que todavía debe ejecutarse

Usar un gimnasio de prueba, un cliente con consentimiento y fecha de nacimiento verificable, y un teléfono permitido por Meta. Consultar la membresía: sin verificación el bot no revela datos; tras verificar devuelve estado/vencimiento del servidor. Congelar siete días y volver a consultar: debe mostrar CONGELADA, fecha de reactivación y vencimiento extendido. Pedir renovar/pagar, abrir el enlace, completar el Sandbox y comprobar una renovación. Volver a consultar para confirmar el estado actual del servidor.

Preparar una plantilla aprobada para confirmación de pago y una automatización ONLINE_APPROVED si se desea confirmar proactivamente. Habilitar el scheduler y comprobar auditoría/envío. Ejecutar el mismo job/evento dos veces: no debe producir mensajes ni renovaciones duplicados. Fuera de la ventana de conversación, WhatsApp requiere plantilla aprobada. Guardar evidencia con IDs de prueba/estados/horas, sin datos personales ni secretos. Repetir en ambos proyectos y registrar el alcance.

## DigitalPersona restaurado

El SDK original 3.4.0 ya se reconstruyó desde las siete partes enviadas por el usuario, con SHA-256 y CRC verificados. Se recuperaron los árboles completos RTE/x64 y RTE/x86; Comercial y ZTATTUZ x64 usan el primero, ZTATTUZ x86 el segundo. Los recursos están incorporados a los paquetes de aplicación completa con la EULA original. La implementación de huella permanece intacta.

`docs/DIGITALPERSONA_RESTAURADO.md` contiene procedencia, hashes y preparación reproducible; `py docs\vendor\digitalpersona\preparar_runtime.py --verify` comprueba los tres árboles. Los binarios no se distribuyen como Runtime independiente. La recuperación de recursos no acredita aún instalación, controlador ni hardware de una nueva compilación. No hace falta volver a adjuntar el SDK.

## Pruebas físicas en Windows

1. Usar un PC de pruebas Windows con la arquitectura correspondiente. Instalar el runtime autorizado, conectar U.are.U, comprobar detección en Huellas y guardar el diagnóstico sin claves.
2. Iniciar Administrador y Recepción con cuentas de prueba y permisos reales. Registrar una huella y verificar sincronización desde el otro equipo. Probar código, huella identificada/no identificada, lector ocupado por la otra aplicación, pausa/reactivación y desconexión/reconexión USB.
3. Con una membresía activa, registrar entrada y comprobar hora de Bogotá y consumo diario. Una segunda entrada el mismo día no vuelve a consumir cupo. El día siguiente del gimnasio consume una vez.
4. Congelar siete días y verificar denegación en ambos roles, incluso con excepción de entrada administrativa. Comprobar vencimiento extendido, cupos conservados y reactivación al terminar. Probar una segunda congelación: se rechaza salvo excepción autorizada con motivo.
5. **Solo ZTATTUZ:** configurar COM/relé desde la aplicación y verificar apertura por autorización real del servidor. Durante congelación, denegación, falta de permisos o fallo de servidor, comprobar físicamente que no abre. La edición Comercial conserva deliberadamente la ausencia de relé/apertura de puerta.
6. Probar dos sesiones PostgreSQL reales con solicitudes concurrentes de congelación y de consumo diario. El script recuperado `deployment/live_freeze_qa.py` genera SQL para fixtures aisladas, observación y limpieza. Revisar los IDs de fixtures antes de ejecutarlo; no es un piloto de autenticación de PCs ni se ejecutó contra servidores en esta instancia.
7. Validar instalación/actualización/desinstalación, accesos directos, iconos azul/cian y títulos en una VM Windows; verificar que IDs/carpetas históricos permiten actualizar sin crear instalaciones duplicadas. Registrar resolución y escala 100/120/125 %.

## Abrir los programas con Python 3.14 o 3.13

Se admite CPython 3.13 y 3.14 estándar, con GIL. Usa 64 bits para Comercial y ZTATTUZ x64; 32 bits para ZTATTUZ x86. El preparador intenta primero 3.14 al crear un entorno, reconoce el launcher `py`, PATH y las rutas de Python Install Manager (`%LOCALAPPDATA%\Python\pythoncore-3.14-64\python.exe`). No necesitas desinstalar 3.14 ni instalar 3.13 si ya tienes 3.14 de la arquitectura correcta. No se promete compatibilidad con cualquier versión, PyPy o Python free-threaded; deben validarse por separado.

1. Descarga el respaldo actualizado y extrae en una carpeta nueva. Conserva tu configuración pública existente; no copies `.venv`. En ZTATTUZ x64 abre `GymSoft_ZTATTUZ_3.6.1_x64`, que corresponde a tu Python de 64 bits.
2. Ejecuta `PREPARAR_PYTHON.bat`. Solo prepara el entorno. Si encuentra una `.venv` incompatible, la renombra a `.venv_respaldo_<fecha>_<id>` y crea otra; conserva la anterior y no modifica `gymsoft_config.json`.
3. Ejecuta `INICIAR_ADMINISTRADOR.bat` o `INICIAR_RECEPCION.bat`. Instalan los requisitos y abren `app.py` o `reception_app.py` desde las fuentes. No generan un EXE y mantienen autenticación, permisos y validación del servidor. Usa este acceso para configurar y probar antes de aceptar la entrega.
4. Debe existir la configuración pública de la edición: URL y clave **publicable** de Supabase, en `gymsoft_config.json` o en las variables de `.env.example`. Un archivo `.env.example` no se carga automáticamente. Comercial cuenta con `INICIAR_CONFIGURACION.bat`. Los tres `gymsoft_config.json` están recuperados y pasan su validación estructural. ZTATTUZ conserva la URL `https://srmquhwpawgipncmvfjf.supabase.co` y la clave publicable de ese proyecto; si utilizas una configuración propia, conserva una copia antes de actualizar. Nunca copies service_role ni secretos de Wompi/Meta al escritorio.

El aviso `Entrega bloqueada. Falta comprobar: …` proviene de la aceptación final, no de pip o Python. El batch actualizado lo detecta y continúa por el modo de instaladores para configuración y pruebas descrito al principio de esta guía. Los accesos desde fuentes siguen disponibles y conservan autenticación y permisos.

## Generar la entrega final después de aceptar la versión

Los prerrequisitos de compilación son los mismos que para los instaladores de configuración. `CREAR_INSTALADORES.bat` llama a los preparadores e instala `requirements-build.txt` automáticamente. Configurar únicamente URL/llave publicable mediante `INICIAR_CONFIGURACION.bat` donde exista o el configurador de la edición. Revisar las migraciones; no ejecutar un esquema inicial sobre una base existente ni reaplicar actualizaciones antiguas después de las nuevas.

Después de completar los pilotos, el servidor actual y la aceptación física, registrar evidencia de la versión para cada criterio aplicable en `release_readiness.json`; no poner todos los valores en true sin pruebas. Ejecutar de nuevo `CREAR_INSTALADORES.bat`: al aprobar la aceptación llama a `build_windows.py`, valida arquitectura, pruebas e icono embebido y genera la entrega final en `salida`. El panel/instalador Propietario de Comercial es privado y nunca se entrega al cliente.

Esta instancia Linux no genera instaladores finales ni acredita los criterios externos/hardware. Los backups públicos de fuentes contienen el estado recuperado; los redistribuibles propietarios se incorporan a la aplicación conforme a su EULA. Los paquetes técnicos de prueba no sustituyen la aceptación final.

## Transferencia de archivos grandes

El SDK ya fue recuperado usando las siete partes. `tools/partir_archivo.py` queda disponible para otros ZIP autorizados que superen el límite de 32 MiB de transferencia: selecciona el original y crea ZIP de hasta 25 MiB, sin modificarlo ni sobrescribir partes. La reconstrucción valida los hashes de cada parte, el archivo completo y el CRC. No repetir esa transferencia para el SDK ya recuperado.

## Validación Windows en GitHub

`.github/workflows/windows-validation.yml` usa Windows 2022 y Python 3.14 de la arquitectura de cada edición. Ejecuta el preparador batch, dependencias y pruebas offline completas; compila los programas reales y los instaladores técnicos, con DigitalPersona original incorporado, diagnósticos e iconos PE. Los informes se conservan en artifacts y en ramas de evidencia; `evidence/windows-actions` mantiene las copias recuperadas con commit y alcance. El workflow mantiene la aceptación final intacta.

El run `37876923101` aprobó las 111 etapas completas de las tres ediciones con Python 3.14.8 x64/x86 y los probes congelados. El run `37879953403`, commit `ea5a2ed`, aprobó los siete EXE y ocho instaladores; ZTATTUZ x86 aprobó además sus 37 etapas actuales y 165 tests. Las instalaciones x64 se detuvieron en una ruta QA demasiado larga; la repetición con una ruta corta está pendiente. El Runtime x86 figura como `NOT_RUN` en un anfitrión Windows x64 por la condición original de su MSI. Ninguna de estas pruebas usa un lector/relé físico ni acredita las cuentas Meta/Wompi. La API de Actions está accesible en la instancia actual; los bloqueos anteriores se conservan como resultados históricos.


El run `37998368137` aprobó los tres jobs, 111 etapas y 484 tests Python mediante `CREAR_INSTALADORES.bat`; Comercial y ZTATTUZ x64 también aprobaron instalación y desinstalación con DigitalPersona. ZTATTUZ comprobó además actualización desde el instalador completo. Los registros originales están en `evidence/windows-actions/37998368137`. Esta evidencia no certifica el lector físico ni los pilotos externos.
