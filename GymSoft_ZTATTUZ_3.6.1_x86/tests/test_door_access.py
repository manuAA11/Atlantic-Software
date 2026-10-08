"""Puerta con transporte simulado: nunca enumera ni abre un USB físico."""
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from door_access import (DoorConfig, ConfigStore, DoorController, DoorDatabase,
    RELAY_ON, RELAY_OFF, BIOMETRIC_METHOD, matches_port, open_relay, equipment_lock)


def until(fn, seconds=3):
    end = time.monotonic() + seconds
    while not fn():
        if time.monotonic() > end: raise AssertionError('El relé simulado no respondió.')
        time.sleep(.005)


class FakeUSB:
    def __init__(self):
        self.frames = []; self.closed = False; self.on = lambda: None
        self.fail_on = False; self.fail_off = False; self.partial = False
        self.out_waiting = 0
    def write(self, data):
        self.frames.append(data)
        if data == RELAY_ON:
            if self.fail_on: raise OSError('USB desconectado al activar')
            self.on()
        if data == RELAY_OFF and self.fail_off and RELAY_ON in self.frames:
            raise OSError('USB desconectado al finalizar')
        return 1 if self.partial else len(data)
    def close(self): self.closed = True


class DoorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ConfigStore(self.temp.name, 'gym-A')
        self.usb = FakeUSB()
        self.factory = Mock(return_value=self.usb)
        self.door = DoorController(self.store, transport=self.factory)
        self.usb.on = self.door._cancel.set  # Tiempo físico simulado sin espera.
        self.config = DoorConfig(True, 'COM7', 3, 0x1A86, 0x7523, '', 'USB-A')
        self.store.save(self.config)
    def tearDown(self):
        self.door.close(); self.temp.cleanup()
    def test_ledger_connections_closed_on_success_duplicate_and_failure(self):
        import sqlite3
        connect = sqlite3.connect
        held = []  # Retenerlas impide que el recolector oculte la fuga.
        def tracked(*args, **kwargs):
            db = connect(*args, **kwargs)
            held.append(db)
            return db
        def assert_closed():
            for db in held:
                with self.assertRaises(sqlite3.ProgrammingError):
                    db.execute('SELECT 1')
        with patch('door_access.sqlite3.connect', side_effect=tracked):
            self.assertTrue(self.door._claim(1, 'event-a'))
            assert_closed()
            self.assertFalse(self.door._claim(1, 'event-a'))
            assert_closed()
            path = self.store.folder / 'puerta_eventos.db'
            # Falla real de SQL; también debe cerrar la conexión.
            with connect(path) as db:
                db.execute('DROP TABLE events')
                db.execute('CREATE TABLE events (invalid_column TEXT)')
            db.close()
            with self.assertRaises(sqlite3.OperationalError):
                self.door._claim(2, 'event-b')
            assert_closed()
        path.unlink()  # En Windows falla si alguna conexión sigue abierta.

    def result(self, client=1, **kwargs):
        return dict(id=client, result='PERMITIDA', override=False,
                    checkin_at=datetime.now(timezone.utc).isoformat(), **kwargs)
    def finish(self): until(lambda: not self.door._pending)
    def submit(self, result=None, client=1, method=BIOMETRIC_METHOD, **kwargs):
        value = self.door.submit(result or self.result(client), client, method, **kwargs)
        self.finish(); return value

    def test_protocol_and_checksum(self):
        for frame in (RELAY_OFF, RELAY_ON):
            self.assertEqual(frame[3], sum(frame[:3]) & 255)
        self.assertEqual(RELAY_ON.hex(), 'a00101a2'); self.assertEqual(RELAY_OFF.hex(), 'a00100a1')
    def test_authorized_entry_pulses_then_off_and_closes(self):
        self.assertTrue(self.submit())
        self.assertEqual(self.usb.frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])
        self.assertTrue(self.usb.closed)
    def test_denied_cases_never_open(self):
        for status in ('INACTIVO', 'VENCIDO', 'SIN PLAN', 'SIN ENTRADAS'):
            result = self.result(status=status); result['result'] = 'DENEGADA'
            self.assertFalse(self.door.submit(result, 1, BIOMETRIC_METHOD))
        self.factory.assert_not_called()
    def test_frozen_rpc_never_touches_relay(self):
        response = dict(self.result(), result='DENEGADA', status='FROZEN', frozen=True)
        raw = Mock(); raw.register_checkin.return_value = response
        wrapped = DoorDatabase(raw, self.door)
        self.assertEqual(wrapped.register_fingerprint_checkin(1, BIOMETRIC_METHOD), response)
        raw.register_checkin.assert_called_once_with(1, BIOMETRIC_METHOD)
        self.factory.assert_not_called()
        self.assertFalse(self.door.submit(dict(response, result='PERMITIDA'), 1, BIOMETRIC_METHOD))
        self.factory.assert_not_called()

    def test_manual_and_override_never_open(self):
        for method in ('RECEPCIÓN', 'REGISTRO MANUAL', 'AUTORIZACIÓN MANUAL'):
            self.assertFalse(self.door.submit(self.result(), 1, method))
        self.assertFalse(self.door.submit(self.result(), 1, BIOMETRIC_METHOD, override=True))
        result = self.result(); result['override'] = True
        self.assertFalse(self.door.submit(result, 1, BIOMETRIC_METHOD))
        self.factory.assert_not_called()
    def test_missing_or_wrong_confirmation_never_open(self):
        for result in (None, {}, {'result':'PERMITIDA'}, self.result(client=2),
                       dict(self.result(), checkin_at='ayer'), dict(self.result(), checkin_at='2026-09-27')):
            self.assertFalse(self.door.submit(result, 1, BIOMETRIC_METHOD))
        self.factory.assert_not_called()
    def test_exact_event_not_replayed_and_same_client_debounced(self):
        result = self.result()
        self.submit(result); self.submit(result); self.submit(self.result())
        self.assertEqual(self.usb.frames.count(RELAY_ON), 1)
    def test_other_client_can_enter_next(self):
        self.submit(client=1); self.submit(client=2)
        self.assertEqual(self.usb.frames.count(RELAY_ON), 2)
    def test_disabled_default_and_offline_never_touch_transport(self):
        self.store.save(DoorConfig())
        self.assertFalse(self.submit()); self.factory.assert_not_called()
        self.store.save(self.config)
        with patch('door_access.open_relay', side_effect=AssertionError('USB real')):
            other = DoorController(self.store, transport=self.factory, offline=True)
            try:
                self.assertFalse(other.submit(self.result(), 1, BIOMETRIC_METHOD))
                self.assertFalse(other.test_pulse()); self.assertFalse(other.secure())
            finally: other.close()
        self.factory.assert_not_called()
    def test_secure_only_off(self):
        self.assertTrue(self.door.secure()); self.finish()
        self.assertNotIn(RELAY_ON, self.usb.frames)
        self.assertEqual(self.usb.frames[-1], RELAY_OFF)
    def test_test_pulse_does_not_call_database(self):
        self.assertTrue(self.door.test_pulse()); self.finish()
        self.assertEqual(self.usb.frames.count(RELAY_ON), 1)
        self.assertFalse((self.store.folder / 'puerta_eventos.db').exists())
    def test_manual_pulse_does_not_consume_membership_or_create_attendance(self):
        self.assertTrue(self.door.manual_pulse()); self.finish()
        self.assertEqual(self.usb.frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])
        self.assertFalse((self.store.folder / 'puerta_eventos.db').exists())
        self.assertIn('APERTURA_MANUAL', (self.store.folder / 'puerta.log').read_text())
    def test_manual_disabled_and_fault_do_not_open(self):
        self.store.save(DoorConfig()); self.assertFalse(self.door.manual_pulse())
        self.store.save(self.config); self.door._fault = True
        self.assertFalse(self.door.manual_pulse()); self.factory.assert_not_called()
    def test_usb_unplug_after_on_still_attempts_off_and_latches_failure(self):
        self.usb.fail_on = True
        self.submit()
        self.assertEqual(self.usb.frames, [RELAY_OFF, RELAY_ON, RELAY_OFF])
        self.assertTrue(self.usb.closed); self.assertTrue(self.door._fault)
        self.assertFalse(self.submit(client=2))
        self.usb.fail_on = False
        self.door.secure(); self.finish()
        self.assertFalse(self.door._fault)
    def test_failed_off_never_reports_success(self):
        self.usb.fail_off = True
        self.submit()
        self.assertTrue(self.door._fault); self.assertTrue(self.usb.closed)
        events = list(self.door.events.queue)
        self.assertEqual(events[-1][0], 'error')
    def test_partial_write_rejected_and_off_attempted(self):
        self.usb.partial = True
        self.submit()
        self.assertNotIn(RELAY_ON, self.usb.frames)
        self.assertTrue(self.door._fault); self.assertTrue(self.usb.closed)
    def test_blocked_driver_output_times_out_without_opening(self):
        self.usb.out_waiting = 4
        start = time.monotonic(); self.submit()
        self.assertLess(time.monotonic() - start, 1.5)
        self.assertNotIn(RELAY_ON, self.usb.frames)
        self.assertTrue(self.door._fault); self.assertTrue(self.usb.closed)
    def test_disconnected_no_delayed_open_after_reconnection(self):
        self.factory.side_effect = OSError('desconectado')
        self.submit(); self.assertTrue(self.door._fault)
        self.factory.side_effect = None
        self.door.secure(); self.finish()
        self.assertNotIn(RELAY_ON, self.usb.frames)
    def test_shutdown_during_pulse_sends_off(self):
        self.usb.on = lambda: None
        self.door.submit(self.result(), 1, BIOMETRIC_METHOD)
        until(lambda: RELAY_ON in self.usb.frames)
        self.door.close()
        self.assertEqual(self.usb.frames[-1], RELAY_OFF); self.assertTrue(self.usb.closed)
    def test_real_pulse_duration_no_busy_wait(self):
        self.store.save(replace(self.config, seconds=1))
        self.usb.on = lambda: None
        start = time.monotonic(); self.submit()
        self.assertGreaterEqual(time.monotonic() - start, 1)
        self.assertLess(time.monotonic() - start, 2.5)
    def test_busy_pulse_does_not_queue_or_extend_opening(self):
        self.usb.on = lambda: None
        self.door.submit(self.result(), 1, BIOMETRIC_METHOD)
        until(lambda: RELAY_ON in self.usb.frames)
        self.assertFalse(self.door.submit(self.result(2), 2, BIOMETRIC_METHOD))
        self.door._cancel.set(); self.finish()
        self.assertEqual(self.usb.frames.count(RELAY_ON), 1)
    def test_cannot_reconfigure_during_pulse(self):
        self.usb.on = lambda: None
        self.door.submit(self.result(), 1, BIOMETRIC_METHOD)
        until(lambda: RELAY_ON in self.usb.frames)
        with self.assertRaises(ValueError): self.door.save_config(DoorConfig())
        self.door.close(); self.assertEqual(self.usb.frames[-1], RELAY_OFF)
    def test_delayed_command_expires_before_any_on(self):
        self.door._execute('access', self.config, (1, self.result()['checkin_at']), self.door.clock()-3, 0)
        self.factory.assert_not_called()
    def test_slow_open_does_not_open_after_expiry(self):
        ticks = [1]
        self.door.clock = lambda: ticks[0]
        def open_slow(_): ticks[0] += 3; return self.usb
        self.door.transport = open_slow
        self.submit(); self.assertNotIn(RELAY_ON, self.usb.frames)
    def test_changed_config_cancels_pending_command(self):
        self.store.save(DoorConfig())
        self.door._execute('access', self.config, (1, self.result()['checkin_at']), self.door.clock(), 0)
        self.factory.assert_not_called()
    def test_corrupted_or_different_gym_config_fails_closed(self):
        self.store.path.write_text('{invalid', encoding='utf-8')
        self.assertFalse(self.submit()); self.factory.assert_not_called()
        self.store.save(self.config)
        self.store.gym_id = 'gym-B'
        self.assertFalse(self.submit()); self.factory.assert_not_called()
    def test_cross_process_ledger_blocks_duplicate(self):
        result = self.result(); self.submit(result)
        self.assertFalse(self.door._claim(1, result['checkin_at']))
        other = DoorController(self.store, transport=self.factory)
        try:
            until(lambda: not other._pending)
            other.submit(result, 1, BIOMETRIC_METHOD)
            until(lambda: not other._pending)
            self.assertEqual(self.usb.frames.count(RELAY_ON), 1)
        finally: other.close()
    def test_equipment_lock_prevents_interleaved_commands(self):
        with equipment_lock(self.temp.name, self.config.port):
            self.submit()
        self.factory.assert_not_called()
    def test_native_callback_only_and_database_response_preserved(self):
        real = Mock(); result = self.result(); real.register_checkin.return_value = result
        proxy = DoorDatabase(real, self.door)
        self.assertIs(proxy.register_checkin(1, BIOMETRIC_METHOD), result)
        self.factory.assert_not_called()
        self.assertIs(proxy.register_fingerprint_checkin(1, BIOMETRIC_METHOD), result)
        self.finish(); self.assertIn(RELAY_ON, self.usb.frames)
        self.assertEqual(real.register_checkin.call_count, 2)
    def test_network_error_no_relay_and_no_retry(self):
        real = Mock(); real.register_checkin.side_effect = TimeoutError('respuesta perdida')
        with self.assertRaises(TimeoutError): DoorDatabase(real, self.door).register_fingerprint_checkin(1, BIOMETRIC_METHOD)
        self.factory.assert_not_called(); real.register_checkin.assert_called_once()
    def test_no_serial_url_and_bounds(self):
        for kwargs in ({'port':'socket://127.0.0.1:1'}, {'port':'COM0'}, {'seconds':0}, {'seconds':11},
                       {'seconds':float('nan')}, {'vid':0x1234}, {'pid':1}):
            with self.assertRaises(ValueError): replace(self.config, **kwargs).validate()
    def test_port_identity_not_reused_for_different_device(self):
        port = dict(port='COM7', vid=0x1A86, pid=0x7523, location='USB-A')
        self.assertTrue(matches_port(self.config, port))
        self.assertFalse(matches_port(self.config, dict(port, location='USB-B')))
        with patch('door_access.available_ports', return_value=[dict(port, vid=1)]), patch('serial.Serial') as serial:
            with self.assertRaises(OSError): open_relay(self.config)
            serial.assert_not_called()
    def test_serial_9600_8n1_bounded_write(self):
        port = dict(port='COM7', vid=0x1A86, pid=0x7523, location='USB-A')
        with patch('door_access.available_ports', return_value=[port]), patch('serial.Serial') as serial:
            open_relay(self.config)
            args = serial.call_args.kwargs
            self.assertEqual((args['baudrate'], args['bytesize'], args['parity'], args['stopbits']), (9600, 8, 'N', 1))
            self.assertLess(args['write_timeout'], 1)


if __name__ == '__main__': unittest.main()
