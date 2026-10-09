"""Install NO FINAL packages only on an explicitly selected ephemeral GitHub runner.

This verifies Windows installation, update, shortcuts and offline diagnostics.
It never authenticates to a gym, connects hardware, changes release acceptance,
or installs anything on a development machine or customer computer.
"""
from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SCOPE = ('Instalación técnica Windows en runner efímero; NO FINAL. '
         'No acredita cuentas, WhatsApp/Wompi reales, lector/relé físico, '
         'PostgreSQL concurrente ni aceptación de release_gate.')
EDITIONS = {'GymSoft_Comercial_3.6.0', 'GymSoft_ZTATTUZ_3.6.1_x64',
            'GymSoft_ZTATTUZ_3.6.1_x86'}
EDITION_CODES = {'GymSoft_Comercial_3.6.0': 'c64', 'GymSoft_ZTATTUZ_3.6.1_x64': 'z64',
                 'GymSoft_ZTATTUZ_3.6.1_x86': 'z32'}
INSTALLATION_MARKER = 'ATLANTIC_EPHEMERAL_INSTALLATION.json'
APP_IDS = {
    'client': '{6C58E8B8-C2ED-4B60-A080-EEA57BB407C2}_is1',
    'owner': '{58D6DD62-FD67-4CC1-8D87-153AFB4EE44A}_is1',
    'admin': '{E89DF404-FD78-4A97-89E8-9BA23D3B0B19}_is1',
    'reception': '{8F529E62-5D29-49E0-99AA-28255D920ECE}_is1',
}


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def confined_path(value, root, *, require_file=False):
    """Reject paths and any symlink/junction that leave or alias the QA tree."""
    path, root = Path(value), Path(root).resolve()
    if not path.is_absolute():
        raise RuntimeError('El informe debe usar rutas absolutas de validación.')
    resolved = path.resolve(strict=require_file)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeError('Ruta fuera del directorio de validación: ' + str(path)) from error
    candidate = path
    while candidate != root and candidate != candidate.parent:
        if candidate.is_symlink() or getattr(candidate, 'is_junction', lambda: False)():
            raise RuntimeError('No se permiten enlaces ni junctions en el paquete técnico.')
        candidate = candidate.parent
    if require_file and not resolved.is_file():
        raise RuntimeError('Falta un archivo técnico requerido: ' + str(resolved))
    return resolved


def require_ephemeral_runner(edition, explicit, *, environ=None, platform=None):
    """No files or processes are changed before the entire guard succeeds."""
    env = os.environ if environ is None else environ
    actual_platform = sys.platform if platform is None else platform
    if not explicit:
        raise RuntimeError('Se exige --ephemeral-runner para autorizar esta prueba técnica.')
    if actual_platform != 'win32':
        raise RuntimeError('La instalación técnica solo se ejecuta en Windows.')
    required = {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
                'RUNNER_OS': 'Windows'}
    if any(env.get(name) != value for name, value in required.items()):
        raise RuntimeError('Solo se admiten runners Windows efímeros alojados por GitHub Actions.')
    if not re.fullmatch(r'[0-9]+', env.get('GITHUB_RUN_ID', '')):
        raise RuntimeError('Falta la identidad verificable del run de GitHub Actions.')
    if not env.get('RUNNER_TEMP') or not env.get('GITHUB_WORKSPACE'):
        raise RuntimeError('Faltan RUNNER_TEMP o GITHUB_WORKSPACE del runner.')
    temp = Path(env['RUNNER_TEMP']).resolve(strict=True)
    workspace = Path(env['GITHUB_WORKSPACE']).resolve(strict=True)
    if not temp.is_dir() or not workspace.is_dir() or temp == Path(temp.anchor):
        raise RuntimeError('Los directorios del runner no son válidos.')
    edition = Path(edition).resolve(strict=True)
    if edition.name not in EDITIONS or edition.parent != workspace:
        raise RuntimeError('La edición debe pertenecer al checkout aislado de GITHUB_WORKSPACE.')
    if not (edition / 'build_windows.py').is_file():
        raise RuntimeError('La edición seleccionada no contiene el constructor original.')
    # Hosted runners use a dedicated temporary directory, separate from checkout.
    if temp == workspace or temp in workspace.parents or workspace in temp.parents:
        raise RuntimeError('RUNNER_TEMP debe ser un directorio separado del checkout.')
    return {'environment': 'github-hosted', 'github_run_id': env['GITHUB_RUN_ID'],
            'runner_temp': str(temp), 'workspace': str(workspace)}


