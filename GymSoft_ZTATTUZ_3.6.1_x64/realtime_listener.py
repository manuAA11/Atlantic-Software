from __future__ import annotations

import asyncio
import threading
from typing import Any, Callable

from supabase import acreate_client

from cloud import (
    CloudService,
    SUPABASE_KEY,
    SUPABASE_URL,
)

class RealtimeListener:
    def __init__(
        self,
        cloud: CloudService,
        callback: Callable[[dict[str, Any]], None],
    ) -> None:
        self.cloud = cloud
        self.callback = callback
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        if self.thread and self.thread.is_alive():
            return

        session = self.cloud.client.auth.get_session()

        if not session:
            raise ValueError(
                "No existe una sesión para iniciar Realtime."
            )

        self.stop_event.clear()

        self.thread = threading.Thread(
            target=self._run,
            name="GymSoft-Realtime",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()

    def _run(self) -> None:
        try:
            asyncio.run(self._listen())
        except Exception as error:
            print("Realtime terminó:", error)





    async def _listen(self) -> None:
        while not self.stop_event.is_set():
            realtime_client = None

            try:
                session = (
                    self.cloud.client.auth.get_session()
                )

                if not session:
                    raise ValueError(
                        "La sesión de Supabase terminó."
                    )

                realtime_client = await acreate_client(
                    SUPABASE_URL,
                    SUPABASE_KEY,
                )

                await realtime_client.auth.set_session(
                    session.access_token,
                    session.refresh_token,
                )

                channel = realtime_client.channel(
                    f"gym:{self.cloud.gym_id}"
                )

                channel.on_postgres_changes(
                    "*",
                    schema="public",
                    table="gym_events",
                    filter=f"gym_id=eq.{self.cloud.gym_id}",
                    callback=self.callback,
                )

                await channel.subscribe()

                print("Realtime conectado correctamente")

                connected_seconds = 0

                while (
                    not self.stop_event.is_set()
                    and connected_seconds < 2400
                ):
                    await asyncio.sleep(1)
                    connected_seconds += 1

            except Exception as error:
                if not self.stop_event.is_set():
                    print(
                        "Realtime se reconectará:",
                        error,
                    )
                    await asyncio.sleep(3)

            finally:
                if realtime_client is not None:
                    try:
                        await (
                            realtime_client
                            .remove_all_channels()
                        )
                    except Exception:
                        pass







