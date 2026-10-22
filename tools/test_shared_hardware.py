"""Real PE selection and alias identity, without loading vendor libraries."""
import importlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from common import digitalpersona_native as native

ROOT = Path(__file__).resolve().parents[1]


def pe(path, machine):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = bytearray(70)
    data[:2] = b'MZ'
    struct.pack_into('<I', data, 60, 64)
    data[64:68] = b'PE\0\0'
    struct.pack_into('<H', data, 68, machine)
    path.write_bytes(data)


class SharedHardware(unittest.TestCase):
    def test_dll_pair_must_match_process_bitness(self):
        for bits, machine, other in ((32, 0x14c, 0x8664), (64, 0x8664, 0x14c)):
            with self.subTest(bits=bits), tempfile.TemporaryDirectory() as folder:
                base = Path(folder)
                wrong = base/'programs/DigitalPersona/wrong'
                good = base/'programs/DigitalPersona/good'
                pe(wrong/'dpfpdd.dll', machine)
                pe(wrong/'dpfj.dll', other)
                pe(good/'dpfpdd.dll', machine)
                pe(good/'dpfj.dll', machine)
                env = {key: str(base/'programs') for key in ('ProgramFiles', 'ProgramFiles(x86)', 'ProgramW6432')}
                env['SystemRoot'] = str(base/'windows')
                with patch.dict(os.environ, env), patch.object(native.sys, 'platform', 'win32'), patch.object(native.struct, 'calcsize', return_value=bits//8):
                    self.assertEqual(native.library_directory(), good)
                    (good/'dpfj.dll').write_bytes(b'not PE')
                    with self.assertRaises(native.NoReader):
                        native.library_directory()

    def test_edition_aliases_preserve_module_identity_and_monkeypatch(self):
        script = '''import sys
from unittest.mock import patch
import digitalpersona_native as native
import fingerprint_service as worker
import door_access as door
from common import digitalpersona_native, fingerprint_service, door_access
assert native is digitalpersona_native
assert worker is fingerprint_service
assert door is door_access
with patch('digitalpersona_native.library_directory', return_value='patched'):
    assert digitalpersona_native.library_directory() == 'patched'
'''
        for edition in ROOT.glob('GymSoft_*'):
            with self.subTest(edition=edition.name):
                subprocess.run([sys.executable, '-c', script], cwd=edition, check=True, capture_output=True)