def native_windows_architecture():
    class SystemInfo(ctypes.Structure):
        _fields_ = [('architecture', ctypes.c_ushort), ('reserved', ctypes.c_ushort),
                    ('page_size', ctypes.c_ulong), ('minimum_address', ctypes.c_void_p),
                    ('maximum_address', ctypes.c_void_p), ('processor_mask', ctypes.c_size_t),
                    ('processors', ctypes.c_ulong), ('processor_type', ctypes.c_ulong),
                    ('allocation_granularity', ctypes.c_ulong),
                    ('processor_level', ctypes.c_ushort), ('processor_revision', ctypes.c_ushort)]
    value = SystemInfo()
    function = ctypes.WinDLL('kernel32', use_last_error=True).GetNativeSystemInfo
    function.argtypes = [ctypes.POINTER(SystemInfo)]
    function.restype = None
    function(ctypes.byref(value))
    return {0: 'x86', 9: 'x64', 12: 'arm64'}.get(value.architecture, 'unknown')


def installation_identity(runner_context, edition):
    if runner_context.get('environment') != 'github-hosted':
        raise RuntimeError('La raíz de instalación necesita el runner efímero ya validado.')
    run_id = runner_context.get('github_run_id', '')
    if not re.fullmatch(r'[0-9]+', run_id) or edition.name not in EDITION_CODES:
        raise RuntimeError('Identidad de instalación técnica inválida.')
    return {'kind': 'Atlantic ephemeral installation QA', 'github_run_id': run_id,
            'edition': edition.name, 'process_id': os.getpid(), 'final': False}


def create_installation_root(runner_context, edition):
    """Use a short, exclusive directory instead of installing into the log tree."""
    identity = installation_identity(runner_context, edition)
    temp = Path(runner_context['runner_temp']).resolve(strict=True)
    if not temp.is_dir() or temp == Path(temp.anchor):
        raise RuntimeError('RUNNER_TEMP no es una raíz de instalación válida.')
    prefix = f"agym-{EDITION_CODES[edition.name]}-{identity['github_run_id']}-{identity['process_id']}-"
    # InstallShield contains long prerequisite paths. Leave ample room below
    # MAX_PATH rather than depending on long-path support of third-party EXEs.
    probe = temp / (prefix + 'xxxxxxxx')
    if len(str(probe).encode('utf-16-le')) // 2 > 110:
        raise RuntimeError('RUNNER_TEMP es demasiado largo para verificar el runtime original.')
    result = Path(tempfile.mkdtemp(prefix=prefix, dir=temp)).resolve()
    try:
        confined_path(result, temp)
        (result / INSTALLATION_MARKER).write_text(json.dumps(identity), encoding='utf-8')
    except Exception:
        # mkdtemp created this exclusive directory; it contains no application
        # yet. Do not leave an unauthenticated directory if marker writing fails.
        shutil.rmtree(result)
        raise
    return result


def remove_installation_root(root, runner_context, edition):
    """Remove only the exclusive directory authenticated as owned by this run."""
    identity = installation_identity(runner_context, edition)
    temp = Path(runner_context['runner_temp']).resolve(strict=True)
    root = confined_path(root, temp)
    prefix = f"agym-{EDITION_CODES[edition.name]}-{identity['github_run_id']}-{identity['process_id']}-"
    if root.parent != temp or not root.name.startswith(prefix):
        raise RuntimeError('Se rechazó limpiar una raíz temporal ajena a esta instalación.')
    marker = confined_path(root / INSTALLATION_MARKER, root, require_file=True)
    if json.loads(marker.read_text(encoding='utf-8')) != identity:
        raise RuntimeError('La raíz temporal no pertenece a esta ejecución de instalación.')
    # Reject links anywhere in the exclusive tree before deleting anything.
    # os.walk does not follow symlinks; inspect directory entries too so Windows
    # junctions cannot turn cleanup into traversal of another installation.
    for folder, directories, files in os.walk(root, followlinks=False):
        for name in directories + files:
            candidate = Path(folder) / name
            confined_path(candidate, root)
    shutil.rmtree(root)


