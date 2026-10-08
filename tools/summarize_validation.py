"""Combine initial results and explicit successful rechecks; retain the failed originals."""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'evidence/closure-validation-20261008'
rows = []
for edition, suffix, count in [('GymSoft_Comercial_3.6.0', 'commercial', 137),
                                ('GymSoft_ZTATTUZ_3.6.1_x86', 'x86', 152),
                                ('GymSoft_ZTATTUZ_3.6.1_x64', 'x64', 153)]:
    initial = json.loads((BASE / edition / 'all/results.json').read_text())
    ui = json.loads((BASE / edition / 'ui/results.json').read_text())
    stages = [dict(s, evidence=f'{edition}/all/{s["name"]}.log') for s in initial['stages']
              if s['name'] not in {x['name'] for x in ui['stages']} and s['name'] != 'python']
    python_log = f'rechecks/python-{suffix}-313-bootstrap-final.log'
    py = (BASE / python_log).read_text()
    passed = bool(re.search(rf'Ran {count} tests .*\n\nOK\s*$', py))
    stages.append({'name': 'python', 'status': 'PASS' if passed else 'FAIL',
                   'tests': count, 'evidence': python_log})
    stages += [dict(s, evidence=f'{edition}/ui/{s["name"]}.log') for s in ui['stages']]
    for name, file, marker in [('backend_sql_flow', f'backend-sql-{suffix}.log', 'PASS: 28 cross-layer checks'),
                               ('marketing_compile', f'marketing-compile-{suffix}.log', 'MARKETING SQL COMPILES')]:
        text = (BASE / 'rechecks' / file).read_text()
        stages.append({'name': name, 'status': 'PASS' if text.startswith(marker) else 'FAIL',
                       'evidence': f'rechecks/{file}'})
    for stage in stages:
        final = BASE / 'rechecks' / f'sql-{suffix}-{stage["name"]}-final.log'
        if final.is_file():
            stage['status'] = 'PASS' if final.read_text().startswith('PASS:') else 'FAIL'
            stage['evidence'] = str(final.relative_to(BASE))
            stage['rechecked_after_sql_fix'] = True
    status = 'PASS' if all(s['status'] == 'PASS' for s in stages) else 'FAIL'
    rows.append({'edition': edition, 'status': status, 'stages': stages,
                 'python_tests': count, 'data_stages': sum(s['name'] not in {x['name'] for x in ui['stages']} for s in stages),
                 'ui_stages': len(ui['stages']), 'initial_failed_stages': [s['name'] for s in initial['stages'] if s['status'] == 'FAIL']})
result = {'status': 'PASS' if all(r['status'] == 'PASS' for r in rows) else 'FAIL',
          'scope': 'Automatic checks in Linux/Tk and PGlite. Synthetic hardware, external transport and Vault. No real external pilot or Windows installation.',
          'editions': rows, 'total_stages': sum(len(r['stages']) for r in rows),
          'python_tests': sum(r['python_tests'] for r in rows),
          'backend_tests_per_edition': 56,
          'notes': ['Original failed run is retained. Python rerun fixes missing icons; complete UI rerun fixes sidebar overflow and verifies role icons.',
                    'Python suite now includes five preparation/build regressions per edition. Rechecked with CPython 3.13.15 including ensurepip; original system 3.13.5 creation failed because ensurepip was absent. Python 3.14 and UI compatibility are recorded separately in python-compatibility.json.',
                    'Counts of checks inside SQL/UI stages overlap and must not be added as unique tests.']}
(BASE / 'summary.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
for row in rows:
    print(row['edition'], row['status'], len(row['stages']), 'stages;', row['python_tests'], 'Python tests;', row['ui_stages'], 'UI stages')
print('TOTAL', result['status'], result['total_stages'], 'stages')
raise SystemExit(0 if result['status'] == 'PASS' else 1)
