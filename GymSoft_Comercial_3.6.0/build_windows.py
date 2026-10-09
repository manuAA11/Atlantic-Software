from __future__ import annotations
import compileall
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
import struct
from product_config import VERSION, PRODUCT_NAME
from atlantic_ui import COPYRIGHT, PUBLISHER
from preparar_entorno import require_runtime

ROOT=Path(__file__).resolve().parent
EXPECTED_BITS=64
EXECUTABLES = (('GymSoftAdmin', 'app.py'), ('GymSoftRecepcion', 'reception_app.py'), ('GymSoftControl', 'owner_panel.py'))
INSTALLER_SCRIPTS = ('instalador_clientes.iss', 'instalador_propietario.iss')
COLLECT_PACKAGES = ('supabase', 'realtime', 'postgrest', 'supabase_auth', 'tzdata')

def verify_executable_icon(executable, icon_name="icono.ico"):
    """Detiene la entrega si PyInstaller no embebió el icono Atlantic aprobado completo."""
    import pefile
    raw=(ROOT/icon_name).read_bytes()
    _,kind,count=struct.unpack_from('<HHH',raw)
    if kind!=1 or count<1:raise ValueError('icono.ico no es un icono Windows válido.')
    expected=set()
    for index in range(count):
        size,offset=struct.unpack_from('<II',raw,6+index*16+8)
        expected.add(hashlib.sha256(raw[offset:offset+size]).hexdigest())
    with pefile.PE(str(executable)) as pe:
        types={entry.id:entry for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries}
        if 3 not in types or 14 not in types:raise ValueError(f'{executable.name}: falta el icono embebido.')
        found=set()
        for entry in types[3].directory.entries:
            for language in entry.directory.entries:
                data=language.data.struct
                found.add(hashlib.sha256(pe.get_data(data.OffsetToData,data.Size)).hexdigest())
        if not expected.issubset(found):raise ValueError(f'{executable.name}: el icono no coincide con el recurso Atlantic aprobado.')

def version_file(name, *, build_root=None):
    from PyInstaller.utils.win32.versioninfo import (VSVersionInfo,FixedFileInfo,
        StringFileInfo,StringTable,StringStruct,VarFileInfo,VarStruct)
    number=tuple(int(x) for x in VERSION.split('.'))+(0,)
    description={'GymSoftAdmin':'Administración','GymSoftRecepcion':'Recepción',
                 'GymSoftControl':'Control comercial'}[name]
    info=VSVersionInfo(ffi=FixedFileInfo(filevers=number,prodvers=number),kids=[
        StringFileInfo([StringTable('040904b0',[
            StringStruct('CompanyName',PUBLISHER),StringStruct('FileDescription',PRODUCT_NAME+' · '+description),
            StringStruct('FileVersion',VERSION),StringStruct('ProductVersion',VERSION),
            StringStruct('LegalCopyright',COPYRIGHT),
            StringStruct('ProductName',PRODUCT_NAME),StringStruct('OriginalFilename',name+'.exe')])]),
        VarFileInfo([VarStruct('Translation',[1033,1200])])])
    target=(Path(build_root) if build_root else ROOT/'build')/f'{name}_version.txt'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(str(info),encoding='utf-8')
    return target

def find_inno_compiler():
    compiler = shutil.which('ISCC.exe')
    if compiler:
        return compiler
    for base in (os.environ.get('ProgramFiles(x86)', ''),
                 os.environ.get('ProgramFiles', ''), os.environ.get('LOCALAPPDATA', '')):
        if not base:
            continue
        for suffix in ('Inno Setup 6/ISCC.exe', 'Programs/Inno Setup 6/ISCC.exe'):
            candidate = Path(base) / suffix
            if candidate.is_file():
                return str(candidate)
    raise RuntimeError('Instala Inno Setup 6: https://jrsoftware.org/isdl.php')


def pyinstaller_command(name, entry, *, dist_root=None, build_root=None):
    """Use the same actual entry points and resources in production and technical QA."""
    build_root = Path(build_root).resolve() if build_root else ROOT / 'build'
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
               '--windowed', '--onedir', '--name', name,
               '--icon', str(ROOT / ('icono_recepcion.ico' if entry == 'reception_app.py' else 'icono.ico')),
               '--version-file', str(version_file(name, build_root=build_root)),
               '--paths', str(ROOT), '--workpath', str(build_root / 'work'),
               '--specpath', str(build_root / 'spec'),
               '--distpath', str(Path(dist_root).resolve() if dist_root else ROOT / 'dist')]
    # Spec files resolve data relative to their own directory, not the shell cwd.
    for resource in ('gymsoft_config.json', 'icono.ico', 'icono_recepcion.ico'):
        command.extend(('--add-data', str(ROOT / resource) + os.pathsep + '.'))
    command.extend(('--hidden-import', 'PIL._tkinter_finder'))
    for package in COLLECT_PACKAGES:
        command.extend(('--collect-all', package))
    command.append(str(ROOT / entry))
    return command