def load_technical_report(edition):
    validation = edition / 'salida' / 'validacion'
    report_path = confined_path(validation / 'paquete-tecnico' / 'informe_empaquetado.json',
                                validation, require_file=True)
    report = json.loads(report_path.read_text(encoding='utf-8-sig'))
    if (report.get('status') != 'PASS' or report.get('final') is not False or
            report.get('mode') != 'installers' or report.get('edition') != edition.name):
        raise RuntimeError('Falta un empaquetado técnico completo PASS/final:false para esta edición.')
    if not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[0-9]+', report.get('run_id', '')):
        raise RuntimeError('El empaquetado técnico no contiene un run_id válido.')
    source_root = validation / 'paquete-tecnico' / 'ejecuciones' / report['run_id']
    all_files = report.get('installers', []) + report.get('executables', [])
    if not all_files:
        raise RuntimeError('El informe técnico no contiene ejecutables.')
    for item in all_files:
        if item.get('status') != 'PASS':
            raise RuntimeError('El paquete contiene un ejecutable no validado.')
        path = confined_path(item['executable'], source_root, require_file=True)
        expected = item.get('sha256', '')
        if not re.fullmatch(r'[a-f0-9]{64}', expected) or sha256(path) != expected:
            raise RuntimeError('SHA256 incorrecto del ejecutable técnico: ' + path.name)
        item['executable'] = str(path)
    for item in report['installers']:
        if item.get('final') is not False:
            raise RuntimeError('El informe contiene un instalador que no está marcado NO FINAL.')
    return report, report_path


def verify_technical_installer_metadata(packaged, *, diagnostics=None):
    """Inspect the compiled marker before any installer process is started."""
    import pefile
    rows = [] if diagnostics is None else diagnostics
    for item in packaged['installers']:
        names = []
        row = {'script': item['script'], 'status': 'RUNNING', 'product_names': names}
        rows.append(row)
        with pefile.PE(item['executable']) as binary:
            for group in getattr(binary, 'FileInfo', []):
                for info in group:
                    for table in getattr(info, 'StringTable', []):
                        for name, value in table.entries.items():
                            if name in (b'ProductName', b'FileDescription'):
                                names.append(value.decode('utf-8', errors='replace'))
        if not any('Validación técnica (no final)' in value for value in names):
            row['status'] = 'FAIL'
            raise RuntimeError('El instalador compilado no contiene la marca técnica NO FINAL: ' + item['script'])
        row['status'] = 'PASS'
    return rows


class CommandRunner:
    def __init__(self, root, report):
        self.root, self.report = Path(root), report
        self.root.mkdir(parents=True, exist_ok=True)

    def run(self, command, *, label, timeout, accepted=(0,), cwd=None):
        index = len(self.report['commands']) + 1
        log = self.root / f'{index:02d}-{label}.log'
        item = {'command': list(map(str, command)), 'log': str(log), 'status': 'RUNNING'}
        self.report['commands'].append(item)
        with log.open('wb') as stream:
            stream.write((json.dumps(item['command'], ensure_ascii=False) + '\n').encode('utf-8'))
            stream.flush()
            process = subprocess.Popen(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                item['status'] = 'TIMEOUT'
                # Limit termination to the command and its child processes. Never
                # terminate Windows Installer globally or another process by name.
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                               stdout=stream, stderr=subprocess.STDOUT, timeout=20, check=False)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                raise RuntimeError(f'Tiempo agotado en {label}; consulta {log}.') from None
        item.update(returncode=code, status='PASS' if code in accepted else 'FAIL')
        if code not in accepted:
            raise RuntimeError(f'{label}: código {code}; consulta {log}.')
        return code


