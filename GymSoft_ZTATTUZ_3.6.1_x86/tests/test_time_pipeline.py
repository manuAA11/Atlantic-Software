import os
from pathlib import Path
import sys
import time
import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gym_time import display_timestamp, local_datetime, local_wall_instant, parse_instant
from server_date import ServerDate
from payment_revision import _when
from cloud_database import CloudDatabase
from reception_expense_revision import open_reception_expense_manager
from ui_text import service_status


class TimePipelineTests(unittest.TestCase):
    def test_every_event_kind_uses_its_absolute_instant(self):
        for kind in ('login', 'logout', 'checkin', 'payment', 'sale', 'expense',
                     'audit', 'client', 'membership', 'fingerprint', 'relay',
                     'configuration', 'WhatsApp', 'Wompi', 'chatbot'):
            with self.subTest(event=kind):
                self.assertEqual(display_timestamp('2026-10-08T02:30:00Z', 'America/Bogota'),
                                 '2026-10-07 21:30:00')
    def test_utc_midnight_and_gym_midnight_are_different(self):
        for utc, local in [('2026-10-07T23:59:59Z', '2026-10-07 18:59:59'),
                           ('2026-10-08T00:00:00Z', '2026-10-07 19:00:00'),
                           ('2026-10-08T04:59:59Z', '2026-10-07 23:59:59'),
                           ('2026-10-08T05:00:00Z', '2026-10-08 00:00:00')]:
            self.assertEqual(display_timestamp(utc), local)
    def test_pc_timezone_and_wall_clock_are_irrelevant(self):
        original_tz = os.environ.get('TZ')
        with patch.dict(os.environ, {'TZ': 'Pacific/Auckland'}):
            if hasattr(time, 'tzset'): time.tzset()
            try:
                db = CloudDatabase.__new__(CloudDatabase)
                db.cloud = SimpleNamespace(timezone='America/Bogota')
                db._fetch_clock = Mock(return_value={'now':'2026-10-08T02:30:00Z',
                    'today':'2026-10-07','timezone':'America/Bogota'})
                self.assertEqual(db._now().isoformat(), '2026-10-07T21:30:00-05:00')
                self.assertEqual(display_timestamp(db._now()), '2026-10-07 21:30:00')
            finally:
                if original_tz is None: os.environ.pop('TZ', None)
                else: os.environ['TZ'] = original_tz
                if hasattr(time, 'tzset'): time.tzset()
    def test_date_has_no_invented_midnight(self):
        self.assertEqual(display_timestamp('2026-10-08'), '2026-10-08')
        self.assertEqual(display_timestamp(date(2026,10,8)), '2026-10-08')
        with self.assertRaises(ValueError): local_datetime('2026-10-08')
        with self.assertRaises(ValueError): parse_instant('2026-10-08')
        with self.assertRaises(ValueError): parse_instant('2026-10-08T02:30:00')
    def test_offset_and_utc_represent_same_instant(self):
        a = '2026-10-08T02:30:00Z'
        b = '2026-10-07T21:30:00-05:00'
        self.assertEqual(parse_instant(a), parse_instant(b))
        self.assertEqual(display_timestamp(a), display_timestamp(b))
    def test_other_gym_and_dst(self):
        self.assertEqual(display_timestamp('2026-10-08T02:30:00Z','Europe/Madrid'), '2026-10-08 04:30:00')
        self.assertEqual(display_timestamp('2026-01-08T14:00:00Z','America/New_York'), '2026-01-08 09:00:00')
        self.assertEqual(display_timestamp('2026-07-08T13:00:00Z','America/New_York'), '2026-07-08 09:00:00')
        self.assertEqual(_when('2026-10-08T02:30:00Z','Europe/Madrid'), '08/10/2026 04:30')
    def test_cache_refreshes_at_server_gym_midnight(self):
        fetch=Mock(side_effect=[{'now':'2026-10-08T04:59:59Z','today':'2026-10-07','timezone':'America/Bogota'},
                                {'now':'2026-10-08T05:00:01Z','today':'2026-10-08','timezone':'America/Bogota'}])
        clock=ServerDate()
        with patch('server_date.monotonic', side_effect=[100,100.5,102]):
            self.assertEqual(clock.get(fetch),date(2026,10,7))
            self.assertEqual(clock.get(fetch),date(2026,10,7))
            self.assertEqual(clock.get(fetch),date(2026,10,8))
        self.assertEqual(fetch.call_count,2)
    def test_server_date_rejects_inconsistent_response(self):
        with self.assertRaises(ValueError):
            ServerDate().get(lambda:{'now':'2026-10-08T02:30:00Z','today':'2026-10-08','timezone':'America/Bogota'})
    def test_local_class_time_is_converted_once(self):
        self.assertEqual(local_wall_instant('2026-10-08 18:00','America/Bogota').astimezone(timezone.utc).isoformat(),
                         '2026-10-08T23:00:00+00:00')
        self.assertEqual(local_wall_instant('2026-10-08T23:00:00Z','America/Bogota').isoformat(),
                         '2026-10-08T23:00:00+00:00')
        for value in ('2026-03-08 02:30', '2026-11-01 01:30'):
            with self.assertRaises(ValueError): local_wall_instant(value,'America/New_York')
    def test_excel_date_and_naive_events_are_rejected_without_rewriting_history(self):
        for value in (date(2026,10,8), '2026-10-08', '08/10/2026', datetime(2026,10,8,2,30)):
            with self.assertRaises(ValueError): CloudDatabase._excel_cell_value(value,'paid_at')
        original='2026-10-08T02:30:00+00:00'
        self.assertEqual(CloudDatabase._excel_cell_value(original,'paid_at'), original)
        self.assertEqual(CloudDatabase._excel_cell_value('2026-10-08','end_date'), '2026-10-08')
    def test_reception_expense_refuses_pc_date_when_server_clock_fails(self):
        db=Mock();db.today.side_effect=ConnectionError('Servidor no disponible')
        dialog=Mock()
        with patch('reception_expense_revision.messagebox.showerror') as error:
            self.assertFalse(open_reception_expense_manager(Mock(),db,dialog))
        dialog.assert_not_called();db.create_expense.assert_not_called();error.assert_called_once()
    def test_legacy_worker_status_uses_a_server_instant_and_rejects_naive(self):
        settings={'phone_number_id':'12345','whatsapp_enabled':True,
                  'last_worker_at':'2026-10-08T02:30:00Z','server_now':'2026-10-08T02:31:00Z'}
        self.assertEqual(service_status(settings),('En servicio','success'))
        self.assertEqual(service_status({**settings,'last_worker_at':'2026-10-08T02:30:00'})[0], 'Estado no disponible')
        self.assertEqual(service_status({k:v for k,v in settings.items() if k!='server_now'})[0], 'Estado no disponible')


if __name__ == '__main__': unittest.main()
