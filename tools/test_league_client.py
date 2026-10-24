"""Transport identity, redirects, oversized responses and error privacy."""
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from common.league_client import LeagueClient

class Reply:
    status_code = 200
    data = b'{"data":[{"name":"Sentadilla"}]}'
    def __enter__(self): return self
    def __exit__(self, *_): pass
    def iter_bytes(self, size): yield self.data

class Transport:
    def __init__(self): self.calls = []
    def stream(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return Reply()

class LeagueTransportTests(unittest.TestCase):
    def setUp(self):
        self.transport = Transport()
        self.cloud = SimpleNamespace(gym_id='own-gym', sessions=SimpleNamespace(ensure=lambda: SimpleNamespace(access_token='private-token')))
        self.endpoint = 'https://'+'a'*20+'.supabase.co/functions/v1/atlantic-league'
        self.source = 'https://'+'b'*20+'.supabase.co'
    def client(self, **kwargs):
        return LeagueClient(self.cloud, self.endpoint, self.source, self.transport, **kwargs)
    def test_uses_current_gym_session_only_and_never_follows_redirects(self):
        self.assertEqual(self.client().call('catalog'), [{'name':'Sentadilla'}])
        args = self.transport.calls[0][1]
        self.assertEqual(args['json']['project_ref'], 'b'*20)
        self.assertEqual(args['json']['gym_id'], 'own-gym')
        self.assertEqual(args['headers']['Authorization'], 'Bearer private-token')
        self.assertNotIn('private-token', str(args['json']))
        self.assertFalse(args['follow_redirects'])
    def test_no_session_or_untrusted_endpoint_sends_nothing(self):
        for endpoint in [self.endpoint+'?secret=1',self.endpoint.replace('https:', 'http:'),self.endpoint.replace('.co/', '.co.evil/')]:
            with self.assertRaises(ValueError): LeagueClient(self.cloud, endpoint, self.source, self.transport)
        self.cloud.sessions.ensure = lambda: None
        with self.assertRaises(ValueError): self.client().call('catalog')
        self.assertEqual(self.transport.calls, [])
    def test_response_bounded_and_server_error_does_not_leak_secrets(self):
        with patch.object(Reply, 'status_code', 403), patch.object(Reply, 'data', b'{"message":"private-token secret server path"}'):
            with self.assertRaises(ValueError) as caught: self.client().call('catalog')
            self.assertNotIn('private-token', str(caught.exception))
        with patch.object(Reply, 'data', b' '*(2*1024*1024+1)):
            with self.assertRaisesRegex(ValueError, 'demasiado grande'): self.client().call('catalog')

if __name__ == '__main__': unittest.main()
