"""Realtime owns a socket and an access token; session refresh stays centralized."""
from __future__ import annotations

import asyncio
import logging
import threading
from supabase import acreate_client, AsyncClientOptions
from cloud import SUPABASE_KEY, SUPABASE_URL

logger = logging.getLogger('Atlantic.AUTH')


class RealtimeListener:
    def __init__(self, cloud, callback):
        self.cloud, self.callback = cloud, callback
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        # Auth/network work happens on the worker, not Tk's main thread.
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, name='GymSoft-Realtime', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def _run(self):
        try:
            asyncio.run(self._listen())
        except Exception:
            logger.warning('Realtime worker stopped; operational details omitted.')

    async def _listen(self):
        failures = 0
        while not self.stop_event.is_set():
            client = None
            try:
                session = await asyncio.to_thread(self.cloud.client.auth.get_session)
                if not session:
                    raise RuntimeError('Authentication required.')
                client = await acreate_client(SUPABASE_URL, SUPABASE_KEY,
                    options=AsyncClientOptions(auto_refresh_token=False, persist_session=False))
                # Never call auth.set_session: it would copy the rotating refresh token.
                token = session.access_token
                await client.realtime.set_auth(token)
                channel = client.channel(f'gym:{self.cloud.gym_id}')
                channel.on_postgres_changes('*', schema='public', table='gym_events',
                    filter=f'gym_id=eq.{self.cloud.gym_id}', callback=self.callback)
                await channel.subscribe()
                failures = 0
                while not self.stop_event.is_set():
                    await asyncio.sleep(1)
                    session = await asyncio.to_thread(self.cloud.client.auth.get_session)
                    if not session:
                        raise RuntimeError('Authentication required.')
                    if session.access_token != token:
                        token = session.access_token
                        await client.realtime.set_auth(token)
            except Exception:
                failures += 1
                logger.info('Realtime reconnect pending (%s).', min(failures, 6))
            finally:
                if client is not None:
                    # Channel failure must not prevent closing the websocket.
                    try:
                        await client.remove_all_channels()
                    except Exception:
                        pass
                    try:
                        await client.realtime.close()
                    except Exception:
                        pass
                    try:
                        await client.auth.close()
                    except Exception:
                        pass
            if not self.stop_event.is_set():
                for _ in range(min(60, 2**min(failures, 6))):
                    if self.stop_event.is_set():
                        break
                    await asyncio.sleep(1)
