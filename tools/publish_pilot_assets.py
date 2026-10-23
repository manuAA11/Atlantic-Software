"""Stage only authenticated client test installers; never owner tools or final builds."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import zipfile

from tools.windows_configuration_delivery import verify_delivery, MANIFEST, expected_installer


def stage(source, output, *, version, source_commit, run_id, tag):
    if (not re.fullmatch(r'\d+\.\d+\.\d+', version) or not re.fullmatch(r'[a-f0-9]{40}', source_commit)
        or not str(run_id).isdigit() or not re.fullmatch(r'[A-Za-z0-9_.-]+', tag)):
        raise ValueError('Identidad de publicación inválida.')
    source, output = Path(source), Path(output)
    if output.exists(): raise ValueError('No se sobrescribe una publicación anterior.')
    receipts = []
    for path in sorted(source.rglob('*.zip')):
        verified = verify_delivery(path)
        with zipfile.ZipFile(path) as archive:
            manifest = json.loads(archive.read(MANIFEST))
            if (manifest['version'] != version or manifest.get('source_commit') != source_commit
                or manifest['github_run_id'] != str(run_id)):
                raise ValueError('Los instaladores no corresponden al commit y ejecución aprobados.')
            name = expected_installer(manifest['edition'], version)
            item = next(f for f in manifest['files'] if f['path'] == name)
            receipts.append((path, manifest, name, item, verified))
    editions = {'GymSoft_Comercial_3.6.0', 'GymSoft_ZTATTUZ_3.6.1_x64', 'GymSoft_ZTATTUZ_3.6.1_x86'}
    if len(receipts) != 3 or {r[1]['edition'] for r in receipts} != editions:
        raise ValueError('Se requieren los tres perfiles compatibles validados.')
    output.mkdir(parents=True)
    releases = []
    for path, manifest, name, item, verified in receipts:
        published_name='AtlanticGym_Actualizar_'+version+'_'+manifest['architecture']+('_proveedor2' if manifest['edition']=='GymSoft_Comercial_3.6.0' else '')+'.exe'
        with zipfile.ZipFile(path) as archive, archive.open(name) as src, (output / published_name).open('xb') as dst:
            shutil.copyfileobj(src, dst)
        target = output / published_name
        with target.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != item['sha256']:
                raise ValueError('El instalador cambió durante la preparación.')
        releases.append(dict(version=version, product='Atlantic Gym', variant='commercial' if manifest['edition']=='GymSoft_Comercial_3.6.0' else 'ztattuz',
            architecture='windows-'+manifest['architecture'], file=published_name, sha256=item['sha256'], bytes=item['bytes'],
            minimum_schema='core-1', installer_url='https://github.com/manuAA11/Atlantic-Software/releases/download/'+tag+'/'+published_name,
            validation=verified, installation=manifest['installation']))
    payload=dict(version=version, final=False, source_commit=source_commit, github_run_id=str(run_id), releases=releases)
    (output/'PILOT_UPDATE_MANIFEST.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    (output/'SHA256SUMS.txt').write_text(''.join(r['sha256']+'  '+r['file']+'\n' for r in releases))
    (output/'LEER_PRIMERO.txt').write_text(
        'Atlantic Gym '+version+' · Actualización opcional de prueba · NO FINAL\n'
        'Los perfiles conservan la conexión y los identificadores de instalación existentes.\n'
        'x64: instalación y actualización verificadas en Windows x64 efímero.\n'
        'x86: compilación y diagnósticos de 32 bits verificados; instalación en Windows de 32 bits pendiente.\n'
        'No se incluyen herramientas privadas de propietario ni migraciones de bases de datos.\n'
        'No se ha certificado aquí el lector/relé físico ni los pilotos de servicios externos.\n')
    return payload


def main():
    parser=argparse.ArgumentParser()
    for name in ('source','output','version','commit','run-id','tag'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    result=stage(args.source,args.output,version=args.version,source_commit=args.commit,run_id=args.run_id,tag=args.tag)
    print(json.dumps(dict(status='PASS',final=False,version=result['version'],client_installers=len(result['releases']))))


if __name__=='__main__':main()
