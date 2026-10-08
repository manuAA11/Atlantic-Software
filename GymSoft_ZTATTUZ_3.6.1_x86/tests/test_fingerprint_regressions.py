"""Device-free regressions at the native ABI, worker and persistence boundaries."""
import ctypes as C
import queue
import time
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from digitalpersona_native import NativeReader, Status, Params, Capture, U, P, MORE, FMD, FID, ReaderError, ReaderBusy, BadScan
from fingerprint_service import FingerprintService
from fingerprint_store import CloudTemplateStore
from test_fingerprint_service import Store, Reader, T, until


class NativeTests(unittest.TestCase):
    def reader(self):
        r=NativeReader.__new__(NativeReader);r.handle=P(1)
        def status(h,s):s.contents.status=0;s.contents.finger=0;return 0
        r.status=status
        def extract(fmt,data,n,out,result,size):
            C.memmove(result,T,len(T));C.cast(size,C.POINTER(U))[0]=len(T);return 0
        r.extract=extract
        return r
    def capture(self,r,*,rc=0,success=1,quality=0):
        calls=[]
        def fn(handle,params,timeout,result,length,image):
            args=C.cast(params,C.POINTER(Params)).contents
            self.assertEqual((args.format,args.processing,args.resolution),(FID,0,500))
            self.assertGreaterEqual(timeout,3000)
            output=C.cast(result,C.POINTER(Capture)).contents
            self.assertEqual((output.size,output.info.size),(36,20))
            output.success=success;output.quality=quality
            C.cast(length,C.POINTER(U))[0]=32;C.memmove(image,b'SENSITIVE_IMAGE'+b'x'*18,32)
            calls.append(image);return rc
        r.capture=fn
        return calls
    def test_status_reallocates_vendor_data(self):
        r=self.reader();sizes=[]
        def status(h,p):
            sizes.append(p.contents.size)
            if len(sizes)==1:p.contents.size=64;return MORE
            self.assertEqual(p.contents.size,64);p.contents.status=0;p.contents.finger=1;return 0
        r.status=status
        self.assertTrue(r.finger_present());self.assertEqual(sizes,[16,64])
    def test_invalid_driver_buffer_rejected(self):
        r=self.reader()
        def status(h,p):p.contents.size=2**32-1;return MORE
        r.status=status
        with self.assertRaises(ReaderError):r.finger_present()
    def test_capture_clears_raw_image(self):
        r=self.reader();images=self.capture(r)
        self.assertEqual(r.read(),T);self.assertEqual(images[0].raw,b'\0'*len(images[0]))
    def test_capture_failure_clears_image(self):
        r=self.reader();images=self.capture(r,rc=0x05BA001F)
        with self.assertRaises(ReaderError):r.read()
        self.assertFalse(any(images[0].raw))
    def test_idle_timeout_not_disconnection(self):
        r=self.reader();self.capture(r,success=0,quality=1);self.assertIsNone(r.read())
    def test_busy_is_transient(self):
        r=self.reader();self.capture(r,rc=0x05BA001E)
        with self.assertRaises(ReaderBusy):r.read()
    def test_calibration_before_capture(self):
        r=self.reader();sequence=[]
        def status(h,s):s.contents.status=2;return 0
        r.status=status;r.calibrate=lambda h:sequence.append('calibrated') or 0;self.capture(r)
        self.assertEqual(r.read(),T);self.assertEqual(sequence,['calibrated'])
    def test_quality_report_preserves_code(self):
        r=self.reader();self.capture(r,success=0,quality=0x100)
        with self.assertRaisesRegex(BadScan,'0x0100'):r.read()
    def test_sdk_more_samples_is_not_failure(self):
        r=self.reader();r.add=lambda *a:MORE
        self.assertIsNone(r.enroll_add(T))
    def test_create_enrollment_uses_sdk_output_length(self):
        r=self.reader();r.add=lambda *a:0
        def create(result,size):C.memmove(result,T,len(T));C.cast(size,C.POINTER(U))[0]=len(T);return 0
        r.create=create;self.assertEqual(r.enroll_add(T),T)
    def test_identify_passes_actual_fmd_lengths_and_candidates(self):
        r=self.reader()
        def identify(fmt,data,n,view,fmt2,count,values,sizes,threshold,out_count,candidates):
            self.assertEqual((fmt,fmt2,n,view,count),(FMD,FMD,len(T),0,2))
            self.assertEqual(list(sizes),[len(T),len(T)+1])
            self.assertEqual(C.string_at(values[0],sizes[0]),T)
            candidates[0].index=1;C.cast(out_count,C.POINTER(U))[0]=1;return 0
        r.identify=identify;self.assertEqual(r.match(T,[T,T+b'y']),[1])


