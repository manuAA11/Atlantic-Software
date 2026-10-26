"""Protect the working x86 reader and relay baseline while unifying clients."""
from tools.hardware_baseline import syntax_sha256
import ast
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class OfficialX86Baseline(unittest.TestCase):
    def test_reader_worker_and_relay_logic_match_official_baseline(self):
        reference=json.loads((ROOT/'deployment/official_baseline.json').read_text())
        self.assertEqual(reference['baseline_edition'],'ZTATTUZ x86 (32-bit)')
        self.assertEqual(set(reference['official_architectures']),{'windows-x86','windows-x64'})
        for name,proof in reference['hardware_proof'].items():
            with self.subTest(module=name):
                data=(ROOT/'common'/name).read_bytes()
                if 'sha256' in proof:
                    # Normalize checkout line endings, as Git does on Windows.
                    normalized=data.replace(b'\r\n',b'\n')
                    self.assertEqual(hashlib.sha256(normalized).hexdigest(),proof['sha256'])
                else:
                    source=data.decode('utf-8')
                    if name=='door_access.py':
                        # The requested discovery fix is a separate read-only
                        # adapter. Preserve the original digest of every other
                        # driver instruction, including ON/OFF and watchdogs.
                        tree=ast.parse(source)
                        discovery=next(item for item in tree.body if isinstance(item,ast.FunctionDef) and item.name=='available_ports')
                        adapter=ast.parse('''def available_ports():
    from common.relay_ports import available_ports as discover_ports
    return discover_ports()
''').body[0]
                        self.assertEqual(ast.dump(discovery),ast.dump(adapter))
                        original=ast.parse('''def available_ports():
    from serial.tools import list_ports
    return [dict(port=p.device, description=p.description or 'Puerto USB',
                 vid=p.vid, pid=p.pid, serial_number=p.serial_number or '', location=p.location or '')
            for p in list_ports.comports()]
''').body[0]
                        tree.body[tree.body.index(discovery)]=original
                        source=ast.unparse(tree)
                    self.assertEqual(syntax_sha256(source,excluded_methods=('is_busy',)),proof['normalized_ast_sha256'])

if __name__=='__main__':unittest.main()
