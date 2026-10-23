"""All existing installations execute the same Commercial application."""
from pathlib import Path
import os
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CommercialUnification(unittest.TestCase):
    def test_shared_application_preserves_provider_contract_and_installation_data(self):
        script = r"""
from unittest.mock import Mock, patch
import app, reception_app, cloud_database, reception_database, runtime_cloud, licensing
from common import app as canonical_admin, reception_app as canonical_reception
from common import cloud_database as canonical_db, runtime_cloud as canonical_cloud
from common.deployment_profile import PROFILE
from product_config import PRODUCT_NAME
assert app is canonical_admin and reception_app is canonical_reception
assert cloud_database is canonical_db and runtime_cloud is canonical_cloud
assert PRODUCT_NAME == 'Atlantic Gym'
assert app.DATA_FOLDER_NAME == PROFILE.data_folder
client=Mock();client.session_manager=Mock()
with patch.object(runtime_cloud, 'managed_client', return_value=client):
    cloud=runtime_cloud.CloudService()
    client.rpc.assert_not_called()  # No network on the Tk construction thread.
    client.rpc.return_value.execute.return_value.data={'gym_id':'preserved-id','gym_name':'Existing Gym','role':'admin','enabled':True,'timezone':'America/Bogota'}
    assert cloud.load_gym() and cloud.gym_id == 'preserved-id'
    client.rpc.assert_called_once_with(PROFILE.context_rpc)
    client.rpc.reset_mock()
    client.rpc.return_value.execute.return_value.data={'product':PROFILE.server_product,'schema_version':PROFILE.server_schema}
    cloud.verify_server();client.rpc.assert_called_once_with(PROFILE.system_rpc)
    client.rpc.reset_mock()
    if PROFILE.legacy_provider:
        cloud.client.core_control=None
        assert licensing.check_license(cloud)['authority']=='core'
        client.rpc.assert_not_called() # Do not call an absent Commercial RPC.
        assert 'updated_at' not in cloud_database.EXCEL_IMPORT_COLUMNS['clients'].values()
        assert PROFILE.data_folder=='GymControl' and not PROFILE.scoped_data
    else:
        client.rpc.return_value.execute.return_value.data={'allowed':True}
        assert licensing.check_license(cloud)['allowed']
        assert client.rpc.call_args.args[0]=='commercial_check_license'
        assert 'updated_at' in cloud_database.EXCEL_IMPORT_COLUMNS['clients'].values()
        assert PROFILE.data_folder=='GymSoft' and PROFILE.scoped_data
"""
        for edition in sorted(ROOT.glob('GymSoft_*')):
            if not (edition/'app.py').is_file():continue
            with self.subTest(edition=edition.name):
                result=subprocess.run([sys.executable,'-c',script],cwd=edition,capture_output=True,text=True,env=dict(os.environ,GYMSOFT_OFFLINE_QA='1'),timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

if __name__=='__main__':unittest.main()
