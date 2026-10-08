"""Casos encontrados al revisar importes y calendarios de una sesión larga."""
from datetime import date, datetime
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from money_input import parse_amount
from plan_forms import membership_form_values, validate_plan
from server_date import ServerDate
import licensing


class ReviewRegressions(unittest.TestCase):
    def test_license_denial_is_deferred_during_payment_then_applied(self):
        class Window:
            def __init__(self):
                self.callbacks = []
                self._foreground_io = True
                self.closed = False
            def after(self, delay, callback): self.callbacks.append(callback)
            def winfo_exists(self): return True
            def close_app(self): self.closed = True
        class InlineThread:
            def __init__(self, target, **kwargs): self.target = target
            def start(self): self.target()
        window = Window()
        with patch.object(licensing, 'check_license', return_value={'allowed': False, 'message': 'Suspendido'}), \
             patch.object(licensing.threading, 'Thread', InlineThread), \
             patch.object(licensing.messagebox, 'showerror') as error:
            licensing.start_license_monitor(window, object())
            window.callbacks.pop(0)()  # Consulta.
            window.callbacks.pop(0)()  # Conserva la respuesta mientras termina el pago.
            self.assertFalse(window.closed); error.assert_not_called()
            window._foreground_io = False
            window.callbacks.pop(0)()
            self.assertTrue(window.closed); error.assert_called_once()

    def test_amounts_preserve_whole_pesos_and_reject_ambiguous_decimals(self):
        for text, expected in [('5000', 5000), ('5.000', 5000), ('5,000', 5000),
                               (' 0 ', 0), ('1.250.000', 1250000)]:
            self.assertEqual(parse_amount(text), expected)
            self.assertEqual(membership_form_values('14/09/2026', text)[1], expected)
            self.assertEqual(validate_plan('Mensual', 30, text)[2], expected)
        for text in ['15,50', '15.50', '1.2.3', '10,000.00', '-1', 'NaN', '1e6',
                     '', '1000000000001', '1,000,00', True]:
            for parse in [parse_amount,
                          lambda v: membership_form_values('14/09/2026', v),
                          lambda v: validate_plan('Mensual', 30, v)]:
                with self.subTest(value=text), self.assertRaises(ValueError):
                    parse(text)

    def test_server_date_refreshes_after_one_minute_without_realtime(self):
        fetch = Mock(side_effect=['2026-09-14', '2026-09-15'])
        cache = ServerDate()
        with patch('server_date.monotonic', return_value=100):
            self.assertEqual(cache.get(fetch), date(2026, 9, 14))
        with patch('server_date.monotonic', return_value=159):
            self.assertEqual(cache.get(fetch), date(2026, 9, 14))
            self.assertEqual(fetch.call_count, 1)
        with patch('server_date.monotonic', return_value=160):
            self.assertEqual(cache.get(fetch), date(2026, 9, 15))
            self.assertEqual(fetch.call_count, 2)

    def test_server_date_refreshes_on_local_midnight_before_expiry(self):
        cache = ServerDate('America/Bogota')
        fetch = Mock(side_effect=[
            {'now':'2026-09-15T04:59:59Z','today':'2026-09-14','timezone':'America/Bogota'},
            {'now':'2026-09-15T05:00:01Z','today':'2026-09-15','timezone':'America/Bogota'}])
        with patch('server_date.monotonic', return_value=100):
            self.assertEqual(cache.get(fetch), date(2026, 9, 14))
        with patch('server_date.monotonic', return_value=102):
            self.assertEqual(cache.get(fetch), date(2026, 9, 15))
        self.assertEqual(fetch.call_count, 2)

    def test_date_error_does_not_renew_stale_cache(self):
        cache = ServerDate()
        with patch('server_date.monotonic', return_value=100):
            cache.get(lambda: '2026-09-14')
        with patch('server_date.monotonic', return_value=200):
            for failure in [TimeoutError('offline'), ValueError('invalid')]:
                with self.assertRaises(type(failure)):
                    cache.get(Mock(side_effect=failure))
            self.assertEqual(cache.get(lambda: '2026-09-15'), date(2026, 9, 15))

    def test_concurrent_date_requests_share_one_fetch(self):
        cache = ServerDate()
        ready, release = threading.Event(), threading.Event()
        calls, values = [], []
        def fetch():
            calls.append(1)
            ready.set()
            self.assertTrue(release.wait(2))
            return '2026-09-14'
        jobs = [threading.Thread(target=lambda: values.append(cache.get(fetch))) for _ in range(3)]
        for job in jobs: job.start()
        self.assertTrue(ready.wait(2)); release.set()
        for job in jobs: job.join(2)
        self.assertEqual(calls, [1])
        self.assertEqual(values, [date(2026, 9, 14)] * 3)

    def test_invalidation_during_fetch_does_not_keep_old_response(self):
        cache = ServerDate()
        def fetch():
            cache.invalidate()
            return '2026-09-14'
        self.assertEqual(cache.get(fetch), date(2026, 9, 14))
        self.assertIsNone(cache.value)
        self.assertEqual(cache.get(lambda: '2026-09-15'), date(2026, 9, 15))


if __name__ == '__main__': unittest.main()
