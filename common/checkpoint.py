"""Create a recoverable source snapshot. Runtime binaries remain in the original release ZIPs."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
ROOT=Path(__file__).resolve().parents[1]
target=ROOT.parent/'outputs/GymSoft_Actualizacion_EN_DESARROLLO_20261003.zip'
target.parent.mkdir(exist_ok=True)
with ZipFile(target,'w',ZIP_DEFLATED) as archive:
    for path in ROOT.rglob('*'):
        if not path.is_file() or path.is_symlink(): continue
        if any(p in path.parts for p in ('.git','node_modules','__pycache__','salida','DigitalPersonaRuntime','audit')):continue
        if path.suffix.lower() in ('.dll','.exe','.msi','.cab','.pdf','.ico','.png','.jpeg') and 'evidence' not in path.parts:continue
        archive.write(path,path.relative_to(ROOT))
print(target)
