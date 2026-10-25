# Multi-Gym: cierre de recuperación, 8 de octubre de 2026

Estado revisado el **14 de octubre de 2026**; la fecha del título identifica la recuperación y sus evidencias históricas.

**Corrección del acceso, 24 de octubre de 2026 (3.8.1):** los errores recuperables
de sesión y contraseña regresan directamente al formulario, conservando el correo.
Se elimina el cuadro Reintentar/Cancelar que podía restaurar otra vez la sesión
fallida o cerrar el inicio. Se limita la espera por un token todavía no válido.
La publicación sigue siendo opcional y NO FINAL; instalación en Windows de 32
bits y lector/relé físicos pendientes. Detalle y verificación:
[Recuperación del acceso 3.8.1](RECUPERACION_ACCESO_3.8.1.md).

**Auditoría posterior de tokens:** se reproduce y corrige una sincronización
incompleta del SDK al cargar la sesión renovada por otro proceso, y se elimina
la rotación forzada de una sesión vigente al arrancar. El rechazo persistente
PGRST303 del proveedor es una incidencia distinta; el acceso real no se declara
recuperado con estas pruebas locales. [Alcance y verificación](SINCRONIZACION_SESIONES.md).

**Estado: código recuperado; creación Windows de siete programas y ocho instaladores aprobada. Instalación nueva, actualización y desinstalación x64 aprobadas; ZIP de configuración publicados y verificados. La aceptación final de integraciones, servidor y hardware sigue pendiente.** Este informe sustituye las afirmaciones de estado del informe histórico, que se conserva como evidencia de aquella ejecución.

**Incidencia del relé USB comunicada el 14 de octubre:** botón de salida
operativo y asistencia registrada, pero sin activación del relé desde el PC de
32 bits. El restablecimiento muestra fallo USB, estado desconocido y última
orden `—`. Se mejora el diagnóstico de las fuentes para conservar fase
y código del error; la causa física/Windows y su resolución siguen pendientes.
El usuario está revisando conexiones antes de continuar las pruebas.
[Estado y prueba del puerto](DIAGNOSTICO_RELE_USB_WINDOWS.md).

**Incidencia del 14 de octubre: Dashboard sin información.** El usuario muestra
clientes y estadísticas existentes, pero el panel falla al cargar. Confirmó que
solo instaló el programa, sin aplicar los dos upgrades nuevos de Supabase.
La corrección separa cargas y muestra datos desconocidos/diagnóstico; el código
necesita un build posterior a `7a44de8`. Posteriormente, el usuario comunicó la
aplicación exitosa del SQL en ZTATTUZ mediante
`membership_internal_staff_and_early_resume`, conservación de registros/importes
y pruebas SQL transaccionales de STAFF y reanudación aprobadas con datos de prueba
revertidos. Esta sesión cloud no lo verificó directamente. Queda comprobar
Dashboard y guardado de planes en el programa instalado; no se publicaron nuevos
instaladores por este reporte. [Estado, procedencia y siguiente comprobación](SOLUCION_PANEL_SIN_DATOS.md).

## Cambio posterior: STAFF y reanudación anticipada

El historial Windows descrito abajo corresponde al código anterior a estos cambios. La rama `feature/internal-plans-early-resume` incorpora planes internos no comerciales, métricas comerciales separadas de la asistencia del personal, y extensión por días completos efectivamente congelados. Guía, migraciones y alcance de validación: [MEMBRESIAS_STAFF_REANUDACION.md](MEMBRESIAS_STAFF_REANUDACION.md). No se aplicaron cambios a proyectos Supabase reales al registrar esta ampliación; después el usuario solicitó los nuevos instaladores de todas las aplicaciones. El run `38495253410`, commit `24ca689`, aprobó las 111 etapas Windows, 499 tests Python y compilación de siete programas/ocho instaladores con estos cambios. Las descargas nuevas están en `configuracion-pruebas-24ca689`; conservan el alcance NO FINAL, instalación x86 pendiente en Windows32 y los upgrades/deploy del servidor pendientes.

## Recuperación verificada

El ZIP original se conserva fuera del checkout, con SHA256 `28ed79ae1d1a9d67c2612e3a44f6b5dc5d845b1c77b59e81dfe4abec0e4ea19b`. Se importaron todas sus fuentes de Comercial 3.6.0 y ZTATTUZ 3.6.1 x86/x64 a Git. El primer checkpoint se publicó en main como `abe9dda6063c7dda10966cbb45d0674ea6762a6f`.

Se compararon fuentes originales, manifiestos/evidencias adjuntas y el historial accesible de los chats anteriores. Los cuatro scripts de migración originales mantienen sus bytes. Un documento de estado ya difería del manifiesto dentro del ZIP original; no se considera un cambio perdido de código.

Del hilo `01a1195a-6aa3-7056-a174-ffd75dd140d7` se recuperaron cambios posteriores al ZIP:

