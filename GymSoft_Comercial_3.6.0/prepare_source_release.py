"""Prepara un ZIP reproducible de FUENTES. No compila EXE ni conecta a la base."""
from pathlib import Path
import hashlib
import zipfile
from product_config import VERSION

ROOT=Path(__file__).resolve().parent

def main():
    parts=[p.read_text(encoding='utf-8') for p in sorted((ROOT/'sql').glob('*.sql'))]
    parts.append((ROOT/'ACTUALIZAR_EDITOR_PROPIETARIO_3.1.0.sql').read_text(encoding='utf-8'))
    parts.append((ROOT/'ACTUALIZAR_TIQUETERAS_3.3.0.sql').read_text(encoding='utf-8'))
    (ROOT/'INSTALAR_BASE_NUEVA.sql').write_text(
        '-- Sólo para un proyecto comercial NUEVO y VACÍO. Incluye el editor 3.1.0.\n'+
        '\n\n'.join(parts)+'\n',encoding='utf-8')
    output=ROOT.parent/'release';output.mkdir(exist_ok=True)
    files=[]
    for p in ROOT.rglob('*'):
        relative=p.relative_to(ROOT)
        if any(part.startswith('.') or part in {'node_modules','__pycache__','build','dist','salida','supabase'} for part in relative.parts):continue
        if p.is_file() and p.suffix in {'.py','.md','.bat','.sql','.json','.iss','.ico','.txt','.mjs'}:
            if p.name.startswith('LEEME_ACTUALIZAR_') and p.name!=f'LEEME_ACTUALIZAR_{VERSION}.md':continue
            files.append(p)
    files.sort()
    target=output/f'GymSoft_Comercial_{VERSION}_COMPLETO.zip'
    prefix=f'GymSoft_Comercial_{VERSION}'
    checksums='\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(ROOT).as_posix() for p in files)+'\n'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            info=zipfile.ZipInfo(prefix+'/'+p.relative_to(ROOT).as_posix(),date_time=(2026,9,13,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,p.read_bytes())
        z.writestr(prefix+'/SHA256_FUENTES.txt',checksums)
    with zipfile.ZipFile(target) as z:
        bad=z.testzip()
        if bad:raise RuntimeError('ZIP dañado: '+bad)
    print(f'{target}\nArchivos: {len(files)+1}\nBytes: {target.stat().st_size}\nSHA256: {hashlib.sha256(target.read_bytes()).hexdigest()}')

if __name__=='__main__':main()
