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
from owner_editor import OwnerEditor
from owner_editor_forms import record_patch
from ui_text import STATES, state_text, state_value, service_status
import runtime_cloud
import licensing
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

    def test_editor_translates_payment_and_class_states_before_saving(self):
        for field,old,entered,expected in [
            ('payment_status','posted','Anulado','void'),
            ('status','PROGRAMADA','Cancelada','CANCELADA'),
            ('result','DENEGADA','Autorizada','PERMITIDA'),
        ]:
            columns=[{'name':field,'type':'text','editable':True,'nullable':False},
                     {'name':'id','type':'bigint','editable':False,'nullable':False}]
            result=record_patch(columns,{field:old,'id':1},{field:entered,'id':'999'})
            self.assertEqual(result,{field:expected})

    def test_unchanged_translated_state_does_not_create_a_change(self):
        columns=[{'name':'payment_status','type':'text','editable':True,'nullable':False}]
        with self.assertRaisesRegex(ValueError,'No hay cambios'):
            record_patch(columns,{'payment_status':'posted'},{'payment_status':'Vigente'})

    def test_editor_displays_all_rows_and_handles_an_empty_page(self):
        for states in [[],['posted','void']]:
            rows=[{'data':{'id':i+1,'payment_status':v}} for i,v in enumerate(states)]
            data={'rows':rows,'total':len(rows),'columns':[
                {'name':'id','editable':False},{'name':'payment_status','editable':True}]}
            fake=NS(busy=False,offset=0,gym={'id':'gym'},
                table_var=Mock(get=lambda:'Pagos y membresías'),search_var=Mock(get=lambda:''),
                tree=Mock(get_children=lambda:()),page_var=Mock(),display=OwnerEditor.display,
                call=Mock(return_value=data))
            fake.run=lambda operation,done:done(operation())
            OwnerEditor.load_records(fake)
            self.assertEqual(fake.tree.insert.call_count,len(rows))
            self.assertEqual(len(fake.items),len(rows))
            if rows:
                self.assertEqual(fake.tree.insert.call_args_list[1].kwargs['values'],['2','Anulado'])
            else:
                fake.page_var.set.assert_called_once_with('0–0 de 0')

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
             patch('licensing.check_license', return_value={'allowed': True}):
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

    def test_license_network_glitch_does_not_close_application(self):
        class Window:
            def __init__(self):
                self.callbacks = []
                self._license_network_notice = False
                self.closed = False

            def after(self, delay, callback):
                self.callbacks.append((delay, callback))
                return len(self.callbacks)

            def winfo_exists(self):
                return True

            def close_app(self):
                self.closed = True

        class InlineThread:
            def __init__(self, target, **_kwargs): self.target = target
            def start(self): self.target()

        window = Window()
        with patch.object(licensing, 'check_license', side_effect=ConnectionError('offline')), \
             patch.object(licensing.threading, 'Thread', InlineThread), \
             patch.object(licensing.messagebox, 'showwarning') as warning, \
             patch.object(licensing.messagebox, 'showerror') as error:
            licensing.start_license_monitor(window, NS())
            launch = window.callbacks.pop(0)[1]
            launch()
            collect = window.callbacks.pop(0)[1]
            collect()

        warning.assert_called_once()
        error.assert_not_called()
        self.assertFalse(window.closed)
        self.assertTrue(window._license_network_notice)
        self.assertTrue(any(delay == 45000 for delay, _ in window.callbacks))

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
            log=(Path(folder)/'GymSoft/logs/aplicacion.log').read_text(encoding='utf-8')
            self.assertIn('RuntimeError',log)
            self.assertNotIn('PRIVATE-TOKEN-AND-CUSTOMER-DATA',log)


if __name__=='__main__':unittest.main()
