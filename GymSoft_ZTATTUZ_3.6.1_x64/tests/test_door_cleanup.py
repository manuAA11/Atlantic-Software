"""Repeated cycles and blocked native cleanup; all USB is simulated."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from door_access import (BIOMETRIC_METHOD, ConfigStore, DoorConfig, DoorController,
                         RELAY_OFF, RELAY_ON, RelayBusy, equipment_lock)


def until(condition, seconds=4):
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() >= deadline:
            raise AssertionError("El transporte simulado no terminó.")
        time.sleep(.005)


class USB:
    def __init__(self):
        self.frames = []
        self.out_waiting = 0
        self.closed = False
        self.on = lambda: None
        self.closing = threading.Event()
        self.release_close = threading.Event()
        self.release_close.set()

    def write(self, frame):
        self.frames.append(frame)
        if frame == RELAY_ON:
            self.on()
        return len(frame)

    def close(self):
        self.closing.set()
        self.release_close.wait(5)
        self.closed = True


class DoorCleanup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.usb = USB()
        self.config = DoorConfig(True, 'COM7', 1, 0x1A86, 0x7523, '', 'USB-A')
        self.store = ConfigStore(self.temp.name, 'cleanup-gym')
        self.transport = Mock(return_value=self.usb)
        self.door = DoorController(self.store, transport=self.transport, admin_authorized=True,
            clock=lambda: 10., ports_provider=lambda: [dict(port='COM7', vid=0x1A86, pid=0x7523, location='USB-A')])
        self.store.save(self.config)

    def tearDown(self):
        self.usb.release_close.set()
        self.door.close()
        until(lambda: not self.door._thread.is_alive())
        self.temp.cleanup()

    def test_shutdown_returns_while_native_close_is_blocked_and_keeps_equipment_lock(self):
        self.usb.release_close.clear()
        started = threading.Event()
        self.usb.on = started.set
        self.assertTrue(self.door.test_pulse())
        self.assertTrue(started.wait(2))
        began = time.monotonic()
        self.door.close()
        elapsed = time.monotonic() - began
        self.assertLess(elapsed, 2.8, 'La llamada de cierre de Tk quedó bloqueada por el controlador USB.')
        self.assertFalse(self.usb.closed)
        self.assertTrue(self.door._thread.is_alive())
        self.assertTrue(self.door._pending)
        with self.assertRaises(RelayBusy):
            with equipment_lock(self.store.folder, 'COM7'):
                pass
        self.assertFalse(self.door.test_pulse())
        self.assertEqual(self.usb.frames.count(RELAY_ON), 1)
        self.assertEqual(self.usb.frames[-1], RELAY_OFF)

    def test_watchdog_keeps_equipment_lock_and_reports_blocked_close_until_cleanup_finishes(self):
        self.usb.release_close.clear()
        release_write = threading.Event()
        self.usb.on = lambda: release_write.wait(4)
        self.usb.cancel_write = release_write.set
        self.assertTrue(self.door.test_pulse())
        self.assertTrue(self.usb.closing.wait(3))
        # The old duplicate finish returned after 1.5s and released the lock
        # while the other thread was still inside the native driver close.
        time.sleep(1.8)
        self.assertTrue(self.door._pending)
        self.assertIsNotNone(self.door._session)
        self.assertTrue(self.door._fault)
        with self.assertRaises(RelayBusy):
            with equipment_lock(self.store.folder, 'COM7'):
                pass
        self.assertIn('cerrar puerto', self.door.snapshot()['last_error'])
        self.assertFalse(self.door.test_pulse())
        self.usb.release_close.set()
        until(lambda: not self.door._pending)
        # A late cleanup cannot silently re-enable access after the timeout.
        self.assertTrue(self.door._fault)
        self.assertTrue(self.door.secure())
        until(lambda: not self.door._pending)
        self.assertFalse(self.door._fault)

    def test_twenty_five_different_authorized_entries_each_close_their_own_transport(self):
        opened = []
        def connect(config):
            self.assertEqual(config.port, 'COM7')
            usb = USB()
            usb.on = self.door._cancel.set
            opened.append(usb)
            return usb
        self.transport.side_effect = connect
        for client_id in range(1, 26):
            response = dict(id=client_id, result='PERMITIDA', checkin_at=datetime.now(timezone.utc).isoformat())
            self.assertTrue(self.door.submit(response, client_id, BIOMETRIC_METHOD))
            until(lambda: not self.door._pending)
            self.assertFalse(self.door._fault)
            self.assertEqual(opened[-1].frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])
            self.assertTrue(opened[-1].closed)
        self.assertEqual(len(opened), 25)

    def test_monitor_thread_failure_does_not_skip_close_or_leave_equipment_lock_held(self):
        with patch('door_access.threading.Timer.start', side_effect=RuntimeError('cannot start thread')):
            self.assertTrue(self.door.secure())
            until(lambda: not self.door._pending)
        self.assertTrue(self.usb.closed)
        self.assertFalse(self.door._fault)
        self.assertEqual(self.usb.frames, [RELAY_OFF, RELAY_OFF])
        with equipment_lock(self.store.folder, 'COM7'):
            pass


if __name__ == '__main__':
    unittest.main()
