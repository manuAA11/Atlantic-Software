"""Native ABI adapter for DigitalPersona Biometric SDK 3.4 (Windows x86/x64).
ABI declarations checked against the supplied dpfpdd.h and dpfj.h.
No device or DLL is accessed at import time. No SDK sample source is copied.
"""
import ctypes as C
import os
from pathlib import Path
import re
import struct
import sys

U = C.c_uint32
P = C.c_void_p
MORE = 0x05BA000D
FMD = 0x001B0001
FID = 0x001B0401
SUPPORTED_READERS = ('4500', '5160')

def supported_reader_model(product):
    """Allow only enabled model numbers reported by the DigitalPersona SDK."""
    if isinstance(product, bytes):
        product = product.decode('utf-8', errors='replace')
    match = re.search(r'(?<!\d)(' + '|'.join(SUPPORTED_READERS) + r')(?!\d)', product)
    return match.group(1) if match else None

class ReaderError(RuntimeError): pass
class NoReader(ReaderError): pass
class BadScan(ReaderError): pass
class ReaderBusy(ReaderError): pass

class Version(C.Structure):
    _fields_ = [('major', C.c_int32), ('minor', C.c_int32), ('maintenance', C.c_int32)]
class HardwareVersion(C.Structure):
    _fields_ = [('hw', Version), ('fw', Version), ('bcd', C.c_uint16)]
class Description(C.Structure):
    _fields_ = [('vendor', C.c_char*128), ('product', C.c_char*128), ('serial', C.c_char*128)]
class HardwareId(C.Structure):
    _fields_ = [('vendor', C.c_uint16), ('product', C.c_uint16)]
class Device(C.Structure):
    _fields_ = [('size', U), ('name', C.c_char*1024), ('descr', Description),
                ('id', HardwareId), ('ver', HardwareVersion), ('modality', U), ('technology', U)]
class Status(C.Structure):
    _fields_ = [('size', U), ('status', U), ('finger', C.c_int32), ('data', C.c_ubyte*1)]
class Params(C.Structure):
    _fields_ = [('size', U), ('format', U), ('processing', U), ('resolution', U)]
class ImageInfo(C.Structure):
    _fields_ = [('size', U), ('width', U), ('height', U), ('resolution', U), ('bpp', U)]
class Capture(C.Structure):
    _fields_ = [('size', U), ('success', C.c_int32), ('quality', U), ('score', U), ('info', ImageInfo)]
class Candidate(C.Structure):
    _fields_ = [('size', U), ('index', U), ('view', U)]

def check(code, operation):
    if code:
        raise ReaderError(f'{operation}: código del lector 0x{code & 0xffffffff:08X}.')

def pe_machine(path):
    """Read the PE architecture without executing a library."""
    try:
        with Path(path).open('rb') as f:
            if f.read(2) != b'MZ': return None
            f.seek(0x3c); offset = int.from_bytes(f.read(4), 'little')
            f.seek(offset)
            if f.read(4) != b'PE\0\0': return None
            return int.from_bytes(f.read(2), 'little')
    except OSError:
        return None

def library_directory():
    if sys.platform != 'win32':
        raise NoReader('El lector requiere Windows.')
    bits = struct.calcsize('P') * 8
    expected = 0x14c if bits == 32 else 0x8664
    roots = [Path(os.environ.get(key, r'C:\Program Files'))
             for key in ('ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432')]
    candidates = []
    for root in dict.fromkeys(roots):
        for vendor in ('DigitalPersona', 'HID Global', 'HID'):
            folder = root/vendor
            if folder.exists(): candidates.extend(folder.rglob('dpfpdd.dll'))
    windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
    if bits == 32: candidates.append(windows/'SysWOW64'/'dpfpdd.dll')
    candidates.append(windows/'System32'/'dpfpdd.dll')
    for dll in candidates:
        if (pe_machine(dll) == expected and
                pe_machine(dll.with_name('dpfj.dll')) == expected):
            return dll.parent
    raise NoReader(f'Falta DigitalPersona Runtime de {bits} bits. Usa «Instalar controlador» en Huellas.')

