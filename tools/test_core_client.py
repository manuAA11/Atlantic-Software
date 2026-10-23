from datetime import datetime, timezone, timedelta
import sys
from pathlib import Path
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock

import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'GymSoft_ZTATTUZ_3.6.1_x86'))
from common.core_client import CoreClient
from common.session_manager import MemorySessionStore


def snapshot(**changes):
    value=dict(product_variant='ztattuz',gym_id='synthetic-gym',status='ACTIVE',license_status='ACTIVE',device_status='AUTHORIZED',
        configuration={'update_channel':'beta','notifications_enabled':True},server_time=datetime.now(timezone.utc).isoformat(),
        grace_days=7,notifications=[],releases=[])
    value.update(changes)
    return value


class CoreClients(unittest.TestCase):
    def client(self, handler=None, cache=None):
        cloud=NS(gym_id='synthetic-gym',sessions=NS(state='ONLINE'),client=NS(raw=NS(supabase_url='https://syntheticprojectref0.supabase.co'),auth=Mock()))
        cloud.client.auth.get_session.return_value=NS(access_token='synthetic-access-token')
        self.store=MemorySessionStore()
        if cache:self.store.save(cache)
        http=httpx.Client(transport=httpx.MockTransport(handler or (lambda request:httpx.Response(200,json=snapshot()))))
        self.addCleanup(http.close)
        return CoreClient(cloud,'https://syntheticprojectref0.supabase.co/functions/v1/atlantic-core','3.7.0','reception',store=self.store,http=http)

    def test_offline_does_not_kill_app_or_clear_valid_license(self):
        def handler(request):raise httpx.ConnectError('offline')
        client=self.client(handler,cache=snapshot())
        self.assertIsNotNone(client.sync())
        self.assertEqual(client.state,'CORE_OFFLINE')
        client.require_operation()
        self.assertEqual(client.grace_state(),'WITHIN_GRACE')

    def test_explicit_suspension_is_distinct_from_network_outage(self):
        client=self.client(cache=snapshot(license_status='SUSPENDED'))
        with self.assertRaises(PermissionError):client.require_operation()
        client.sync();client.require_operation()
        self.assertEqual(client.state,'ONLINE')

    def test_wrong_gym_or_unapproved_remote_configuration_is_rejected(self):
        client=self.client(cache=snapshot())
        for value in (snapshot(gym_id='other-gym'),snapshot(configuration={'command':'run arbitrary script'})):
            with self.assertRaises(ValueError):client.validate(value)
        self.assertEqual(client.snapshot['gym_id'],'synthetic-gym')

    def test_only_minimal_telemetry_and_access_token_are_sent(self):
        seen=[]
        def handler(request):seen.append(request);return httpx.Response(200,json=snapshot())
        client=self.client(handler);client.sync()
        self.assertEqual(seen[0].headers['Authorization'],'Bearer synthetic-access-token')
        body=seen[0].read().decode()
        self.assertNotIn('refresh_token',body)
        self.assertNotIn('email',body)
        self.assertNotIn('fingerprint_template',body)
        self.assertEqual(len(client.device_id),64)

    def test_server_error_keeps_cached_configuration(self):
        client=self.client(lambda request:httpx.Response(500,json={'error':'synthetic'}),cache=snapshot())
        client.sync();self.assertEqual(client.snapshot['configuration']['update_channel'],'beta')
        self.assertIsNotNone(self.store.load())

    def test_grace_exceeded_is_reported_without_automatic_suspension(self):
        client=self.client(cache=snapshot(server_time=(datetime.now(timezone.utc)-timedelta(days=10)).isoformat()))
        self.assertEqual(client.grace_state(),'GRACE_EXCEEDED');client.require_operation()
