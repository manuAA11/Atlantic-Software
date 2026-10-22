import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'GymSoft_ZTATTUZ_3.6.1_x86'))
from common.session_ui import recover_identity


class IdentityRecovery(unittest.TestCase):
    def cloud(self):
        return NS(user_id='user', gym_id='gym', role='receptionist', email='same@example.invalid',
            sign_in=Mock(), load_gym=Mock(return_value=True), sessions=Mock())

    def test_wrong_email_rejected_before_changing_session(self):
        cloud = self.cloud()
        with self.assertRaises(ValueError):
            recover_identity(cloud, 'other@example.invalid', 'synthetic')
        cloud.sign_in.assert_not_called()

    def test_same_context_recovers_without_replaying_a_write(self):
        cloud = self.cloud()
        recover_identity(cloud, 'same@example.invalid', 'synthetic')
        cloud.sign_in.assert_called_once()
        cloud.sessions.start.assert_called_once()
        cloud.sessions.logout.assert_not_called()

    def test_changed_gym_cannot_reuse_open_workspace(self):
        cloud = self.cloud()
        def changed():
            cloud.gym_id = 'different'
            return True
        cloud.load_gym.side_effect = changed
        with self.assertRaises(PermissionError):
            recover_identity(cloud, 'same@example.invalid', 'synthetic')
        cloud.sessions.logout.assert_called_once()
        self.assertEqual(cloud.gym_id, 'gym')
