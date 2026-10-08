"""Create independent source backups after local validation; never a final release."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path('/workspace/deliverables')
summary = json.loads((ROOT / 'evidence/closure-validation-20261008/summary.json').read_text())
parity = json.loads((ROOT / 'evidence/closure-validation-20261008/parity.json').read_text())
if summary['status'] != 'PASS' or parity['status'] != 'PASS':
    raise SystemExit('Source backups blocked: local validation or synchronization failed.')
files = sorted(set(subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')) - {''})
shared = {'backend', 'common', 'supabase', 'onboarding', 'deployment', 'assets', 'docs', 'evidence'}
root_files = {'AGENTS.md', '.env.example', '.gitignore'}
OUTPUT.mkdir(parents=True, exist_ok=True)
manifest = {'type': 'DEVELOPMENT_SOURCE_BACKUPS', 'final_release': False, 'packages': []}
for product, editions in [('AtlanticGym', {'GymSoft_Comercial_3.6.0'}),
                          ('ZTATTUZ', {'GymSoft_ZTATTUZ_3.6.1_x86', 'GymSoft_ZTATTUZ_3.6.1_x64'})]:
    name = f'{product}_FUENTES_EN_DESARROLLO_20261008'
    target = OUTPUT / (name + '.zip')
    included = [name for name in files if Path(name).parts[0] in shared | editions or name in root_files]
    warning = ('# ' + product + ': respaldo de fuentes en desarrollo\n\n'
               'Contiene todas las fuentes recuperadas disponibles de este producto, assets, pruebas, migraciones y configuración publicable.\n'
               'No es una entrega final ni un instalador. Falta el redistribuible DigitalPersona autorizado y la aceptación externa/Windows.\n'
               'No hay secretos, venv ni node_modules; instalar requirements.txt y npm ci en cada edición.\n'
               'Leer docs/ESTADO_CIERRE.md y docs/INTEGRACIONES_Y_WINDOWS.md. Conservar release_readiness.json: no forzar los criterios a true.\n\n'
               'Ediciones incluidas: ' + ', '.join(sorted(editions)) + '.\n'
               'Entradas: app.py (Administrador), reception_app.py (Recepción); owner_panel.py solo en Comercial y privado del propietario.\n'
               'Los generadores comunes que sincronizan productos esperan el monorepo completo. El runtime y build de cada edición son independientes.\n')
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(name + '/README.md', warning)
        for relative in included:
            path = ROOT / relative
            if not path.is_file() or path.is_symlink():
                raise SystemExit('Invalid source file: ' + relative)
            archive.write(path, name + '/' + relative)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        for edition in editions:
            for required in ('app.py', 'reception_app.py', 'atlantic_ui.py', 'icono.ico', 'icono_recepcion.ico', 'requirements.txt', 'requirements-build.txt', 'release_readiness.json', '.env.example', 'tests/backend_sql_flow.mjs'):
                assert f'{name}/{edition}/{required}' in names, required
        assert not any('/node_modules/' in n or '/.env' in n and not n.endswith('.env.example') for n in names)
    item = {'file': target.name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(included) + 1, 'bytes': target.stat().st_size}
    manifest['packages'].append(item)
    print(item['file'], item['files'], 'files', item['sha256'])
(OUTPUT / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