def uninstall_entries():
    import winreg
    rows = []
    # HKCU Uninstall is shared between WOW64 views; enumerate it once. HKLM
    # Uninstall is redirected and must be inspected in both registry views.
    for hive_name, hive, views in (
            ('HKCU', winreg.HKEY_CURRENT_USER, ((0, 0),)),
            ('HKLM', winreg.HKEY_LOCAL_MACHINE, ((32, winreg.KEY_WOW64_32KEY),
                                               (64, winreg.KEY_WOW64_64KEY)))):
        for view, view_flag in views:
            for role, app_id in APP_IDS.items():
                key_name = r'Software\Microsoft\Windows\CurrentVersion\Uninstall' + '\\' + app_id
                try:
                    with winreg.OpenKey(hive, key_name, 0, winreg.KEY_READ | view_flag) as key:
                        def read(name):
                            try:
                                return winreg.QueryValueEx(key, name)[0]
                            except FileNotFoundError:
                                return ''
                        rows.append({'role': role, 'hive': hive_name, 'view': view, 'key': key_name,
                                     'display_name': read('DisplayName'),
                                     'install_location': read('InstallLocation') or read('Inno Setup: App Path'),
                                     'uninstall_command': read('UninstallString')})
                except FileNotFoundError:
                    continue
    return rows


def uninstall_executable(command):
    match = re.match(r'^"([^"]+\.exe)"(?:\s|$)|^(.+?\.exe)(?:\s|$)', command, re.IGNORECASE)
    if not match:
        raise RuntimeError('Registro de desinstalación sin ejecutable reconocible.')
    return Path(match.group(1) or match.group(2))


def validate_registered_apps(rows, locations):
    if {row['role'] for row in rows} != set(locations):
        raise RuntimeError('Los registros de instalación no coinciden con los programas técnicos esperados.')
    identities = set()
    for row in rows:
        role_root = locations[row['role']].resolve()
        location = Path(row['install_location']).resolve()
        if location != role_root or 'Validación técnica (no final)' not in row['display_name']:
            raise RuntimeError('Se creó un registro de instalación fuera del directorio técnico autorizado.')
        uninstaller = confined_path(uninstall_executable(row['uninstall_command']), role_root,
                                    require_file=True)
        if uninstaller.parent != role_root:
            raise RuntimeError('El desinstalador no pertenece a la instalación técnica.')
        identity = (row['role'], row['hive'], row['view'], row['key'])
        if identity in identities:
            raise RuntimeError('Hay registros de instalación duplicados.')
        identities.add(identity)
    # A product must have exactly one uninstall registration, not both views/hives.
    if len(rows) != len(locations):
        raise RuntimeError('Una aplicación tiene registros de instalación duplicados.')
    return sorted((row['role'], row['hive'], row['view'], row['key'], row['install_location']) for row in rows)


SHORTCUT_SCRIPT = r'''
param([string]$InstallationRoot, [string]$OutputPath)
$ErrorActionPreference = 'Stop'
$prefix = [IO.Path]::GetFullPath($InstallationRoot).TrimEnd('\') + '\'
$shell = New-Object -ComObject WScript.Shell
$rows = @()
foreach ($kind in @('Desktop', 'Programs', 'CommonDesktopDirectory', 'CommonPrograms')) {
    $folder = [Environment]::GetFolderPath($kind)
    if (-not $folder -or -not (Test-Path -LiteralPath $folder)) { continue }
    foreach ($link in Get-ChildItem -LiteralPath $folder -Recurse -Filter '*.lnk' -File) {
        $item = $shell.CreateShortcut($link.FullName)
        if ($item.TargetPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
            $rows += [pscustomobject]@{ shortcut=$link.FullName; kind=$kind; target=$item.TargetPath;
                icon=$item.IconLocation; working_directory=$item.WorkingDirectory; arguments=$item.Arguments }
        }
    }
}
ConvertTo-Json -InputObject @($rows) -Depth 4 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
'''


