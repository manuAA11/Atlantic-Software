import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release_gate import REQUIRED, require_release_ready

class ReleaseGateTests(unittest.TestCase):
    def test_local_pass_does_not_authorize_an_untested_provider_or_hardware(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'evidence.json').write_text('{}')
            checks={name:{'passed':True,'evidence':'evidence.json'} for name in REQUIRED}
            checks['wompi_sandbox']['passed']=False
            (root/'release_readiness.json').write_text(json.dumps({'version':'test','checks':checks}))
            with self.assertRaisesRegex(SystemExit,'wompi_sandbox'):require_release_ready(root,'test')
    def test_a_new_version_cannot_reuse_missing_or_old_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaises(SystemExit):require_release_ready(root,'new')
            checks={name:{'passed':True,'evidence':'missing.json'} for name in REQUIRED}
            (root/'release_readiness.json').write_text(json.dumps({'version':'old','checks':checks}))
            with self.assertRaisesRegex(SystemExit,'versión'):require_release_ready(root,'new')
            with self.assertRaisesRegex(SystemExit,'Falta comprobar'):require_release_ready(root,'old')
    def test_verified_current_version_can_proceed_to_windows_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'evidence.json').write_text('{}')
            checks={name:{'passed':True,'evidence':'evidence.json'} for name in REQUIRED}
            (root/'release_readiness.json').write_text(json.dumps({'version':'test','checks':checks}))
            require_release_ready(root,'test')
