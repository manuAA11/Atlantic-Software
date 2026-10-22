import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace as NS
from unittest.mock import Mock

from common.session_manager import (MemorySessionStore, SessionManager, SessionOffline,
    SessionUnavailable, ManagedClient)


class Error(Exception):
    def __init__(self, code):
        self.code = code


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