- Turno `01a11cb7-12ca-735d-98f0-b7815a9d679d`: resolución de `extensions.gen_random_bytes` y generador de migración correctiva del scheduler.
- Turno `01a11cc2-48af-717e-9838-1b3d5d3fcbf2`: rutas del gateway Edge, dos regresiones HTTP adicionales, índices de Marketing/congelación y script completo de pruebas aisladas de concurrencia PostgreSQL con sus tres correcciones posteriores.

Los dos archivos de evidencia remota del último turno se recibieron truncados. Sus fragmentos y procedencia están en `evidence/history-recovered-20261008.json`; no se reconstruyeron inventando contenido. El 9 de octubre se pudo abrir el chat compartido original completo y comparar 82 sustituciones posteriores al ZIP: 77 coinciden y cinco corresponden a mejoras posteriores presentes en el repositorio. No se encontraron cambios funcionales verificables perdidos de ese período. La huella, congelación, reloj del servidor y bloqueo del relé están conservados; la auditoría sanitizada está en `evidence/shared-chat-audit-20261009.json`. Hay 28 cuerpos de parches ocultos y evidencia redactada; **esto no garantiza identidad byte a byte con el último entorno remoto**.

## Ediciones y sincronización

- **Atlantic Gym Comercial 3.6.0:** Administrador, Recepción y panel privado del propietario; licencias, suscripciones, invitaciones y equipos aprobados son exclusivos de Comercial. Se conserva su ausencia de relé/apertura de puerta.
- **Atlantic Gym · ZTATTUZ 3.6.1 x86/x64:** Administrador y Recepción, compatibilidad con la base ZTATTUZ anterior y control del relé. La arquitectura del loader nativo, Python/build e instalador se conserva por edición.
- El inventario de sincronización de la recuperación registró 32 comparaciones de archivos PASS y 30 de 45 módulos Python con el mismo nombre idénticos en las tres ediciones. Las diferencias de app/cloud/licencia, arquitectura y puerta se conservan. Ese inventario histórico está en `evidence/closure-validation-20261008/parity.json`; las correcciones posteriores incorporan diagnóstico Comercial y helpers de empaquetado comunes, con validación separada.

## Atlantic UI Kit, branding e iconos

Políticas permanentes en `AGENTS.md`, especificación en `docs/ATLANTIC_UI_KIT.md` y tokens compartidos en `common/atlantic_ui.py`, copiados a cada edición independiente. Se conservan el diseño oscuro aprobado, navegación, tarjetas, formularios, diálogos, inputs, estados y componentes existentes. La fuente es nativa: Segoe UI en Windows, system en macOS; no se distribuye SF Pro.

Administrador utiliza el G azul y Recepción el G cian de la referencia aprobada. Se recrearon assets aislados de la lámina visible: no son los archivos maestros originales ni recortes exactos. La procedencia está en `assets/atlantic/README.md`. Se aplican a ventanas principales, login/diálogos, selección del icono PyInstaller, metadatos PE y recursos/accesos directos de los futuros instaladores. Firma discreta: `© Atlantic Tech Software — All rights reserved. By Manuel Cuellar`. IDs, nombres técnicos y directorios de actualización se conservan.

Se corrigieron el desbordamiento de la barra lateral al 125 % y un icono de acceso directo de Recepción declarado pero no instalado en Comercial. Las pruebas Tk y recursos de instaladores pasan. El run Windows `37879953403` verificó arquitectura e iconos PE de los siete EXE reales y sus diagnósticos; la instalación efectiva se comprueba por separado.

## Funciones recuperadas

Congelación por siete días, extensión de vencimiento, una por membresía salvo excepción con motivo, denegación de acceso mientras está congelada, reactivación y conservación de cupos permanecen en el servidor. Las tiqueteras descuentan una vez por día del gimnasio. Las pruebas cubren límites de fecha, cancelación, excepción y renovación durante congelación.

Calendario DATE, instantes TIMESTAMPTZ, zona del gimnasio y America/Bogota de ZTATTUZ se conservan. Importación, auditoría y presentación no inventan horas de medianoche. Scheduler, recordatorios y chatbot consultan estados del servidor. La nueva migración del scheduler es aditiva; no reescribe la original.

WhatsApp, chatbot, automatizaciones y Wompi tienen pantallas conectadas al backend, autorización, Vault, consentimiento, verificación de identidad, firma de eventos, reintentos/estados y operaciones idempotentes. La prueba adicional conecta el handler HTTP y estas funciones con SQL migrado: pregunta por membresía, verifica identidad, informa congelación, genera enlace y aplica un pago firmado sin renovación duplicada. Meta/Wompi y Vault son fixtures de esa prueba. **Las integraciones no se declaran terminadas sin el piloto real.**

El actualizador manual de Marketing fallaba al reaplicarse por políticas y triggers existentes. Se corrigieron los scripts compartidos/de las tres ediciones; el generador conserva migraciones históricas. La prueba adicional de recompilación/reaplicación pasa. Se debe respetar el orden de actualizaciones; no reaplicar un script antiguo después de uno nuevo que redefine funciones.

