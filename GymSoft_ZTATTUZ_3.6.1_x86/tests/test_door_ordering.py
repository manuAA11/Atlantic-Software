"""Regression tests for serial write ordering; no ports or real hardware."""
from dataclasses import replace
import threading
import time
import unittest

from door_access import DoorConfig, PulseSession, RELAY_OFF, RELAY_ON


class Controller:
    def __init__(self):
        self._cancel = threading.Event()
        self._fault = False
        self.records = []
        self.messages = []

    def _write(self, connection, frame):
        if connection.write(frame) != len(frame):
            raise OSError('partial write')

    def _record(self, event, **fields):
        self.records.append(dict(event=event, **fields))

    def _status(self, *args):
        self.messages.append(args)


class PausedUSB:
    def __init__(self, *, cancellation_releases=False):
        self.frames = []
        self.closed = False
        self.on_entered = threading.Event()
        self.off_entered = threading.Event()
        self.release_on = threading.Event()
        self.cancel_called = threading.Event()
        self.cancellation_releases = cancellation_releases

    def write(self, frame):
        if frame == RELAY_ON:
            # Pause BEFORE sending ON; the old finish() could send OFF here
            # while its logger was running, then this ON arrived last.
            self.on_entered.set()
            if not self.release_on.wait(20):
                raise TimeoutError('simulated driver blocked')
        if self.closed:
            raise OSError('port closed')
        self.frames.append(frame)
        if frame == RELAY_OFF:
            self.off_entered.set()
        return len(frame)

    def cancel_write(self):
        self.cancel_called.set()
        if self.cancellation_releases:
            self.release_on.set()

    def close(self):
        self.closed = True


class OrderingTests(unittest.TestCase):
    def make_session(self, **kwargs):
        controller = Controller()
        connection = PausedUSB(**kwargs)
        session = PulseSession(controller, connection,
            replace(DoorConfig(), seconds=1), 'access')
        return controller, connection, session

    def writer(self, session, errors):
        def write():
            try:
                session.write(RELAY_ON)
            except Exception as error:
                errors.append(error)
        worker = threading.Thread(target=write, daemon=True)
        worker.start()
        return worker

    def test_terminal_off_waits_for_on_and_is_the_last_frame(self):
        controller, usb, session = self.make_session()
        errors = []
        worker = self.writer(session, errors)
        finisher = threading.Thread(target=session.finish, daemon=True)
        try:
            self.assertTrue(usb.on_entered.wait(10))
            finisher.start()
            self.assertTrue(usb.cancel_called.wait(10))
            self.assertFalse(usb.off_entered.wait(.05),
                'OFF must not race with the earlier unfinished ON')
            usb.release_on.set()
            self.assertTrue(session.done.wait(10))
            worker.join(10)
            finisher.join(10)
            self.assertEqual(usb.frames, [RELAY_ON, RELAY_OFF])
            self.assertTrue(usb.closed)
            self.assertFalse(errors)
            self.assertFalse(controller._fault)
        finally:
            usb.release_on.set()
            worker.join(10)
            if finisher.ident is not None:
                finisher.join(10)

    def test_watchdog_cancels_a_blocked_write_before_terminal_off(self):
        controller, usb, session = self.make_session(cancellation_releases=True)
        errors = []
        worker = self.writer(session, errors)
        try:
            self.assertTrue(usb.on_entered.wait(10))
            session.arm()
            self.assertTrue(session.done.wait(10))
            worker.join(10)
            self.assertTrue(usb.cancel_called.is_set())
            self.assertEqual(usb.frames, [RELAY_ON, RELAY_OFF])
            self.assertTrue(usb.closed)
            self.assertFalse(errors)
            self.assertFalse(controller._fault)
            self.assertEqual(controller.records[-1]['reason'], 'watchdog')
        finally:
            usb.release_on.set()
            worker.join(10)
            session.finish()

    def test_uncancelable_write_reports_unknown_without_concurrent_off(self):
        controller, usb, session = self.make_session()
        errors = []
        worker = self.writer(session, errors)
        try:
            self.assertTrue(usb.on_entered.wait(10))
            started = time.monotonic()
            self.assertFalse(session.finish(reason='shutdown'))
            self.assertLess(time.monotonic() - started, 1.7)
            self.assertIsInstance(session.error, TimeoutError)
            self.assertTrue(controller._fault)
            self.assertTrue(session.done.is_set())
            self.assertTrue(usb.cancel_called.is_set())
            self.assertTrue(usb.closed)
            self.assertEqual(usb.frames, [])
            self.assertEqual(controller.records[-1]['state'], 'Desconocido')
            usb.release_on.set()
            worker.join(10)
            self.assertEqual(usb.frames, [])
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], OSError)
        finally:
            usb.release_on.set()
            worker.join(10)

    def test_no_new_on_can_start_after_finish(self):
        controller, usb, session = self.make_session()
        self.assertTrue(session.finish())
        with self.assertRaises(TimeoutError):
            session.write(RELAY_ON)
        self.assertEqual(usb.frames, [RELAY_OFF])
        self.assertFalse(controller._fault)

    def test_shutdown_cancellation_then_repeated_finish_sends_off_once(self):
        controller, usb, session = self.make_session(cancellation_releases=True)
        errors = []
        worker = self.writer(session, errors)
        try:
            self.assertTrue(usb.on_entered.wait(10))
            self.assertTrue(session.finish(reason='shutdown'))
            self.assertTrue(session.finish())
            worker.join(10)
            self.assertEqual(usb.frames, [RELAY_ON, RELAY_OFF])
            self.assertFalse(errors)
            self.assertTrue(controller._cancel.is_set())
            self.assertFalse(controller._fault)
        finally:
            usb.release_on.set()
            worker.join(10)

    def test_cancel_error_still_attempts_off_when_write_unwinds(self):
        controller, usb, session = self.make_session()
        errors = []
        def failing_cancel():
            usb.cancel_called.set()
            usb.release_on.set()
            raise OSError('cancellation failed')
        usb.cancel_write = failing_cancel
        worker = self.writer(session, errors)
        try:
            self.assertTrue(usb.on_entered.wait(10))
            self.assertTrue(session.finish())
            worker.join(10)
            self.assertEqual(usb.frames, [RELAY_ON, RELAY_OFF])
            self.assertFalse(errors)
            self.assertTrue(usb.closed)
            self.assertFalse(controller._fault)
            self.assertEqual(controller.records[-2]['event'], 'relay_cancel_failed')
            self.assertEqual(controller.records[-1]['event'], 'relay_unlock_end')
        finally:
            usb.release_on.set()
            worker.join(10)


if __name__ == '__main__':
    unittest.main()