class ServiceTests(unittest.TestCase):
    def start(self,store=None,reader=None):
        self.store=store or Store();self.reader=reader or Reader();self.calls=[]
        def register(*args):self.calls.append(args);return {'result':'PERMITIDA'}
        self.service=FingerprintService(self.store,register,lambda:self.reader)
        self.service.RELEASE_LIMIT=.05;self.service.pause(True)
        lease=patch('fingerprint_service.ReaderLease',return_value=SimpleNamespace(acquire=lambda:True,close=lambda:None))
        lease.start();self.addCleanup(lease.stop)
        self.service.start();self.addCleanup(lambda:(self.service.close(),self.service.thread.join(2)))
        until(lambda:self.service.reader is not None)
    def enroll(self):
        self.service.send('enroll',9);until(lambda:self.service.phase=='capture')
        for n in range(3):self.reader.samples.put(T);until(lambda:self.reader.added==n+1)
        until(lambda:self.service.phase=='verify_new')
    def results(self):
        result=[]
        while not self.service.events.empty():
            k,v=self.service.events.get_nowait()
            if k=='enrollment_end':result.append(v)
        return result
    def test_cloud_verified_before_success_and_no_attendance(self):
        self.start();self.enroll();self.assertEqual(self.store.saved,0);self.assertFalse(self.results())
        self.reader.samples.put(T);until(lambda:self.service.target is None)
        self.assertEqual(self.results()[0]['result'],'saved');self.assertEqual(self.store.values,{9:T});self.assertFalse(self.calls)
    def test_bad_final_sample_does_not_save(self):
        self.start();self.enroll();self.reader.hits=[];self.reader.samples.put(T)
        until(lambda:'no coincide' in self.service._status)
        self.assertFalse(self.store.saved);self.assertFalse(self.results())
    def test_stale_finger_flag_no_longer_stalls(self):
        self.start();self.reader.present=True;self.enroll();self.reader.samples.put(T)
        until(lambda:self.service.target is None);self.assertEqual(self.store.saved,1)
    def test_cancel_before_verification_keeps_previous(self):
        self.start(Store({9:T+b'old'}));self.enroll();self.service.send('cancel')
        until(lambda:self.service.target is None);self.assertEqual(self.store.values,{9:T+b'old'});self.assertEqual(self.results()[0]['result'],'cancelled')
    def test_lost_write_ack_is_read_back_without_second_write(self):
        class Lost(Store):
            def save(self,values):super().save(values);raise ConnectionError('ACK')
        self.start(Lost());self.enroll();self.reader.samples.put(T);until(lambda:self.service.target is None)
        self.assertEqual(self.store.saved,1);self.assertEqual(self.results()[0]['result'],'saved')
    def test_unconfirmed_save_has_no_success(self):
        class Discard(Store):
            def save(self,values):self.saved+=1
        self.start(Discard());self.enroll();self.reader.samples.put(T);until(lambda:self.service.target is None)
        self.assertEqual(self.results()[0]['result'],'failed');self.assertFalse(self.store.values)
    def test_network_loss_after_write_never_claims_success(self):
        class Lost(Store):
            def load(self):
                if self.saved:raise ConnectionError('offline')
                return super().load()
        self.start(Lost());self.enroll();self.reader.samples.put(T);until(lambda:self.service.target is None)
        self.assertEqual(self.results()[0]['result'],'failed');self.assertEqual(self.store.saved,1)
    def test_another_computer_change_not_overwritten(self):
        self.start();self.enroll();self.store.values[9]=T+b'other';self.reader.samples.put(T);until(lambda:self.service.target is None)
        self.assertFalse(self.store.saved);self.assertEqual(self.store.values[9],T+b'other')
    def test_another_computer_registers_same_finger(self):
        self.start();self.enroll();self.store.values[8]=T;self.reader.samples.put(T);until(lambda:self.service.target is None)
        self.assertFalse(self.store.saved);self.assertEqual(self.results()[0]['result'],'failed')
    def test_verify_registered_finger_never_records_attendance(self):
        self.start(Store({9:T}));self.service.send('verify',9);until(lambda:self.service.phase=='verify_only')
        self.reader.samples.put(T);until(lambda:self.service.target is None)
        self.assertEqual(self.results()[0]['result'],'verified');self.assertFalse(self.calls);self.assertFalse(self.store.saved)
    def test_timeout_unfreezes_editor(self):
        self.start();self.service.ENROLLMENT_SECONDS=.05;self.service.send('enroll',9)
        until(lambda:self.service._status and 'a tiempo' in self.service._status)
        self.assertEqual(self.results()[0]['result'],'failed');self.assertFalse(self.store.saved)
    def test_native_error_keeps_diagnostic_not_fake_disconnect(self):
        self.start();self.enroll()
        self.reader.read=lambda:(_ for _ in ()).throw(ReaderError('Capturar huella: 0x05BA0014'))
        until(lambda:self.service.target is None)
        self.assertIn('0x05BA0014',self.results()[0]['message'])
    def test_finished_enrollment_then_global_checkin_once(self):
        self.start();self.enroll();self.reader.samples.put(T);until(lambda:self.service.target is None)
        self.service.pause(False);self.reader.samples.put(T);until(lambda:len(self.calls)==1)
        self.reader.samples.put(T);time.sleep(.15);self.assertEqual(len(self.calls),1)
    def test_delete_confirmed_by_read(self):
        self.start(Store({9:T}));self.service.send('delete',9)
        until(lambda:self.store.saved==1);self.assertFalse(self.store.values)
    def test_held_finger_does_not_repeat_after_cooldown(self):
        self.start(Store({9:T}));self.reader.present=True;self.service.pause(False)
        self.reader.samples.put(T);until(lambda:len(self.calls)==1)
        self.service.last[9]-=11
        self.reader.samples.put(T);time.sleep(.17)
        self.assertEqual(len(self.calls),1)
    def test_cloud_failure_does_not_close_usb_reader(self):
        class Failing(Store):
            def save(self,value):raise ConnectionError('offline')
        self.start(Failing());self.enroll();self.reader.samples.put(T);until(lambda:self.service.target is None)
        self.assertFalse(self.reader.closed);self.assertEqual(self.results()[0]['result'],'failed')

if __name__=='__main__':unittest.main()
