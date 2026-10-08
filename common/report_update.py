"""Collect validation evidence and a reviewable development report, without releasing a build."""
from pathlib import Path
import base64
import hashlib
import html
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / 'outputs'
EVIDENCE = ROOT / 'evidence'
PRODUCTS = [
    ('Comercial', 'GymSoft_Comercial_3.6.0', 132, 90),
    ('ZTATTUZ x86', 'GymSoft_ZTATTUZ_3.6.1_x86', 147, 87),
    ('ZTATTUZ x64', 'GymSoft_ZTATTUZ_3.6.1_x64', 148, 87),
]

def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows])

def render_markdown(text):
    """Small renderer for this report's headings, tables, lists and paragraphs."""
    output, paragraph, listing = [], [], False
    def inline(value):
        value = html.escape(value)
        return re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
    def flush():
        if paragraph:
            output.append('<p>' + inline(' '.join(paragraph)) + '</p>')
            paragraph.clear()
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith('- ') and listing:
            output.append('</ul>'); listing = False
        if line.startswith('|'):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith('|'):
                rows.append([cell.strip() for cell in lines[i].strip('|').split('|')]); i += 1
            output.append('<div class="table-wrap"><table><thead><tr>' + ''.join('<th>' + inline(c) + '</th>' for c in rows[0]) + '</tr></thead><tbody>')
            for row in rows[2:]:
                output.append('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in row) + '</tr>')
            output.append('</tbody></table></div>')
            continue
        if line.startswith('#'):
            flush(); n = len(line) - len(line.lstrip('#'))
            output.append(f'<h{n}>' + inline(line[n:].strip()) + f'</h{n}>')
        elif line.startswith('- '):
            flush()
            if not listing: output.append('<ul>'); listing = True
            output.append('<li>' + inline(line[2:]) + '</li>')
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
        i += 1
    flush()
    if listing: output.append('</ul>')
    return '\n'.join(output)

def main():
    OUT.mkdir(exist_ok=True)
    EVIDENCE.mkdir(exist_ok=True)
    matrix, stage_total = [], 0
    full_results = []
    for label, folder, python_count, marketing_count in PRODUCTS:
        source = ROOT / folder / 'salida' / 'validacion'
        target = EVIDENCE / 'tests' / folder
        shutil.copytree(source, target, dirs_exist_ok=True)
        scopes = []
        for scope in ['data', 'ui']:
            result = json.loads((source / f'resultado_pruebas_{scope}.json').read_text())
            if result['status'] != 'PASS' or any(s['status'] != 'PASS' for s in result['stages']):
                raise RuntimeError(f'Validation not passed: {folder}/{scope}')
            scopes.append(len(result['stages']))
            stage_total += scopes[-1]
            full_results.append({'edition': label, **result})
        python_log = (source / 'python.log').read_text(errors='replace')
        if not re.search(rf'Ran {python_count} tests.*\n\nOK', python_log, re.S):
            raise RuntimeError('Python evidence does not match: ' + folder)
        matrix.append([label, f'{scopes[0]} PASS', f'{scopes[1]} PASS', f'{python_count} PASS', '52 PASS', '55 PASS', f'{marketing_count} PASS'])
    rechecks = EVIDENCE / 'tests' / 'rechecks'
    rechecks.mkdir(parents=True, exist_ok=True)
    for name in ['marketing_contracts_commercial_final.log', 'marketing_contracts_ztattuz_final.log',
                 'marketing_ui_commercial_final.log', 'marketing_ui_ztattuz_final.log',
                 'marketing_ui_ztattuz_x64_final.log', 'freeze_ui_commercial_final.log',
                 'time_commercial_final.log', 'time_ztattuz_final.log']:
        path = ROOT / name
        if not path.is_file() or 'PASS:' not in path.read_text(errors='replace'):
            raise RuntimeError('Missing successful recheck: ' + name)
        shutil.copy2(path, rechecks / name)
    (EVIDENCE / 'tests' / 'all_results.json').write_text(json.dumps(full_results, ensure_ascii=False, indent=2))

    migration_rows = []
    for path in sorted((ROOT / 'supabase' / 'migrations').glob('*.sql')):
        if path.name.startswith(('20261003035126', '20261003124254', '20261008024020', '20261008031059')):
            migration_rows.append([path.name, len(path.read_bytes()), hashlib.sha256(path.read_bytes()).hexdigest()])
    changed = subprocess.run(['git', 'diff', '--name-only', '77ac9fc'], cwd=ROOT, check=True, text=True, capture_output=True).stdout
    untracked = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT, check=True, text=True, capture_output=True).stdout
    manifest = []
    for name in sorted(set((changed + untracked).splitlines())):
        path = ROOT / name
        if not path.is_file() or path.is_symlink() or any(p in path.parts for p in ['node_modules', 'salida', '__pycache__', 'DigitalPersonaRuntime', 'evidence']):
            continue
        if path.suffix.lower() in ['.png', '.ico', '.dll', '.exe', '.msi', '.cab']:
            continue
        manifest.append({'path': name, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    (EVIDENCE / 'changed_files_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    report = '''# Gym Soft y ZTATTUZ: actualización en desarrollo

Revisión: 8 de octubre de 2026. Este paquete conserva código fuente, migraciones, pruebas y capturas. No es un instalador final. Las versiones permanecen en Comercial 3.6.0 y ZTATTUZ 3.6.1 x86/x64.

## Resultado y límites actuales

Se continuó WhatsApp oficial, automatizaciones, chatbot y Wompi. La congelación y el reloj del gimnasio están integrados en sus motores compartidos, sin una segunda lógica de membresía. Las Edge Functions marketing se desplegaron en ambos proyectos. Las cuatro migraciones nuevas aún no aparecen aplicadas en los servidores: sus comandos no devolvieron respuesta incluso con 120 segundos de espera, y se comprobó después que no había transacciones de migración activas o bloqueadas ni tablas nuevas instaladas. El entorno local se desconectó temporalmente; el acceso se recuperó para guardar este avance.

No se activaron campañas ni se realizaron cobros reales. Las pruebas locales no sustituyen un piloto con Meta, un pago Wompi externo, dos sesiones PostgreSQL reales o el lector/relay físico. No se marca la actualización como terminada.

## Pruebas ejecutadas

''' + table(['Edición', 'Etapas datos', 'Etapas UI', 'Python', 'Congelación SQL', 'Tiempo SQL', 'Contratos Marketing'], matrix) + f'''

Las suites completas suman {stage_total} etapas PASS. Los casos de Python y SQL están incluidos en esas etapas; las columnas no deben sumarse como casos únicos. Backend compartido: 54 tests PASS en cada edición. Los últimos cambios afectados se volvieron a verificar: contratos Marketing 90/87, ocho pantallas Marketing 76 comprobaciones por edición, congelación UI 48 comprobaciones y pipeline SQL 55. Los resultados JSON y sus logs se conservan en evidence/tests; los rechecks finales están en evidence/tests/rechecks.

Los ensayos de SQL usan PGlite. Promise.all comparte una sesión de ese motor y no acredita dos PCs concurrentes. La huella y el relé se prueban con adaptadores simulados. Los smoke tests de Tk se ejecutan en Linux con pantalla de prueba, incluso los que se llaman windows_ui_smoke; la compilación y ejecución Windows físicas siguen pendientes.

## Causa raíz de las horas y corrección

Se corrigió el truncamiento del offset UTC durante presentación y el uso de DATE como datetime a medianoche durante importación. También se encontraron fuentes del reloj del PC en reglas de negocio y cálculo duplicado del estado del cliente. El motor activo de Supabase ahora consulta el reloj del servidor, conserva DATE para calendario y TIMESTAMPTZ para instantes, y convierte una sola vez el instante a gym.timezone. Se usa ZoneInfo; no se reetiqueta un instante UTC como hora local.

Los nuevos eventos de entrada, pago, venta, gasto y auditoría reciben reloj del servidor aunque el escritorio envíe un valor falso. Los eventos de WhatsApp, chatbot y Wompi se integran en Registro de actividades con ese mismo reloj y responsable verificado cuando corresponde. El timestamp original de Wompi se conserva y aparece convertido en el detalle del pago. Una fecha sin hora no se convierte en un evento 00:00 ficticio.

Los usos residuales de hora del PC quedan clasificados como diagnóstico, nombres de archivos o UI cosmética y en la base SQLite antigua de respaldo; no son la fuente de los eventos actuales de negocio. El inventario global está en temporal_inventory.txt y temporal_inventory_current.txt.

No se actualizan masivamente timestamps históricos. Se inspeccionaron tipos y ejemplos reales y se conservaron hashes de audit_logs, memberships y checkins. En la última comprobación, los 30 registros de auditoría comercial y los 1304 de ZTATTUZ y sus hashes seguían iguales al baseline. Esto protege los datos observados; no reconstruye horas que se hubieran perdido históricamente ni atribuye todos los reportes antiguos de medianoche a una sola fila sin evidencia.

''' + table(['Instante o regla', 'America/Bogota'], [
    ['08/10/2026 02:30:00Z', '07/10/2026 21:30:00 (9:30 PM)'],
    ['08/10/2026 04:59:59Z', '07/10/2026 23:59:59'],
    ['08/10/2026 05:00:00Z', '08/10/2026 00:00:00'],
    ['Recordatorio 09:00 local', '14:00 UTC'],
]) + '''

Las primeras tres conversiones también se verificaron mediante consultas reales de solo lectura en ambos proyectos. El timezone de ZTATTUZ debe quedar America/Bogota al aplicar la migración diaria; antes del despliegue su tabla gyms todavía no contiene esa columna. Comercial usa el timezone de cada gym. Se prueban otra zona y los límites de días, incluidos horarios estacionales.

## Congelación y membresías

Congelar desde el 08/10/2026 bloquea del 8 al 14 inclusive, reactiva el 15 a medianoche local y mueve un vencimiento del 20 al 27. El motor informa FROZEN y deniega huella, código, búsqueda manual y override de acceso. El controlador no solicita apertura del relay ni aunque reciba una respuesta contradictoria.

La política inicial es siete días y una congelación por ciclo, configurable por gym/plan. La excepción y cancelación administrativas exigen motivo. Se guardan responsable real, fechas locales, instantes UTC, días añadidos, estado, motivo, cancelación y finalización. Los eventos son MEMBERSHIP_FROZEN, MEMBERSHIP_FREEZE_COMPLETED, MEMBERSHIP_FREEZE_CANCELLED y CHECK_IN_DENIED_MEMBERSHIP_FROZEN.

La tiquetera conserva entradas y extiende vigencia. El máximo de un consumo por día se calcula con el día del gimnasio. La extensión conserva el tiempo restante y mueve ciclos prepagados para evitar superposición. La renovación Wompi usa el vencimiento extendido y no borra congelación ni historial. Un respaldo/importación conserva el historial sin conceder extensión de nuevo.

Los recordatorios de vencimiento usan la fecha nueva: para vencer el 27, tres días antes es el 24. Se invalidan los mensajes obsoletos y el envío vuelve a comprobar congelación y vencimiento antes de contactar Meta. El chatbot muestra CONGELADA, último día congelado, reactivación y nuevo vencimiento. Cumpleaños y comunicaciones generales mantienen su política propia. No se implementó prórroga.

Se prueban duplicación e idempotencia, máximo uno, override con motivo, cancelación, auditoría, cinco rutas de acceso, conservación de cupos, vencimiento +7, recordatorios, chatbot, renovación e importación. El código usa locks transaccionales y unicidad; queda pendiente demostrarlo con dos sesiones PostgreSQL reales.

## Archivos modificados y añadidos

- common/membership_freezes.sql: políticas, historial, bloqueo transaccional, cancelación, vencimiento, entrada, auditoría y reloj.
- common/gym_time.py y common/server_date.py: instantes aware, calendario IANA y caché del reloj del servidor limitada por medianoche local.
- common/membership_freeze_ui.py: elegibilidad, confirmación, política por plan/gym, excepción, cancelación e historial.
- common/marketing_api.sql y marketing_service.sql: eventos en auditoría general y responsable del vínculo Meta/Wompi.
- common/marketing_payments.sql y marketing_desktop.sql: validación, conservación y exposición del instante original del proveedor.
- common/marketing_scheduler.sql: pg_cron, pg_net, Vault, finalización y health de infraestructura.
- backend/handler.mjs y core: autenticación, chatbot, scheduler, webhook, pagos, estado de salud y onboarding.
- common/marketing_ui.py y copias de marketing_client.py, payment_revision.py, ui_text.py, cloud_database.py, reception_database.py, reception_app.py y app.py en las tres ediciones.
- onboarding/index.html, common/build_onboarding.mjs y deployment/configure_meta.mjs: conexión oficial Meta y configuración privada.
- common/release_gate.py, release_readiness.json y build_windows.py: bloqueo de builds sin aceptación y evidencia de la versión.
- Tests SQL/Python, backend y UI de congelación y tiempo, sincronizados en las tres ediciones.

evidence/changed_files_manifest.json enumera los archivos de código/documentación cambiados respecto al baseline 77ac9fc y sus SHA-256. No enumera binarios originales como si fueran cambios de esta implementación.

## Migraciones preparadas, orden y huellas

''' + table(['Archivo en supabase/migrations', 'Bytes', 'SHA-256'], migration_rows) + '''

Las copias ACTUALIZAR_CONSUMO_DIARIO.sql, ACTUALIZAR_MARKETING.sql, ACTUALIZAR_CONGELACION_Y_HORAS.sql y ACTUALIZAR_SCHEDULER.sql están en cada edición. No instalar el esquema inicial sobre una base existente ni ejecutar una migración vieja después de las nuevas. El historial remoto se debe inspeccionar y registrar por proyecto.

## Problemas encontrados y corregidos

- Instantes UTC truncados, fechas importadas como medianoche y respaldo a la fecha del PC para gastos: corregidos en las fuentes y helpers.
- Marketing no aparecía en el registro general: se añadieron productores de actividad del servidor y etiquetas legibles; actualizar SENT dos veces no duplica el evento.
- Estado de cliente inferido de nuevo en escritorio: se consume el resultado autoritativo del motor, incluida congelación.
- Fixtures antiguos no tenían el nuevo reloj ni las respuestas completas de integración: se actualizaron antes de ejecutar las regresiones.
- El bloqueo de release ocultaba el error de arquitectura del Python x64: se ordenó después de comprobar arquitectura y antes de compilar; el último suite x64 pasó 148 tests.
- Un log anterior llamado python_ztattuz_x64_final.log conserva el intento fallido anterior; la evidencia autoritativa más reciente está en evidence/tests/GymSoft_ZTATTUZ_3.6.1_x64/python.log, PASS.
- apply_migration no devuelve resultado ni instala cambios; se comprobó el schema y las sesiones. No se usa execute_sql para eludir el mecanismo de migraciones.

## Cierre pendiente

- Aplicar y verificar las cuatro migraciones; timezone real de ZTATTUZ; scheduler instalado con capacidades de envío y pagos desactivadas.
- Dos sesiones PostgreSQL concurrentes con un cliente ficticio, sin duplicar congelaciones ni consumir dos entradas.
- Publicar y registrar el dominio HTTPS oficial de autorización Meta; configurar la aplicación y el número del titular; validar un mensaje, su webhook, chatbot y automatización con destinatario autorizado.
- Configurar llaves Wompi Sandbox por el formulario privado; validar pago externo, idempotencia, conciliación y renovación mientras está congelado. Sin cobros reales ni habilitación de producción.
- Probar huella y relay físicos, ejecutables Windows de las dos arquitecturas e instalación/actualización.
- Actualizar documentación y evidencia de aceptación, después versión/changelog final e instaladores.

release_readiness.json mantiene todas las aceptaciones externas pendientes. Ningún PASS de simulación se presenta como prueba real de Meta, Wompi, hardware o dos PCs. GUIA_CONGELACION_Y_HORAS.md contiene el procedimiento operativo y de despliegue. Los runtimes e iconos originales permanecen en los paquetes completos previos; este checkpoint de fuente los excluye deliberadamente y no es un instalador.
'''
    markdown_path = OUT / 'Informe_Actualizacion_20261008.md'
    markdown_path.write_text(report, encoding='utf-8')
    (ROOT / 'INFORME_VALIDACION_EN_DESARROLLO.md').write_text(report, encoding='utf-8')
    (ROOT / 'ESTADO_IMPLEMENTACION.md').write_text(report.split('## Causa raíz')[0] + '\nMigraciones, proveedores, concurrencia real y hardware pendientes. No generar builds finales.\n', encoding='utf-8')
    images = []
    for name, caption in [('freeze_admin_125.png', 'Congelación: pantalla real de Tk con datos ficticios, escala 125%.'),
                          ('wompi_timestamps_125.png', 'Detalle Wompi: timestamp del fixture convertido a Bogotá; no es un cobro real.')]:
        path = EVIDENCE / 'ui' / name
        if path.exists():
            encoded = base64.b64encode(path.read_bytes()).decode('ascii')
            images.append('<figure><img alt="' + html.escape(caption) + '" src="data:image/png;base64,' + encoded + '"><figcaption>' + html.escape(caption) + '</figcaption></figure>')
    style = 'body{font:16px/1.6 system-ui,Segoe UI,sans-serif;color:#172638;background:#f3f6fa;margin:0}main{max-width:1100px;margin:auto;background:white;padding:36px}h1,h2{line-height:1.25;color:#123f70}h2{margin-top:2em}code{font:13px ui-monospace,monospace;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #d4deea;padding:10px;text-align:left;overflow-wrap:anywhere}th{background:#eaf0f8}.table-wrap{overflow:auto}img{max-width:100%;height:auto;border:1px solid #d4deea}figure{margin:24px 0}figcaption{font-size:14px;color:#52657b}@media(max-width:700px){main{padding:20px}}'
    document = '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Gym Soft: validación en desarrollo</title><style>' + style + '</style><main>' + render_markdown(report) + '<h2>Capturas de las pruebas</h2>' + ''.join(images) + '</main></html>'
    html_path = OUT / 'Informe_Actualizacion_20261008.html'
    html_path.write_text(document, encoding='utf-8')
    print(json.dumps({'stages_pass': stage_total, 'changed_files': len(manifest), 'report': str(html_path), 'markdown': str(markdown_path), 'screenshots_embedded': len(images)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