class NativeReader:
    """All methods must be used by one worker thread, including enrollment."""
    def __init__(self):
        self.handle = P()
        self.model = None
        directory = library_directory()
        self._directory_handle = os.add_dll_directory(str(directory))
        self.capture_lib = C.WinDLL(str(directory/'dpfpdd.dll'))
        self.match_lib = C.WinDLL(str(directory/'dpfj.dll'))
        def bind(lib, name, args):
            fn = getattr(lib, name); fn.argtypes = args; fn.restype = C.c_int32
            return fn
        self.init = bind(self.capture_lib, 'dpfpdd_init', [])
        self.exit = bind(self.capture_lib, 'dpfpdd_exit', [])
        self.query = bind(self.capture_lib, 'dpfpdd_query_devices', [C.POINTER(U), C.POINTER(Device)])
        self.open = bind(self.capture_lib, 'dpfpdd_open_ext', [C.c_char_p, U, C.POINTER(P)])
        self._close = bind(self.capture_lib, 'dpfpdd_close', [P])
        self.status = bind(self.capture_lib, 'dpfpdd_get_device_status', [P, C.POINTER(Status)])
        self.calibrate = bind(self.capture_lib, 'dpfpdd_calibrate', [P])
        self.capture = bind(self.capture_lib, 'dpfpdd_capture', [P,C.POINTER(Params),U,C.POINTER(Capture),C.POINTER(U),P])
        self.extract = bind(self.match_lib, 'dpfj_create_fmd_from_fid', [C.c_int32,P,U,C.c_int32,P,C.POINTER(U)])
        self.identify = bind(self.match_lib, 'dpfj_identify', [C.c_int32,P,U,U,C.c_int32,U,C.POINTER(P),C.POINTER(U),U,C.POINTER(U),C.POINTER(Candidate)])
        self.start = bind(self.match_lib, 'dpfj_start_enrollment', [C.c_int32])
        self.add = bind(self.match_lib, 'dpfj_add_to_enrollment', [C.c_int32,P,U,U])
        self.create = bind(self.match_lib, 'dpfj_create_enrollment_fmd', [P,C.POINTER(U)])
        self.finish = bind(self.match_lib, 'dpfj_finish_enrollment', [])
        self.initialized = False
        check(self.init(), 'Inicialización'); self.initialized = True
        try:
            n = U(0); rc = self.query(C.byref(n), None)
            if rc not in (0, MORE): check(rc, 'Detectar lector')
            if not n.value: raise NoReader('Conecta el DigitalPersona U.are.U 4500 o 5160 a un puerto USB.')
            devices = (Device*n.value)()
            for device in devices: device.size = C.sizeof(Device)
            check(self.query(C.byref(n), devices), 'Detectar lector')
            supported = [d for d in devices[:n.value] if supported_reader_model(d.descr.product)]
            if not supported: raise NoReader('No se detectó un DigitalPersona U.are.U 4500 o 5160 compatible. Comprueba el controlador del lector.')
            check(self.open(supported[0].name, 4, C.byref(self.handle)), 'Abrir lector; cierra otras aplicaciones que lo utilicen')
            self.model = supported_reader_model(supported[0].descr.product)
        except Exception:
            self.close(); raise

    def close(self):
        if self.handle.value:
            self._close(self.handle); self.handle = P()
        if getattr(self, 'initialized', False): self.exit(); self.initialized = False
        if getattr(self, '_directory_handle', None):
            self._directory_handle.close(); self._directory_handle = None

    def device_status(self):
        # DPFPDD_DEV_STATUS ends in variable vendor data. Its C sizeof is only
        # the minimum, not necessarily the allocation required by the driver.
        length = C.sizeof(Status)
        for _ in range(3):
            buffer = C.create_string_buffer(length)
            status = C.cast(buffer, C.POINTER(Status))
            status.contents.size = length
            rc = self.status(self.handle, status)
            if rc != MORE:
                check(rc, 'Consultar lector')
                return status.contents.status, bool(status.contents.finger)
            requested = status.contents.size
            if not length < requested <= 65536:
                raise ReaderError('El controlador devolvió un tamaño de estado no válido.')
            length = requested
        raise ReaderError('No se pudo consultar el estado completo del lector.')

    def finger_present(self):
        state, present = self.device_status()
        if state == 3: raise ReaderError('El lector necesita reconectarse.')
        return present

    def read(self):
        state, _ = self.device_status()
        if state == 1: raise ReaderBusy('El lector está ocupado. Espera un momento.')
        if state == 2: check(self.calibrate(self.handle), 'Calibrar lector')
        if state == 3: raise ReaderError('El lector necesita reconectarse.')
        params = Params(C.sizeof(Params), FID, 0, 500)
        result = Capture(); result.size = C.sizeof(result); result.info.size = C.sizeof(ImageInfo)
        image = C.create_string_buffer(2*1024*1024); length = U(len(image))
        try:
            # Capture must have time to acquire a stable image. This blocks only
            # the reader worker; Tk remains responsive. Cancel is bounded by 4 s.
            rc = self.capture(self.handle,C.byref(params),4000,C.byref(result),C.byref(length),image)
            if rc == 0x05BA001E: raise ReaderBusy('El lector está ocupado. Espera un momento.')
            check(rc, 'Capturar huella')
            if not result.success:
                if result.quality & 3: return None
                raise BadScan(f'Lectura incompleta (calidad 0x{result.quality:04X}). Retira el dedo y apoya su yema en el centro.')
            if not 0 < length.value <= len(image):
                raise ReaderError('El controlador devolvió una imagen de tamaño no válido.')
            fmd = C.create_string_buffer(4096); size = U(len(fmd))
            rc = self.extract(FID,image,length.value,FMD,fmd,C.byref(size))
            if rc: raise BadScan(f'No se extrajo una huella clara (0x{rc & 0xffffffff:08X}). Retira el dedo y vuelve a intentarlo.')
            if not 30 <= size.value <= len(fmd) or not fmd.raw.startswith(b'FMR\0'):
                raise ReaderError('El lector no devolvió una plantilla ANSI válida.')
            return fmd.raw[:size.value]
        finally:
            C.memset(image, 0, len(image))

    def match(self, sample, templates):
        if not templates: return []
        values = [C.create_string_buffer(value) for value in templates]
        pointers = (P*len(values))(*(C.cast(value,P).value for value in values))
        sizes = (U*len(values))(*(len(value) for value in templates))
        count = U(min(2,len(values)))
        candidates = (Candidate*count.value)()
        for candidate in candidates: candidate.size = C.sizeof(Candidate)
        data = C.create_string_buffer(sample)
        check(self.identify(FMD,data,len(sample),0,FMD,len(values),pointers,sizes,
                            0x7fffffff//100000,C.byref(count),candidates), 'Identificar huella')
        return sorted(set(candidates[i].index for i in range(count.value)))

    def enroll_start(self): check(self.start(FMD), 'Iniciar registro')
    def enroll_add(self, sample):
        data = C.create_string_buffer(sample)
        rc = self.add(FMD,data,len(sample),0)
        if rc == MORE: return None
        check(rc, 'Registrar muestra')
        data = C.create_string_buffer(4096); n = U(len(data))
        check(self.create(data,C.byref(n)), 'Crear huella')
        return data.raw[:n.value]
    def enroll_finish(self): check(self.finish(), 'Finalizar registro')
