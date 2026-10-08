import base64
import ctypes
import queue
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from fingerprint_service import FingerprintService
from fingerprint_store import CloudTemplateStore
from digitalpersona_native import Device,Status,Params,ImageInfo,Capture,Candidate,NativeReader

T=b'FMR\0'+b'x'*40
class Store:
    def __init__(self,values=None): self.values=dict(values or {}); self.saved=0
    def load(self): return dict(self.values)
    def save(self,values): self.values=dict(values); self.saved+=1
class Reader:
    def __init__(self): self.samples=queue.Queue(); self.hits=[0]; self.added=0; self.closed=False; self.present=False
    def read(self):
        try:return self.samples.get(timeout=.02)
        except queue.Empty:return None
    def match(self,sample,templates):return self.hits if templates else []
    def finger_present(self):return self.present
    def enroll_start(self):self.added=0
    def enroll_add(self,sample):
        self.added+=1
        return T if self.added==3 else None
    def enroll_finish(self):pass
    def close(self):self.closed=True

def until(fn):
    end=time.monotonic()+3
    while not fn():
        if time.monotonic()>end: raise AssertionError('La respuesta simulada no llegó.')
        time.sleep(.01)

class Tests(unittest.TestCase):
    def start(self,values=None,register=None):
        store=Store(values);reader=Reader();calls=[]
        def record(*args): calls.append(args); return {'result':'PERMITIDA'}
        service=FingerprintService(store,register or record,lambda:reader)
        # Reader lease is OS integration; all automated tests use a fake lease, never USB.
        lease=patch('fingerprint_service.ReaderLease',return_value=SimpleNamespace(acquire=lambda:True,close=lambda:None))
        lease.start();self.addCleanup(lease.stop)
        service.start();self.addCleanup(lambda:(service.close(),service.thread.join(2)))
        until(lambda:service._status is not None)
        return service,store,reader,calls
    def test_abi_sizes(self):
        self.assertEqual([ctypes.sizeof(t) for t in (Device,Status,Params,ImageInfo,Capture,Candidate)], [1452,16,16,20,36,12])
    def test_import_never_loads_driver(self):
        with patch('digitalpersona_native.library_directory',side_effect=RuntimeError('not loaded')):
            self.assertTrue(callable(NativeReader))
    def test_known_and_duplicate(self):
        s,store,r,calls=self.start({1:T});r.samples.put(T);until(lambda:len(calls)==1)
        r.samples.put(T);time.sleep(.15);self.assertEqual(len(calls),1)
    def test_unknown(self):
        s,store,r,calls=self.start({1:T});r.hits=[];r.samples.put(T)
        until(lambda:'no reconocida' in s._status);self.assertFalse(calls)
    def test_ambiguous(self):
        s,store,r,calls=self.start({1:T,2:T});r.hits=[0,1];r.samples.put(T)
        until(lambda:'ambigua' in s._status);self.assertFalse(calls)
    def test_paused(self):
        s,store,r,calls=self.start({1:T});s.pause(True);r.samples.put(T)
        time.sleep(.15);self.assertFalse(calls)
    def test_no_repeated_network_write(self):
        calls=[]
        def fail(*args):calls.append(args);raise ConnectionError()
        s,store,r,_=self.start({1:T},fail);r.samples.put(T)
        until(lambda:len(calls)==1 and not s.enabled.is_set())
        r.samples.put(T);time.sleep(.15);self.assertEqual(len(calls),1)
    def test_invalid_checkin_response_pauses_instead_of_crashing_ui(self):
        s,store,r,calls=self.start({1:T},lambda *args:None);r.samples.put(T)
        until(lambda:not s.enabled.is_set())
        events=list(s.events.queue)
        self.assertTrue(any(k=='uncertain' for k,v in events))
        self.assertFalse(any(k=='access' for k,v in events))
    def test_enrollment_three_samples(self):
        s,store,r,calls=self.start();s.send('enroll',9)
        until(lambda:s._status.startswith('Coloca el mismo'))
        for n in range(3):r.samples.put(T);until(lambda:r.added==n+1)
        until(lambda:s.phase=='verify_new');self.assertEqual(store.saved,0)
        r.samples.put(T)
        until(lambda:store.saved==1);self.assertEqual(store.values,{9:T});self.assertFalse(calls)
    def test_enrollment_duplicate_other_client(self):
        s,store,r,calls=self.start({1:T});s.send('enroll',9)
        until(lambda:s._status.startswith('Coloca el mismo'));r.samples.put(T)
        time.sleep(.1);self.assertEqual(store.saved,0);self.assertFalse(calls)
    def test_cancel_keeps_old_template(self):
        s,store,r,calls=self.start({1:T});s.send('enroll',1)
        until(lambda:s._status.startswith('Coloca el mismo'));s.send('cancel');r.samples.put(T)
        time.sleep(.15);self.assertEqual(store.saved,0)
    def test_remote_delete_rechecked_before_match(self):
        s,store,r,calls=self.start({1:T});store.values={};r.samples.put(T)
        until(lambda:'no reconocida' in s._status);self.assertFalse(calls)
    def test_delete(self):
        s,store,r,calls=self.start({1:T});s.send('delete',1)
        until(lambda:store.saved==1);self.assertEqual(store.values,{})
    def test_cloud_no_disk_and_cas(self):
        calls=[]
        class Db:
            gym_id='gym-a'
            def __init__(self):self.client=self
            def rpc(self,name,params):calls.append((name,params));return params
            def _execute(self,query):
                if query['p_action']=='list':return SimpleNamespace(data=[{'client_id':1,'template':base64.b64encode(T).decode(),'revision':'v1'}])
                return SimpleNamespace(data={'saved':True,'revision':'v2'})
        store=CloudTemplateStore(Db());self.assertEqual(store.load(),{1:T})
        store.save({1:T+b'z'})
        self.assertEqual(calls[-1][1]['p_expected'],'v1')
        self.assertEqual(calls[-1][1]['p_gym_id'],'gym-a')
    def test_cloud_changes_single_record(self):
        store=CloudTemplateStore(None)
        with self.assertRaises(ValueError):store.save({1:T,2:T})

if __name__=='__main__':unittest.main()
