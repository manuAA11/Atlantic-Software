"""Synchronize only the new additive membership upgrade and its shared modules."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = {
    'internal_plans.sql': ('ACTUALIZAR_PLANES_INTERNOS.sql', '20261013090000_internal_plans.sql'),
    'early_resume.sql': ('ACTUALIZAR_REANUDACION_MEMBRESIAS.sql', '20261013091000_early_resume.sql'),
}
MODULES = ('plan_forms.py', 'plan_editor_ui.py', 'membership_freeze_ui.py', 'membership_features.py')
TESTS = ('internal_memberships.mjs', 'early_resume.mjs', 'membership_feature_fixture.mjs',
         'test_internal_plans.py', 'membership_editor_smoke.py', 'freeze_ui_smoke.py')

def synchronize():
    for source, (standalone, migration) in MIGRATIONS.items():
        content = (ROOT / 'common' / source).read_bytes()
        (ROOT / 'supabase' / 'migrations' / migration).write_bytes(content)
        for edition in ROOT.glob('GymSoft_*'):
            (edition / standalone).write_bytes(content)
            (edition / 'supabase' / 'migrations' / migration).write_bytes(content)
    for edition in ROOT.glob('GymSoft_*'):
        for name in MODULES:
            source = ROOT / 'common' / name
            if source.exists():
                shutil.copyfile(source, edition / name)
        for name in TESTS:
            source = ROOT / 'common' / name
            if source.exists():
                shutil.copyfile(source, edition / 'tests' / name)

if __name__ == '__main__':
    synchronize()
    print('New membership migrations/modules synchronized; historical migrations untouched.')
