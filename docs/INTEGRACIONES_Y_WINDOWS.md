# Acciones pendientes para cerrar la actualización

Las pantallas de Marketing de Administrador ya llaman al backend compartido. Recepción tiene las consultas y vinculación permitidas por su rol. La configuración por gimnasio se hará desde la aplicación; no se deben introducir claves en el código ni enviarlas por chat.

## Entorno cloud

En la configuración de este entorno, revisar y guardar el borrador de instalación/inicio y las dos entradas de red: `bawrakwhzkxmhmgkczqu.supabase.co` (Comercial) y `srmquhwpawgipncmvfjf.supabase.co` (ZTATTUZ). Después publicar el entorno para conservar el snapshot. Guardar el borrador no publica ni aplica automáticamente su red a esta máquina.

El intento de consultar `/functions/v1/marketing/health` fue bloqueado por el proxy (`Tunnel connection failed: 403 Forbidden`), antes de llegar al servicio. Tras aplicar la red, repetir esa consulta de lectura. Debe responder 200 con `ready`, `database` y `scheduler_installed` verdaderos. No hace falta una contraseña para ese endpoint. Comprobar la lista real de migraciones antes de desplegar; el historial parcial registra despliegues posteriores al informe original.

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

## Recursos DigitalPersona excluidos del ZIP

Recuperar el paquete original completo o el redistribuible autorizado del proveedor DigitalPersona/HID para U.are.U. Cada edición requiere `DigitalPersonaRuntime/setup.exe` y su árbol completo del instalador, sin separar sus MSI/CAB/DLL. Los loaders buscan `dpfpdd.dll` y `dpfj.dll` con arquitectura compatible: x86 para ZTATTUZ x86; x64 para Comercial y ZTATTUZ x64. No existe ese árbol en el material recuperado. No sustituirlo por archivos vacíos ni una DLL de una fuente no verificada.

Para continuar, hace falta la ubicación del paquete completo anterior o del redistribuible autorizado. Registrar procedencia, permiso de redistribución y SHA256 al incorporarlo. El driver real y la compatibilidad del lector solo se acreditan en Windows.

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
4. Debe existir la configuración pública de la edición: URL y clave **publicable** de Supabase, en `gymsoft_config.json` o en las variables de `.env.example`. Un archivo `.env.example` no se carga automáticamente. Comercial cuenta con `INICIAR_CONFIGURACION.bat`. ZTATTUZ debe conservar la URL `https://srmquhwpawgipncmvfjf.supabase.co` y la clave publicable de ese proyecto; recupera la configuración de tu instalación existente. Nunca copies service_role ni secretos de Wompi/Meta al escritorio.

El error `Entrega bloqueada. Falta comprobar: …` proviene de la aceptación final, no de pip o Python. `CREAR_INSTALADORES.bat` comprueba esos criterios antes de descargar dependencias de compilación y muestra los accesos anteriores. No cambiar `release_readiness.json` a true para quitar el mensaje. Puedes seguir usando las fuentes para completar las pruebas.

## Generar EXE e instaladores cuando se acepte la versión

Comercial usa CPython 3.13 o 3.14 x64; ZTATTUZ x86 y x64 usan una de esas versiones de su arquitectura. Instalar Tk, Node LTS e Inno Setup 6. En cada carpeta ejecutar `PREPARAR_PYTHON.bat` y `PREPARAR_PRUEBAS.bat`; instalar `requirements-build.txt`. Configurar únicamente URL/llave publicable mediante `INICIAR_CONFIGURACION.bat` donde exista o el configurador de la edición. Revisar las migraciones; no ejecutar un esquema inicial sobre una base existente ni reaplicar actualizaciones antiguas después de las nuevas.

Completar `release_readiness.json` con evidencia de la versión para cada criterio aplicable; no poner todos los valores en true sin pruebas. Solo entonces ejecutar `CREAR_INSTALADORES.bat`, que llama a `build_windows.py`, valida arquitectura, pruebas e icono embebido. Los outputs se generan en `salida`. El panel/instalador Propietario de Comercial es privado y nunca se entrega al cliente.

Esta instancia Linux no genera instaladores finales ni acredita los criterios externos/hardware. Los backups de fuentes contienen el estado recuperado, no reemplazan el redistribuible Windows ausente.
