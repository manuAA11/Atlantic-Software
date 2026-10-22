"""Device-free SDK boundary for exercising the real NativeReader.

Only DLL loading is substituted. Production enumeration, capture parameters,
enrollment, identification, worker and persistence paths still execute.
Equality matching here is synthetic; it does not measure biometric accuracy.
"""
from contextlib import contextmanager
import ctypes as C
from pathlib import Path
import queue
from types import SimpleNamespace
from unittest.mock import patch

import digitalpersona_native as native


class FakeSDK:
    def __init__(self, products=('U.are.U 5160 Fingerprint Reader',), open_error=0):
        self.products = products
        self.open_error = open_error
        self.samples = queue.Queue()
        self.added = self.exits = self.closes = self.directory_closes = 0
        self.opened = []
        self.enrolled = None
        self.loaded = []
        self.capture_lib = SimpleNamespace()
        self.match_lib = SimpleNamespace()
        for name, method in {
            'dpfpdd_init': lambda: 0, 'dpfpdd_exit': self.exit,
            'dpfpdd_query_devices': self.query, 'dpfpdd_open_ext': self.open,
            'dpfpdd_close': self.close, 'dpfpdd_get_device_status': self.status,
            'dpfpdd_calibrate': lambda handle: 0, 'dpfpdd_capture': self.capture,
        }.items():
            setattr(self.capture_lib, name, self.function(method))
        for name, method in {
            'dpfj_create_fmd_from_fid': self.extract, 'dpfj_identify': self.identify,
            'dpfj_start_enrollment': self.start, 'dpfj_add_to_enrollment': self.add,
            'dpfj_create_enrollment_fmd': self.create,
            'dpfj_finish_enrollment': lambda: 0,
        }.items():
            setattr(self.match_lib, name, self.function(method))

    @staticmethod
    def function(method):
        # NativeReader binds argtypes/restype on the callable, just like ctypes.
        def call(*args):
            return method(*args)
        return call

    @staticmethod
    def size(pointer):
        return C.cast(pointer, C.POINTER(native.U))

    def query(self, count, devices):
        n = self.size(count)
        if devices is None:
            n[0] = len(self.products)
            return native.MORE if self.products else 0
        assert n[0] >= len(self.products)
        for index, product in enumerate(self.products):
            assert devices[index].size == C.sizeof(native.Device)
            devices[index].name = f'fake-reader-{index}'.encode()
            devices[index].descr.vendor = b'DigitalPersona, Inc.'
            devices[index].descr.product = product.encode()
        n[0] = len(self.products)
        return 0

    def open(self, name, priority, handle):
        assert priority == 4  # SDK exclusive capture; shared process lease too.
        self.opened.append(name)
        if not self.open_error:
            C.cast(handle, C.POINTER(native.P))[0] = native.P(1)
        return self.open_error

    def close(self, handle):
        self.closes += 1
        return 0

    def exit(self):
        self.exits += 1
        return 0

    def close_directory(self):
        self.directory_closes += 1

    def status(self, handle, status):
        assert status.contents.size >= C.sizeof(native.Status)
        status.contents.status = 0
        status.contents.finger = 0
        return 0

    def capture(self, handle, params, timeout, result, length, image):
        p = C.cast(params, C.POINTER(native.Params)).contents
        assert (p.format, p.processing, p.resolution) == (native.FID, 0, 500)
        assert timeout == 4000
        result = C.cast(result, C.POINTER(native.Capture)).contents
        assert result.size == C.sizeof(native.Capture)
        assert result.info.size == C.sizeof(native.ImageInfo)
        try:
            sample = self.samples.get(timeout=.02)
        except queue.Empty:
            result.success = 0
            result.quality = 1  # SDK capture timeout, not a broken reader.
            return 0
        assert len(sample) <= self.size(length)[0]
        C.memmove(image, sample, len(sample))
        self.size(length)[0] = len(sample)
        result.success = 1
        result.quality = 0
        return 0

    def extract(self, fmt, image, length, output_fmt, output, size):
        assert (fmt, output_fmt) == (native.FID, native.FMD)
        assert length <= self.size(size)[0]
        C.memmove(output, image, length)
        self.size(size)[0] = length
        return 0

    def identify(self, fmt, data, length, view, template_fmt, count,
                 templates, sizes, threshold, result_count, candidates):
        assert (fmt, view, template_fmt) == (native.FMD, 0, native.FMD)
        assert threshold == 0x7fffffff // 100000
        sample = C.string_at(data, length)
        hits = [i for i in range(count) if C.string_at(templates[i], sizes[i]) == sample]
        hits = hits[:self.size(result_count)[0]]
        for pos, index in enumerate(hits):
            assert candidates[pos].size == C.sizeof(native.Candidate)
            candidates[pos].index = index
            candidates[pos].view = 0
        self.size(result_count)[0] = len(hits)
        return 0

    def start(self, fmt):
        assert fmt == native.FMD
        self.added = 0
        self.enrolled = None
        return 0

    def add(self, fmt, sample, length, view):
        assert (fmt, view) == (native.FMD, 0)
        self.added += 1
        self.enrolled = C.string_at(sample, length)
        return 0 if self.added >= 3 else native.MORE

    def create(self, output, size):
        assert self.added >= 3 and len(self.enrolled) <= self.size(size)[0]
        C.memmove(output, self.enrolled, len(self.enrolled))
        self.size(size)[0] = len(self.enrolled)
        return 0

    def load(self, path):
        name = Path(path).name
        self.loaded.append(name)
        assert name in ('dpfpdd.dll', 'dpfj.dll'), name
        return self.capture_lib if name == 'dpfpdd.dll' else self.match_lib

    @contextmanager
    def installed(self):
        # No registry, physical USB device or real DLL is consulted in tests.
        with patch.object(native, 'library_directory', return_value=Path('fake-sdk')), \
                patch.object(native.os, 'add_dll_directory', create=True,
                             return_value=SimpleNamespace(close=self.close_directory)), \
                patch.object(native.C, 'WinDLL', create=True, side_effect=self.load):
            yield self
