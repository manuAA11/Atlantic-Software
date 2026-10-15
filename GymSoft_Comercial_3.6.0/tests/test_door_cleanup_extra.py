"""Shutdown race regressions with event-controlled simulated USB; no hardware."""
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from door_access import (ConfigStore, DoorConfig, DoorController, PulseSession,
                         RELAY_OFF, RELAY_ON, RelayBusy, equipment_lock)
from test_door_cleanup import USB, until


class TrackedUSB(USB):
    def __init__(self):
        super().__init__()
        self.close_calls = 0
        self.cancel_calls = 0
        self.release_write = threading.Event()

    def cancel_write(self):
        self.cancel_calls += 1
        self.release_write.set()

    def close(self):
        self.close_calls += 1
        self.closing.set()
        self.release_close.wait()
        self.closed = True


class DoorCleanupExtra(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.usb = TrackedUSB()
        self.config = DoorConfig(True, 'COM7', 10, 0x1A86, 0x7523, '', 'USB-A')
        self.store = ConfigStore(self.temp.name, 'cleanup-extra-gym')
        self.transport = Mock(return_value=self.usb)
        self.door = DoorController(self.store, transport=self.transport,
            admin_authorized=True, clock=lambda: 10.,
            ports_provider=lambda: [dict(port='COM7', vid=0x1A86, pid=0x7523, location='USB-A')])
        self.store.save(self.config)
        self.barriers = []

    def tearDown(self):
        for barrier in self.barriers:
            barrier.set()
        self.usb.release_write.set()
        self.usb.release_close.set()
        self.door.close()
        until(lambda: not self.door._thread.is_alive())
        shutdown = self.door._shutdown_thread
        if shutdown:
            shutdown.join(timeout=1)
        self.temp.cleanup()

    def barrier(self):
        event = threading.Event()
        self.barriers.append(event)
        return event

    def assert_port_owned(self):
        with self.assertRaises(RelayBusy):
            with equipment_lock(self.store.folder, self.config.port):
                pass

    def test_shutdown_cancels_blocked_on_before_ten_second_watchdog(self):
        entered = threading.Event()
        def blocked_on():
            entered.set()
            self.usb.release_write.wait()
        self.usb.on = blocked_on
        self.assertTrue(self.door.test_pulse())
        self.assertTrue(entered.wait(2))
        began = time.monotonic()
        self.door.close()
        self.assertLess(time.monotonic() - began, 2.8)
        self.assertEqual(self.usb.cancel_calls, 1)
        self.assertEqual(self.usb.frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])
        self.assertEqual(self.usb.close_calls, 1)
        self.assertTrue(self.usb.closed)
        self.assertFalse(self.door._thread.is_alive())

    def test_shutdown_after_last_authorization_check_before_on_never_sends_on(self):
        armed = threading.Event()
        release_arm = self.barrier()
        def arm(session):
            armed.set()
            release_arm.wait()
        with patch.object(PulseSession, 'arm', arm):
            self.assertTrue(self.door.test_pulse())
            self.assertTrue(armed.wait(2))
            # These are the first actions of close(); delay its background
            # finisher to exercise the ON guard independently of finished=True.
            self.door._stop.set()
            self.door._cancel.set()
            release_arm.set()
            until(lambda: not self.door._thread.is_alive())
        self.assertNotIn(RELAY_ON, self.usb.frames)
        self.assertEqual(self.usb.frames, [RELAY_OFF, RELAY_OFF])
        self.assertEqual(self.usb.close_calls, 1)

    def test_repeated_shutdown_has_one_finisher_and_one_terminal_off(self):
        self.usb.release_close.clear()
        self.usb.on = self.door._cancel.set
        self.assertTrue(self.door.test_pulse())
        self.assertTrue(self.usb.closing.wait(2))
        session = self.door._session
        self.door.close()
        shutdown = self.door._shutdown_thread
        self.assertIsNotNone(shutdown)
        self.door.close()
        self.assertIs(self.door._shutdown_thread, shutdown)
        self.assertEqual(self.usb.frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])
        self.assertEqual(self.usb.close_calls, 1)
        self.assertTrue(self.door._pending)
        self.assertFalse(session.done.is_set())
        self.assertTrue(self.door._fault)
        self.assert_port_owned()
        self.usb.release_close.set()
        until(lambda: not self.door._thread.is_alive())
        self.assertTrue(session.done.is_set())
        self.assertTrue(self.door._fault)

    def test_close_observer_thread_start_failure_still_closes_transport(self):
        timer = threading.Timer
        class UnavailableObserver:
            def start(self):
                raise RuntimeError('Simulated observer thread creation failure')
            def cancel(self):
                pass
        def make_timer(seconds, callback, *args, **kwargs):
            if getattr(callback, '__name__', '') == '_close_timeout':
                return UnavailableObserver()
            return timer(seconds, callback, *args, **kwargs)
        self.usb.on = self.door._cancel.set
        with patch('door_access.threading.Timer', side_effect=make_timer):
            self.assertTrue(self.door.test_pulse())
            until(lambda: not self.door._pending)
        self.assertTrue(self.usb.closed, 'An optional observer must never bypass native cleanup.')
        self.assertEqual(self.usb.close_calls, 1)
        self.assertEqual(self.usb.frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])

    def test_shutdown_during_blocked_open_retains_lock_and_only_sends_off(self):
        opened = threading.Event()
        release_open = self.barrier()
        def connect(config):
            opened.set()
            release_open.wait()
            return self.usb
        self.transport.side_effect = connect
        self.assertTrue(self.door.test_pulse())
        self.assertTrue(opened.wait(2))
        self.assertIsNone(self.door._session)
        began = time.monotonic()
        self.door.close()
        self.assertLess(time.monotonic() - began, 2.8)
        self.assertTrue(self.door._pending)
        self.assert_port_owned()
        self.assertEqual(self.transport.call_count, 1)
        release_open.set()
        until(lambda: not self.door._thread.is_alive())
        self.assertEqual(self.usb.frames, [RELAY_OFF, RELAY_OFF])
        self.assertEqual(self.usb.close_calls, 1)
        self.assertNotIn(RELAY_ON, self.usb.frames)
        self.assertEqual(self.transport.call_count, 1)


if __name__ == '__main__':
    unittest.main()
