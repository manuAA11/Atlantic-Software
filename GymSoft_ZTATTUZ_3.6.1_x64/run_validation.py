"""Ejecuta las pruebas locales y conserva un informe por etapa, sin credenciales."""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from product_config import VERSION
from validation_process import run_stage

ROOT=Path(__file__).resolve().parent
SQL_TESTS=('time_pipeline','membership_freezes','audit_logs','marketing_contracts','daily_tickets','fingerprints','upgrade_compatibility','security','contracts','ticket_plans','ticket_followup')
UI_TESTS=('marketing_ui_smoke','freeze_ui_smoke','door_ui_smoke','dialog_design_ui_smoke','ui_wait_smoke','access_layout_ui_smoke','client_fingerprint_ui_smoke','fingerprint_ui_smoke','windows_ui_smoke','responsive_ui_smoke','biometric_ui_smoke','ticket_ui_smoke',
          'performance_ui_smoke','popdown_ui_smoke','layout_modes_ui_smoke','review_ui_smoke',
          'layout_consistency_ui_smoke')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-only',action='store_true',help='Pruebas de datos sin abrir ventanas.')
    parser.add_argument('--ui-only',action='store_true',help='Solo pruebas gráficas, sin repetir la simulación.')
    args=parser.parse_args()
    print(f'Gym soft {VERSION} · Validación local con lector simulado', flush=True)
    if args.data_only and args.ui_only:parser.error('Selecciona un solo alcance.')
    target=ROOT/'salida/validacion';target.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,GYMSOFT_OFFLINE_QA='1',PYTHON=sys.executable,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONUNBUFFERED='1')
    result=dict(version=VERSION,started_at=datetime.now(timezone.utc).isoformat(),
                platform=sys.platform,scope='data' if args.data_only else 'ui' if args.ui_only else 'all',
                status='RUNNING',stages=[])
    def save():
        encoded=json.dumps(result,ensure_ascii=False,indent=2)
        (target/'resultado_pruebas.json').write_text(encoded,encoding='utf-8')
        (target/f'resultado_pruebas_{result["scope"]}.json').write_text(encoded,encoding='utf-8')
        lines=[f'Gym soft {VERSION} · {result["status"]}',f'Alcance: {result["scope"]} · Plataforma: {sys.platform}',
               *[f'{r["status"]}: {r["name"]} ({r["seconds"]:.1f} s) · {r["log"]}' for r in result['stages']],
               '', 'Estas pruebas usan datos ficticios y PostgreSQL local.',
               'Pendiente de comprobación manual: instaladores, hardware del lector, correo de acceso,',
               'conexión real entre equipos y envío de WhatsApp. Un PASS no garantiza ausencia de todo bug.']
        if result.get('error'):lines+=['',result['error']]
        (target/'RESUMEN_PRUEBAS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    def stage(name,command):
        print('\nPRUEBA: '+name,flush=True)
        start=time.monotonic();log=target/(name+'.log')
        try:
            with log.open('w',encoding='utf-8') as output:
                def emit(line):
                    output.write(line);output.flush()
                    print(line,end='',flush=True)
                outcome=run_stage(command,cwd=ROOT,env=env,name=name,emit=emit,
                                  timeout=120 if name in ('fingerprint_ui_smoke', 'access_layout_ui_smoke') else 300)
            record=dict(name=name,status='PASS' if outcome.returncode==0 else 'FAIL',
                        seconds=outcome.seconds,log=log.name,timed_out=outcome.timed_out,
                        callback_failure=outcome.callback_failure)
        except Exception as error:
            result['stages'].append(dict(name=name,status='FAIL',
                seconds=round(time.monotonic()-start,2),log=log.name,error=str(error)))
            save()
            raise
        result['stages'].append(record)
        save()
        if outcome.returncode:
            reason='Se agotó el tiempo de la prueba.' if outcome.timed_out else 'La prueba detectó un error.'
            raise RuntimeError(f'Falló {name}. {reason} Revisa {log}.')
    save()
    try:
        if not args.ui_only:
            node=shutil.which('node')
            if not node:raise RuntimeError('Instala Node.js LTS en este equipo de compilación y vuelve a abrir el archivo .bat.')
            if not (ROOT/'node_modules/@electric-sql/pglite/package.json').is_file():
                raise RuntimeError('Falta la base local de pruebas. Ejecuta PREPARAR_PRUEBAS.bat; después repite la validación.')
            stage('python',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py'])
            stage('contratos_extraidos',[sys.executable,'tests/extract_contracts.py'])
            for name in SQL_TESTS:stage(name,[node,f'tests/{name}.mjs'])
            stage('marketing_backend',[node,'--test','--test-reporter=tap',*[str(p) for p in sorted((ROOT/'marketing_backend/tests').glob('*.test.mjs'))]])
            stage('recorrido_huellas',[sys.executable,'tests/fingerprint_journey.py'])
            stage('simulacion_gimnasio',[sys.executable,'tests/gym_simulation.py'])
        if not args.data_only:
            print('Mantén visibles las ventanas de prueba y el escritorio desbloqueado hasta terminar.',flush=True)
            for name in UI_TESTS:stage(name,[sys.executable,f'tests/{name}.py'])
        result['status']='PASS'
    except Exception as error:
        result['status']='FAIL';result['error']=str(error)
        raise
    finally:save()
    print('\nPruebas completadas. Informe: '+str(target/'RESUMEN_PRUEBAS.txt'),flush=True)


if __name__=='__main__':main()
