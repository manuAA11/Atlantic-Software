"""Server-date filters must not run RPCs on Tk or read Tk on workers."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
import threading
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock
from store_pos_ui import StorePosPanel


class Input:
    def __init__(self, value):
        self.value, self.thread = value, threading.get_ident()

    def get(self):
        if threading.get_ident() != self.thread:
            raise AssertionError('Tk input read on background worker')
        return self.value


class StoreBackgroundTests(unittest.TestCase):
    def panel(self, period):
        panel = NS(period=Input(period), date_from=Input('2026-10-01'),
                   date_to=Input('2026-10-16'), employee_filter=Input('Todos'),
                   product_filter=Input('Todos'), client_filter=Input('Todos'),
                   employees={}, history_products={}, history_clients={}, db=Mock())
        panel.history_filters = lambda: StorePosPanel.history_filters(panel)
        main = threading.get_ident()
        def clock():
            self.assertNotEqual(threading.get_ident(), main)
            return date(2026, 10, 16)
        panel.db._today.side_effect = clock
        return panel

    def run_query(self, load):
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(load).result(timeout=2)

    def test_server_date_resolved_off_tk_for_each_relative_period(self):
        for period, first in [('Hoy', '2026-10-16'), ('Semana', '2026-10-12'),
                              ('Mes', '2026-10-01'), ('Últimos 2 años', '2024-10-16')]:
            with self.subTest(period=period):
                panel = self.panel(period)
                load, signature = StorePosPanel.history_query(panel, lambda filters: filters)
                panel.db._today.assert_not_called()
                panel.period.value = 'Rango'
                result = self.run_query(load)
                self.assertEqual(result, dict(limit=300, date_from=first, date_to='2026-10-16'))
                self.assertEqual(signature[0], period)

    def test_explicit_range_and_selection_are_snapshotted_without_clock(self):
        panel = self.panel('Rango')
        panel.employee_filter.value = 'Recepción'
        panel.employees['Recepción'] = 'employee-a'
        load, _ = StorePosPanel.history_query(panel, lambda filters: filters)
        panel.date_from.value = 'invalid'
        panel.employees.clear()
        result = self.run_query(load)
        self.assertEqual(result['employee_id'], 'employee-a')
        self.assertEqual(result['date_from'], '2026-10-01')
        panel.db._today.assert_not_called()

    def test_clock_error_propagates_to_background_error_handling(self):
        panel = self.panel('Hoy')
        panel.db._today.side_effect = RuntimeError('server unavailable')
        load, _ = StorePosPanel.history_query(panel, lambda filters: filters)
        with self.assertRaisesRegex(RuntimeError, 'server unavailable'):
            self.run_query(load)

    def test_invalid_range_rejected_before_dispatch(self):
        panel = self.panel('Rango')
        panel.date_from.value = '2026-10-20'
        with self.assertRaises(ValueError):
            StorePosPanel.history_query(panel, Mock())


if __name__ == '__main__':
    unittest.main()