def verify_executable_architecture(executable):
    import pefile
    expected = 0x8664 if EXPECTED_BITS == 64 else 0x14c
    with pefile.PE(str(executable)) as binary:
        if binary.FILE_HEADER.Machine != expected:
            raise RuntimeError(f'{executable.name}: el ejecutable no es de {EXPECTED_BITS} bits.')


def freeze_executables(*, dist_root=None, build_root=None, runner=subprocess.run):
    dist_root = Path(dist_root).resolve() if dist_root else ROOT / 'dist'
    results = []
    for name, entry in EXECUTABLES:
        command = pyinstaller_command(name, entry, dist_root=dist_root, build_root=build_root)
        runner(command, cwd=ROOT, check=True)
        executable = dist_root / name / (name + '.exe')
        icon_name = 'icono_recepcion.ico' if entry == 'reception_app.py' else 'icono.ico'
        verify_executable_icon(executable, icon_name)
        verify_executable_architecture(executable)
        results.append({'name': name, 'entry': entry, 'icon': icon_name,
                        'executable': executable, 'process_bits': EXPECTED_BITS,
                        'sha256': hashlib.sha256(executable.read_bytes()).hexdigest()})
    return results


def diagnose_frozen_executable(executable, report, *, runner=subprocess.run):
    # Existing diagnostics exercise frozen components without login or network.
    executable, report = Path(executable), Path(report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.unlink(missing_ok=True)
    runner([str(executable), '--diagnostico', '--sin-red', '--silencioso',
            '--informe', str(report)], cwd=executable.parent, check=True, timeout=45)
    if not report.is_file():
        raise RuntimeError(f'{executable.name}: el diagnóstico no generó su informe.')
    data = json.loads(report.read_text(encoding='utf-8'))
    if data.get('estado') != 'OK':
        raise RuntimeError(f'{executable.name}: no pasó el diagnóstico de componentes.')
    return data


def main():
    if sys.platform!='win32':
        raise SystemExit('Los ejecutables Windows se compilan en Windows con Python 3.13 o 3.14 de 64 bits.')
    os.chdir(ROOT)
    os.environ['GYMSOFT_OFFLINE_QA'] = '1'  # No USB/driver required during compilation.
    try:
        require_runtime(EXPECTED_BITS)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
    from release_gate import require_release_ready
    require_release_ready(ROOT,VERSION)
    from product_config import load_config
    load_config()
    if not (ROOT/'gymsoft_config.json').is_file():
        raise SystemExit('Falta gymsoft_config.json. Ejecuta INICIAR_CONFIGURACION.bat.')
    # The public configuration is validated above. Server compatibility and
    # access are checked at login, not while building an offline installer.
    if not compileall.compile_dir(str(ROOT),quiet=1,rx=__import__('re').compile(r'[/\\](\.venv[^/\\]*|node_modules|dist|build)[/\\]')):
        raise SystemExit('Hay errores Python. No se generó el instalador.')
    try:
        compiler = find_inno_compiler()
    except RuntimeError as error:
        raise SystemExit(str(error)) from error
    subprocess.run([sys.executable,'run_validation.py'],check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_fingerprint_*.py'], check=True)
    for result in freeze_executables():
        report = ROOT/'salida'/'validacion'/(result['name'].replace(' ', '_')+'_ejecutable.json')
        diagnose_frozen_executable(result['executable'], report)
    for script in INSTALLER_SCRIPTS:
        subprocess.run([compiler,'/DAppVersion='+VERSION,script],check=True)
    output=ROOT/'salida';output.mkdir(exist_ok=True)
    panel=output/f'GymSoft_Control_Propietario_{VERSION}.zip'
    with zipfile.ZipFile(panel,'w',zipfile.ZIP_DEFLATED) as z:
        for p in (ROOT/'dist/GymSoftControl').rglob('*'):
            if p.is_file():z.write(p,p.relative_to(ROOT/'dist'))
    deliverables=[output/f'GymSoft_Instalar_o_Actualizar_{VERSION}.exe',output/f'GymSoft_Propietario_PRIVADO_{VERSION}.exe',panel]
    (output/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name for p in deliverables)+'\n')
    print(f'Solo GymSoft_Instalar_o_Actualizar_{VERSION}.exe se entrega a clientes.')
    print(f'GymSoft_Propietario_PRIVADO_{VERSION}.exe instala tu panel privado y su acceso directo.')
    print(f'GymSoft_Control_Propietario_{VERSION}.zip es exclusivo del proveedor.')

if __name__=='__main__':main()