def inspect_shortcuts(runner, qa_root, install_root, label):
    script = qa_root / 'shortcut-audit.ps1'
    script.write_text(SHORTCUT_SCRIPT, encoding='utf-8-sig')
    output = qa_root / (label + '.json')
    runner.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                '-File', str(script), '-InstallationRoot', str(install_root), '-OutputPath', str(output)],
               label=label, timeout=60)
    return json.loads(output.read_text(encoding='utf-8-sig'))


def verify_shortcuts(rows, expected, edition):
    counts = {path: 0 for path in expected}
    kinds = {path: set() for path in expected}
    for row in rows:
        target = Path(row['target']).resolve()
        if target not in expected:
            raise RuntimeError('Acceso directo técnico con ejecutable inesperado: ' + str(target))
        if Path(row['working_directory']).resolve() != target.parent:
            raise RuntimeError('Acceso directo con carpeta de trabajo incorrecta.')
        icon_location, separator, index = row['icon'].rpartition(',')
        if not separator or index.strip() != '0':
            raise RuntimeError('Acceso directo sin el icono de producto aprobado.')
        icon = Path(icon_location.strip('"')).resolve()
        confined_path(icon, expected[target]['install_root'], require_file=True)
        if sha256(icon) != sha256(edition / expected[target]['icon']):
            raise RuntimeError('El icono del acceso directo no corresponde al rol instalado.')
        counts[target] += 1
        kinds[target].add('desktop' if row['kind'] in ('Desktop', 'CommonDesktopDirectory') else 'programs')
    if any(value != {'desktop', 'programs'} for value in kinds.values()):
        raise RuntimeError('Falta el acceso directo de escritorio o menú de un programa técnico.')
    return {str(path): count for path, count in counts.items()}


def verify_installed_apps(build, packaged, locations, runner, qa_root):
    expected, results = {}, []
    commercial = 'Comercial' in build.ROOT.name
    for name, entry in build.EXECUTABLES:
        if commercial:
            role = 'owner' if entry == 'owner_panel.py' else 'client'
            relative = Path(name + '.exe') if role == 'owner' else Path('Recepcion' if entry == 'reception_app.py' else 'Admin') / (name + '.exe')
        else:
            role = 'reception' if entry == 'reception_app.py' else 'admin'
            relative = Path(name + '.exe')
        executable = confined_path(locations[role] / relative, locations[role], require_file=True)
        original = next(item for item in packaged['executables'] if item['name'] == name)
        if sha256(executable) != original['sha256']:
            raise RuntimeError('El EXE instalado difiere del EXE técnico validado: ' + executable.name)
        icon = 'icono_recepcion.ico' if entry == 'reception_app.py' else 'icono.ico'
        build.verify_executable_icon(executable, icon)
        build.verify_executable_architecture(executable)
        target_report = qa_root / 'diagnosticos' / (name.replace(' ', '_') + '.json')
        target_report.parent.mkdir(parents=True, exist_ok=True)
        target_report.unlink(missing_ok=True)
        runner.run([str(executable), '--diagnostico', '--sin-red', '--silencioso',
                    '--informe', str(target_report)], label='diagnostico-' + name.replace(' ', '_'),
                   timeout=60, cwd=executable.parent)
        if not target_report.is_file():
            raise RuntimeError('El programa instalado no produjo diagnóstico: ' + name)
        diagnostic = json.loads(target_report.read_text(encoding='utf-8-sig'))
        if diagnostic.get('estado') != 'OK':
            raise RuntimeError('Falló el diagnóstico del programa instalado: ' + name)
        expected[executable] = {'icon': icon, 'install_root': locations[role]}
        results.append({'executable': str(executable), 'sha256': sha256(executable),
                        'status': 'PASS', 'icon': icon, 'diagnostic': diagnostic})
    return expected, results


