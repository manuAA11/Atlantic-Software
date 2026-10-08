from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
path = next((ROOT/'supabase/migrations').glob('*_membership_freezes_time_pipeline.sql'))
content = (ROOT/'common/membership_freezes.sql').read_text()
path.write_text(content)
for product in ROOT.glob('GymSoft_*'):
    (product/'ACTUALIZAR_CONGELACION_Y_HORAS.sql').write_text(content)
    (product/'supabase/migrations'/path.name).write_text(content)
    for name in ('gym_time.py', 'membership_freeze_ui.py', 'release_gate.py'):
        if (ROOT/'common'/name).exists():
            shutil.copyfile(ROOT/'common'/name, product/name)
    for name in ('membership_freezes.mjs', 'time_pipeline.mjs', 'test_time_pipeline.py', 'freeze_ui_smoke.py', 'test_release_gate.py'):
        if (ROOT/'common'/name).exists():
            shutil.copyfile(ROOT/'common'/name, product/'tests'/name)
    p = product/'tests/migrations.mjs'
    s = p.read_text()
    if 'freezes=true' not in s:
        s = s.replace('marketing=true}', 'marketing=true,freezes=true}')
        condition = 'freezes && marketing && daily' + (' && upgrade' if 'upgrade=true' in s else '')
        s = s.replace(' return db;', f" if({condition}) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_CONGELACION_Y_HORAS.sql'),'utf8'));\n return db;")
        p.write_text(s)
    p = product/'run_validation.py'
    s = p.read_text()
    if "'membership_freezes'" not in s:
        s = s.replace("SQL_TESTS=('", "SQL_TESTS=('membership_freezes','", 1)
    if "'time_pipeline'" not in s:
        s = s.replace("SQL_TESTS=('", "SQL_TESTS=('time_pipeline','", 1)
    if (product/'tests/freeze_ui_smoke.py').exists() and "'freeze_ui_smoke'" not in s:
        s = s.replace("UI_TESTS=('", "UI_TESTS=('freeze_ui_smoke','", 1)
    p.write_text(s)
print('Freeze migration and shared modules synchronized for all three targets')