## Pruebas de esta instancia

La regresión completa anterior se ejecutó con Python 3.13.5, Tk 8.6.16, Node 24.19.0 y PGlite 0.5.8. Dependencias instaladas con lockfiles; setup repetido y arranque de display con Tk comprobados. La tabla conserva el alcance de esa ejecución; los rechecks actuales aparecen después. No se usaron datos ni cobros reales.

| Edición | Etapas datos | Etapas gráficas | Total etapas | Tests Python | Tests backend | Congelación SQL | Tiempo SQL | Marketing SQL | Flujo HTTP/SQL |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Comercial | 20 PASS | 18 PASS | 38 PASS | 137 PASS | 56 PASS | 52 PASS | 55 PASS | 90 PASS | 28 PASS |
| ZTATTUZ x86 | 19 PASS | 19 PASS | 38 PASS | 156 PASS | 56 PASS | 52 PASS | 55 PASS | 87 PASS | 28 PASS |
| ZTATTUZ x64 | 19 PASS | 19 PASS | 38 PASS | 157 PASS | 56 PASS | 52 PASS | 55 PASS | 87 PASS | 28 PASS |

**114 etapas aprobadas y 450 pruebas Python.** Las columnas internas están incluidas en las etapas y no se suman como casos únicos. El backend es compartido; sus 56 tests se ejecutan por edición. Se ejecutaron contratos, migraciones, seguridad, permisos, clientes/pagos, importación, huellas, simulación de jornada, fechas/logs, freeze, tiqueteras, Marketing, pruebas gráficas y branding.

El primer run completo detectó iconos ausentes y desbordamiento gráfico. Se conserva su resultado FAIL. Tras corregirlos se repitió Python y toda la UI, además de las suites SQL afectadas y comprobaciones nuevas. El resumen final combina estos resultados explícitamente y enlaza cada log: `evidence/closure-validation-20261008/summary.json`. No se borraron ni transformaron los FAIL originales en PASS.

## Compatibilidad de Python y diagnóstico Windows

Se admite CPython 3.13/3.14 estándar con la arquitectura de cada edición. Preparador y build comparten la validación; se reconoce el launcher, PATH y Python Install Manager. Una `.venv` incompatible se conserva como `.venv_respaldo_<fecha>_<id>`; la configuración pública no se modifica. Las pruebas nuevas verifican creación real en ruta con espacios, reutilización, conservación de archivos, rechazo de arquitectura/versión incompatible y aceptación 3.14 seguida del gate final.

Se ejecutaron **450 tests con CPython 3.13.15 y otros 450 con 3.14.7**, además de **56 etapas de UI con 3.14/Tk 9.0.4**. Se resolvieron y descargaron 40 wheels de dependencias/build para Windows cp314 x64 y 40 para x86. Un entorno 3.12 real se sustituyó por 3.14 desde CLI conservando el entorno anterior y la configuración. Un programa de prueba con PyInstaller 6.22.2 abre Tk/Pillow e importa Supabase, openpyxl, pyserial y cryptography en Linux. El primer empaquetado detectó `PIL._tkinter_finder` ausente; se añadió como hidden import en las tres ediciones y se conservó el FAIL junto al recheck PASS.

El primer run de creación con el Python 3.13.5 del sistema falló por falta de `ensurepip`; se conservan esos logs. El recheck completo usa una distribución 3.13.15 con ensurepip. No se saltaron tests ni se simularon las creaciones. Evidencia: `evidence/closure-validation-20261008/python-compatibility.json`. La resolución de wheels no acredita ejecución en Windows; las suites de fuentes x86 en Linux corren en un proceso x64. No se promete cualquier versión, PyPy o free-threaded.

GitHub Actions ejecutó las tres ediciones en Windows Server 2022 con CPython 3.14.8. Los 450 tests Python aprobaron, incluida la edición ZTATTUZ x86 en un proceso real de 32 bits. Se corrigió la comparación de rutas de `windows_ui_smoke`: el selector devuelve la ruta resuelta y la prueba esperaba el texto sin resolver. La repetición confirmó ese arreglo y avanzó hasta la etapa 35. Después se preparó un escritorio Windows amplio y se detectó un desbordamiento real del Dashboard al 125 %. Se ajustaron el ancho de sus iconos métricos y su margen horizontal, conservando texto, fuente y cuatro columnas. El run `37861669196` (commit `becc44a`) aprobó las 37 etapas completas de cada edición: **111 etapas Windows PASS**, incluidos los 450 tests Python, datos y UI. El probe congelado posterior falló al resolver iconos relativos desde su nueva carpeta de spec; se reprodujo el error con PyInstaller y se corrige usando rutas absolutas. El recheck `37876923101` confirmó compilación, icono PE y ejecución de los tres probes congelados con PASS (x64 y x86), y volvió a aprobar las 111 etapas completas. El job conservó un FAIL global por el código 1 esperado del gate; se corrige únicamente la salida del workflow tras verificar ese bloqueo. Los informes FAIL y PASS se conservan con commit y alcance en `evidence/windows-actions`. Estas suites no acreditan instaladores ni hardware.

