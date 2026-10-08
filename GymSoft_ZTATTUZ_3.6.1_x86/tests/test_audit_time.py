import unittest
from types import SimpleNamespace
from gym_time import display_timestamp, timezone_for
class AuditTimeTests(unittest.TestCase):
    def test_gym_time_not_computer_time(self):
        self.assertEqual(display_timestamp('2026-10-04T02:28:59Z','America/Bogota'),'2026-10-03 21:28:59')
        self.assertEqual(display_timestamp('2026-10-04T02:28:59Z','Europe/Madrid'),'2026-10-04 04:28:59')
    def test_offset_converted_once(self):
        self.assertEqual(display_timestamp('2026-10-03T21:28:59-05:00','America/Bogota'),'2026-10-03 21:28:59')
        self.assertEqual(display_timestamp('2026-10-03 21:28:59','America/Bogota'),'2026-10-03 21:28:59')
    def test_daylight_saving(self):
        self.assertEqual(display_timestamp('2026-07-03T17:00:01Z','America/New_York'),'2026-07-03 13:00:01')
        self.assertEqual(display_timestamp('2026-01-03T17:00:01Z','America/New_York'),'2026-01-03 12:00:01')
    def test_resolve_gym(self):
        self.assertEqual(timezone_for(SimpleNamespace(cloud=SimpleNamespace(timezone='Europe/Madrid'))),'Europe/Madrid')
if __name__=='__main__': unittest.main()
