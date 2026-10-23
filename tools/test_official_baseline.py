"""Protect the working x86 reader and relay baseline while unifying clients."""
from tools.hardware_baseline import syntax_sha256
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class OfficialX86Baseline(unittest.TestCase):
    def test_reader_worker_and_relay_logic_match_official_baseline(self):
        reference=json.loads((ROOT/'deployment/official_baseline.json').read_text())
        self.assertEqual(reference['baseline_edition'],'ZTATTUZ x86 (32-bit)')
        for name,proof in reference['hardware_proof'].items():
            with self.subTest(module=name):
                data=(ROOT/'common'/name).read_bytes()
                if 'sha256' in proof:
                    # Normalize checkout line endings, as Git does on Windows.
                    normalized=data.replace(b'\r\n',b'\n')
                    self.assertEqual(hashlib.sha256(normalized).hexdigest(),proof['sha256'])
                else:
                    self.assertEqual(syntax_sha256(data.decode('utf-8'),excluded_methods=('is_busy',)),proof['normalized_ast_sha256'])

if __name__=='__main__':unittest.main()
