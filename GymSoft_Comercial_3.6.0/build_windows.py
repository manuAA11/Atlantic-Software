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

ROOT=Path(__file__).resolve().parent

def verify_executable_icon(executable, icon_name="icono.ico"):
    """Detiene la entrega si PyInstaller no embebió el icono GS completo."""
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
        if not expected.issubset(found):raise ValueError(f'{executable.name}: el icono no coincide con GS.')

def version_file(name):
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
    target=ROOT/'build'/f'{name}_version.txt'
    target.parent.mkdir(exist_ok=True)
    target.write_text(str(info),encoding='utf-8')
    return target

def main():
    if sys.platform!='win32':
        raise SystemExit('Los ejecutables Windows se compilan en Windows con Python 3.13 de 64 bits.')
    os.chdir(ROOT)
    os.environ['GYMSOFT_OFFLINE_QA'] = '1'  # No USB/driver required during compilation.
    if sys.version_info[:2]!=(3,13) or struct.calcsize('P')!=8:
        raise SystemExit('Usa Python 3.13 de 64 bits para esta entrega.')
    from release_gate import require_release_ready
    require_release_ready(ROOT,VERSION)
    from product_config import load_config
    load_config()
    if not (ROOT/'gymsoft_config.json').is_file():
        raise SystemExit('Falta gymsoft_config.json. Ejecuta INICIAR_CONFIGURACION.bat.')
    # The public configuration is validated above. Server compatibility and
    # access are checked at login, not while building an offline installer.
    if not compileall.compile_dir(str(ROOT),quiet=1,rx=__import__('re').compile(r'[/\\](\.venv|node_modules|dist|build)[/\\]')):
        raise SystemExit('Hay errores Python. No se generó el instalador.')
    compiler=shutil.which('ISCC.exe')
    if not compiler:
        for base in [os.environ.get('ProgramFiles(x86)',''),os.environ.get('ProgramFiles',''),os.environ.get('LOCALAPPDATA','')]:
            for suffix in ['Inno Setup 6/ISCC.exe','Programs/Inno Setup 6/ISCC.exe']:
                candidate=Path(base)/suffix
                if candidate.is_file():compiler=str(candidate);break
            if compiler:break
    if not compiler:raise SystemExit('Instala Inno Setup 6 antes de continuar: https://jrsoftware.org/isdl.php')
    subprocess.run([sys.executable,'run_validation.py'],check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_fingerprint_*.py'], check=True)
    for name,entry in [('GymSoftAdmin','app.py'),('GymSoftRecepcion','reception_app.py'),('GymSoftControl','owner_panel.py')]:
        icon_name = 'icono_recepcion.ico' if entry == 'reception_app.py' else 'icono.ico'
        subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name',name,
            '--icon',icon_name, '--version-file',str(version_file(name)), '--add-data','gymsoft_config.json;.', '--add-data','icono.ico;.', '--add-data','icono_recepcion.ico;.', '--collect-all','supabase','--collect-all','realtime',
            '--collect-all','postgrest','--collect-all','supabase_auth','--collect-all','tzdata',entry],check=True)
        verify_executable_icon(ROOT/'dist'/name/(name+'.exe'), icon_name)
    for script in ['instalador_clientes.iss','instalador_propietario.iss']:
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
