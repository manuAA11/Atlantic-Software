"""Reader UI failures must not stop event delivery or replay confirmed access.

These tests run the production poll loop with a deterministic Tk scheduler.
They do not open USB devices or certify a Windows installation.
"""
import queue
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from fingerprint_ui import FingerprintPanel


class Value:
    def __init__(self, value): self.value = value
    def get(self): return self.value
    def set(self, value): self.value = value


class PollRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.panel = p = FingerprintPanel.__new__(FingerprintPanel)
        p.root = SimpleNamespace(after=Mock(return_value='next-poll'), ready=True)
        p.controller = SimpleNamespace(enabled=Value(True))
        p.state = Value('Lector listo.')
        p.service = SimpleNamespace(events=queue.Queue(), pause=Mock(), close=Mock())
        p.ui_events = queue.Queue()
        p.closed = False
        p.window = p.inline_editor = None
        p.enrolling = False
        p.templates = set()
        p.clients = {}
        p.fill = Mock()
        p.show_access = Mock()
        p.show_unrecognized = Mock()
        grab = patch('tk_window_state.grab_path', return_value='')
        self.grab = grab.start()
        self.addCleanup(grab.stop)

    def tearDown(self):
        # Tcl and its variables must be finalized on the creating thread,
        # before an unrelated reader worker can trigger cyclic collection.
        import gc
        self.panel = None
        gc.collect()

    def next_poll(self):
        callback = self.panel.root.after.call_args.args[1]
        callback()

    def test_failed_result_does_not_stop_next_scan_or_replay_access(self):
        p = self.panel
        first = {'result': 'PERMITIDA', 'id': 1}
        second = {'result': 'DENEGADA', 'id': 2}
        p.show_access.side_effect = [RuntimeError('failed to render'), None]
        p.service.events.put(('access', first))
        p.poll()
        p.root.after.assert_called_once()
        p.service.pause.assert_called_with(False)
        p.service.events.put(('access', second))
        self.next_poll()
        self.assertEqual([call.args[0] for call in p.show_access.call_args_list], [first, second])
        self.assertTrue(p.service.events.empty())
        self.assertEqual(p.root.after.call_count, 2)

    def test_failed_template_widget_does_not_block_later_access(self):
        p = self.panel
        p.inline_editor = SimpleNamespace(templates_updated=Mock(side_effect=RuntimeError('closed editor')))
        p.service.events.put(('templates', [1]))
        p.service.events.put(('access', {'result': 'PERMITIDA', 'id': 1}))
        p.poll()
        self.assertEqual(p.templates, {1})
        p.show_access.assert_called_once()
        p.root.after.assert_called_once()

    def test_unrecognized_display_error_still_schedules_another_poll(self):
        p = self.panel
        p.show_unrecognized.side_effect = RuntimeError('failed to render')
        p.service.events.put(('unrecognized', 'Huella no reconocida.'))
        p.poll()
        p.root.after.assert_called_once()
        p.show_access.assert_not_called()

    def test_uncertain_checkin_stays_paused_if_warning_dialog_fails(self):
        p = self.panel
        p.service.events.put(('uncertain', 'Revisa el historial antes de reactivar la lectura.'))
        with patch('fingerprint_ui.messagebox.showwarning', side_effect=RuntimeError('dialog unavailable')):
            p.poll()
        self.assertFalse(p.controller.enabled.get())
        p.service.pause.assert_called_with(True)
        p.root.after.assert_called_once()
        self.next_poll()
        p.service.pause.assert_called_with(True)
        p.show_access.assert_not_called()

    def test_client_list_error_does_not_leave_reader_permanently_paused(self):
        p = self.panel
        p.fill.side_effect = RuntimeError('list unavailable')
        p.ui_events.put(('clients', [{'id': 1}]))
        p.poll()
        p.service.pause.assert_called_with(False)
        p.root.after.assert_called_once()

    def test_pause_check_failure_fails_closed_and_recovers_next_poll(self):
        p = self.panel
        self.grab.side_effect = [RuntimeError('window state unavailable'), '']
        p.poll()
        p.service.pause.assert_called_with(True)
        p.root.after.assert_called_once()
        self.next_poll()
        p.service.pause.assert_called_with(False)

    def test_closed_panel_does_not_process_queued_access(self):
        p = self.panel
        p.closed = True
        p.service.events.put(('access', {'result': 'PERMITIDA'}))
        p.poll()
        p.show_access.assert_not_called()
        p.root.after.assert_not_called()

    def test_destroy_during_event_does_not_reschedule_or_consume_next_access(self):
        p = self.panel
        p.show_access.side_effect = lambda _: setattr(p, 'closed', True)
        p.service.events.put(('access', {'result': 'PERMITIDA', 'id': 1}))
        p.service.events.put(('access', {'result': 'PERMITIDA', 'id': 2}))
        p.poll()
        p.show_access.assert_called_once()
        self.assertEqual(p.service.events.qsize(), 1)
        p.root.after.assert_not_called()

    def test_worker_recovers_ui_with_one_checkin_and_pulse_per_person(self):
        from datetime import datetime, timezone
        import tempfile
        import tkinter as tk
        from door_access import ConfigStore, DoorConfig, DoorController, DoorDatabase, RELAY_ON
        from fingerprint_service import FingerprintService
        from test_fingerprint_service import Reader, Store, T, until
        from test_door_access import FakeUSB

        # Use Tcl's actual after queue, a real worker and the real access/relay
        # wrapper. Only USB, stored templates and the server response are fake.
        p = self.panel
        root = p.root = tk.Tcl()
        root.ready = True
        root.report_callback_exception = Mock()
        p.controller.enabled = tk.BooleanVar(root, True)
        p.state = tk.StringVar(root)
        p.show_access.side_effect = [RuntimeError('render failure after confirmed access'), None]
        second = T + b'second'
        reader = Reader()
        reader.match = lambda sample, templates: [i for i, value in enumerate(templates) if value == sample]
        server = Mock()
        server.register_checkin.side_effect = lambda client, method: dict(
            id=client, result='PERMITIDA', checkin_at=datetime.now(timezone.utc).isoformat())
        with tempfile.TemporaryDirectory() as folder:
            store = ConfigStore(folder, 'poll-recovery-test')
            usb = FakeUSB()
            door = DoorController(store, transport=lambda _: usb, clock=lambda: 10,
                                  ports_provider=lambda: [])
            usb.on = door._cancel.set
            store.save(DoorConfig(True, 'COM7', 3, 0x1A86, 0x7523))
            service = p.service = FingerprintService(
                Store({1: T, 2: second}), DoorDatabase(server, door).register_fingerprint_checkin,
                lambda: reader)
            with patch('fingerprint_service.ReaderLease',
                       return_value=SimpleNamespace(acquire=lambda: True, close=lambda: None)):
                service.start()
                try:
                    until(lambda: service.reader is not None)
                    p.poll()
                    for index, sample in enumerate((T, second), 1):
                        reader.samples.put(sample)
                        def delivered():
                            root.eval('update')
                            return p.show_access.call_count == index and not door._pending
                        until(delivered)
                        self.assertEqual(server.register_checkin.call_count, index)
                        self.assertEqual(usb.frames.count(RELAY_ON), index)
                    self.assertEqual([call.args[0] for call in server.register_checkin.call_args_list], [1, 2])
                    root.report_callback_exception.assert_not_called()
                finally:
                    p.closed = True
                    root.after_cancel(p.job)
                    service.close()
                    service.thread.join(2)
                    door.close()
                self.assertFalse(service.thread.is_alive())


if __name__ == '__main__': unittest.main()
