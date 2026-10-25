"""Startup recovery reaches the credential form instead of restoring in a loop."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'GymSoft_ZTATTUZ_3.6.1_x86'))
from common import runtime_cloud as access
from common.session_manager import SessionClockError


class LoginRecovery(unittest.TestCase):
    def setUp(self):
        self.root = Mock()
        self.cloud = Mock(email='same@example.invalid', role='admin')
        self.cloud.restore_session.return_value = False
        self.cloud.load_gym.return_value = True
        self.forms = []
        self.answers = [('same@example.invalid', 'synthetic-password')]
        def form(*args, **kwargs):
            value = Mock(result=self.answers.pop(0), creating_account=False)
            value.options = kwargs
            self.forms.append(value)
            return value
        for name, value in (
            ('common.runtime_cloud.CloudService', Mock(return_value=self.cloud)),
            ('common.runtime_cloud.LoginDialog', Mock(side_effect=form)),
            ('common.runtime_cloud._record_login_error', Mock()),
            ('common.runtime_cloud.messagebox', Mock()),
            ('ui_tasks.run_io', Mock(side_effect=lambda root, fn, **kwargs: fn())),
            ('licensing.check_license', Mock(return_value={'allowed': True})),
        ):
            guard = patch(name, value)
            guard.start()
            self.addCleanup(guard.stop)

    def assert_no_error_cancel_or_revocation(self):
        access.messagebox.askretrycancel.assert_not_called()
        access.messagebox.showerror.assert_not_called()
        self.cloud.sessions.logout.assert_not_called()
        self.root.destroy.assert_not_called()

    def test_saved_restore_error_opens_login_and_succeeds(self):
        self.cloud.restore_session.side_effect = SessionClockError('El servidor todavía no pudo validar la sesión.')
        self.assertIs(access.connect_cloud(self.root), self.cloud)
        self.cloud.restore_session.assert_called_once()
        self.cloud.sign_in.assert_called_once_with('same@example.invalid', 'synthetic-password')
        self.assertIn('servidor', self.forms[0].options['error_message'])
        self.assert_no_error_cancel_or_revocation()

    def test_bad_credentials_return_to_form_then_corrected_password_works(self):
        self.answers.append(('same@example.invalid', 'corrected-password'))
        self.cloud.sign_in.side_effect = [ValueError('Invalid login credentials'), None]
        self.assertIs(access.connect_cloud(self.root), self.cloud)
        self.assertEqual(len(self.forms), 2)
        self.assertEqual(self.forms[1].options['error_message'], 'Correo o contraseña incorrectos.')
        self.assertEqual(self.forms[1].options['initial_email'], 'same@example.invalid')
        self.cloud.restore_session.assert_called_once()
        self.assertEqual(self.cloud.sign_in.call_args.args, ('same@example.invalid', 'corrected-password'))
        self.assert_no_error_cancel_or_revocation()

    def test_failure_after_saved_restore_does_not_restore_again(self):
        self.cloud.restore_session.return_value = True
        self.cloud.load_gym.side_effect = [ValueError('JWT issued at future'), True]
        self.assertIs(access.connect_cloud(self.root), self.cloud)
        self.cloud.restore_session.assert_called_once()
        self.assertEqual(len(self.forms), 1)
        self.assertIn('servidor', self.forms[0].options['error_message'])
        self.assert_no_error_cancel_or_revocation()

    def test_reception_returns_to_login_without_changing_role(self):
        self.cloud.role = 'receptionist'
        self.cloud.restore_session.side_effect = ValueError('JWT issued at future')
        self.assertIs(access.connect_cloud(self.root, reception=True), self.cloud)
        access.CloudService.assert_called_once_with(session_role='reception')
        self.assertEqual(self.cloud.role, 'receptionist')
        self.assert_no_error_cancel_or_revocation()

    def test_only_explicitly_closing_form_cancels_startup(self):
        self.answers = [None]
        self.cloud.restore_session.side_effect = ValueError('JWT issued at future')
        self.assertIsNone(access.connect_cloud(self.root))
        self.assertEqual(len(self.forms), 1)
        self.cloud.sessions.close.assert_called_once()
        self.cloud.sign_in.assert_not_called()
        self.assert_no_error_cancel_or_revocation()

    def test_configuration_error_cannot_retry_credentials_forever(self):
        access.CloudService.side_effect = ValueError('Proveedor sin configurar')
        self.assertIsNone(access.connect_cloud(self.root))
        self.assertEqual(self.forms, [])
        access.messagebox.showerror.assert_called_once()


class SavedSessionStartup(unittest.TestCase):
    def test_startup_does_not_force_rotation_of_a_valid_saved_session(self):
        saved = NS(user=NS(id='synthetic-user', email='synthetic@example.invalid'))
        sessions = Mock()
        sessions.restore.return_value = saved
        sessions.ensure.return_value = saved
        cloud = NS(sessions=sessions)
        self.assertTrue(access.CloudService.restore_session(cloud))
        sessions.ensure.assert_called_once_with()
        self.assertEqual(cloud.user_id, 'synthetic-user')
        self.assertEqual(cloud.email, 'synthetic@example.invalid')


if __name__ == '__main__':
    unittest.main()
