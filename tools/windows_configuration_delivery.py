"""Create and verify a client-only configuration installer ZIP, without publishing.

This standard-library helper consumes genuine Windows QA receipts. It never
builds, installs, contacts a server, modifies release acceptance or publishes a
release. A ZIP remains NO FINAL, including when local installation tests pass.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile
import zipfile


EDITIONS = {
    'GymSoft_Comercial_3.6.0': ('Comercial', 'x64', 'instalador_clientes.iss'),
    'GymSoft_ZTATTUZ_3.6.1_x64': ('ZTATTUZ', 'x64', 'instalador_completo.iss'),
    'GymSoft_ZTATTUZ_3.6.1_x86': ('ZTATTUZ', 'x86', 'instalador_completo.iss'),
}
SCOPE = ('Instaladores para configurar y probar; NO FINAL. Las pruebas locales '
         'y de instalación no acreditan WhatsApp/Wompi con cuentas reales, '
         'lector/relé físico ni concurrencia PostgreSQL real.')
MANIFEST = 'MANIFIESTO_CLIENTE.json'
README = 'LEER_PRIMERO.txt'
SUMS = 'SHA256SUMS.txt'


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def safe_path(path, root, *, require_file=True):
    path, root = Path(path), Path(root).resolve()
    resolved = path.resolve(strict=require_file)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise RuntimeError('Un archivo de pruebas está fuera de su directorio autorizado.') from error
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or getattr(candidate, 'is_junction', lambda: False)():
            raise RuntimeError('No se admiten enlaces ni junctions en la entrega.')
        if candidate == root:
            break
    if require_file and not resolved.is_file():
        raise RuntimeError('Falta un archivo requerido de la entrega.')
    return resolved


def checked_file(path, root, expected, *, size=None):
    path = safe_path(path, root)
    if (not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected)
            or sha256_file(path) != expected or (size is not None and path.stat().st_size != size)):
        raise RuntimeError('SHA256 o tamaño incorrecto: ' + path.name)
    return path


def read_json(path):
    value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(value, dict):
        raise RuntimeError('El comprobante JSON no contiene un objeto válido.')
    return value


def literal_constants(path, names):
    result = {}
    for node in ast.parse(Path(path).read_text(encoding='utf-8-sig')).body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        for target in targets:
            if isinstance(target, ast.Name) and target.id in names:
                result[target.id] = ast.literal_eval(node.value)
    if set(result) != set(names):
        raise RuntimeError('Faltan constantes de versión o de las pruebas completas.')
    return result


def expected_installer(edition_name, version):
    product, bits, _ = EDITIONS[edition_name]
    name = (f'GymSoft_Instalar_o_Actualizar_{version}.exe' if product == 'Comercial'
            else f'ZTATTUZ_Instalar_o_Actualizar_{version}_{bits}.exe')
    return 'VALIDACION_NO_FINAL_' + name


def expected_configuration_files(edition_name, version):
    product, _, _ = EDITIONS[edition_name]
    main = expected_installer(edition_name, version)
    if product == 'Comercial':
        return {'instalador_clientes.iss': main,
                'instalador_propietario.iss': f'PRIVADO_PROPIETARIO/VALIDACION_NO_FINAL_GymSoft_Propietario_PRIVADO_{version}.exe'}
    return {'instalador_admin.iss': f'COMPONENTES/VALIDACION_NO_FINAL_ZTATTUZ_Admin_{version}.exe',
            'instalador_recepcion.iss': f'COMPONENTES/VALIDACION_NO_FINAL_ZTATTUZ_Recepcion_{version}.exe',
            'instalador_completo.iss': main}


def validate_local_suite(edition, version, receipt):
    constants = literal_constants(edition / 'run_validation.py', ('SQL_TESTS', 'UI_TESTS'))
    expected = ['python', 'contratos_extraidos', *constants['SQL_TESTS'],
                'marketing_backend', 'recorrido_huellas', 'simulacion_gimnasio',
                *constants['UI_TESTS']]
    stages = receipt.get('stages', [])
    if (len(expected) != 37 or receipt.get('status') != 'PASS' or receipt.get('scope') != 'all'
            or receipt.get('platform') != 'win32' or receipt.get('version') != version
            or [stage.get('name') for stage in stages] != expected
            or any(stage.get('status') != 'PASS' or stage.get('timed_out')
                   or stage.get('callback_failure') for stage in stages)):
        raise RuntimeError('La entrega exige las 37 etapas completas aprobadas en Windows.')
    evidence = receipt.get('evidence', {})
    validation = edition / 'salida' / 'validacion'
    original = validation / 'resultado_pruebas_all.json'
    if Path(evidence.get('report', '')) != original:
        raise RuntimeError('El informe de pruebas no corresponde a esta edición.')
    checked_file(original, validation, evidence.get('sha256'))
    if read_json(original) != {key: value for key, value in receipt.items() if key != 'evidence'}:
        raise RuntimeError('El comprobante completo difiere del informe original de pruebas.')
    logs = evidence.get('logs', [])
    if [item.get('path') for item in logs] != [name + '.log' for name in expected]:
        raise RuntimeError('La entrega exige los registros originales de todas las etapas.')
    for stage, item in zip(stages, logs):
        if stage.get('log') != item['path']:
            raise RuntimeError('Un registro de prueba no coincide con su etapa.')
        checked_file(validation / item['path'], validation, item.get('sha256'))
    return {'status': 'PASS', 'scope': 'all', 'platform': 'win32', 'stages': len(stages),
            'report_sha256': evidence['sha256']}


def load_inputs(edition):
    edition = Path(edition).resolve(strict=True)
    if edition.name not in EDITIONS or not (edition / 'build_windows.py').is_file():
        raise RuntimeError('Selecciona una edición válida de Comercial o ZTATTUZ.')
    version = literal_constants(edition / 'product_config.py', ('VERSION',))['VERSION']
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version):
        raise RuntimeError('La versión de la edición no es válida.')
    validation = edition / 'salida' / 'validacion'
    packaging_path = safe_path(validation / 'paquete-tecnico' / 'informe_empaquetado.json', validation)
    packaged = read_json(packaging_path)
    if (packaged.get('status') != 'PASS' or packaged.get('final') is not False
            or packaged.get('mode') != 'installers' or packaged.get('edition') != edition.name
            or packaged.get('version') != version or packaged.get('release_gate_modified') is not False
            or not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[0-9]+', packaged.get('run_id', ''))):
        raise RuntimeError('Falta un empaquetado completo NO FINAL válido de esta edición.')
    suite = validate_local_suite(edition, version, packaged.get('full_local_validation', {}))
    copies = packaged.get('configuration_installers', {})
    directory = edition / 'salida' / 'PRUEBAS_PARA_CONFIGURAR' / packaged['run_id']
    if copies.get('final') is not False or Path(copies.get('directory', '')) != directory:
        raise RuntimeError('Falta la entrega para configurar de la misma ejecución.')
    manifest_path = safe_path(directory / 'MANIFIESTO.json', edition)
    manifest = read_json(manifest_path)
    if (manifest.get('type') != 'INSTALLERS_CONFIGURATION_VALIDATION'
            or manifest.get('final') is not False or manifest.get('edition') != edition.name
            or manifest.get('version') != version or manifest.get('run_id') != packaged['run_id']
            or manifest.get('full_local_validation') != packaged['full_local_validation']
            or manifest.get('files') != copies.get('files')):
        raise RuntimeError('El manifiesto de configuración no coincide con el empaquetado.')
    expected_files = expected_configuration_files(edition.name, version)
    files = manifest.get('files', [])
    if (len(files) != len(expected_files)
            or {item.get('path') for item in files} != set(expected_files.values())):
        raise RuntimeError('La entrega para configurar está incompleta.')
    installers = packaged.get('installers', [])
    if (len(installers) != len(expected_files)
            or {item.get('script') for item in installers} != set(expected_files)):
        raise RuntimeError('Falta un instalador original aprobado.')
    original_root = validation / 'paquete-tecnico' / 'ejecuciones' / packaged['run_id']
    originals = {item['script']: item for item in installers}
    for item in files:
        if type(item.get('bytes')) is not int or item['bytes'] <= 0:
            raise RuntimeError('Falta el tamaño válido de un instalador completo.')
        checked_file(directory / item['path'], directory, item.get('sha256'), size=item.get('bytes'))
        script = next(script for script, path in expected_files.items() if path == item['path'])
        original = originals[script]
        if (original.get('status') != 'PASS' or original.get('final') is not False
                or original.get('sha256') != item.get('sha256')):
            raise RuntimeError('Una copia no coincide con su instalador original aprobado.')
        checked_file(original['executable'], original_root, original.get('sha256'))
    installation_path = safe_path(validation / 'instalacion-tecnica' / 'informe_instalacion.json', validation)
    installation = read_json(installation_path)
    if (installation.get('final') is not False or installation.get('edition') != edition.name
            or installation.get('version') != version or installation.get('release_gate_modified') is not False
            or installation.get('packaging_report_sha256') != sha256_file(packaging_path)
            or installation.get('runner', {}).get('environment') != 'github-hosted'
            or not re.fullmatch(r'[0-9]+', installation.get('runner', {}).get('github_run_id', ''))
            or 'NO FINAL' not in installation.get('scope', '')):
        raise RuntimeError('El informe de instalación no acredita este empaquetado técnico.')
    product, bits, _ = EDITIONS[edition.name]
    if bits == 'x86':
        if (installation.get('status') != 'NOT_RUN'
                or installation.get('native_windows_architecture') != 'x64'
                or 'NOT VersionNT64' not in installation.get('reason', '')
                or '32 bits' not in installation.get('reason', '')
                or installation.get('commands') or installation.get('installed_executables')):
            raise RuntimeError('x86 requiere el alcance explícito NOT_RUN por el MSI de Windows de 32 bits.')
    elif (installation.get('status') != 'PASS'
          or installation.get('native_windows_architecture') != 'x64'
          or any(installation.get(stage, {}).get('status') != 'PASS'
                 for stage in ('fresh_installation', 'runtime', 'shortcuts', 'update', 'cleanup'))):
        raise RuntimeError('La instalación, actualización y limpieza x64 deben estar aprobadas.')
    acceptance = safe_path(edition / 'release_readiness.json', edition)
    metadata = {'edition': edition.name, 'version': version, 'product': product, 'architecture': bits,
                'final': False, 'scope': SCOPE, 'packaging_run_id': packaged['run_id'],
                'github_run_id': installation['runner']['github_run_id'],
                'local_validation': suite,
                'installation': {'status': installation['status'], 'scope': installation['scope'],
                                 'reason': installation.get('reason'),
                                 'native_windows_architecture': installation['native_windows_architecture'],
                                 'report_sha256': sha256_file(installation_path)},
                'evidence': {'packaging_sha256': sha256_file(packaging_path),
                             'configuration_manifest_sha256': sha256_file(manifest_path)},
                'release_gate_modified': False, 'release_readiness_sha256': sha256_file(acceptance)}
    commit = os.environ.get('GITHUB_SHA')
    if commit:
        if not re.fullmatch(r'[a-fA-F0-9]{40}', commit):
            raise RuntimeError('La identidad GITHUB_SHA no es válida.')
        metadata['source_commit'] = commit.lower()
    current_run = os.environ.get('GITHUB_RUN_ID')
    if current_run and current_run != metadata['github_run_id']:
        raise RuntimeError('El informe corresponde a otra ejecución de GitHub Actions.')
    return directory / expected_installer(edition.name, version), metadata, acceptance


def readme_for(metadata):
    os_requirement = ('Windows de 32 bits exclusivamente. El MSI original DigitalPersona x86 rechaza Windows x64. '
                      'Se comprobaron compilación y diagnósticos de 32 bits; la instalación en Windows de 32 bits sigue pendiente.'
                      if metadata['architecture'] == 'x86' else
                      'Windows de 64 bits. Se comprobaron instalación, actualización, accesos directos y desinstalación en un runner Windows x64 efímero.')
    return ('ATLANTIC GYM · INSTALADORES PARA CONFIGURAR Y PROBAR · NO FINAL\n\n'
            f"Edición {metadata['product']} {metadata['architecture']} · versión {metadata['version']}.\n"
            f"Pruebas GitHub Actions: {metadata['github_run_id']}.\n\n"
            'Extrae este ZIP en una carpeta nueva y abre su archivo VALIDACION_NO_FINAL_*.exe. '
            'El instalador completo incluye Administración, Recepción, los iconos aprobados y el runtime del lector con su EULA. '
            'El computador donde instalas la aplicación no necesita Python ni Node.js.\n\n'
            + os_requirement + '\n\n'
            'Configura los servicios y la operación desde las pantallas de la aplicación. '
            'WhatsApp y Wompi requieren sus cuentas, backend y credenciales privadas en el servidor; nunca guardes secretos en el escritorio. '
            'Este ZIP no modifica ni despliega bases de datos o el backend.\n\n'
            'Esta es una versión para configuración y pruebas. La aceptación final sigue pendiente; '
            'las pruebas locales no acreditan WhatsApp/Wompi reales, PostgreSQL concurrente ni lector/relé físico.\n\n'
            'El panel PRIVADO_PROPIETARIO no está incluido. No mezcles Comercial con ZTATTUZ. '
            'El runtime DigitalPersona se incluye dentro de la aplicación y no se distribuye aquí por separado.\n')


def verify_delivery(path):
    path = Path(path)
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise RuntimeError('El ZIP contiene nombres de archivo duplicados.')
        for item in archive.infolist():
            name = PurePosixPath(item.filename)
            if (item.is_dir() or name.is_absolute() or len(name.parts) != 1
                    or '\\' in item.filename or name.name in ('.', '..')
                    or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise RuntimeError('El ZIP contiene rutas o enlaces no autorizados.')
        if archive.testzip() is not None:
            raise RuntimeError('CRC incorrecto del ZIP de instalación.')
        if MANIFEST not in names:
            raise RuntimeError('Falta el manifiesto del ZIP de clientes.')
        manifest = json.loads(archive.read(MANIFEST).decode('utf-8'))
        edition, version = manifest.get('edition'), manifest.get('version')
        if (edition not in EDITIONS or not isinstance(version, str)
                or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', version)
                or manifest.get('type') != 'CLIENT_CONFIGURATION_INSTALLER'
                or manifest.get('final') is not False or manifest.get('release_gate_modified') is not False):
            raise RuntimeError('El ZIP no es una entrega para clientes NO FINAL válida.')
        product, bits, _ = EDITIONS[edition]
        local = manifest.get('local_validation', {})
        installed = manifest.get('installation', {})
        if (manifest.get('product') != product or manifest.get('architecture') != bits
                or manifest.get('scope') != SCOPE
                or not re.fullmatch(r'[0-9]+', manifest.get('github_run_id', ''))
                or not re.fullmatch(r'[0-9]{8}T[0-9]{6}Z-[0-9]+', manifest.get('packaging_run_id', ''))
                or local.get('status') != 'PASS' or local.get('scope') != 'all'
                or local.get('platform') != 'win32' or local.get('stages') != 37
                or installed.get('native_windows_architecture') != 'x64'
                or 'NO FINAL' not in installed.get('scope', '')
                or installed.get('status') != ('NOT_RUN' if bits == 'x86' else 'PASS')
                or (bits == 'x86' and ('NOT VersionNT64' not in installed.get('reason', '')
                                      or '32 bits' not in installed.get('reason', '')))):
            raise RuntimeError('Los metadatos del ZIP no conservan el alcance real de sus pruebas.')
        hashes = [manifest.get('release_readiness_sha256'), local.get('report_sha256'),
                  installed.get('report_sha256'), *manifest.get('evidence', {}).values()]
        if any(not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value) for value in hashes):
            raise RuntimeError('Faltan comprobantes válidos de los informes originales.')
        executable = expected_installer(edition, version)
        if set(names) != {executable, README, MANIFEST, SUMS}:
            raise RuntimeError('El ZIP contiene archivos incompletos o ajenos a la entrega de clientes.')
        files = manifest.get('files', [])
        if len(files) != 2 or {item.get('path') for item in files} != {executable, README}:
            raise RuntimeError('El manifiesto no contiene exactamente el instalador completo y su guía.')
        digests = {}
        for item in files:
            digest, size = hashlib.sha256(), 0
            with archive.open(item['path']) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    digest.update(chunk)
                    size += len(chunk)
            actual = digest.hexdigest()
            if item.get('sha256') != actual or item.get('bytes') != size:
                raise RuntimeError('SHA256 o tamaño incorrecto dentro del ZIP: ' + item['path'])
            digests[item['path']] = actual
        digests[MANIFEST] = hashlib.sha256(archive.read(MANIFEST)).hexdigest()
        expected_sums = ''.join(digests[name] + '  ' + name + '\n' for name in (executable, README, MANIFEST))
        if archive.read(SUMS).decode('utf-8') != expected_sums:
            raise RuntimeError('Los comprobantes SHA256 del ZIP no coinciden.')
    return {'status': 'PASS', 'path': str(path.resolve()), 'sha256': sha256_file(path),
            'bytes': path.stat().st_size, 'edition': edition, 'version': version,
            'github_run_id': manifest.get('github_run_id'), 'final': False}


def create_delivery(edition, output):
    source, metadata, acceptance = load_inputs(edition)
    output = Path(output).absolute()
    for candidate in (output, *output.parents):
        if candidate.is_symlink() or getattr(candidate, 'is_junction', lambda: False)():
            raise RuntimeError('El destino no puede contener enlaces ni junctions.')
    name = f"AtlanticGym_{metadata['product']}_{metadata['architecture']}_PRUEBAS_PARA_CONFIGURAR_NO_FINAL.zip"
    target = output / name
    if target.exists():
        raise RuntimeError('El ZIP ya existe; no se sobrescribe una entrega anterior.')
    source_hash = sha256_file(source)
    readme = readme_for(metadata).encode('utf-8')
    manifest = {**metadata, 'type': 'CLIENT_CONFIGURATION_INSTALLER',
                'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'files': [{'path': source.name, 'sha256': source_hash, 'bytes': source.stat().st_size},
                          {'path': README, 'sha256': hashlib.sha256(readme).hexdigest(), 'bytes': len(readme)}]}
    encoded = json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8')
    sums = ''.join(item['sha256'] + '  ' + item['path'] + '\n' for item in manifest['files'])
    sums += hashlib.sha256(encoded).hexdigest() + '  ' + MANIFEST + '\n'
    output.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + name + '.', suffix='.preparando', dir=output)
    os.close(descriptor)
    temporary = Path(temporary)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.write(source, source.name)
            archive.writestr(README, readme)
            archive.writestr(MANIFEST, encoded)
            archive.writestr(SUMS, sums.encode('utf-8'))
        verify_delivery(temporary)
        if sha256_file(acceptance) != metadata['release_readiness_sha256']:
            raise RuntimeError('La aceptación cambió durante el empaquetado; se rechazó publicar el ZIP local.')
        # Windows rename rejects an existing destination. POSIX link supplies
        # the same atomic no-overwrite contract, including simultaneous runs.
        if os.name == 'nt':
            temporary.rename(target)
        else:
            os.link(temporary, target)
            temporary.unlink()
        return verify_delivery(target)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edition', type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path, help='Directorio del ZIP local para clientes.')
    mode.add_argument('--verify-delivery', type=Path, metavar='ZIP', help='Comprobar CRC y todos los archivos y SHA del ZIP.')
    args = parser.parse_args(argv)
    try:
        result = verify_delivery(args.verify_delivery) if args.verify_delivery else create_delivery(args.edition, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        return 0
    except Exception as error:
        print(f'FAIL · {type(error).__name__}: {error}', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
