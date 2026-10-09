"""Compile actual Windows applications for technical verification, never final delivery.

Example (from an edition):
    .venv\\Scripts\\python.exe ..\\tools\\windows_packaging_qa.py --freeze-only
    .venv\\Scripts\\python.exe ..\\tools\\windows_packaging_qa.py --installers

This separate QA entry point does not modify release acceptance. CREAR_INSTALADORES
and build_windows.main still require valid release_gate evidence before building.
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

    def __call__(self, command, *, cwd=None, check=False, timeout=None):
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
                process = subprocess.Popen(command, cwd=cwd, stdout=stream,
                                           stderr=subprocess.STDOUT)
                try:
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', type=Path, default=Path.cwd(),
                        help='Carpeta de una de las tres ediciones.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--freeze-only', action='store_true', help='Compilar entradas reales y comprobar sus ejecutables.')
    mode.add_argument('--installers', action='store_true', help='Además compilar Inno técnico con runtime completo. No instala ni entrega finales.')
    args = parser.parse_args(argv)
    edition = args.edition.resolve()
    if edition.name not in PRODUCT_EDITIONS or not (edition / 'build_windows.py').is_file():
        parser.error('Selecciona una carpeta válida de Comercial o ZTATTUZ x64/x86.')
    output = edition / 'salida' / 'validacion' / 'paquete-tecnico'
    output.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + f'-{os.getpid()}'
    qa_root = output / 'ejecuciones' / run_id
    qa_root.mkdir(parents=True)
    (qa_root / 'LEER_NO_FINAL.txt').write_text(SCOPE + '\nNo distribuir ni instalar en equipos de clientes.\n', encoding='utf-8')
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
