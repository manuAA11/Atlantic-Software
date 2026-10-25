"""Pinned Supabase SDK integration over an in-memory HTTP transport, no live account."""
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import sys
import tempfile
import time
import unittest

import httpx
from supabase import ClientOptions, create_client
from common.session_manager import (SessionManager, MemorySessionStore, ManagedClient,
    WindowsSessionStore, SessionOffline)


def token(exp):
    def part(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
    return part({'alg': 'HS256'})+'.'+part({'exp': exp, 'sub': '11111111-1111-4111-8111-111111111111'})+'.fake'


def payload(exp, refresh):
    return {'access_token': token(exp), 'refresh_token': refresh, 'token_type': 'bearer',
        'expires_in': 3600, 'expires_at': exp,
        'user': {'id': '11111111-1111-4111-8111-111111111111', 'aud': 'authenticated',
            'email': 'synthetic@example.invalid', 'created_at': '2026-10-22T00:00:00Z',
            'app_metadata': {}, 'user_metadata': {}}}


class SDKSessionTests(unittest.TestCase):
    def setup_clients(self):
        self.calls = []
        self.offline = False
        self.exp = int(time.time())+3600
        def handler(request):
            self.calls.append(request)
            if self.offline:
                raise httpx.ConnectError('offline', request=request)
            if request.url.path.endswith('/token'):
                body = json.loads(request.content)
                if body.get('refresh_token'):
                    self.assertEqual(body['refresh_token'], 'initial-refresh')
                    return httpx.Response(200, json=payload(self.exp+3600, 'rotated-refresh'))
                return httpx.Response(200, json=payload(self.exp, 'initial-refresh'))
            if request.url.path.endswith('/rpc/test_write'):
                self.assertEqual(request.headers['Authorization'], 'Bearer '+token(self.exp+3600))
                return httpx.Response(200, json={'ok': True})
            return httpx.Response(404, json={})
        self.transport = httpx.MockTransport(handler)
        self.store = MemorySessionStore()
        self.managers = []
        for _ in range(2):
            http = httpx.Client(transport=self.transport)
            self.addCleanup(http.close)
            raw = create_client('https://synthetic.supabase.co', 'public-test-key', options=ClientOptions(
                auto_refresh_token=False, persist_session=False, httpx_client=http))
            self.managers.append(SessionManager(raw, self.store, clock=lambda: self.exp))
        return self.managers

    def test_shared_store_rotation_and_query_headers(self):
        first, second = self.setup_clients()
        first.operation('sign_in_with_password', {'email': 'synthetic@example.invalid', 'password': 'synthetic'})
        with ThreadPoolExecutor(max_workers=2) as pool:
            sessions = list(pool.map(lambda manager: manager.ensure(), (first, second)))
        self.assertEqual([session.refresh_token for session in sessions], ['rotated-refresh']*2)
        refreshes = [r for r in self.calls if r.url.params.get('grant_type') == 'refresh_token']
        self.assertEqual(len(refreshes), 1)
        result = ManagedClient(second.client, second).rpc('test_write').execute()
        self.assertEqual(result.data, {'ok': True})
        self.assertEqual(self.store.load()['refresh_token'], 'rotated-refresh')

    def test_restore_and_network_failure_keep_recoverable_tokens(self):
        first, second = self.setup_clients()
        first.operation('sign_in_with_password', {'email': 'synthetic@example.invalid', 'password': 'synthetic'})
        self.assertIsNotNone(second.restore())
        self.offline = True
        with self.assertRaises(SessionOffline):
            second.ensure(force=True)
        self.assertEqual(second.session.refresh_token, 'initial-refresh')
        self.assertEqual(self.store.load()['refresh_token'], 'initial-refresh')

    def test_peer_rotation_updates_already_created_edge_client(self):
        first, second = self.setup_clients()
        first.operation('sign_in_with_password', {'email': 'synthetic@example.invalid', 'password': 'synthetic'})
        second.restore()
        previous = second.client.functions
        self.assertEqual(previous.headers['Authorization'], 'Bearer '+token(self.exp))
        first.ensure(force=True)
        received = []
        def handler(request):
            received.append(request)
            self.assertTrue(request.url.path.endswith('/functions/v1/session_probe'))
            self.assertEqual(request.headers['Authorization'], 'Bearer '+token(self.exp+3600))
            return httpx.Response(200, json={'ok': True})
        self.transport.handler = handler
        ManagedClient(second.client, second).functions.invoke('session_probe', invoke_options={'body': {}})
        self.assertEqual(len(received), 1)
        self.assertEqual(second.auth._headers['Authorization'], 'Bearer '+token(self.exp+3600))

    def test_peer_logout_removes_cached_authenticated_headers(self):
        first, second = self.setup_clients()
        first.operation('sign_in_with_password', {'email': 'synthetic@example.invalid', 'password': 'synthetic'})
        second.restore()
        previous = second.client.functions
        self.store.clear()
        self.assertIsNone(second.ensure())
        self.assertEqual(second.state, 'SIGNED_OUT')
        self.assertIsNot(second.client.functions, previous)
        self.assertEqual(second.client.functions.headers['Authorization'], 'Bearer public-test-key')
        self.assertEqual(second.auth._headers['Authorization'], 'Bearer public-test-key')

    def test_valid_restored_session_reuses_token_without_rotation(self):
        first, second = self.setup_clients()
        first.operation('sign_in_with_password', {'email': 'synthetic@example.invalid', 'password': 'synthetic'})
        second.clock = lambda: self.exp-1000
        expected = second.restore().access_token
        self.assertEqual(second.ensure().access_token, expected)
        self.assertEqual(second.state, 'ONLINE')
        self.assertFalse(any(r.url.params.get('grant_type') == 'refresh_token' for r in self.calls))

    def test_peer_rotation_replaces_cached_storage_client(self):
        first, second = self.setup_clients()
        first.operation('sign_in_with_password', {'email': 'synthetic@example.invalid', 'password': 'synthetic'})
        second.restore()
        previous = second.client.storage
        first.ensure(force=True)
        second.ensure()
        received = []
        def handler(request):
            received.append(request)
            self.assertIn('/storage/v1/object/list/', request.url.path)
            self.assertEqual(request.headers['Authorization'], 'Bearer '+token(self.exp+3600))
            return httpx.Response(200, json=[])
        self.transport.handler = handler
        self.assertEqual(second.client.storage.from_('synthetic').list(), [])
        self.assertEqual(len(received), 1)
        self.assertIsNot(second.client.storage, previous)

    def test_actual_postgrest_future_rejection_waits_with_same_auth_header(self):
        first, _ = self.setup_clients()
        first.operation('sign_in_with_password', {'email': 'synthetic@example.invalid', 'password': 'synthetic'})
        first.clock = lambda: self.exp-1000
        waits, calls = [], []
        first.wait = waits.append
        def handler(request):
            calls.append(request)
            self.assertTrue(request.url.path.endswith('/rpc/test_write'))
            self.assertEqual(request.headers['Authorization'], 'Bearer '+token(self.exp))
            if len(calls) <= 2:
                return httpx.Response(401, json={'code': 'PGRST303', 'message': 'JWT issued at future',
                    'details': None, 'hint': None})
            return httpx.Response(200, json={'ok': True})
        self.transport.handler = handler
        self.assertEqual(ManagedClient(first.client, first).rpc('test_write').execute().data, {'ok': True})
        self.assertEqual(waits, [1., 2.])
        self.assertEqual(len(calls), 3)
        self.assertEqual(self.store.load()['refresh_token'], 'initial-refresh')

    @unittest.skipUnless(sys.platform == 'win32', 'Windows DPAPI round-trip runs in Windows CI x86/x64')
    def test_dpapi_encrypted_at_rest_and_namespace_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            store = WindowsSessionStore('synthetic-provider|reception', directory=folder)
            value = {'refresh_token': 'synthetic-secret-for-qa'}
            with store.transaction():
                store.save(value)
                self.assertNotIn(b'synthetic-secret-for-qa', store.path.read_bytes())
                self.assertEqual(store.load(), value)
            other = WindowsSessionStore('synthetic-provider|admin', directory=folder)
            self.assertIsNone(other.load())
            store.clear()
            self.assertIsNone(store.load())