Los tres `gymsoft_config.json` publicables están presentes desde el checkpoint recuperado `abe9dda` y pasan la validación estructural de cada producto. No falta recuperar esos archivos. Esa comprobación no equivale a conectarse al servidor ni a verificar credenciales privadas de integraciones.

El log Windows aportado por el usuario instaló correctamente dependencias con Python 3.13 x64 y se detuvo en `Entrega bloqueada. Falta comprobar: …`. Ese mensaje corresponde a aceptación final pendiente. `CREAR_INSTALADORES.bat` comprueba la aceptación: si está aprobada, construye la entrega final; mientras está pendiente, genera instaladores reales identificados para configuración y pruebas después de repetir todas las validaciones locales. Estos últimos quedan en `salida/PRUEBAS_PARA_CONFIGURAR/<identificador>/`, con prefijo `VALIDACION_NO_FINAL_`. Los accesos `INICIAR_ADMINISTRADOR.bat`/`INICIAR_RECEPCION.bat` permiten también configurar/probar desde fuentes con autenticación y permisos normales. El gate conserva todas las aceptaciones aplicables. Se corrigió únicamente el requisito de relé de Comercial: queda `not_applicable`, `passed:false`, con prueba versionada de identidad y ausencia de esa función; ZTATTUZ sigue requiriendo relé físico. Los demás criterios no se modifican.

## Empaquetado e instalación técnica

Los tres builders comparten su camino de compilación real con `tools/windows_packaging_qa.py`, usan rutas absolutas de datos/iconos y verifican arquitectura PE. La entrada de producción mantiene la aceptación antes de compilar. El helper técnico compila Administrador/Recepción y el panel privado Comercial en una salida separada marcada NO FINAL; registra comandos, errores, hashes y diagnósticos sin red/cuentas. Comercial incorpora el mismo contrato de diagnóstico de componentes de ZTATTUZ en sus tres entradas, sin cambiar el acceso normal.

El run GitHub Actions `37879953403`, commit `ea5a2ed`, aprobó la compilación de **siete EXE reales y ocho instaladores Inno**: Comercial produce tres programas y dos instaladores; cada ZTATTUZ produce dos programas y tres instaladores. Los siete ejecutables completaron su diagnóstico de componentes en Windows con Python 3.14.8 de la arquitectura correspondiente. Los informes con comandos, hashes y alcance están en `evidence/windows-actions/37879953403/<edición>/paquete-tecnico/informe_empaquetado.json`. Ese resultado acredita compilación y diagnóstico, no la instalación completa ni un piloto con cuentas reales. Las ejecuciones anteriores permanecen intactas para comparar los arreglos.

Los ocho scripts Inno presentan la EULA original y ya no ofrecen DigitalPersona como paso opcional omitido en instalaciones silenciosas. Comprueban bibliotecas, versión/arquitectura, códigos de resultado y reinicio; conservan un Runtime igual o más nuevo compatible. Comercial exige Windows 10, y su cliente requiere x64 nativo por el Runtime. ZTATTUZ x86 conserva Windows de 32 bits: su MSI original rechaza Windows de 64 bits. Los IDs y directorios históricos permanecen.

La prueba de instalación del run `37879953403` se detuvo en Comercial y ZTATTUZ x64 durante la instalación en una ruta QA de aproximadamente 300 caracteres. Se corrigió la raíz técnica dentro de `RUNNER_TEMP`; el run `37998368137` aprobó instalación nueva y desinstalación x64, y actualización ZTATTUZ. Los resultados FAIL originales se conservan. x86 mantiene instalación `NOT_RUN` porque el sistema anfitrión es x64; instalar su MSI requiere Windows de 32 bits.

El run `38001250527`, commit `fe2a95b2413caf1567afe688b2b80af060d27615`, aprobó los tres jobs: **111 etapas, 484 tests Python, siete EXE y ocho instaladores**, además de 53 pruebas auxiliares por job. Comercial cliente/Propietario y ZTATTUZ x64 aprobaron instalación nueva, actualización sin reemplazar la ubicación anterior, registros y accesos sin duplicados, diagnósticos instalados, DLL originales DigitalPersona y desinstalación. ZTATTUZ x64 utilizó el wrapper completo para instalación nueva y actualización. Las 111 etapas y sus hashes conservan exactamente sus bytes Windows en `evidence/windows-actions/38001250527`; la instalación x86 permanece `NOT_RUN`. Se conserva también el FAIL `38000930440`, causado por un fixture que mezclaba rutas Windows cortas/completas, corregido sin aflojar las comprobaciones de producción.

