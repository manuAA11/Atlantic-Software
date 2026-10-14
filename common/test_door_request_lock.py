"""Slow/stale RPCs never permit a duplicate write or delayed unlock."""
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from door_access import DoorConfig, ConfigStore, DoorController, DoorDatabase, BIOMETRIC_METHOD, RELAY_ON
from test_door_access import FakeUSB, until
from datetime import datetime, timezone

class AccessRequestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=ConfigStore(self.temp.name,'gym-test')
        self.usb=FakeUSB()
        self.transport=Mock(return_value=self.usb)
        self.ticks=10
        self.door=DoorController(self.store,transport=self.transport,clock=lambda:self.ticks,
                                 ports_provider=lambda:[])
        self.usb.on=self.door._cancel.set
        self.store.save(DoorConfig(True,'COM7',3,0x1A86,0x7523))
        self.result=dict(id=1,result='PERMITIDA',checkin_at=datetime.now(timezone.utc).isoformat())
    def tearDown(self):
        self.door.close();self.temp.cleanup()

    def test_slow_confirmed_response_records_once_without_delayed_unlock(self):
        backend=Mock()
        def rpc(*args): self.ticks+=3;return self.result
        backend.register_checkin.side_effect=rpc
        actual=DoorDatabase(backend,self.door).register_fingerprint_checkin(1,BIOMETRIC_METHOD)
        self.assertIs(actual,self.result)
        backend.register_checkin.assert_called_once()
        self.transport.assert_not_called()
        self.assertIn('access_response_expired',(self.store.folder/'puerta.log').read_text())

    def test_backend_exception_releases_inflight_lock_without_opening(self):
        backend=Mock();backend.register_checkin.side_effect=ConnectionError()
        proxy=DoorDatabase(backend,self.door)
        with self.assertRaises(ConnectionError):proxy.register_fingerprint_checkin(1,BIOMETRIC_METHOD)
        # Exceed only the completion debounce; the released OS lock must allow
        # a deliberate later request rather than a permanent pending flag.
        backend.register_checkin.side_effect=None;backend.register_checkin.return_value=self.result
        import time
        with patch('door_access.time.time',return_value=time.time()+2):
            actual=proxy.register_fingerprint_checkin(1,BIOMETRIC_METHOD)
        self.assertIs(actual,self.result)
        until(lambda:not self.door._pending)
        self.assertEqual(backend.register_checkin.call_count,2)
        self.assertEqual(self.usb.frames.count(RELAY_ON),1)

    def test_second_database_instance_cannot_repeat_inflight_rpc(self):
        backend=Mock();entered=threading.Event();proceed=threading.Event()
        results=[];errors=[]
        def rpc(*args):
            entered.set()
            if not proceed.wait(10):raise TimeoutError('Test synchronization')
            return self.result
        backend.register_checkin.side_effect=rpc
        first=DoorDatabase(backend,self.door);second=DoorDatabase(backend,self.door)
        def work():
            try:results.append(first.register_fingerprint_checkin(1,BIOMETRIC_METHOD))
            except BaseException as error:errors.append(error)
        thread=threading.Thread(target=work)
        thread.start()
        try:
            self.assertTrue(entered.wait(10))
            import time
            with patch('door_access.time.time',return_value=time.time()+20):
                duplicate=second.register_fingerprint_checkin(1,BIOMETRIC_METHOD)
            self.assertTrue(duplicate['duplicate_read'])
            self.assertEqual(backend.register_checkin.call_count,1)
        finally:
            proceed.set();thread.join(10)
        self.assertFalse(thread.is_alive());self.assertFalse(errors)
        self.assertEqual(results,[self.result])
        until(lambda:not self.door._pending)

if __name__=='__main__':unittest.main()
