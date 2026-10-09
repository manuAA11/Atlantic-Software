"""Compile actual Windows applications for technical verification, never final delivery.

Example (from an edition):
    .venv\\Scripts\\python.exe ..\\tools\\windows_packaging_qa.py --freeze-only
    .venv\\Scripts\\python.exe ..\\tools\\windows_packaging_qa.py --installers

This separate QA entry point does not modify release acceptance. Production
build_windows.main still requires valid release_gate evidence before building.
--para-configurar additionally runs the complete local validation and publishes
verified technical installers in PRUEBAS_PARA_CONFIGURAR, never final outputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys


SCOPE = ('Validación técnica de empaquetado Windows; NO FINAL. '
         'No acredita cuentas, WhatsApp/Wompi reales, PostgreSQL concurrente, '
         'lector/relé físico ni aceptación de release_gate.')
PRODUCT_EDITIONS = {'GymSoft_Comercial_3.6.0', 'GymSoft_ZTATTUZ_3.6.1_x64',
                    'GymSoft_ZTATTUZ_3.6.1_x86'}


class LoggedRunner:
    """Retain native command output and failures, including PyInstaller and Inno."""
    def __init__(self, log_root):
        self.log_root = Path(log_root)
        self.log_root.mkdir(parents=True, exist_ok=True)
        self.count = 0
        self.commands = []

    def __call__(self, command, *, cwd=None, check=False, timeout=None, live_output=False):
        self.count += 1
        log = self.log_root / f'{self.count:02d}-comando.log'
        record = {'command': list(map(str, command)), 'log': str(log), 'status': 'RUNNING'}
        self.commands.append(record)
        # communicate(timeout) is necessary for windowed diagnostics: an import
        # error can otherwise leave a Windows error dialog waiting indefinitely.
        try:
            with log.open('w', encoding='utf-8') as stream:
                stream.write(json.dumps(record['command'], ensure_ascii=False) + '\n')
                stream.flush()
                if live_output and timeout is not None:
                    raise ValueError('La salida en vivo no se usa con diagnósticos que necesitan timeout.')
                process = subprocess.Popen(command, cwd=cwd,
                                           stdout=subprocess.PIPE if live_output else stream,
                                           stderr=subprocess.STDOUT,
                                           text=live_output, encoding='utf-8' if live_output else None,
                                           errors='replace' if live_output else None)
                try:
                    if live_output:
                        for line in process.stdout:
                            stream.write(line)
                            stream.flush()
                            print(line, end='', flush=True)
                        process.stdout.close()
                    returncode = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                    record['status'] = 'TIMEOUT'
                    raise
            record['returncode'] = returncode
            record['status'] = 'PASS' if returncode == 0 else 'FAIL'
            print(f"{record['status']} · comando {self.count} · {log}", flush=True)
            result = subprocess.CompletedProcess(command, returncode)
            if check:
                result.check_returncode()
            return result
        except Exception:
            if record['status'] == 'RUNNING':
                record['status'] = 'FAIL'
            raise


def require_runtime_files(root, expected_bits):
    """Authenticate the complete runtime against the tracked SDK manifest."""
    authority = root.parent / 'docs' / 'vendor' / 'digitalpersona' / 'sdk-manifest.json'
    if not authority.is_file():
        raise RuntimeError('Falta el manifiesto original del SDK; no se puede verificar el runtime.')
    manifest = json.loads(authority.read_text(encoding='utf-8'))
    architecture = 'x64' if expected_bits == 64 else 'x86'
    required = manifest['runtimes'][architecture]['files'] + [manifest['license']]
    hashes = {}
    for item in required:
        path = root / 'DigitalPersonaRuntime' / item['path']
        if path.is_symlink() or not path.is_file():
            raise RuntimeError('Falta el archivo original del runtime: ' + item['path'])
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.stat().st_size != item['bytes'] or actual != item['sha256']:
            raise RuntimeError('Integridad incorrecta del runtime: ' + item['path'])
        hashes[item['path']] = actual
    return hashes


def installer_filename(script, version):
    match = re.search(r'^OutputBaseFilename=(.+)$', script.read_text(encoding='utf-8-sig'), re.MULTILINE)
    if not match:
        raise ValueError(f'{script.name}: falta OutputBaseFilename.')
    return match.group(1).strip().replace('{#AppVersion}', version) + '.exe'


def compile_technical_installers(build, *, qa_root, dist_root, runner):
    require_runtime_files(build.ROOT, build.EXPECTED_BITS)
    compiler = build.find_inno_compiler()
    components = qa_root / 'instaladores' / 'componentes'
    output = qa_root / 'instaladores'
    components.mkdir(parents=True, exist_ok=True)
    results = []
    for name in build.INSTALLER_SCRIPTS:
        script = build.ROOT / name
        component = name in ('instalador_admin.iss', 'instalador_recepcion.iss')
        target_root = components if component else output
        original_name = installer_filename(script, build.VERSION)
        filename = original_name if component else 'VALIDACION_NO_FINAL_' + original_name
        command = [compiler, '/DAppVersion=' + build.VERSION, '/DBuildValidation=1',
                   '/DBuildDistRoot=' + str(dist_root), '/DBuildComponentRoot=' + str(components),
                   '/O' + str(target_root)]
        if not component:
            command.append('/F' + Path(filename).stem)
        command.append(str(script))
        runner(command, cwd=build.ROOT, check=True)
        executable = target_root / filename
        if not executable.is_file():
            raise RuntimeError(f'{script.name}: no se generó {executable.name}.')
        results.append({'script': name, 'executable': str(executable),
                        'sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
                        'status': 'PASS', 'final': False})
    return results


def run_configuration_validation(build, runner):
    """Require this invocation's complete local suite, including GUI and SQL."""
    import run_validation
    started = datetime.now(timezone.utc)
    print('Verificando todas las funciones locales antes de crear los instaladores de pruebas...', flush=True)
    command = [sys.executable, str(build.ROOT / 'run_validation.py')]
    outcome = runner(command, cwd=build.ROOT, check=True, live_output=True)
    if outcome is None or outcome.returncode != 0:
        raise RuntimeError('La ejecución de las pruebas locales no terminó correctamente; no se publica ningún instalador.')
    finished = datetime.now(timezone.utc)
    target = build.ROOT / 'salida' / 'validacion' / 'resultado_pruebas_all.json'
    if target.is_symlink() or not target.is_file():
        raise RuntimeError('La ejecución no generó su informe completo de pruebas locales; no se publica ningún instalador.')
    result = json.loads(target.read_text(encoding='utf-8'))
    expected = ['python', 'contratos_extraidos', *run_validation.SQL_TESTS,
                'marketing_backend', 'recorrido_huellas', 'simulacion_gimnasio',
                *run_validation.UI_TESTS]
    stages = result.get('stages', [])
    try:
        report_started = datetime.fromisoformat(result['started_at'])
        fresh = started <= report_started <= finished
    except (KeyError, TypeError, ValueError):
        fresh = False
    if (result.get('status') != 'PASS' or result.get('scope') != 'all'
            or result.get('platform') != 'win32' or result.get('version') != build.VERSION
            or [stage.get('name') for stage in stages] != expected
            or any(stage.get('status') != 'PASS' or stage.get('timed_out')
                   or stage.get('callback_failure') for stage in stages)
            or not fresh):
        raise RuntimeError('Las pruebas locales completas de esta ejecución no están aprobadas; no se publica ningún instalador.')
    for stage in stages:
        log = target.parent / stage['log']
        if (stage['log'] != stage['name'] + '.log'
                or log.parent != target.parent or log.is_symlink() or not log.is_file()):
            raise RuntimeError('Falta un registro de las pruebas locales; no se publica ningún instalador.')
    # Bind the receipt to the original report and each native stage log. These
    # hashes do not replace the suite or turn any pending acceptance into PASS.
    result['evidence'] = {'report': str(target), 'sha256': sha256_file(target),
                          'logs': [{'path': stage['log'],
                                    'sha256': sha256_file(target.parent / stage['log'])}
                                   for stage in stages]}
    return result


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def publish_configuration_installers(build, report, qa_root):
    """Publish all verified application installers atomically, preserving old runs."""
    validation = report.get('full_local_validation', {})
    if (report.get('status') != 'PASS' or report.get('final') is not False
            or report.get('mode') != 'installers'
            or validation.get('status') != 'PASS' or validation.get('scope') != 'all'
            or validation.get('platform') != 'win32' or validation.get('version') != build.VERSION
            or not validation.get('stages')
            or any(stage.get('status') != 'PASS' or stage.get('timed_out')
                   or stage.get('callback_failure') for stage in validation['stages'])):
        raise RuntimeError('No se publican archivos sin pruebas locales y empaquetado completos aprobados.')
    if (report.get('edition') != build.ROOT.name or report.get('version') != build.VERSION
            or not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[0-9]+', report.get('run_id', ''))):
        raise RuntimeError('La entrega no pertenece a esta edición o tiene una identidad de ejecución inválida.')
    if [item.get('script') for item in report['installers']] != list(build.INSTALLER_SCRIPTS):
        raise RuntimeError('La selección de instaladores está incompleta o no pertenece a esta edición.')
    if (len(report['executables']) != len(build.EXECUTABLES)
            or {item.get('entry') for item in report['executables']} != {entry for name, entry in build.EXECUTABLES}):
        raise RuntimeError('Falta verificar un programa de esta edición.')
    if any(item.get('status') != 'PASS' or item.get('diagnostic', {}).get('estado') != 'OK'
           for item in report['executables']):
        raise RuntimeError('Falta aprobar el diagnóstico de un programa.')
    qa_root = Path(qa_root).resolve()
    selected = []
    for item in report['installers']:
        source = Path(item['executable'])
        if (item.get('status') != 'PASS' or item.get('final') is not False
                or source.is_symlink() or not source.is_file()
                or qa_root not in source.resolve().parents
                or sha256_file(source) != item['sha256']):
            raise RuntimeError('No se publica un instalador incompleto, externo o alterado.')
        for parent in (source, *source.parents):
            if parent == qa_root:
                break
            if parent.is_symlink() or getattr(parent, 'is_junction', lambda: False)():
                raise RuntimeError('No se publica un instalador desde un enlace o junction.')
        name = source.name if source.name.startswith('VALIDACION_NO_FINAL_') else 'VALIDACION_NO_FINAL_' + source.name
        folder = ('PRIVADO_PROPIETARIO' if item['script'] == 'instalador_propietario.iss'
                  else 'COMPONENTES' if item['script'] in ('instalador_admin.iss', 'instalador_recepcion.iss') else '')
        selected.append((source, Path(folder) / name, item['sha256']))
    base = build.ROOT / 'salida' / 'PRUEBAS_PARA_CONFIGURAR'
    target = base / report['run_id']
    staging = base / ('.' + report['run_id'] + '.preparando')
    if (base.is_symlink() or getattr(base, 'is_junction', lambda: False)()
            or target.exists() or staging.exists()):
        raise RuntimeError('El destino ya existe o es un enlace; no se sobrescribe ninguna entrega anterior.')
    for parent in base.parents:
        if parent.is_symlink() or getattr(parent, 'is_junction', lambda: False)():
            raise RuntimeError('El destino de pruebas contiene un enlace simbólico.')
    base.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    try:
        manifest = {'type': 'INSTALLERS_CONFIGURATION_VALIDATION', 'final': False,
                    'scope': SCOPE, 'edition': report['edition'], 'version': build.VERSION,
                    'run_id': report['run_id'], 'full_local_validation': report['full_local_validation'],
                    'files': []}
        for source, relative, expected in selected:
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            if sha256_file(destination) != expected:
                raise RuntimeError('La copia de un instalador no conservó su integridad; no se publica la entrega.')
            manifest['files'].append({'path': relative.as_posix(), 'sha256': expected,
                                      'bytes': destination.stat().st_size})
        readme = (
            'ATLANTIC GYM · INSTALADORES PARA CONFIGURACIÓN Y PRUEBAS · NO FINAL\n\n'
            'Instaladores reales de la aplicación con sus programas, iconos aprobados y componentes necesarios. '
            'Se generaron después de aprobar las pruebas locales completas y los diagnósticos de los ejecutables.\n\n'
            'Úselos para instalar, configurar desde la aplicación y completar las pruebas pendientes. '
            'La aceptación final continúa pendiente en release_readiness.json. '
            'Las pruebas locales no acreditan WhatsApp/Wompi con cuentas reales, lector/relé físico ni concurrencia PostgreSQL real.\n\n'
            'Instale el archivo VALIDACION_NO_FINAL de esta carpeta. En ZTATTUZ el instalador completo incluye Administración y Recepción; '
            'COMPONENTES conserva sus instaladores individuales. '
            'En Comercial PRIVADO_PROPIETARIO es exclusivo del propietario del software y no se entrega a clientes.\n\n'
            'WhatsApp y Wompi se configuran mediante la aplicación y su backend; no guarde claves privadas en el escritorio. '
            'Consulte docs/INTEGRACIONES_Y_WINDOWS.md del paquete de fuentes. '
            'Lea y acepte la EULA DigitalPersona presentada por el instalador.\n\n'
            'No mezcle Comercial con ZTATTUZ. Esta carpeta no contiene instaladores finales; '
            'CREAR_INSTALADORES generará la entrega final únicamente al aprobar su aceptación válida.\n'
        )
        (staging / 'LEER_PRIMERO.txt').write_text(readme, encoding='utf-8')
        (staging / 'MANIFIESTO.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        (staging / 'SHA256SUMS.txt').write_text(
            ''.join(item['sha256'] + '  ' + item['path'] + '\n' for item in manifest['files']), encoding='utf-8')
        # A unique destination avoids replacing any previous complete build.
        if target.exists():
            raise RuntimeError('Ya existe una entrega con este identificador; no se sobrescribe.')
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print('Instaladores para configurar y probar: ' + str(target), flush=True)
    return {'directory': str(target), 'final': False, 'files': manifest['files']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', type=Path, default=Path.cwd(),
                        help='Carpeta de una de las tres ediciones.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze-only', action='store_true', help='Compilar entradas reales y comprobar sus ejecutables.')
    mode.add_argument('--installers', action='store_true', help='Además compilar Inno técnico con runtime completo. No instala ni entrega finales.')
    parser.add_argument('--para-configurar', action='store_true',
                        help='Con --installers: ejecutar todas las pruebas y publicar instaladores NO FINAL para configurar.')
    args = parser.parse_args(argv)
    if args.para_configurar and not args.installers:
        parser.error('--para-configurar requiere --installers.')
    edition = args.edition.resolve()
    if edition.name not in PRODUCT_EDITIONS or not (edition / 'build_windows.py').is_file():
        parser.error('Selecciona una carpeta válida de Comercial o ZTATTUZ x64/x86.')
    output = edition / 'salida' / 'validacion' / 'paquete-tecnico'
    output.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + f'-{os.getpid()}'
    qa_root = output / 'ejecuciones' / run_id
    qa_root.mkdir(parents=True)
    (qa_root / 'LEER_NO_FINAL.txt').write_text(SCOPE + '\nUse PRUEBAS_PARA_CONFIGURAR solo después de verificar sus pruebas completas.\n', encoding='utf-8')
    runner = LoggedRunner(qa_root / 'logs')
    report = {'status': 'RUNNING', 'final': False, 'scope': SCOPE, 'edition': edition.name,
              'version': None, 'mode': 'installers' if args.installers else 'freeze-only',
              'date_utc': datetime.now(timezone.utc).isoformat(), 'run_id': run_id,
              'python': sys.version, 'process_bits': struct.calcsize('P') * 8,
              'release_gate_modified': False, 'executables': [], 'installers': [],
              'commands': runner.commands}
    # An interrupted rerun must never leave the previous PASS as current evidence.
    (output / 'informe_empaquetado.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    try:
        if sys.platform != 'win32':
            raise RuntimeError('Esta verificación requiere Windows con Python compatible de la arquitectura de la edición.')
        sys.path.insert(0, str(edition))
        build = importlib.import_module('build_windows')
        report['version'] = build.VERSION
        build.require_runtime(build.EXPECTED_BITS)
        from product_config import load_config
        load_config()  # Validate the existing public configuration; never log its values.
        if args.installers:
            report['runtime_sha256'] = require_runtime_files(edition, build.EXPECTED_BITS)
            build.find_inno_compiler()  # Detect missing compiler before expensive builds.
        os.environ['GYMSOFT_OFFLINE_QA'] = '1'
        os.environ.setdefault('PYINSTALLER_CONFIG_DIR', str(qa_root / 'cache-pyinstaller'))
        if args.para_configurar:
            report['full_local_validation'] = run_configuration_validation(build, runner)
        dist_root = qa_root / 'dist'
        for result in build.freeze_executables(dist_root=dist_root, build_root=qa_root / 'build', runner=runner):
            item = {**result, 'executable': str(result['executable']), 'status': 'PASS'}
            report['executables'].append(item)
            diagnostic = build.diagnose_frozen_executable(result['executable'],
                          qa_root / 'diagnosticos' / (result['name'].replace(' ', '_') + '.json'), runner=runner)
            item['diagnostic'] = diagnostic
        if args.installers:
            report['installers'] = compile_technical_installers(build, qa_root=qa_root, dist_root=dist_root, runner=runner)
        report['status'] = 'PASS'
        if args.para_configurar:
            report['configuration_installers'] = publish_configuration_installers(build, report, qa_root)
        print('PASS · empaquetado técnico Windows · NO FINAL', flush=True)
        return 0
    except Exception as error:
        report['status'] = 'FAIL'
        report['error'] = f'{type(error).__name__}: {error}'
        print('FAIL · ' + report['error'], file=sys.stderr, flush=True)
        return 1
    finally:
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        (qa_root / 'informe_empaquetado.json').write_text(payload, encoding='utf-8')
        (output / 'informe_empaquetado.json').write_text(payload, encoding='utf-8')


if __name__ == '__main__':
    sys.exit(main())