Los [ZIP de instaladores para clientes](https://github.com/manuAA11/Atlantic-Software/releases/tag/configuracion-pruebas-fe2a95b) están publicados y marcados NO FINAL. Se descargaron los tres y se comprobaron CRC, todos los hashes internos, tamaño/digest de GitHub, commit y run ID; evidencia en `evidence/installer-downloads-20261009.json`. El panel Propietario no está en los ZIP públicos. El PC donde se instalan no requiere Python, Node ni Inno. El alcance sigue siendo configuración/pruebas, sin acreditar cuentas reales ni hardware físico.

El modo `--para-configurar` del helper, utilizado automáticamente por `CREAR_INSTALADORES.bat` cuando falta aceptación final, exige un nuevo `run_validation.py` completo y todas las compilaciones/diagnósticos aprobados antes de publicar archivos. La publicación verifica hashes, conserva ejecuciones anteriores y coloca el panel Comercial en `PRIVADO_PROPIETARIO`; ese instalador no se entrega a clientes. WhatsApp/Wompi se configuran desde la aplicación instalada y su backend, con autenticación y permisos normales. Este modo no modifica readiness ni acredita las pruebas externas pendientes.

Las suites unitarias en Linux/CPython 3.14 aprobaron **484 tests** (Comercial 153, ZTATTUZ x86 165, x64 166), incluidos diagnóstico y aplicabilidad del gate. El recibo está en `evidence/packaging-qa-20261008/local-unittest-receipt.json`; registra la finalización observada de las herramientas. El run Windows `38001250527` repitió esos 484 tests y las 37 etapas por edición mediante el `.bat` real; sus logs nativos se preservan separadamente y corresponden al commit indicado.

## Disponibilidad y aceptación pendiente

1. La denegación inicial de red quedó superada en esta instancia. Ambos Supabase respondieron health HTTP200 con base/scheduler disponibles; la conexión pública Comercial y los diagnósticos de red de las tres ediciones aprobaron. Se corrigió el contexto TLS agregando certifi a las CA del sistema, conservando verificación de certificado/hostname. Evidencias: `evidence/live-health-20261009.json` y `evidence/network-diagnostic-20261009`. Estas consultas públicas no acreditan sesiones autenticadas, pilotos ni concurrencia real.
2. No hay cuentas/número Meta ni Wompi Sandbox disponibles aquí para acreditar los pilotos. La habilitación de plataforma, conexión desde la app y prueba conjunta están detalladas en `docs/INTEGRACIONES_Y_WINDOWS.md`. Los secretos se introducen únicamente en el host/Vault o formulario privado; no por chat.
3. El SDK DigitalPersona 3.4.0 se reconstruyó desde las siete partes adjuntas, verificando SHA-256 y CRC. Incluye los redistribuibles completos x64 y x86: se integraron localmente con MSI, CAB, bootstrapper, prerrequisitos y licencia originales. No falta volver a pedir el SDK. La procedencia, hashes y preparación reproducible están en `docs/DIGITALPERSONA_RESTAURADO.md`; la distribución del Runtime se limita a incorporarlo a la aplicación conforme a su EULA.
4. El usuario confirma que la huella funciona en su instalación actual; se conserva su código. Los nuevos EXE e instaladores x64 aprobaron compilación, instalación, actualización, diagnóstico y desinstalación en Windows Server 2022. Continúan pendientes la comprobación en su Windows con lector/relé físicos, aceptación de la versión y concurrencia/scheduler contra el servidor actual. La instalación x86 requiere validación en Windows32. La evidencia histórica parcial y la confirmación de la instalación anterior no certifican esos resultados nuevos.

Se comprobaron respaldos extraídos en carpetas independientes: imports aislados y flujo HTTP/SQL PASS, instalando node_modules en cada una. Los hashes de las fuentes runtime coinciden con el checkout; evidencia en `evidence/closure-validation-20261008/independent-backups.json`.

Los respaldos publicados en Git incluyen **aplicaciones completas desde las fuentes en desarrollo**: fuentes recuperadas, assets, tests, requirements, migraciones, configuración pública, .env.example y guías. Incorporan los Runtime originales bajo cada edición, con sus EULA y términos; no requieren reconstruir archivos MSI/CAB. El helper comprueba CRC e inventario SHA-256 de todo el contenido. También se conserva la alternativa de respaldo de fuentes. Ningún paquete contiene venv/node_modules ni secretos, ni acredita aceptación externa. Los detalles y verificación están en `docs/PAQUETES_APLICACION_COMPLETA.md`. `CREAR_INSTALADORES.bat` permite instalar para configurar y probar antes de la entrega final; `release_readiness.json` conserva los criterios externos pendientes. Las instrucciones exactas y procedimientos de aceptación están en la guía enlazada.

El entorno de desarrollo Linux/Tk/PGlite está comprobado. `install_script` y `start_skill` se actualizaron y guardaron como borrador con Python 3.14.7/Tk 9.0.4 y Python 3.13.15, ambos con ensurepip, requisitos build y lockfile. La instalación completa se repitió y el arranque Tk se comprobó. Esa persistencia no equivale a publicar el snapshot ni valida una máquina futura. El usuario debe revisar/publicar en la configuración del entorno para conservarlo.

La revisión de puerta solicitada el 14 de octubre está en [CONTROL_PUERTA_ESTADO.md](CONTROL_PUERTA_ESTADO.md). Añade watchdog, debounce previo al RPC, diagnóstico y capa opcional común; los instaladores de `24ca689` preceden a esa revisión. Las pruebas Windows y descargas nuevas deben corresponder al commit posterior de puerta, sin sustituir el historial anterior.

Revisión de puerta completada por software: run `38555801086`/commit `7a44de8`, 111 etapas y 599 tests Python Windows aprobados. Instaladores actualizados en [configuracion-pruebas-7a44de8](https://github.com/manuAA11/Atlantic-Software/releases/tag/configuracion-pruebas-7a44de8), con alcance NO FINAL y [checklist presencial](../PRUEBA_PUERTA_ZTATTUZ.md). Detalle/descarga separada de Propietario y su alcance de verificación en [CONTROL_PUERTA_ESTADO.md](CONTROL_PUERTA_ESTADO.md).

## Incidencia prioritaria del 15 de octubre: relé y Bluetooth

El usuario pidió pausar Tienda/POS: la primera entrada abre, la música Bluetooth
se interrumpe al activar el relé y las siguientes entradas se registran sin
abrir. Indicó un adaptador USB en la conexión del relé, sin confirmar su tipo.
Todavía no se recibió el diagnóstico de Windows. No se confirmó una causa
eléctrica, de controlador, de adaptador o de arquitectura de 32 bits.

Se corrigieron dos defectos reproducidos con USB simulado: cierre nativo capaz
de bloquear el hilo de interfaz, y liberación del bloqueo exclusivo antes de
terminar una limpieza concurrente. El cierre conserva el bloqueo hasta terminar,
marca estado desconocido si se atasca, intenta cancelación/OFF fuera de Tk y no
permite ON después de comenzar el cierre. Mantiene autorización, watchdog,
debounce, comandos y necesidad de restablecimiento explícito tras fallo.

Las tres ediciones aprobaron 69 pruebas de puerta cada una y 78 comprobaciones
de interfaz cada una: **207 pruebas unitarias y 234 comprobaciones gráficas**.
Esto es Linux/CPython/Tk con USB simulado, sin probar Windows32, Bluetooth ni el
relé del usuario. Se conservan reproducciones FAIL y resultados PASS en
`evidence/relay-cleanup-20261015`. La guía y el colector de estado Windows están
en [DIAGNOSTICO_USB_BLUETOOTH_32BITS.md](DIAGNOSTICO_USB_BLUETOOTH_32BITS.md).

Estas fuentes aún necesitan compilación Windows y prueba en el equipo afectado;
los instaladores publicados anteriormente no incorporan la corrección. El API
GitHub/Actions sigue rechazando la conexión de este entorno con `Forbidden`.
No se modificó `release_readiness.json` ni se acreditó aceptación de hardware.
El trabajo de Tienda permanece conservado como borrador en el entorno y en un
checkpoint local, sin generar instaladores ni retomar su implementación durante
la incidencia.


## Revisión de huella sin respuesta · 16 de octubre de 2026

Base revisada: `6755f49257ab44e795092dafb89a836cc5aabdc8`, checkpoint de
`wip/tienda-pos-20261015`, que conserva las correcciones recientes del relé.
El usuario reporta que ZTATTUZ x86 no reacciona al colocar el dedo y que el
relé funciona. No se dispone del diagnóstico ni del equipo afectado.

Se reprodujo un fallo de continuidad en `FingerprintPanel.poll`: cualquier
excepción de presentación (resultado de acceso, lista, editor o diálogo)
salía del callback antes de programar el siguiente `after`. Los nuevos
eventos dejaban de llegar a la pantalla y el estado de pausa podía quedar
sin actualizar. Esto es compatible con una interfaz que deja de reaccionar,
pero no confirma la causa del incidente físico ni un defecto exclusivo de x86.

La corrección procesa cada evento una sola vez, registra únicamente fase/tipo
de error y mantiene la programación del siguiente ciclo. Una incertidumbre
del servidor conserva la pausa; un fallo al consultar la modalidad también
pausa la captura hasta poder evaluar de nuevo su estado. Cerrar la aplicación
interrumpe el consumo y no programa callbacks nuevos. El mismo defecto estaba
en las tres ediciones: se aplica sólo el ciclo compartido, conservando las
variantes de lector y el callback propio de ZTATTUZ. No cambian el driver,
la exclusividad del lector, la autorización, las escrituras ni el relé.

Validación local, Linux x64 / CPython 3.12.14:

- Antes de corregir: las ocho regresiones iniciales fallaban (seis errores y
  dos aserciones), incluida la ausencia de un siguiente callback tras fallar
  la presentación de un ingreso.
- Después: **59 pruebas de huella PASS en ZTATTUZ x86**, **59 en ZTATTUZ x64**
  y **52 en Comercial**, mediante `unittest discover -s tests -p
  'test_fingerprint*.py'`. Se incluyen nueve regresiones nuevas por edición.
- La integración nueva usa el scheduler Tcl real, el trabajador de huella y
  `DoorDatabase`/`DoorController` reales, con lector, servidor y USB simulados.
  Después de provocar un fallo visual en el primer ingreso, procesa un segundo
  cliente y comprueba exactamente una escritura y un pulso por persona.
- Una primera ejecución conjunta de x86 terminó con `Tcl_AsyncDelete` por la
  recolección tardía del intérprete del test en un hilo distinto. Se corrigió
  la limpieza del fixture para finalizar Tcl en su hilo y se repitieron las
  tres suites con los resultados PASS anteriores; no se cambió producción
  para resolver ese fallo del test.

No se ha ejecutado esta corrección en Windows32 ni con un lector/relé físico.
No se modifica `release_readiness.json`, no se declara aceptación final y no
se generan instaladores. Queda pendiente comprobar el paquete instalado y el
diagnóstico de la máquina de ZTATTUZ para confirmar la causa del reporte.

### Compilación autorizada y bloqueo de tienda · 16 de octubre de 2026

El usuario autorizó publicar en `manuAA11/Atlantic-Software` la corrección,
pruebas, documentación y activación del workflow de Windows. Se publicó
`960de702068f3b721882b4eaba6d7141f8a69cb1` en
`fix/ztattuz-x86-fingerprint-checkin`. La ejecución `38938911835` comprobó las
tres ediciones con CPython 3.14; en x86 pasaron Python, SQL de huella, recorrido
de huella, puerta y las pruebas gráficas de huella. La validación completa se
detuvo al abrir Tienda en `performance_ui_smoke`, sin producir instaladores.

La causa identificada es `StorePosPanel.history_filters`: consultaba
`db._today()` en el hilo de Tk. La prueba rechaza toda consulta en ese hilo y
el aviso modal de error impedía que continuara. Ahora se capturan los filtros
en Tk y se resuelve la fecha del servidor en el trabajador antes de consultar
historial/estadísticas. No se sustituye el reloj del servidor por el del PC.
Se sincronizan las mejoras ya presentes del POS compartido a sus tres copias,
incluida la carga de productos después de conocer la disponibilidad de tienda.

Se añaden cuatro regresiones por edición para consultas fuera de Tk, filtros
capturados, fallo del reloj y rango inválido. Pasan localmente las 54 pruebas
de núcleo POS/filtros en x86 y las 27 pruebas de empaquetado/entrega. Se incluyen
en la validación completa las pruebas SQL POS/importación y la prueba gráfica
POS; la copia/restauración del propietario sólo corresponde a Comercial.
La entrega requiere ahora 40 etapas Windows en ZTATTUZ y 41 en Comercial,
con los mismos requisitos de hashes, frescura y ausencia de callbacks fallidos.
La prueba del instante de la venta compara instantes absolutos, admitiendo
offsets equivalentes sin admitir fechas sin zona. SQL POS: 68 comprobaciones
PASS; importación POS: 24 comprobaciones PASS en PGlite local x64.
No se modifica la aceptación final ni se acredita hardware real.

### Resultado Windows e instalador x86 · 16 de octubre de 2026

La ejecución `38979194277`, código
`9c1a6183ef214110dabddfce119f796bb6f00980`, terminó con **SUCCESS en las
tres ediciones**. ZTATTUZ x86: **40 etapas PASS**, **289 pruebas Python PASS**
con CPython 3.14.8 de 32 bits en Windows; pruebas SQL, interfaz, rendimiento,
huella, puerta simulada, tienda POS e importación incluidas. ZTATTUZ x64:
40 etapas PASS y 290 pruebas Python PASS. Comercial completó sus 41 etapas.
Los ejecutables, iconos, diagnósticos congelados y empaquetado técnico pasaron.
Las ediciones x64 aprobaron instalación, actualización y desinstalación en el
runner efímero. La instalación **x86 permanece NOT_RUN**: el MSI original
DigitalPersona exige `NOT VersionNT64`; el runner es Windows x64. Esto no
acredita una instalación en un sistema operativo Windows de 32 bits.

Se generó y descargó el instalador completo x86, que contiene los componentes
de Administración y Recepción y el runtime original. Se verificaron localmente
la estructura del ZIP, metadatos, hashes e identidad de ejecución mediante
`tools/windows_configuration_delivery.verify_delivery`: PASS. El archivo PE
del instalador es x86 (`0x14c`).

- Instalador: `VALIDACION_NO_FINAL_ZTATTUZ_Instalar_o_Actualizar_3.6.1_x86.exe`;
  97.428.026 bytes; SHA256
  `b50cc70dbe903f616daa9e57f25b3ef01405cd5b984fe66230a1e944c689da20`.
- Paquete: `AtlanticGym_ZTATTUZ_x86_PRUEBAS_PARA_CONFIGURAR_NO_FINAL.zip`;
  96.938.264 bytes; SHA256
  `e968dd01bdae7fdddd8c63c8f1a86dedb4c801b7a642953e6e78068ed5012931`.
- Evidencia: rama `ci/windows-evidence/38979194277/GymSoft_ZTATTUZ_3.6.1_x86`
  y artifact `12081031397`; artifact de entrega `12080996400`.

La extracción independiente mediante innoextract 1.9 no admite la versión del
contenedor Inno actual y no se usó para validar ni modificar el instalador.
La verificación de integridad contra el manifiesto original sí pasó. No se
modificó `release_readiness.json`. Es una entrega **NO FINAL para configurar
y probar**, pendiente de instalación Windows32, lector/relé físicos, servicios
externos y las demás aceptaciones ya descritas. No se ha confirmado que la
excepción corregida fuera la causa exacta en el equipo del gimnasio.


## Diseño League en Atlantic Gym — desarrollo

Se añaden League claro y League oscuro a Configuración → Apariencia, usando
los colores de la PWA y los componentes compartidos de escritorio. Se mantienen
Oscuro y Minimal y la preferencia local. Los botones, campos, tarjetas e iconos
circulares reutilizan el UI Kit; no se incorpora un navegador ni se cambia
la lógica de sesiones, datos o hardware. CSS no se ejecuta en Tkinter.

La caché de imágenes y fondos distingue las paletas para permitir alternarlas
sin conservar colores del tema anterior. Pruebas locales: persistencia y
conmutación real Tk en Administración/Recepción a escalas 100 y 125 %.
Pendiente: revisión visual completa de las pantallas reales en Windows x86/x64
y validación de publicación; estos cambios aún no están en el instalador ni
en el aviso de actualización. No se afirma una reproducción idéntica de la web:
la estructura de escritorio y los controles nativos se conservan.

Fluidez: la aplicación de apariencia agrupa controles nuevos y procesa sólo
los subárboles abiertos; ya no recorre todas las páginas ocultas cada vez que
aparece un control. Las lecturas existentes en segundo plano y las búsquedas
con pausa se conservan. Pendiente medir tiempos en el equipo Windows real;
no se garantiza equivalencia de animación con la PWA.

## Rutinas, clases, reservas y Configuración — pruebas

Desarrollo compartido: catálogo League reutilizado, 44 ejercicios y 8 plantillas
opcionales, editor con casillas y parámetros, asignación grupal, revisiones sin
borrado, calendario/lista, clases recurrentes, reservas e historial. Apariencia se
ubica sólo en Configuración en Administración y Recepción. Los coaches usan una
concesión explícita del gimnasio y no reciben privilegios administrativos.

Diagnóstico, archivos, migración, carga controlada, reversión y límites:
`docs/training/DIAGNOSTICO.md`, `IMPLEMENTACION.md` y `VALIDACION.md`.
No se aplica SQL ni se cargan ejemplos en ZTATTUZ. No se publica una actualización
remota ni se modifica `release_readiness.json`. La integración nativa con datos
sintéticos y los servicios source de League pasa. El run de League `40085884463`
aprobó 27 pruebas de integración, las carreras con dos backends PostgreSQL 17 y
8 pruebas de navegador sobre `66f1eba`. La matriz Windows de esta revisión y los
gates de publicación se registran en `docs/training/VALIDACION.md`; no se acredita
hardware ni aceptación productiva con estos fixtures. El run Windows `40085884474`
aprobó los tres perfiles, incluida instalación/actualización/desinstalación x64.
La instalación x86 permanece NOT_RUN por requerir Windows de 32 bits. El recheck
PWA `40086794784` volvió a aprobar 27 casos y 8 pruebas de navegador. Los
instaladores técnicos NO_FINAL no se publicaron en el actualizador del gimnasio.


## Candidata Atlantic Gym 3.8.0 — preparación de despliegue

Versión compartida x86/x64 en `pruebas`. Publicación desactivada; aceptación
3.8.0 pendiente. Preflight real de sólo lectura compatible, actualización de
entrenamiento aún sin aplicar al servidor. Ensayo de respaldos PostgreSQL con
22 tablas sintéticas aprobado en League `40103947068`, con 30 casos de integración
y 8 de navegador. Windows `40103947031` aprobó los tres perfiles, sus regresiones,
compilación y las instalaciones/actualizaciones/desinstalaciones x64. La instalación
x86 sigue NOT_RUN por requerir Windows de 32 bits. Los ZIP de cliente x86/x64 se
descargaron y comprobaron contra sus manifiestos y los informes originales de CI;
son NO_FINAL y no activan el aviso remoto. Evidencia:
`evidence/candidate-3.8.0-validation.json`; entrega: `docs/training/ENTREGA_3.8.0.md`.
Se corrigieron
los valores de versión Inno y las instrucciones ausentes detectados por los dos
runs previos. Guía y resultados en `docs/training`.
