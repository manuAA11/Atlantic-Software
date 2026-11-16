"""Capture recovery with a scripted sensor; never opens USB or writes real biometric data."""
import queue
import time
import unittest
from unittest.mock import patch
from fingerprint_service import FingerprintService
from digitalpersona_native import BadScan
from test_fingerprint_service import Reader, Store, T


def wait_for(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError('The corrected capture was not processed promptly.')
        time.sleep(.005)


class ScriptedReader(Reader):
    def __init__(self):
        super().__init__()
        self.read_count = 0

    def read(self):
        try:
            item = self.samples.get(timeout=.02)
        except queue.Empty:
            return None
        self.read_count += 1
        if isinstance(item, Exception):
            raise item
        return item


class CaptureRecoveryTests(unittest.TestCase):
    def start_reader(self, values=None):
        reader = ScriptedReader()
        store = Store({1: T} if values is None else values)
        calls = []
        def register(*args):
            calls.append(args)
            return {'result': 'PERMITIDA'}
        lease = patch('fingerprint_service.ReaderLease')
        lease.start().return_value.acquire.return_value = True
        self.addCleanup(lease.stop)
        service = FingerprintService(store, register, lambda: reader)
        service.pause(True)
        self.addCleanup(lambda: (service.close(), service.thread.join(2)))
        service.start()
        wait_for(lambda: service.reader is reader)
        return service, reader, store, calls

    def bad_capture(self, reader):
        reader.samples.put(BadScan('Lectura incompleta (calidad 0x0100). Ajusta el dedo.'))

    def test_adjusting_held_finger_after_bad_capture_can_check_in(self):
        service, reader, store, calls = self.start_reader()
        reader.present = True
        service.pause(False)
        self.bad_capture(reader)
        wait_for(lambda: service._status and 'incompleta' in service._status)
        self.assertFalse(calls)
        reader.samples.put(T)
        wait_for(lambda: len(calls) == 1)
        self.assertFalse(reader.closed)
        self.assertEqual(store.saved, 0)

    def test_repeated_bad_captures_never_check_in_or_reopen_reader(self):
        service, reader, store, calls = self.start_reader()
        reader.present = True
        service.pause(False)
        self.bad_capture(reader)
        self.bad_capture(reader)
        wait_for(lambda: reader.read_count == 2)
        self.assertFalse(calls)
        self.assertFalse(reader.closed)
        reader.samples.put(T)
        wait_for(lambda: len(calls) == 1)
        self.assertEqual(store.saved, 0)

    def test_enrollment_retries_incomplete_capture_without_counting_it(self):
        service, reader, store, calls = self.start_reader({})
        reader.present = True
        service.send('enroll', 9)
        wait_for(lambda: service.phase == 'capture')
        self.bad_capture(reader)
        wait_for(lambda: service._status and 'incompleta' in service._status)
        self.assertEqual(service.samples, 0)
        reader.samples.put(T)
        wait_for(lambda: reader.added == 1)
        self.assertEqual(service.samples, 1)
        self.assertEqual(store.saved, 0)
        self.assertFalse(calls)

    def test_verification_retries_without_saving_or_recording_attendance(self):
        service, reader, store, calls = self.start_reader()
        reader.present = True
        service.send('verify', 1)
        wait_for(lambda: service.phase == 'verify_only')
        self.bad_capture(reader)
        wait_for(lambda: service._status and 'incompleta' in service._status)
        reader.samples.put(T)
        wait_for(lambda: service.target is None)
        self.assertTrue(any(kind == 'enrollment_end' and value['result'] == 'verified'
                            for kind, value in list(service.events.queue)))
        self.assertEqual(store.saved, 0)
        self.assertFalse(calls)

    def test_unknown_fingerprint_after_incomplete_capture_is_still_rejected(self):
        service, reader, store, calls = self.start_reader()
        reader.present = True
        reader.hits = []
        service.pause(False)
        self.bad_capture(reader)
        wait_for(lambda: service._status and 'incompleta' in service._status)
        reader.samples.put(T)
        wait_for(lambda: service._status and 'no reconocida' in service._status)
        self.assertFalse(calls)
        self.assertEqual(store.saved, 0)

    def test_bad_release_probe_preserves_successful_capture_gate(self):
        service, reader, store, calls = self.start_reader()
        service.RELEASE_LIMIT = .05
        reader.present = True
        service.pause(False)
        reader.samples.put(T)
        wait_for(lambda: len(calls) == 1)
        accepted_at = service.release_at
        service.last[1] -= 11
        self.bad_capture(reader)
        wait_for(lambda: service._status and 'incompleta' in service._status)
        self.assertEqual(service.release_at, accepted_at)
        reader.samples.put(T)
        wait_for(lambda: reader.read_count == 3)
        time.sleep(.15)
        self.assertEqual(len(calls), 1)
        self.assertEqual(store.saved, 0)

    def test_close_interrupts_repeated_bad_capture_retries(self):
        service, reader, store, calls = self.start_reader()
        service.pause(False)
        self.bad_capture(reader)
        wait_for(lambda: reader.read_count == 1)
        service.close()
        service.thread.join(.5)
        self.assertFalse(service.thread.is_alive())
        self.assertTrue(reader.closed)
        self.assertFalse(calls)
        self.assertEqual(store.saved, 0)


if __name__ == '__main__':
    unittest.main()
