from pathlib import Path
import shutil
R=Path(__file__).resolve().parents[1]
for d in R.glob('GymSoft_*'):
 for n in ['marketing_ui.py','marketing_client.py','marketing_reception.py']:(d/n).write_text((R/'common'/n).read_text())
 for n in ['marketing_contracts.mjs','marketing_ui_smoke.py']:
  if (R/'common'/n).exists():(d/'tests'/n).write_text((R/'common'/n).read_text())
 p=d/'tests/migrations.mjs';s=p.read_text()
 if 'marketing=true' not in s:
  s=s.replace('daily=true}', 'daily=true,marketing=true}').replace(' return db;',' if(marketing && daily'+(' && upgrade' if 'upgrade=true' in s else '')+") await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_MARKETING.sql'),'utf8'));\n return db;");p.write_text(s)
 p=d/'run_validation.py';s=p.read_text()
 if "'marketing_contracts'" not in s:s=s.replace("SQL_TESTS=('","SQL_TESTS=('audit_logs','marketing_contracts','",1)
 if "'marketing_ui_smoke'" not in s and (d/'tests/marketing_ui_smoke.py').exists():s=s.replace("UI_TESTS=('","UI_TESTS=('marketing_ui_smoke','",1)
 if "stage('marketing_backend'" not in s:s=s.replace("            stage('recorrido_huellas'", "            stage('marketing_backend',[node,'--test',*[str(p) for p in sorted((ROOT/'marketing_backend/tests').glob('*.test.mjs'))]])\n            stage('recorrido_huellas'")
 p.write_text(s)
 shutil.copytree(R/'backend',d/'marketing_backend',dirs_exist_ok=True)
 shutil.copytree(R/'backend',d/'supabase/functions/marketing',dirs_exist_ok=True,ignore=shutil.ignore_patterns('tests'))
