"""Run existing offline checks without editing source; retain each failure."""
import argparse, datetime, importlib.util, json, os, pathlib, subprocess, sys, time
p=argparse.ArgumentParser()
p.add_argument('edition',choices=['GymSoft_Comercial_3.6.0','GymSoft_ZTATTUZ_3.6.1_x86','GymSoft_ZTATTUZ_3.6.1_x64'])
p.add_argument('--scope',choices=['data','ui','smoke','all'],default='data')
p.add_argument('--run-label',default='',help='Optional suffix to retain a separate run, e.g. python314.')
a=p.parse_args()
if a.run_label and not all(c.isalnum() or c in '-_' for c in a.run_label):
 p.error('--run-label must contain only letters, digits, - or _.')
root=pathlib.Path(__file__).resolve().parents[1]/a.edition
sys.path.insert(0,str(root))
import run_validation
from validation_process import run_stage
out=pathlib.Path(__file__).resolve().parents[1]/'evidence'/'closure-validation-20261008'/a.edition/(a.scope+('-'+a.run_label if a.run_label else ''))
out.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,GYMSOFT_OFFLINE_QA='1',PYTHON=sys.executable,PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONUNBUFFERED='1')
steps=[]
if a.scope in ('data','all'):
 steps=[('python',[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py']),('contracts_extracted',[sys.executable,'tests/extract_contracts.py']),('migrations',['node','tests/migrations.mjs'])]
 steps += [(n,['node',f'tests/{n}.mjs']) for n in run_validation.SQL_TESTS]
 steps += [('marketing_backend',['node','--test','--test-reporter=tap',*[str(x) for x in sorted((root/'marketing_backend/tests').glob('*.test.mjs'))]])]
 steps += [(n,[sys.executable,f'tests/{f}.py']) for n,f in [('recorrido_huellas','fingerprint_journey'),('simulacion_gimnasio','gym_simulation')]]
if a.scope in ('ui','smoke','all'):
 names=run_validation.UI_TESTS if a.scope in ('ui','all') else ['marketing_ui_smoke','freeze_ui_smoke','windows_ui_smoke']
 if a.scope in ('ui','all'):
  names=list(names)+sorted(p.stem for p in (root/'tests').glob('*_ui_smoke.py') if p.stem not in names)
 steps += [(n,[sys.executable,f'tests/{n}.py']) for n in names]
result={'edition':a.edition,'scope':a.scope,'python':sys.version,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stages':[],'note':'Existing source tests. Contracts extracted from current source. Offline PGlite and simulated hardware; no Windows or external-service verification.'}
for name,cmd in steps:
 with (out/(name+'.log')).open('w') as f:
  r=run_stage(cmd,cwd=root,env=env,name=name,emit=lambda line:f.write(line),timeout=300)
 record={'name':name,'status':'PASS' if r.returncode==0 else 'FAIL','returncode':r.returncode,'seconds':r.seconds,'timed_out':r.timed_out,'callback_failure':r.callback_failure}
 result['stages'].append(record)
 (out/'results.json').write_text(json.dumps(result,indent=2))
 print(a.edition,name,record['status'],flush=True)
result['status']='PASS' if all(x['status']=='PASS' for x in result['stages']) else 'FAIL'
(out/'results.json').write_text(json.dumps(result,indent=2))
sys.exit(0 if result['status']=='PASS' else 1)
