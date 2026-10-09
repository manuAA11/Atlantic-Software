# Multi-Gym: cierre de recuperación, 8 de octubre de 2026

Estado revisado el **9 de octubre de 2026**; la fecha del título identifica la recuperación y sus evidencias históricas.

**Estado: código recuperado; compilación Windows de los siete programas y ocho instaladores técnicos aprobada. La instalación real se está verificando; la aceptación final de integraciones, servidor y hardware sigue pendiente.** Este informe sustituye las afirmaciones de estado del informe histórico, que se conserva como evidencia de aquella ejecución.

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

La prueba de instalación del run `37879953403` se detuvo en Comercial y ZTATTUZ x64 durante la instalación en una ruta QA de aproximadamente 300 caracteres. Se está repitiendo con una ruta corta dentro de `RUNNER_TEMP`; los resultados FAIL originales se conservan y no se declara aprobada la instalación, actualización ni desinstalación completa. En ese mismo run el Runtime x86 corresponde a `NOT_RUN`, porque el sistema anfitrión es x64. La compilación y las 37 etapas actuales de ZTATTUZ x86 aprobaron, incluidos sus 165 tests en un proceso Python de 32 bits; instalar su MSI requiere Windows de 32 bits.

El modo `--para-configurar` del helper, utilizado automáticamente por `CREAR_INSTALADORES.bat` cuando falta aceptación final, exige un nuevo `run_validation.py` completo y todas las compilaciones/diagnósticos aprobados antes de publicar archivos. La publicación verifica hashes, conserva ejecuciones anteriores y coloca el panel Comercial en `PRIVADO_PROPIETARIO`; ese instalador no se entrega a clientes. WhatsApp/Wompi se configuran desde la aplicación instalada y su backend, con autenticación y permisos normales. Este modo no modifica readiness ni acredita las pruebas externas pendientes.

Las suites unitarias actuales en Linux/CPython 3.14 aprobaron **484 tests** (Comercial 153, ZTATTUZ x86 165, x64 166), incluidos diagnóstico y aplicabilidad del gate. El recibo de sus ejecuciones está en `evidence/packaging-qa-20261008/local-unittest-receipt.json`; registra la finalización observada de las herramientas, no un log nativo de Windows. Los 111 stages Windows y probes anteriores corresponden al commit indicado en sus informes. ZTATTUZ x86 tiene además el recheck actual de 37 etapas mencionado arriba; la repetición completa de Comercial/x64 y del nuevo flujo batch queda pendiente.

## Bloqueos concretos y entrega

1. El proxy de esta instancia bloqueó las consultas públicas de health a ambos Supabase antes de llegar al servicio. Las dos entradas de red se guardaron en el borrador del entorno; necesitan aplicación/publicación desde su configuración y una nueva comprobación de conexión.
2. No hay cuentas/número Meta ni Wompi Sandbox disponibles aquí para acreditar los pilotos. La habilitación de plataforma, conexión desde la app y prueba conjunta están detalladas en `docs/INTEGRACIONES_Y_WINDOWS.md`. Los secretos se introducen únicamente en el host/Vault o formulario privado; no por chat.
3. El SDK DigitalPersona 3.4.0 se reconstruyó desde las siete partes adjuntas, verificando SHA-256 y CRC. Incluye los redistribuibles completos x64 y x86: se integraron localmente con MSI, CAB, bootstrapper, prerrequisitos y licencia originales. No falta volver a pedir el SDK. La procedencia, hashes y preparación reproducible están en `docs/DIGITALPERSONA_RESTAURADO.md`; la distribución del Runtime se limita a incorporarlo a la aplicación conforme a su EULA.
4. El usuario confirma que la huella funciona en su instalación actual; se conserva su código. Los nuevos EXE e instaladores aprobaron compilación y diagnóstico de componentes en Windows. Se está verificando la instalación nueva; continúan pendientes lector/relé físicos, aceptación de la versión y concurrencia/scheduler contra el servidor actual. La evidencia histórica parcial y la confirmación sobre la instalación anterior no certifican esos resultados nuevos.

Se comprobaron respaldos extraídos en carpetas independientes: imports aislados y flujo HTTP/SQL PASS, instalando node_modules en cada una. Los hashes de las fuentes runtime coinciden con el checkout; evidencia en `evidence/closure-validation-20261008/independent-backups.json`.

Los respaldos publicados en Git incluyen **aplicaciones completas desde las fuentes en desarrollo**: fuentes recuperadas, assets, tests, requirements, migraciones, configuración pública, .env.example y guías. Incorporan los Runtime originales bajo cada edición, con sus EULA y términos; no requieren reconstruir archivos MSI/CAB. El helper comprueba CRC e inventario SHA-256 de todo el contenido. También se conserva la alternativa de respaldo de fuentes. Ningún paquete contiene venv/node_modules ni secretos, ni acredita aceptación externa. Los detalles y verificación están en `docs/PAQUETES_APLICACION_COMPLETA.md`. `CREAR_INSTALADORES.bat` permite instalar para configurar y probar antes de la entrega final; `release_readiness.json` conserva los criterios externos pendientes. Las instrucciones exactas y procedimientos de aceptación están en la guía enlazada.

El entorno de desarrollo Linux/Tk/PGlite está comprobado. `install_script` y `start_skill` se actualizaron y guardaron como borrador con Python 3.14.7/Tk 9.0.4 y Python 3.13.15, ambos con ensurepip, requisitos build y lockfile. La instalación completa se repitió y el arranque Tk se comprobó. Esa persistencia no equivale a publicar el snapshot ni valida una máquina futura. El usuario debe revisar/publicar en la configuración del entorno para conservarlo.