def record_runtime():
    from digitalpersona_native import library_directory
    import pefile
    folder = library_directory()
    rows = []
    for name in ('dpfpdd.dll', 'dpfj.dll'):
        path = folder / name
        with pefile.PE(str(path)) as binary:
            if binary.FILE_HEADER.Machine != 0x8664:
                raise RuntimeError('El runtime instalado no es x64: ' + name)
            info = binary.VS_FIXEDFILEINFO[0]
            version = (info.FileVersionMS >> 16, info.FileVersionMS & 65535,
                       info.FileVersionLS >> 16, info.FileVersionLS & 65535)
            if version < (3, 4, 0, 127):
                raise RuntimeError('El runtime instalado es anterior al original recuperado.')
        rows.append({'library': name, 'path': str(path), 'version': '.'.join(map(str, version)),
                     'sha256': sha256(path), 'architecture': 'x64'})
    return {'status': 'PASS', 'libraries': rows,
            'scope': 'Archivos del runtime instalado; no conecta ni prueba el lector.',
            'cleanup': 'Runtime del sistema conservado hasta destruir el runner efímero.'}


def preserve_sdk_log(qa_root):
    """Preserve only the known vendor-installation log, never the environment."""
    base = os.environ.get('LOCALAPPDATA')
    if not base:
        return {'status': 'NOT_PRESENT', 'reason': 'LOCALAPPDATA no disponible.'}
    source = Path(base) / 'AtlanticTechSoftware' / 'logs' / 'DigitalPersona_instalacion.log'
    if not source.is_file():
        return {'status': 'NOT_PRESENT', 'reason': 'El runtime no produjo el registro MSI conocido.'}
    if source.is_symlink() or getattr(source, 'is_junction', lambda: False)():
        raise RuntimeError('El registro del runtime no debe ser un enlace.')
    destination = qa_root / 'logs' / 'DigitalPersona_instalacion.log'
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return {'status': 'PRESERVED', 'log': str(destination), 'sha256': sha256(destination)}


