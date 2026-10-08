import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import digitalpersona_native as native

class ArchitectureTests(unittest.TestCase):
    def make_pe(self, path, machine):
        path.parent.mkdir(parents=True,exist_ok=True)
        raw=bytearray(80);raw[:2]=b'MZ';struct.pack_into('<I',raw,0x3c,64)
        raw[64:68]=b'PE\0\0';struct.pack_into('<H',raw,68,machine);path.write_bytes(raw)
    def test_each_process_loads_only_matching_pair(self):
        for width, machine in [(4,0x14c),(8,0x8664)]:
            with self.subTest(width=width), tempfile.TemporaryDirectory() as tmp:
                base=Path(tmp);folder=base/'DigitalPersona'
                for name in ('dpfpdd.dll','dpfj.dll'):self.make_pe(folder/name,machine)
                env={k:tmp for k in ('ProgramFiles','ProgramFiles(x86)','ProgramW6432','SystemRoot')}
                with patch.dict(os.environ,env),patch.object(native.sys,'platform','win32'),patch.object(native.struct,'calcsize',return_value=width):
                    self.assertEqual(native.library_directory(),folder)
                    self.make_pe(folder/'dpfj.dll',0x8664 if width==4 else 0x14c)
                    with self.assertRaises(native.NoReader):native.library_directory()
    def test_invalid_or_missing_dll_not_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bad.dll';p.write_bytes(b'not a DLL')
            self.assertIsNone(native.pe_machine(p))
            self.assertIsNone(native.pe_machine(p.with_name('missing.dll')))
    def test_installers_target_native_x64_os(self):
        root=Path(__file__).resolve().parents[1]
        for name in ('admin','recepcion','completo'):
            text=(root/f'instalador_{name}.iss').read_text(encoding='utf-8-sig')
            self.assertIn('ArchitecturesAllowed=x64os',text)
            self.assertIn('ArchitecturesInstallIn64BitMode=x64os',text)

    def test_build_rejects_32_bit_python_before_compiling(self):
        import build_windows
        cwd = Path.cwd()
        try:
            with patch.dict(os.environ), \
                    patch.object(build_windows.sys, 'platform', 'win32'), \
                    patch.object(build_windows.sys, 'version_info', (3, 13, 0)), \
                    patch.object(build_windows.struct, 'calcsize', return_value=4), \
                    patch.object(build_windows.subprocess, 'run') as run:
                with self.assertRaisesRegex(SystemExit, 'CPython 3.13 o 3.14 de 64 bits'):
                    build_windows.main()
                run.assert_not_called()
        finally:
            os.chdir(cwd)
