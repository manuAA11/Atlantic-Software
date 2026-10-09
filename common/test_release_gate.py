import json
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release_gate import REQUIRED, require_release_ready

class ReleaseGateTests(unittest.TestCase):
    def commercial_fixture(self, root, product='Atlantic Gym', version='3.6.0'):
        (root/'product_config.py').write_text(
            f'PRODUCT_NAME = {product!r}\nVERSION = {version!r}\n', encoding='utf-8')
        (root/'app.py').write_text('class GymSoftApp: pass\n', encoding='utf-8')
        (root/'reception_app.py').write_text('class ReceptionApp: pass\n', encoding='utf-8')
        (root/'evidence.json').write_text('{}', encoding='utf-8')
        checks={name:{'passed':True,'evidence':'evidence.json'} for name in REQUIRED}
        reason='Comercial conserva la ausencia de relé.'
        checks['relay_hardware']={'passed':False,'state':'not_applicable',
            'reason':reason,'evidence':'relay-not-applicable.json'}
        proof={'criterion':'relay_hardware','state':'not_applicable',
            'product_name':product,'version':version,'reason':reason,
            'source_hash_encoding':'UTF-8; line endings normalized to LF',
            'source_sha256':{name:hashlib.sha256((root/name).read_text(encoding='utf-8').encode('utf-8')).hexdigest()
                             for name in ('product_config.py','app.py','reception_app.py')},
            'absent_modules':['door_access.py']}
        data={'version':version,'checks':checks}
        (root/'release_readiness.json').write_text(json.dumps(data),encoding='utf-8')
        (root/'relay-not-applicable.json').write_text(json.dumps(proof),encoding='utf-8')
        return data, proof

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

    def test_commercial_can_document_its_absent_relay_without_a_hardware_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data,_=self.commercial_fixture(root)
            require_release_ready(root,'3.6.0')
            self.assertIs(data['checks']['relay_hardware']['passed'],False)

    def test_commercial_not_applicable_relay_does_not_authorize_missing_wompi(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data,_=self.commercial_fixture(root)
            data['checks']['wompi_sandbox']['passed']=False
            (root/'release_readiness.json').write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaisesRegex(SystemExit,'wompi_sandbox') as error:
                require_release_ready(root,'3.6.0')
            self.assertNotIn('relay_hardware',str(error.exception))

    def test_ztattuz_cannot_declare_its_relay_not_applicable(self):
        for claim_pass in (False,True):
            with self.subTest(passed=claim_pass),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);data,_=self.commercial_fixture(
                    root,product='Atlantic Gym · ZTATTUZ',version='3.6.1')
                data['checks']['relay_hardware']['passed']=claim_pass
                data['product_name']='Atlantic Gym'  # A manifest cannot override code identity.
                (root/'release_readiness.json').write_text(json.dumps(data),encoding='utf-8')
                with self.assertRaisesRegex(SystemExit,'relay_hardware'):
                    require_release_ready(root,'3.6.1')

    def test_other_commercial_requirements_cannot_be_declared_not_applicable(self):
        for name in REQUIRED:
            if name=='relay_hardware':continue
            with self.subTest(criterion=name),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);data,_=self.commercial_fixture(root)
                data['checks'][name]['state']='not_applicable'
                (root/'release_readiness.json').write_text(json.dumps(data),encoding='utf-8')
                with self.assertRaisesRegex(SystemExit,name):require_release_ready(root,'3.6.0')

    def test_absent_relay_requires_matching_complete_evidence(self):
        changes={'criterion':'freeze','state':'passed','product_name':'Atlantic Gym · ZTATTUZ',
                 'version':'old','reason':'Otra justificación','source_sha256':{},'absent_modules':[]}
        for name,value in changes.items():
            with self.subTest(field=name),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);_,proof=self.commercial_fixture(root)
                proof[name]=value
                (root/'relay-not-applicable.json').write_text(json.dumps(proof),encoding='utf-8')
                with self.assertRaisesRegex(SystemExit,'relay_hardware'):
                    require_release_ready(root,'3.6.0')

    def test_absent_relay_evidence_must_still_match_the_source_version(self):
        for source in ('product_config.py','app.py','reception_app.py'):
            with self.subTest(source=source),tempfile.TemporaryDirectory() as folder:
                root=Path(folder);self.commercial_fixture(root)
                with (root/source).open('a',encoding='utf-8') as output:output.write('# modified\n')
                with self.assertRaisesRegex(SystemExit,'relay_hardware'):
                    require_release_ready(root,'3.6.0')

    def test_git_crlf_checkout_keeps_the_same_source_applicability_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.commercial_fixture(root)
            for source in ('product_config.py','app.py','reception_app.py'):
                text=(root/source).read_text(encoding='utf-8')
                (root/source).write_bytes(text.replace('\n','\r\n').encode('utf-8'))
            require_release_ready(root,'3.6.0')

    def test_commercial_with_a_door_module_cannot_reuse_absence_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.commercial_fixture(root)
            (root/'door_access.py').write_text('RELAY_ON = bytes([1,2,3,4])\n',encoding='utf-8')
            with self.assertRaisesRegex(SystemExit,'relay_hardware'):require_release_ready(root,'3.6.0')

    def test_absent_relay_cannot_be_presented_as_an_approved_hardware_test(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);data,_=self.commercial_fixture(root)
            data['checks']['relay_hardware']['passed']=True
            (root/'release_readiness.json').write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaisesRegex(SystemExit,'relay_hardware'):require_release_ready(root,'3.6.0')
