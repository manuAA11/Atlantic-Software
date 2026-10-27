"""Transient/persistent Windows-like USB faults; no native USB or database."""
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from common.door_access import (BIOMETRIC_METHOD, ConfigStore, DoorConfig, DoorDatabase,
                                DoorController, RELAY_OFF, RELAY_ON, RelayBusy)
from common.relay_recovery import RecoveringDoorController


class SerialException(OSError):
    pass


class SerialTimeoutException(OSError):
    pass


def wait_for(predicate):
    deadline = time.monotonic() + 5
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError('Worker did not complete')
        time.sleep(.005)


class NativeUSB:
    def __init__(self, factory, index):
        self.factory, self.index = factory, index
        self.frames = []
        self.opened = True
        self.saw_on = False
        self.factory.write_threads.append([])

    @property
    def out_waiting(self):
        if (self.factory.mode == 'drain_failure' and self.index == 1 and self.saw_on and
                self.frames[-1] == RELAY_OFF):
            error = SerialException(13, 'synthetic final drain failure')
            error.winerror = 5
            raise error
        return 0

    def write(self, data):
        if not self.opened:
            raise OSError('Closed fake USB')
        self.frames.append(data)
        self.factory.write_threads[self.index].append(threading.get_ident())
        self.factory.events.append(('write', self.index, data))
        if data == RELAY_ON:
            self.saw_on = True
            # Controlled pulse completion, no physical timer or contacts.
            if self.factory.mode != 'watchdog':
                self.factory.controller._cancel.set()
            if self.factory.mode == 'on_failure':
                raise SerialException(13, 'synthetic ON failure')
        if data == RELAY_OFF and self.index == 1 and self.saw_on and self.factory.mode not in ('healthy', 'drain_failure'):
            if self.factory.mode == 'timeout':
                raise SerialTimeoutException('synthetic terminal write timeout')
            if self.factory.mode == 'embedded_winerror':
                raise SerialException("WriteFile failed (PermissionError(13, 'synthetic', None, 5))")
            error = SerialException(13, 'synthetic terminal failure')
            error.winerror = 5
            raise error
        if data == RELAY_OFF and self.index >= 2 and self.factory.mode == 'persistent':
            error = SerialException(13, 'synthetic persistent failure')
            error.winerror = 5
            raise error
        return len(data)

    def cancel_write(self):
        self.factory.events.append(('cancel', self.index))

    def close(self):
        self.factory.events.append(('close_enter', self.index))
        if self.index == 1:
            self.factory.close_entered.set()
            if self.factory.mode == 'blocked_close':
                self.factory.close_release.wait(5)
            if self.factory.mode == 'close_failure':
                raise OSError('synthetic failed native close')
        self.opened = False
        self.factory.events.append(('close_done', self.index))
        if self.index == 1 and self.factory.after_close:
            self.factory.after_close()


class Factory:
    def __init__(self, mode='transient'):
        self.mode = mode
        self.connections = []
        self.events = []
        self.write_threads = []
        self.controller = None
        self.after_close = None
        self.close_entered = threading.Event()
        self.close_release = threading.Event()
        self.present = True

    def __call__(self, config):
        index = len(self.connections)
        self.events.append(('open', index))
        if index >= 2 and self.mode == 'open_failure':
            error = SerialException(13, 'synthetic failed reopen')
            error.winerror = 5
            raise error
        if any(item.opened for item in self.connections):
            raise AssertionError('A new handle opened before the previous native close finished')
        connection = NativeUSB(self, index)
        self.connections.append(connection)
        return connection


class RelayRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.store = ConfigStore(self.folder.name, 'synthetic-gym')
        self.config = DoorConfig(True, 'COM4', 3, 0x1A86, 0x7523, 'synthetic', 'usb-test')
        self.store.save(self.config)
        self.controllers = []
        self.factories = []

    def tearDown(self):
        for factory in self.factories:
            factory.close_release.set()
        for controller in self.controllers:
            controller.close()
        self.folder.cleanup()

    def make(self, mode='transient', cls=RecoveringDoorController, **kwargs):
        factory = Factory(mode)
        self.factories.append(factory)
        def ports():
            return ([dict(port=self.config.port, vid=self.config.vid, pid=self.config.pid,
                          serial_number=self.config.serial_number, location=self.config.location)]
                    if factory.present else [])
        controller = cls(self.store, transport=factory, ports_provider=ports,
                         clock=lambda: 10., admin_authorized=True, **kwargs)
        self.controllers.append(controller)
        factory.controller = controller
        wait_for(lambda: not controller.is_busy)
        return controller, factory

    def pulse(self, controller, member=1):
        response = dict(id=member, result='PERMITIDA', checkin_at=datetime.now(timezone.utc).isoformat())
        self.assertTrue(controller.submit(response, member, BIOMETRIC_METHOD))
        wait_for(lambda: not controller.is_busy)

    def records(self):
        import json
        log = Path(self.folder.name) / 'puerta.log'
        return [json.loads(line) for line in log.read_text().splitlines() if line.startswith('{')]

    def test_released_baseline_latches_the_supplied_failure_pattern(self):
        controller, factory = self.make(cls=DoorController)
        self.pulse(controller)
        self.assertTrue(controller._fault)
        self.assertEqual(len(factory.connections), 2)
        self.assertEqual(factory.connections[1].frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])

    def test_one_fresh_handle_recovers_only_off_and_next_authorized_person_can_use_it(self):
        controller, factory = self.make()
        self.pulse(controller)
        self.assertFalse(controller._fault)
        self.assertEqual(len(factory.connections), 3)
        self.assertEqual(factory.connections[1].frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])
        self.assertEqual(factory.connections[2].frames, [RELAY_OFF, RELAY_OFF])
        self.assertLess(factory.events.index(('close_done', 1)), factory.events.index(('open', 2)))
        self.assertIn('relay_off_recovery_succeeded', [row['event'] for row in self.records()])
        self.pulse(controller, member=2)
        self.assertEqual(sum(c.frames.count(RELAY_ON) for c in factory.connections), 2)

    def test_real_watchdog_finisher_can_recover_on_the_worker_after_close(self):
        self.config = replace(self.config, seconds=1)
        self.store.save(self.config)
        controller, factory = self.make('watchdog')
        self.pulse(controller)
        self.assertFalse(controller._fault)
        self.assertEqual(len(factory.connections), 3)
        self.assertNotEqual(factory.write_threads[1][1], factory.write_threads[1][2])
        self.assertEqual(factory.connections[2].frames, [RELAY_OFF, RELAY_OFF])

    def test_serial_write_timeout_and_embedded_windows_code_are_recoverable(self):
        for mode in ('timeout', 'embedded_winerror', 'drain_failure'):
            with self.subTest(mode=mode):
                # Each controller uses a distinct member so the shared ledger
                # cannot suppress the fault injection as a duplicate access.
                controller, factory = self.make(mode)
                self.pulse(controller, member=100 + len(self.controllers))
                self.assertFalse(controller._fault)
                self.assertEqual(len(factory.connections), 3)
                self.assertEqual(factory.connections[2].frames, [RELAY_OFF, RELAY_OFF])
                controller.close()

    def test_recovery_cannot_repeat_the_server_write_or_consume_another_entry(self):
        controller, factory = self.make()
        response = dict(id=1, result='PERMITIDA', checkin_at=datetime.now(timezone.utc).isoformat())
        database = Mock()
        database.register_checkin.return_value = response
        wrapped = DoorDatabase(database, controller)
        self.assertEqual(wrapped.register_checkin(1, BIOMETRIC_METHOD), response)
        wait_for(lambda: not controller.is_busy)
        database.register_checkin.assert_called_once_with(1, BIOMETRIC_METHOD)
        self.assertFalse(controller._fault)
        self.assertEqual(sum(c.frames.count(RELAY_ON) for c in factory.connections), 1)

    def test_denied_or_frozen_result_after_recovery_never_opens(self):
        controller, factory = self.make()
        self.pulse(controller)
        count = len(factory.connections)
        for changes in ({'result': 'DENEGADA'}, {'frozen': True}, {'duplicate_read': True}, {'override': True}):
            result = dict(id=2, result='PERMITIDA', checkin_at=datetime.now(timezone.utc).isoformat())
            result.update(changes)
            self.assertFalse(controller.submit(result, 2, BIOMETRIC_METHOD))
        self.assertEqual(len(factory.connections), count)

    def test_persistent_fault_has_one_reconnection_and_no_late_opening(self):
        controller, factory = self.make('persistent')
        self.pulse(controller)
        self.assertTrue(controller._fault)
        self.assertEqual(len(factory.connections), 3)
        self.assertTrue(all(frame == RELAY_OFF for frame in factory.connections[2].frames))
        result = dict(id=2, result='PERMITIDA', checkin_at=datetime.now(timezone.utc).isoformat())
        self.assertFalse(controller.submit(result, 2, BIOMETRIC_METHOD))
        self.assertEqual(sum(c.frames.count(RELAY_ON) for c in factory.connections), 1)
        self.assertEqual(sum(event[0] == 'open' for event in factory.events), 3)

    def test_missing_identity_does_not_reopen(self):
        controller, factory = self.make()
        factory.after_close = lambda: setattr(factory, 'present', False)
        self.pulse(controller)
        self.assertTrue(controller._fault)
        self.assertEqual(len(factory.connections), 2)

    def test_changed_configuration_does_not_reopen(self):
        controller, factory = self.make()
        factory.after_close = lambda: self.store.save(replace(self.config, port='COM9'))
        self.pulse(controller)
        self.assertTrue(controller._fault)
        self.assertEqual(len(factory.connections), 2)

    def test_failed_close_does_not_reopen(self):
        controller, factory = self.make('close_failure')
        self.pulse(controller)
        self.assertTrue(controller._fault)
        self.assertEqual(len(factory.connections), 2)

    def test_pending_native_close_cannot_release_equipment_lock_or_reopen(self):
        from common.door_access import equipment_lock
        controller, factory = self.make('blocked_close')
        self.assertTrue(controller.test_pulse())
        self.assertTrue(factory.close_entered.wait(2))
        self.assertTrue(controller.is_busy)
        self.assertEqual(len(factory.connections), 2)
        with self.assertRaises(RelayBusy):
            with equipment_lock(self.folder.name, 'COM4'):
                self.fail('A pending close released the equipment lock')
        controller._stop.set()
        factory.close_release.set()
        wait_for(lambda: not controller.is_busy)
        self.assertEqual(len(factory.connections), 2)

    def test_on_failure_never_retries_a_cycle(self):
        controller, factory = self.make('on_failure')
        self.pulse(controller)
        self.assertTrue(controller._fault)
        self.assertEqual(len(factory.connections), 2)

    def test_reopen_failure_stays_latched_without_loop(self):
        controller, factory = self.make('open_failure')
        self.pulse(controller)
        self.assertTrue(controller._fault)
        self.assertEqual(sum(event[0] == 'open' for event in factory.events), 3)

    def test_shutdown_cancels_the_single_recovery_before_open(self):
        controller, factory = self.make()
        factory.after_close = controller._stop.set
        self.pulse(controller)
        self.assertTrue(controller._fault)
        self.assertEqual(len(factory.connections), 2)

    def test_healthy_pulse_keeps_existing_three_frames(self):
        controller, factory = self.make('healthy')
        self.pulse(controller)
        self.assertFalse(controller._fault)
        self.assertEqual(len(factory.connections), 2)
        self.assertEqual(factory.connections[1].frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])
        self.assertNotIn('relay_off_recovery_start', [row['event'] for row in self.records()])

    def test_manual_rest_failure_cannot_start_recursive_recovery(self):
        controller, factory = self.make('persistent')
        self.pulse(controller)
        initial = len(factory.connections)
        self.assertTrue(controller.secure())
        wait_for(lambda: not controller.is_busy)
        self.assertTrue(controller._fault)
        self.assertEqual(len(factory.connections), initial + 1)

    def test_offline_does_not_open_or_enumerate_usb(self):
        controller, factory = self.make(offline=True)
        self.assertEqual(factory.connections, [])
        self.assertFalse(controller.test_pulse())
        with patch.object(controller, 'ports_provider', side_effect=AssertionError('USB scan')):
            controller._check_connection()

    def test_disabled_control_never_scans_or_opens_usb(self):
        self.store.save(replace(self.config, enabled=False))
        controller, factory = self.make()
        with patch.object(controller, 'ports_provider', side_effect=AssertionError('USB scan')):
            controller._check_connection()
            self.assertFalse(controller.test_pulse())
        self.assertEqual(factory.connections, [])

    def test_another_window_owning_the_relay_prevents_reconnection(self):
        from common import door_access
        controller, factory = self.make()
        original = door_access.equipment_lock
        calls = []
        def lock(folder, port):
            calls.append(port)
            if len(calls) == 2:
                raise RelayBusy()
            return original(folder, port)
        with patch.object(door_access, 'equipment_lock', side_effect=lock):
            self.pulse(controller)
        self.assertTrue(controller._fault)
        self.assertEqual(len(factory.connections), 2)


if __name__ == '__main__':
    unittest.main()
