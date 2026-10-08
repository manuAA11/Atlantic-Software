import unittest
from datetime import date
from uuid import uuid4
from plan_forms import plan_end_date, validate_months, carryover_values, membership_request
from followup import ticket_groups, spreadsheet_text
from cloud_database import CloudDatabase
from unittest.mock import Mock


class TicketTests(unittest.TestCase):
    def test_calendar_anniversary_and_month_end(self):
        plan = {'duration_days': 30, 'duration_months': 1, 'entry_limit': 15}
        for start, end in [('2024-01-31', '2024-02-28'), ('2025-01-31', '2025-02-27'), ('2026-04-01', '2026-04-30')]:
            self.assertEqual(plan_end_date(plan, start).isoformat(), end)
        self.assertEqual(plan_end_date({'duration_days': 30}, '2026-02-01').isoformat(), '2026-03-02')

    def test_carryover_only_for_started_tickets_with_valid_count(self):
        plan = {'entry_limit': 20, 'duration_days': 30}
        self.assertEqual(carryover_values(plan, '2026-09-01', 7, date(2026, 9, 8))[0], 7)
        for count in (-1, 21, '1.5', ''):
            with self.assertRaises(ValueError):
                carryover_values(plan, '2026-09-01', count, date(2026, 9, 8))
        with self.assertRaises(ValueError):
            carryover_values(plan, '2026-09-09', 0, date(2026, 9, 8))
        for months, limit in [(0, 15), (121, 20), ('abc', 15), (1, None)]:
            with self.assertRaises(ValueError):
                validate_months(months, limit)

    def test_ranges_include_boundaries_once(self):
        rows = [{'entries_remaining': n, 'client_id': n} for n in range(50)]
        groups = ticket_groups(rows)
        self.assertEqual([len(rows) for rows in groups.values()], [1, 5, 5, 5, 5, 29])
        self.assertEqual(len({r['client_id'] for rows in groups.values() for r in rows}), 50)

    def test_transferred_balance_does_not_send_a_payment(self):
        key = str(uuid4())
        rpc, params = membership_request('gym', 1, 2, '2026-09-01', 9999, 'Efectivo',
            carryover=True, initial_entries_used=12, request_id=key)
        self.assertEqual(rpc, 'register_ticket_carryover')
        self.assertNotIn('p_amount', params)
        self.assertEqual(params['p_request_id'], key)
        self.assertEqual(params['p_entries_used'], 12)

    def test_adapter_persists_calendar_months(self):
        db = CloudDatabase.__new__(CloudDatabase)
        db.gym_id = 'gym'
        db.client = Mock()
        db._data = Mock(return_value=[{'id': 2}])
        db.add_plan('Bono 20', 60, 50000, 20, 2)
        payload = db.client.table.return_value.insert.call_args.args[0]
        self.assertEqual((payload['duration_months'], payload['entry_limit']), (2, 20))

    def test_export_preserves_contacts_as_text(self):
        self.assertEqual(spreadsheet_text('+573001234567'), "'+573001234567")
        self.assertEqual(spreadsheet_text('=1+1'), "'=1+1")


if __name__ == '__main__':
    unittest.main()
