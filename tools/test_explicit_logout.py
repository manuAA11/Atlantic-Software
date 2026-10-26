"""Explicit logout clears only this role, even offline, and opens a fresh login."""
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'GymSoft_Comercial_3.6.0'))
from common.session_manager import MemorySessionStore, SessionManager
from common.session_ui import SessionStatus, logout_busy, run_application, sign_out_session


def manager():
    client = Mock(supabase_key='synthetic-public-key')
    client.options.headers = {}
    store = MemorySessionStore()
    value = SessionManager(client, store)
    # Keep this test independent of session expiry; production uses ensure().
    client.auth.get_session = lambda: value.session
    value.session = NS(access_token='synthetic', refresh_token='synthetic-refresh')
    store.save({'synthetic': True})
    return value, client, store


class ExplicitLogout(unittest.TestCase):
    def test_local_scope_clears_credentials_and_stops_refresh(self):
        sessions, client, store = manager()
        other_role = MemorySessionStore()
        other_role.save({'reception': 'synthetic'})
        sign_out_session(sessions)
        client.auth.sign_out.assert_called_once_with({'scope': 'local'})
        self.assertIsNone(sessions.session)
        self.assertIsNone(store.load())
        self.assertEqual(sessions.state, 'SIGNED_OUT')
        self.assertTrue(sessions.stop_event.is_set())
        self.assertEqual(client.options.headers['Authorization'], 'Bearer synthetic-public-key')
        self.assertEqual(other_role.load(), {'reception': 'synthetic'})

    def test_offline_logout_still_clears_local_credentials(self):
        sessions, client, store = manager()
        client.auth.sign_out.side_effect = ConnectionError('synthetic network outage')
        sign_out_session(sessions)
        self.assertEqual(sessions.state, 'SIGNED_OUT')
        self.assertIsNone(store.load())
        self.assertIsNone(sessions.session)
        self.assertFalse(sessions.maintenance)

    def test_disk_failure_stops_refresh_and_unbinds_tokens_but_does_not_claim_success(self):
        sessions, client, store = manager()
        with patch.object(store, 'clear', side_effect=PermissionError('synthetic disk error')):
            with self.assertRaises(PermissionError):
                sign_out_session(sessions)
        self.assertEqual(sessions.state, 'SIGNED_OUT')
        self.assertIsNone(sessions.session)
        self.assertTrue(sessions.stop_event.is_set())
        self.assertEqual(client.options.headers['Authorization'], 'Bearer synthetic-public-key')
        self.assertIsNotNone(store.load())
        self.assertIsNone(sessions.ensure())
        self.assertEqual(sessions.state, 'SIGNED_OUT')

    def test_quiesce_rejects_new_requests_until_logout_has_finished(self):
        sessions, client, store = manager()
        def server_signout(options):
            with self.assertRaises(RuntimeError):
                with sessions.request():
                    self.fail('New requests may not enter during logout')
        client.auth.sign_out.side_effect = server_signout
        sign_out_session(sessions)

    def test_access_is_stopped_after_pending_requests_and_before_token_removal(self):
        sessions, client, store = manager()
        order = []
        def stop_access():
            self.assertTrue(sessions.maintenance)
            self.assertEqual(sessions.active_requests, 0)
            order.append('access stopped')
        client.auth.sign_out.side_effect = lambda options: order.append('signout')
        sign_out_session(sessions, stop_access)
        self.assertEqual(order, ['access stopped', 'signout'])

    def test_open_workspace_is_destroyed_before_a_new_login_is_built(self):
        events = []
        class App:
            ready = True
            def __init__(self, returning):
                self._return_to_login = returning
            def mainloop(self):
                events.append('old closed' if self._return_to_login else 'new login')
        first, second = App(True), App(False)
        factory = Mock(side_effect=[first, second])
        run_application(factory)
        self.assertEqual(events, ['old closed', 'new login'])
        self.assertEqual(factory.call_count, 2)

    def test_canceling_new_login_ends_without_restoring_old_workspace(self):
        run_application(Mock(return_value=NS(ready=False)))


class LogoutUIFlow(unittest.TestCase):
    def root(self):
        return NS(ready=True, _foreground_io=False, pages={}, door=NS(is_busy=False),
                  winfo_children=lambda: [], close_app=Mock(), withdraw=Mock())

    def test_busy_operation_or_cart_keeps_current_session(self):
        root = self.root()
        for field, value in (('_foreground_io', True), ('door', NS(is_busy=True)),
                             ('pages', {'shop': NS(pos=NS(cart=NS(rows={1: 'synthetic'})))})):
            candidate = self.root()
            setattr(candidate, field, value)
            self.assertTrue(logout_busy(candidate))
        self.assertFalse(logout_busy(root))

    def test_logout_closes_old_workspace_after_clearing_tokens(self):
        root = self.root()
        sessions, _, _ = manager()
        status = NS(root=root, cloud=NS(sessions=sessions))
        with patch('common.session_ui.run_io', side_effect=lambda root, fn, **kw: fn()):
            SessionStatus.sign_out(status)
        self.assertFalse(root.ready)
        self.assertTrue(root._return_to_login)
        root.withdraw.assert_called_once()
        root.close_app.assert_called_once()
        self.assertIsNone(sessions.store.load())

    def test_disk_error_keeps_authentication_blocked_and_does_not_reopen_cached_session(self):
        root = self.root()
        sessions, _, store = manager()
        status = NS(root=root, cloud=NS(sessions=sessions))
        with patch.object(store, 'clear', side_effect=PermissionError()), \
             patch('common.session_ui.run_io', side_effect=lambda root, fn, **kw: fn()), \
             patch('common.session_ui.messagebox') as messages:
            SessionStatus.sign_out(status)
        root.close_app.assert_not_called()
        self.assertFalse(root.ready)
        self.assertFalse(getattr(root, '_return_to_login', False))
        messages.showerror.assert_called_once()


if __name__ == '__main__':
    unittest.main()
