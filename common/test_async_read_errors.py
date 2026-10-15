"""Read failures expose actionable guidance without credentials or record text."""
from pathlib import Path
import os
import queue
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui_performance import (AsyncPageMixin, BackgroundReads, classify_read_failure,
                            record_read_failure, read_error_status)


class APIError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message


class Value:
    def __init__(self):
        self.value = ''
    def set(self, value):
        self.value = value
    def get(self):
        return self.value


class Page:
    def __init__(self):
        self._view_pending = set()
        self._view_errors = set()
        self._view_error_details = {}
        self._view_loaded = False
        self._view_dirty = True
        self._view_updated_at = 0
        self._view_callbacks = []
        self._view_status = Value()
        self.refresh = Mock()
    def winfo_exists(self):
        return True
    def winfo_viewable(self):
        return True


class AsyncReadErrors(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {'LOCALAPPDATA': self.folder.name})
        self.environment.start()
    def tearDown(self):
        self.environment.stop()
        self.folder.cleanup()

    def test_missing_population_names_only_incremental_update_order(self):
        failure = classify_read_failure(APIError('PGRST202',
            'Could not find the function public.membership_population(p_gym_id) in the schema cache'))
        self.assertEqual(failure.category, 'membership_update')
        self.assertEqual(failure.code, 'PGRST202')
        self.assertLess(failure.message.index('ACTUALIZAR_PLANES_INTERNOS.sql'),
                        failure.message.index('ACTUALIZAR_REANUDACION_MEMBRESIAS.sql'))
        self.assertIn('proyecto existente', failure.message)
        self.assertIn('verificar las actualizaciones previas', failure.message)
        self.assertIn('caché de funciones', failure.message)
        self.assertNotIn('schema.sql', failure.message)
        self.assertRegex(failure.reference, r'^GS-LECTURA-[A-F0-9]{12}$')

    def test_missing_other_function_and_missing_column_are_distinct(self):
        function = classify_read_failure(APIError('42883', 'function public.other_function does not exist'))
        column = classify_read_failure(APIError('PGRST204',
            "Could not find the 'membership_population' column of 'plans' in the schema cache"))
        self.assertEqual(function.category, 'server_function')
        self.assertEqual(column.category, 'server_structure')
        self.assertNotIn('ACTUALIZAR_PLANES_INTERNOS.sql', column.message)
        self.assertEqual(classify_read_failure(APIError('42P01', 'relation missing')).category,
                         'server_structure')

    def test_connection_permissions_and_session_have_fixed_guidance(self):
        examples = [(TimeoutError('sensitive record'), 'connection'),
                    (ConnectionError('sensitive URL'), 'connection'),
                    (APIError('42501', 'permission denied'), 'permission'),
                    (APIError('PGRST301', 'JWT expired'), 'session')]
        for error, expected in examples:
            with self.subTest(category=expected):
                self.assertEqual(classify_read_failure(error).category, expected)
        # Auth errors must not be misreported as a missing upgrade merely
        # because the failed request happened to name the population RPC.
        self.assertEqual(classify_read_failure(APIError('42501',
            'permission denied for membership_population')).category, 'permission')

    def test_server_timeout_and_overload_do_not_suggest_missing_migrations(self):
        for code, category in (('57014', 'server_timeout'), ('53300', 'server_busy')):
            with self.subTest(code=code):
                private = 'private_QUERY_client_123_membership_population'
                failure = classify_read_failure(APIError(code, private))
                self.assertEqual(failure.category, category)
                self.assertEqual(failure.code, code)
                self.assertNotIn('ACTUALIZAR', failure.message)
                self.assertNotIn(private, repr(failure))

    def test_unknown_messages_and_codes_never_leave_classifier_or_log(self):
        secret = 'Bearer eyJ_secret_TOKEN https://example.test?api_key=private Client: Ana-123'
        page = Page()
        try:
            raise APIError(secret, secret)
        except APIError as error:
            failure = record_read_failure(page, 'dashboard', error)
        self.assertEqual(failure.category, 'unknown')
        self.assertEqual(failure.code, '')
        self.assertNotIn(secret, repr(failure))
        log = (Path(self.folder.name) / 'GymControl/logs/lecturas.log').read_text(encoding='utf-8')
        self.assertIn(failure.reference, log)
        self.assertIn('category=unknown code=NONE', log)
        self.assertIn('test_async_read_errors.py:', log)
        for private in ('eyJ_secret_TOKEN', 'api_key', 'Ana-123', 'raise APIError'):
            self.assertNotIn(private, log)

    def coordinator(self, page, key='dashboard'):
        reads = object.__new__(BackgroundReads)
        reads.root = SimpleNamespace(report_callback_exception=Mock())
        reads.epoch = 0
        reads.slots = {}
        reads.results = queue.Queue()
        reads.work = queue.Queue()
        request = ((0, ()), lambda: None, Mock())
        reads.slots[(page, key)] = {'running': True, 'request': request, 'last': None}
        page._view_pending.add(key)
        return reads, request

    def test_worker_failure_is_available_without_stdout_and_preserves_loaded_values(self):
        page = Page()
        page._view_loaded = True
        reads, request = self.coordinator(page)
        reads.results.put(((page, 'dashboard'), request, None,
                           APIError('PGRST202', 'membership_population function missing')))
        with patch('builtins.print') as output:
            reads._drain()
        output.assert_not_called()
        self.assertFalse(page._view_pending)
        self.assertEqual(page._view_errors, {'dashboard'})
        self.assertTrue(page._view_loaded)
        self.assertIn('toda la información', page._view_status.get())
        self.assertIn('reintentar', page._view_status.get())
        request[2].assert_not_called()
        self.assertEqual(page._view_error_details['dashboard'].category, 'membership_update')

    def test_invalidated_and_replaced_errors_do_not_contaminate_new_request(self):
        for replaced in (False, True):
            with self.subTest(replaced=replaced):
                page = Page()
                reads, request = self.coordinator(page)
                reads.results.put(((page, 'dashboard'), request, None, TimeoutError('old')))
                if replaced:
                    reads.slots[(page, 'dashboard')]['request'] = ((0, ('new',)), lambda: None, Mock())
                else:
                    reads.epoch = 1
                with patch('ui_performance.record_read_failure') as record:
                    reads._drain()
                record.assert_not_called()
                self.assertFalse(page._view_errors)
                self.assertFalse(page._view_error_details)

    def test_retry_clears_only_that_section_and_new_success_recovers(self):
        page = Page()
        reads, old_request = self.coordinator(page)
        page._view_error_details = {'dashboard': classify_read_failure(TimeoutError()),
                                    'tickets': classify_read_failure(TimeoutError())}
        page._view_errors = {'dashboard', 'tickets'}
        reads.owners = set()
        reads.closed = False
        reads._schedule = Mock()
        reads.submit(page, 'dashboard', (), lambda: {}, Mock())
        self.assertNotIn('dashboard', page._view_error_details)
        self.assertNotIn('dashboard', page._view_errors)
        self.assertIn('tickets', page._view_error_details)
        request = reads.slots[(page, 'dashboard')]['request']
        reads.results.put(((page, 'dashboard'), request, {}, None))
        with patch('ui_performance.grab_path', return_value=''):
            reads._drain()
        request[2].assert_called_once_with({})
        self.assertTrue(page._view_loaded)
        self.assertEqual(page._view_errors, {'tickets'})
        self.assertIn('reintentar', page._view_status.get())

    def test_obsolete_response_does_not_hide_another_sections_failure(self):
        page = Page()
        reads, request = self.coordinator(page)
        failure = record_read_failure(page, 'tickets', TimeoutError('private host'))
        page._view_errors.add('tickets')
        reads.epoch = 1
        reads.results.put(((page, 'dashboard'), request, None, TimeoutError('obsolete')))
        reads._drain()
        self.assertEqual(page._view_error_details, {'tickets': failure})
        self.assertIn('reintentar', page._view_status.get())

    def test_dialog_retries_only_after_explicit_choice(self):
        page = Page()
        failure = record_read_failure(page, 'dashboard', TimeoutError('private host'))
        with patch('desktop_ui.messagebox.askretrycancel', return_value=False) as dialog:
            AsyncPageMixin.show_read_error(page)
        page.refresh.assert_not_called()
        self.assertIn(failure.reference, dialog.call_args.args[1])
        self.assertNotIn('private host', dialog.call_args.args[1])
        with patch('desktop_ui.messagebox.askretrycancel', return_value=True):
            AsyncPageMixin.show_read_error(page)
        page.refresh.assert_called_once()

    def test_callback_missing_plan_function_shows_incremental_upgrade_without_retry(self):
        import desktop_ui
        for code, function in (('PGRST202', 'save_membership_plan'),
                               ('42883', 'membership_population'),
                               ('', 'save_membership_plan')):
            with self.subTest(code=code, function=function):
                root = SimpleNamespace(winfo_exists=lambda: True, refresh=Mock())
                desktop_ui.install_error_handler(root)
                private = 'Bearer private_TOKEN client_name=Secret'
                error = APIError(code, f'Could not find the function public.{function} {private}')
                with patch('desktop_ui.messagebox.showerror') as dialog:
                    root.report_callback_exception(APIError, error, None)
                shown = dialog.call_args.args[1]
                self.assertIn('verificar las actualizaciones previas', shown)
                self.assertIn('caché de funciones', shown)
                self.assertLess(shown.index('ACTUALIZAR_PLANES_INTERNOS.sql'),
                                shown.index('ACTUALIZAR_REANUDACION_MEMBRESIAS.sql'))
                self.assertIn('Referencia: GS-', shown)
                self.assertNotIn(private, shown)
                root.refresh.assert_not_called()
        # Editions retain their historical GymSoft/GymControl data directories.
        logs = list(Path(self.folder.name).glob('*/logs/aplicacion.log'))
        self.assertEqual(len(logs), 1)
        log = logs[0].read_text(encoding='utf-8')
        self.assertNotIn('private_TOKEN', log)
        self.assertNotIn('client_name', log)

    def test_callback_unknown_or_unrelated_failure_retains_generic_reference(self):
        import desktop_ui
        for error in (ValueError('Bearer private_TOKEN client_name=Secret'),
                      APIError('42501', 'permission denied for save_membership_plan private_TOKEN'),
                      APIError('PGRST202', 'Could not find the function unrelated_function private_TOKEN')):
            with self.subTest(error_type=type(error).__name__):
                root = SimpleNamespace(winfo_exists=lambda: True, refresh=Mock())
                desktop_ui.install_error_handler(root)
                with patch('desktop_ui.messagebox.showerror') as dialog:
                    root.report_callback_exception(type(error), error, None)
                shown = dialog.call_args.args[1]
                self.assertIn('revisa el resultado antes de repetir la operación', shown)
                self.assertIn('Referencia: GS-', shown)
                self.assertNotIn('ACTUALIZAR', shown)
                self.assertNotIn('private_TOKEN', shown)
                root.refresh.assert_not_called()


if __name__ == '__main__':
    unittest.main()
