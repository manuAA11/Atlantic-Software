import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from common.session_manager import (MemorySessionStore, SessionManager, SessionOffline,
    SessionUnavailable, SessionClockError, ManagedClient)


class Error(Exception):
    def __init__(self, code, message=''):
        self.code = code
        self.message = message
        super().__init__(message)


def session(token='old', expires=100):
    value = Mock(access_token=token, refresh_token=token+'-refresh', expires_at=expires)
    value.model_dump.return_value = {'token': token}
    return value


class Sessions(unittest.TestCase):
    def manager(self):
        self.store = MemorySessionStore()
        self.client = Mock()
        self.client.supabase_key = "synthetic-public-key"
        self.client.options.headers = {}
        self.now = 1000.
        self.manager = SessionManager(self.client, self.store, clock=lambda: self.now, monotonic=lambda: self.now)
        self.manager._load = lambda: self.manager.session
        self.manager.session = session()
        self.client.auth.refresh_session.return_value = NS(session=session('new', 3000))
        return self.manager

    def test_parallel_expiry_refreshes_once(self):
        manager = self.manager()
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda _: manager.ensure(), range(30)))
        self.assertEqual(self.client.auth.refresh_session.call_count, 1)
        self.assertTrue(all(value.access_token == 'new' for value in results))

    def test_network_preserves_identity_and_backs_off(self):
        manager = self.manager()
        original = manager.session
        self.client.auth.refresh_session.side_effect = ConnectionError('network')
        for _ in range(3):
            with self.assertRaises(SessionOffline):
                manager.ensure()
        self.assertIs(manager.session, original)
        self.assertEqual(manager.state, 'OFFLINE')
        self.assertEqual(self.client.auth.refresh_session.call_count, 1)
        self.now += 65
        self.client.auth.refresh_session.side_effect = None
        self.assertEqual(manager.ensure().access_token, 'new')

    def test_revoked_requires_login(self):
        manager = self.manager()
        self.client.auth.refresh_session.side_effect = Error('refresh_token_already_used')
        with self.assertRaises(SessionUnavailable):
            manager.ensure()
        self.assertIsNone(manager.session)
        self.assertEqual(manager.state, 'AUTH_REQUIRED')

    def test_requests_after_session_loss_never_fall_back_to_anonymous(self):
        manager = self.manager()
        manager.session = None
        manager.state = 'AUTH_REQUIRED'
        client = ManagedClient(self.client, manager)
        for operation in (lambda: client.rpc('register_checkin', {}).execute(),
                          lambda: client.functions.invoke('write', invoke_options={'body': {}})):
            with self.assertRaises(SessionUnavailable):
                operation()
        self.client.rpc.assert_not_called()
        self.client.functions.invoke.assert_not_called()

    def test_relogin_restarts_worker_while_previous_worker_is_exiting(self):
        manager = self.manager()
        manager.worker = Mock()
        manager.worker.is_alive.return_value = True
        previous_stop = manager.stop_event
        manager.close()
        with patch('common.session_manager.threading.Thread') as thread:
            manager.start()
        thread.return_value.start.assert_called_once()
        self.assertTrue(previous_stop.is_set())
        self.assertIsNot(manager.stop_event, previous_stop)
        self.assertFalse(manager.stop_event.is_set())

    def test_resume_resets_backoff(self):
        manager = self.manager()
        manager.retry_at = 99999
        self.now += 200
        self.assertEqual(manager.tick().access_token, 'new')

    def test_rejected_stale_token_does_not_rotate_new_session(self):
        manager = self.manager()
        manager.session = session('latest', 3000)
        self.assertEqual(manager.ensure(force=True, rejected_token='stale').access_token, 'latest')
        self.client.auth.refresh_session.assert_not_called()

    def test_logout_clears_local_even_if_offline(self):
        manager = self.manager()
        self.store.save({'secret': 'fake'})
        self.client.auth.sign_out.side_effect = ConnectionError()
        with self.assertRaises(ConnectionError):
            manager.logout()
        self.assertIsNone(manager.session)
        self.assertIsNone(self.store.load())

    def test_transport_error_never_replays_write(self):
        manager = self.manager()
        manager.session = session('valid', 3000)
        self.client.rpc.return_value.execute.side_effect = TimeoutError('uncertain write')
        client = ManagedClient(self.client, manager)
        with self.assertRaises(TimeoutError):
            client.rpc('register_checkin', {}).execute()
        self.client.rpc.return_value.execute.assert_called_once()
        self.client.auth.refresh_session.assert_not_called()

    def test_jwt_rejection_rebuilds_query_after_refresh(self):
        manager = self.manager()
        manager.session = session('valid', 3000)
        first, second = Mock(), Mock()
        first.execute.side_effect = Error('PGRST303')
        second.execute.return_value = NS(data=['result'])
        self.client.rpc.side_effect = [first, second]
        client = ManagedClient(self.client, manager)
        self.assertEqual(client.rpc('register_checkin', {}).execute().data, ['result'])
        self.assertEqual(self.client.rpc.call_count, 2)
        self.client.auth.refresh_session.assert_called_once_with('valid-refresh')

    def test_future_jwt_waits_without_rotating_or_logging_out(self):
        manager = self.manager()
        manager.session = session('valid', 3000)
        manager.wait = Mock()
        query = self.client.rpc.return_value
        query.execute.side_effect = [Error('PGRST303', 'JWT issued at future'),
            Error('PGRST303', 'JWT issued at future'), NS(data='saved')]
        self.assertEqual(ManagedClient(self.client, manager).rpc('write').execute().data, 'saved')
        self.assertEqual([c.args[0] for c in manager.wait.call_args_list], [1., 2.])
        self.client.auth.refresh_session.assert_not_called()
        self.client.auth.sign_out.assert_not_called()
        self.assertEqual(query.execute.call_count, 3)

    def test_future_jwt_exhaustion_is_bounded_and_preserves_session(self):
        manager = self.manager()
        original = manager.session = session('valid', 3000)
        manager.wait = Mock()
        query = self.client.rpc.return_value
        query.execute.side_effect = Error('PGRST303', 'JWT issued at future')
        with self.assertRaisesRegex(SessionClockError, 'servidor'):
            ManagedClient(self.client, manager).rpc('write').execute()
        self.assertEqual(query.execute.call_count, 4)
        self.assertEqual(sum(c.args[0] for c in manager.wait.call_args_list), 6.)
        self.assertIs(manager.session, original)
        self.client.auth.refresh_session.assert_not_called()
        self.client.auth.sign_out.assert_not_called()

    def test_expired_then_future_jwt_refreshes_once_then_waits(self):
        manager = self.manager()
        manager.session = session('valid', 3000)
        manager.wait = Mock()
        self.client.rpc.return_value.execute.side_effect = [Error('PGRST303', 'JWT expired'),
            Error('PGRST303', 'JWT issued at future'), NS(data='saved')]
        self.assertEqual(ManagedClient(self.client, manager).rpc('write').execute().data, 'saved')
        self.client.auth.refresh_session.assert_called_once()
        manager.wait.assert_called_once_with(1.)

    def test_generic_401_or_future_message_without_jwt_code_never_replays(self):
        for error in (Error('401', 'JWT issued at future'), Error('42501', 'JWT issued at future')):
            manager = Sessions.manager(self)
            manager.session = session('valid', 3000)
            manager.wait = Mock()
            self.client.rpc.return_value.execute.side_effect = error
            with self.assertRaises(Error):
                ManagedClient(self.client, manager).rpc('write').execute()
            self.client.rpc.return_value.execute.assert_called_once()
            manager.wait.assert_not_called()
            self.client.auth.refresh_session.assert_not_called()

    def test_transport_failure_after_future_rejection_never_replays(self):
        manager = self.manager()
        manager.session = session('valid', 3000)
        manager.wait = Mock()
        self.client.rpc.return_value.execute.side_effect = [Error('PGRST303', 'JWT issued at future'),
            TimeoutError('uncertain write')]
        with self.assertRaises(TimeoutError):
            ManagedClient(self.client, manager).rpc('write').execute()
        self.assertEqual(self.client.rpc.return_value.execute.call_count, 2)
        manager.wait.assert_called_once_with(1.)

    def test_edge_calls_refresh_before_invocation_and_never_replay(self):
        manager = self.manager()
        client = ManagedClient(self.client, manager)
        self.client.functions.invoke.side_effect = TimeoutError('uncertain Edge write')
        with self.assertRaises(TimeoutError):
            client.functions.invoke('marketing/admin', invoke_options={'body': {'action': 'synthetic'}})
        self.client.auth.refresh_session.assert_called_once()
        self.client.functions.invoke.assert_called_once()
        self.assertEqual(manager.active_requests, 0)

    def test_query_constructed_before_expiry_uses_latest_headers(self):
        manager = self.manager()
        client = ManagedClient(self.client, manager)
        query = client.table('clients').select('*').limit(1)
        self.client.table.assert_not_called()
        query.execute()
        self.client.auth.refresh_session.assert_called_once()
        self.client.table.assert_called_once_with('clients')


if __name__ == '__main__':
    unittest.main()
