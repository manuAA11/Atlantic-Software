"""Short cache using server time and monotonic elapsed time, independent of the PC clock."""
from datetime import date, timedelta
from threading import Lock
from time import monotonic
from zoneinfo import ZoneInfo
from gym_time import parse_instant


class ServerDate:
    def __init__(self, timezone='America/Bogota'):
        self.timezone = ZoneInfo(timezone)
        self.lock = Lock()
        self.value = None
        self.until = 0.0
        self.revision = 0

    def invalidate(self):
        self.revision += 1
        self.value = None

    def get(self, fetch):
        with self.lock:
            now = monotonic()
            if self.value is not None and now < self.until:
                return self.value
            revision = self.revision
            result = fetch()
            lifetime = 60
            if isinstance(result, dict):
                self.timezone = ZoneInfo(result['timezone'])
                instant = parse_instant(result['now']).astimezone(self.timezone)
                value = date.fromisoformat(result['today'])
                if instant.date() != value:
                    raise ValueError('El reloj del servidor no corresponde al día del gimnasio.')
                midnight = (instant + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                lifetime = min(lifetime, max(0, midnight.timestamp() - instant.timestamp()))
            else:
                # Legacy date-only RPC support for existing isolated test clients.
                value = date.fromisoformat(str(result))
            if self.revision == revision:
                self.value = value
                self.until = now + lifetime
            return value
