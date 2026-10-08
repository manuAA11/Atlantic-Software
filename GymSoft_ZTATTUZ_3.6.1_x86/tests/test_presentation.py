"""Verifica traducciones que afectan datos y mensajes de operaciones inciertas."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from desktop_ui import friendly_error, install_error_handler
from ui_text import STATES, state_text, state_value, service_status
import runtime_cloud
import app as admin_app


class PresentationTest(unittest.TestCase):
    def test_dashboard_uses_compact_priority_expiration_cards(self):
        keys = [key for key, *_ in admin_app.DashboardPage.EXPIRATION_BUCKETS]
        labels = [label for _key, label, *_ in admin_app.DashboardPage.EXPIRATION_BUCKETS]
        self.assertEqual(keys, ['expired', 'days_0_7', 'days_8_15', 'days_16_30'])
        self.assertEqual(labels, ['Vencidas', '0–7 días', '8–15 días', '16–30 días'])
        self.assertNotIn('days_31_plus', keys)

    def test_state_labels_roundtrip_without_changing_server_values(self):
        for field,values in STATES.items():
            for raw,label in values.items():
                with self.subTest(field=field,value=raw):
                    self.assertEqual(state_text(field,raw),label)
                    self.assertEqual(state_value(field,label),raw)




    def test_server_error_dictionary_preserves_guidance_without_raw_keys(self):
        for raw in ["{'message': 'Escribe un motivo.', 'code': 'P0001', 'details': None}",
                    '{"message":"Escribe un motivo.","code":"P0001","details":null}']:
            result=friendly_error(raw+'\n\nActualiza el historial antes de reintentar.')
            self.assertEqual(result,'Escribe un motivo.\n\nActualiza el historial antes de reintentar.')

    def test_authentication_errors_are_actionable(self):
        self.assertIn('Correo o contraseña incorrectos',friendly_error('Invalid login credentials'))
        self.assertIn('Confirma tu correo',friendly_error('Email not confirmed'))
        self.assertIn('Ya existe una cuenta',friendly_error('User already registered'))

    def test_login_retry_returns_directly_to_credentials_form(self):
        attempts = []

        class FakeCloud:
            def __init__(self):
                self.client = Mock()
                self.role = 'admin'
                self.gym_id = 'gym-1'
                self.gym_name = 'Demo'
                self.email = ''
                self.load_count = 0

            def sign_in(self, email, password):
                attempts.append((email, password))
                if len(attempts) == 1:
                    raise ValueError('Invalid login credentials')

            def verify_server(self): pass

            def load_gym(self):
                self.load_count += 1
                return True

        class FakeLogin:
            created = []

            def __init__(self, _parent, creating_account=False, **_kwargs):
                self.result = ('first@example.test', 'wrong-password') if not self.created else ('again@example.test', 'correct-password')
                self.creating_account = creating_account
                self.created.append(self)

        parent = NS(wait_window=Mock())
        with patch.object(runtime_cloud, 'CloudService', FakeCloud), \
             patch.object(runtime_cloud, 'LoginDialog', FakeLogin), \
             patch.object(runtime_cloud.messagebox, 'askyesno', return_value=True) as choice, \
             patch.object(runtime_cloud.messagebox, 'askretrycancel', return_value=True) as retry, \
             patch('ui_tasks.run_io', side_effect=lambda parent, fn: fn()):
            result = runtime_cloud.connect_cloud(parent)

        self.assertIsInstance(result, FakeCloud)
        self.assertEqual(attempts, [
            ('first@example.test', 'wrong-password'),
            ('again@example.test', 'correct-password'),
        ])
        self.assertEqual(choice.call_count, 1)
        self.assertEqual(retry.call_count, 1)
        self.assertEqual(len(FakeLogin.created), 2)
        self.assertFalse(FakeLogin.created[0].creating_account)
        self.assertFalse(FakeLogin.created[1].creating_account)

    def test_lost_response_never_claims_rollback(self):
        result=friendly_error('Connection reset by peer')
        self.assertIn('No se pudo confirmar',result)
        self.assertIn('historial antes de repetirla',result)
        self.assertNotIn('revertido',result)


    def test_whatsapp_needs_a_recent_service_heartbeat(self):
        now=datetime(2026,9,7,12,tzinfo=timezone.utc)
        settings={'phone_number_id':'test','whatsapp_enabled':True}
        self.assertEqual(service_status(settings,now)[0],'Pendiente de activar')
        for age in [timedelta(days=1),timedelta(seconds=-60)]:
            self.assertEqual(service_status({**settings,'last_worker_at':(now-age).isoformat()},now)[0],
                             'Sin actividad reciente')
        self.assertEqual(service_status({**settings,'last_worker_at':now.isoformat()},now),
                         ('En servicio','success'))
        self.assertEqual(service_status({**settings,'last_worker_at':now.isoformat(),'whatsapp_enabled':False},now)[0],
                         'Envíos pausados')
        self.assertEqual(service_status({**settings,'last_worker_at':'invalid'},now)[0],'Estado no disponible')

    def test_callback_failure_is_visible_and_log_does_not_include_data(self):
        root=Mock(winfo_exists=lambda:True)
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ',{'LOCALAPPDATA':folder}), \
             patch('desktop_ui.messagebox.showerror') as alert:
            install_error_handler(root)
            try:
                raise RuntimeError('PRIVATE-TOKEN-AND-CUSTOMER-DATA')
            except RuntimeError:
                root.report_callback_exception(*sys.exc_info())
            alert.assert_called_once()
            self.assertIn('Referencia: GS-',alert.call_args.args[1])
            log=(Path(folder)/'GymControl/logs/aplicacion.log').read_text(encoding='utf-8')
            self.assertIn('RuntimeError',log)
            self.assertNotIn('PRIVATE-TOKEN-AND-CUSTOMER-DATA',log)


if __name__=='__main__':unittest.main()