def application_install_commands(installers, locations, qa_root, *, fresh, commercial):
    """Test the customer's entry points; only a fresh QA install overrides paths."""
    commands = []
    if commercial:
        for role, script in (('client', 'instalador_clientes.iss'),
                             ('owner', 'instalador_propietario.iss')):
            label = ('instalar-' if fresh else 'actualizar-') + role
            command = [str(installers[script]), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART']
            if fresh:
                command.append('/DIR=' + str(locations[role]))
            command.append('/LOG=' + str(qa_root / (label + '.log')))
            commands.append((label, command))
    else:
        label = 'instalar-completo' if fresh else 'actualizar-completo'
        command = [str(installers['instalador_completo.iss']), '/VERYSILENT',
                   '/SUPPRESSMSGBOXES', '/NORESTART']
        if fresh:
            parent = locations['admin'].parent
            if (locations['admin'].name != 'admin' or locations['reception'].name != 'reception' or
                    locations['reception'].parent != parent):
                raise RuntimeError('Los componentes deben compartir la raíz técnica exclusiva.')
            command.append('/QAInstallRoot=' + str(parent))
        command.append('/LOG=' + str(qa_root / (label + '.log')))
        commands.append((label, command))
    return commands


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', type=Path, default=Path.cwd())
    parser.add_argument('--ephemeral-runner', action='store_true')
    parser.add_argument('--timeout', type=int, default=600, help='Límite en segundos por instalador (45..1800).')
    args = parser.parse_args(argv)
    report = {'status': 'RUNNING', 'final': False, 'scope': SCOPE, 'edition': args.edition.name,
              'date_utc': datetime.now(timezone.utc).isoformat(), 'release_gate_modified': False,
              'commands': [], 'installed_executables': [], 'cleanup': {'status': 'NOT_RUN'},
              'stage': 'runner_guard', 'explicit_ephemeral_runner': args.ephemeral_runner,
              'runner_context': {name: os.environ.get(name) for name in
                 ('GITHUB_ACTIONS', 'RUNNER_ENVIRONMENT', 'RUNNER_OS', 'GITHUB_RUN_ID',
                  'RUNNER_TEMP', 'GITHUB_WORKSPACE')}}
    qa_root, runner, install_root, locations = None, None, None, {}
    def execute():
        nonlocal qa_root, runner, install_root, locations
        if not 45 <= args.timeout <= 1800:
            raise RuntimeError('El timeout debe estar entre 45 y 1800 segundos.')
        edition = args.edition.resolve(strict=True)
        report['runner'] = require_ephemeral_runner(edition, args.ephemeral_runner)
        # Once the runner guard has succeeded, retain preflight failures as files
        # too. This creates only QA evidence; no installer has been authorized yet.
        run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + f'-{os.getpid()}'
        candidate = edition / 'salida' / 'validacion' / 'instalacion-tecnica' / 'ejecuciones' / run_id
        confined_path(candidate, edition / 'salida' / 'validacion')
        candidate.mkdir(parents=True, exist_ok=False)
        qa_root = candidate
        report['run_id'] = run_id
        report['stage'] = 'authenticate_packaging'
        packaged, source_report = load_technical_report(edition)
        report['packaging_report'] = str(source_report)
        report['packaging_report_sha256'] = sha256(source_report)
        report['stage'] = 'native_architecture'
        architecture = native_windows_architecture()
        report['native_windows_architecture'] = architecture
        sys.path.insert(0, str(edition))
        build = importlib.import_module('build_windows')
        report['version'] = build.VERSION
        report['stage'] = 'match_edition_and_version'
        if (set(item['script'] for item in packaged['installers']) != set(build.INSTALLER_SCRIPTS) or
                set(item['name'] for item in packaged['executables']) != set(name for name, entry in build.EXECUTABLES) or
                packaged.get('version') != build.VERSION):
            raise RuntimeError('El paquete técnico no coincide con los programas y versión actuales.')
        report['stage'] = 'verify_installer_metadata'
        metadata = report.setdefault('installer_metadata', [])
        verify_technical_installer_metadata(packaged, diagnostics=metadata)
        if build.EXPECTED_BITS == 32 and architecture == 'x64':
            report.update(status='NOT_RUN', reason='El MSI DigitalPersona x86 exige NOT VersionNT64. '
                          'El runner Windows x64 no acredita instalación en Windows de 32 bits.')
            return
        if architecture != 'x64' or build.EXPECTED_BITS != 64:
            raise RuntimeError('Solo se acredita instalación nativa x64 en los runners Windows disponibles.')
        report['stage'] = 'reject_existing_installations'
        if uninstall_entries():
            raise RuntimeError('Ya existe un producto Gym instalado; se rechaza modificar instalaciones anteriores.')
        from windows_packaging_qa import require_runtime_files
        report['stage'] = 'verify_runtime_sources'
        report['runtime_source_sha256'] = require_runtime_files(edition, build.EXPECTED_BITS)
        runner = CommandRunner(qa_root / 'logs', report)
        report['stage'] = 'prepare_short_installation_directory'
        install_root = create_installation_root(report['runner'], edition)
        report['installation_root'] = str(install_root)
        installers = {item['script']: Path(item['executable']) for item in packaged['installers']}
        commercial = 'Comercial' in edition.name
        roles = ('client', 'owner') if commercial else ('admin', 'reception')
        locations = {role: install_root / role for role in roles}
        fresh_commands = application_install_commands(installers, locations, qa_root,
                                                       fresh=True, commercial=commercial)
        report['fresh_installation'] = {'entry_points': [Path(command[0]).name for _, command in fresh_commands],
                                        'status': 'RUNNING'}
        for label, command in fresh_commands:
            report['stage'] = label
            code = runner.run(command, label=label, timeout=args.timeout, accepted=(0, 3010), cwd=edition)
            if code == 3010:
                report['restart_required'] = True
        report['stage'] = 'verify_registrations'
        first_registration = validate_registered_apps(uninstall_entries(), locations)
        report['stage'] = 'verify_installed_runtime'
        report['runtime'] = record_runtime()
        report['stage'] = 'verify_installed_executables'
        expected, report['installed_executables'] = verify_installed_apps(build, packaged, locations, runner, qa_root)
        report['stage'] = 'verify_shortcuts'
        links = inspect_shortcuts(runner, qa_root, install_root, 'accesos-directos')
        report['shortcuts'] = {'status': 'PASS', 'counts': verify_shortcuts(links, expected, edition), 'entries': links}
        report['fresh_installation']['status'] = 'PASS'
        update_commands = application_install_commands(installers, locations, qa_root,
                                                        fresh=False, commercial=commercial)
        for label, command in update_commands:
            report['stage'] = label
            code = runner.run(command, label=label, timeout=args.timeout, accepted=(0, 3010), cwd=edition)
            if code == 3010:
                report['restart_required'] = True
        report['stage'] = 'verify_updated_registrations'
        after_update = validate_registered_apps(uninstall_entries(), locations)
        if after_update != first_registration:
            raise RuntimeError('El actualizador cambió directorios o creó registros duplicados.')
        report['stage'] = 'verify_updated_executables'
        expected, update_results = verify_installed_apps(build, packaged, locations, runner, qa_root / 'actualizacion')
        update_links = inspect_shortcuts(runner, qa_root, install_root, 'accesos-actualizados')
        update_counts = verify_shortcuts(update_links, expected, edition)
        if (len(update_links) != len(links) or update_counts != report['shortcuts']['counts']):
            raise RuntimeError('El actualizador creó accesos directos duplicados.')
        report['update'] = {'status': 'PASS', 'same_registration_and_locations': True,
                            'entry_points': [Path(command[0]).name for _, command in update_commands],
                            'existing_directories_reused_without_override': True,
                            'executables': update_results, 'shortcuts': update_links}
        report['status'] = 'PASS'
    try:
        execute()
    except Exception as error:
        report.update(status='FAIL', error=f'{type(error).__name__}: {error}', failed_stage=report['stage'])
    finally:
        if runner is not None and locations:
            try:
                # Only uninstall records rooted in directories assigned to this run.
                for row in uninstall_entries():
                    role = row['role']
                    if role not in locations:
                        raise RuntimeError('La limpieza encontró un producto que no pertenece a esta prueba.')
                    expected_root = locations[role].resolve()
                    if Path(row['install_location']).resolve() != expected_root:
                        raise RuntimeError('Se rechazó limpiar una instalación ajena al directorio técnico.')
                    uninstaller = confined_path(uninstall_executable(row['uninstall_command']), expected_root,
                                                require_file=True)
                    runner.run([str(uninstaller), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                                '/LOG=' + str(qa_root / ('desinstalar-' + role + '.log'))],
                               label='desinstalar-' + role, timeout=180, accepted=(0, 3010), cwd=expected_root)
                if uninstall_entries():
                    raise RuntimeError('Quedaron registros de las aplicaciones después de desinstalar.')
                remaining = inspect_shortcuts(runner, qa_root, install_root, 'accesos-despues-desinstalar')
                if remaining:
                    raise RuntimeError('Quedaron accesos directos después de desinstalar.')
                if any(path.exists() for path in (Path(item['executable']) for item in report['installed_executables'])):
                    raise RuntimeError('Quedaron ejecutables de las aplicaciones después de desinstalar.')
                remove_installation_root(install_root, report['runner'], args.edition.resolve())
                report['cleanup'] = {'status': 'PASS', 'application_registrations_removed': True,
                                     'application_executables_removed': True, 'shortcuts_removed': True,
                                     'system_runtime_removed': False, 'exclusive_installation_directory_removed': True}
            except Exception as error:
                report['cleanup'] = {'status': 'FAIL', 'error': f'{type(error).__name__}: {error}'}
                report['status'] = 'FAIL'
                report.setdefault('failed_stage', 'cleanup')
        if qa_root is not None:
            try:
                report['sdk_log'] = preserve_sdk_log(qa_root)
            except Exception as error:
                report['sdk_log'] = {'status': 'ERROR', 'error': f'{type(error).__name__}: {error}'}
        payload = json.dumps(report, ensure_ascii=False, indent=2)
        if qa_root is not None:
            (qa_root / 'informe_instalacion.json').write_text(payload, encoding='utf-8')
            latest = qa_root.parents[1] / 'informe_instalacion.json'
            latest.write_text(payload, encoding='utf-8')
        print(payload, flush=True)
    return 0 if report['status'] in ('PASS', 'NOT_RUN') else 1


if __name__ == '__main__':
    sys.exit(main())
