"""Realtime socket recovery must never copy a rotating refresh credential."""
import asyncio
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'GymSoft_ZTATTUZ_3.6.1_x86'))
from common.realtime_listener import RealtimeListener


class RealtimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_access_token_changes_propagate_and_all_resources_close(self):
        cloud = NS(client=NS(auth=Mock()), gym_id='synthetic-gym')
        cloud.client.auth.get_session.side_effect = [NS(access_token='initial'), NS(access_token='new')]
        listener = RealtimeListener(cloud, Mock())
        channel = Mock()
        channel.subscribe = AsyncMock()
        client = NS(channel=Mock(return_value=channel), realtime=NS(set_auth=AsyncMock(), close=AsyncMock()),
            auth=NS(set_session=AsyncMock(), close=AsyncMock()), remove_all_channels=AsyncMock())
        async def wait(_):
            listener.stop()
        with patch('common.realtime_listener.acreate_client', AsyncMock(return_value=client)) as create, \
             patch('common.realtime_listener.asyncio.sleep', wait):
            await listener._listen()
        self.assertEqual([call.args[0] for call in client.realtime.set_auth.call_args_list], ['initial', 'new'])
        client.auth.set_session.assert_not_called()
        options = create.call_args.kwargs['options']
        self.assertFalse(options.auto_refresh_token)
        self.assertFalse(options.persist_session)
        client.remove_all_channels.assert_awaited_once()
        client.realtime.close.assert_awaited_once()
        client.auth.close.assert_awaited_once()

    async def test_channel_cleanup_failure_still_closes_socket(self):
        cloud = NS(client=NS(auth=Mock()), gym_id='synthetic-gym')
        cloud.client.auth.get_session.return_value = NS(access_token='initial')
        listener = RealtimeListener(cloud, Mock())
        channel = Mock()
        async def subscribe():
            listener.stop()
            raise ConnectionError('transport')
        channel.subscribe = subscribe
        client = NS(channel=Mock(return_value=channel), realtime=NS(set_auth=AsyncMock(), close=AsyncMock()),
            auth=NS(set_session=AsyncMock(), close=AsyncMock()), remove_all_channels=AsyncMock(side_effect=RuntimeError()))
        with patch('common.realtime_listener.acreate_client', AsyncMock(return_value=client)):
            await listener._listen()
        client.realtime.close.assert_awaited_once()
        client.auth.close.assert_awaited_once()
