import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'GymSoft_ZTATTUZ_3.6.1_x86'))
from common.session_ui import recover_identity, SessionStatus


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


class RecoveryForm(unittest.TestCase):
    def status(self):
        status = SessionStatus.__new__(SessionStatus)
        status.root = Mock()
        status.root._foreground_io = False
        status.cloud = NS(email='same@example.invalid', sessions=NS(state='AUTH_REQUIRED'))
        return status

    def test_wrong_password_returns_to_form_without_closing_workspace(self):
        status = self.status()
        forms = [NS(result=('same@example.invalid', 'wrong')),
                 NS(result=('same@example.invalid', 'correct'))]
        with patch('runtime_cloud.LoginDialog', side_effect=forms) as form, \
             patch('common.session_ui.recover_identity', side_effect=[ValueError('Invalid login credentials'), None]) as recover, \
             patch('common.session_ui.run_io', side_effect=lambda root, fn, **kw: fn()), \
             patch('common.session_ui.messagebox') as messages:
            status.recover()
        self.assertEqual(recover.call_count, 2)
        self.assertEqual(form.call_args.kwargs['initial_email'], 'same@example.invalid')
        self.assertEqual(form.call_args.kwargs['error_message'], 'Correo o contraseña incorrectos.')
        self.assertFalse(form.call_args.kwargs['allow_signup'])
        messages.showerror.assert_not_called()
        status.root.destroy.assert_not_called()

    def test_cancel_reauthentication_keeps_workspace_and_requires_login(self):
        status = self.status()
        with patch('runtime_cloud.LoginDialog', return_value=NS(result=None)), \
             patch('common.session_ui.recover_identity') as recover, \
             patch('common.session_ui.messagebox'):
            status.recover()
        recover.assert_not_called()
        status.root.destroy.assert_not_called()
        self.assertEqual(status.cloud.sessions.state, 'AUTH_REQUIRED')
