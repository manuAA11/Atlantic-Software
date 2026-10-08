"""Exercise real environment creation/reuse and preservation, not batch emulation."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preparar_entorno import prepare_environment, runtime_is_supported, valid_environment

BITS = struct.calcsize('P') * 8


class PrepareEnvironmentTests(unittest.TestCase):
    def test_creates_and_reuses_real_environment_in_path_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='Atlantic test ') as directory:
            root = Path(directory)
            self.assertEqual(prepare_environment(root, BITS), 'created')
            self.assertTrue(valid_environment(root / '.venv', BITS))
            marker = root / '.venv' / 'preserve.txt'
            marker.write_text('preserve existing environment')
            self.assertEqual(prepare_environment(root, BITS), 'reused')
            self.assertEqual(marker.read_text(), 'preserve existing environment')
            self.assertFalse(list(root.glob('.venv_respaldo_*')))

    def test_preserves_broken_environment_before_creating_replacement(self):
        with tempfile.TemporaryDirectory(prefix='Atlantic recover ') as directory:
            root = Path(directory)
            (root / '.venv').mkdir()
            (root / '.venv' / 'keep.txt').write_text('old environment data')
            (root / 'gymsoft_config.json').write_text('public configuration')
            self.assertEqual(prepare_environment(root, BITS), 'created')
            backups = list(root.glob('.venv_respaldo_*'))
            self.assertEqual(len(backups), 1)
            self.assertEqual((backups[0] / 'keep.txt').read_text(), 'old environment data')
            self.assertEqual((root / 'gymsoft_config.json').read_text(), 'public configuration')
            self.assertTrue(valid_environment(root / '.venv', BITS))

    def test_wrong_architecture_leaves_existing_files_untouched(self):
        with tempfile.TemporaryDirectory(prefix='Atlantic incompatible ') as directory:
            root = Path(directory)
            (root / '.venv').mkdir()
            marker = root / '.venv' / 'keep.txt'
            marker.write_text('must not move')
            with self.assertRaisesRegex(RuntimeError, 'CPython 3.13 o 3.14'):
                prepare_environment(root, 32 if BITS == 64 else 64)
            self.assertEqual(marker.read_text(), 'must not move')
            self.assertFalse(list(root.glob('.venv_respaldo_*')))

    def test_supported_versions_keep_architecture_and_runtime_constraints(self):
        for version in ((3, 13), (3, 14)):
            for bits in (32, 64):
                with self.subTest(version=version, bits=bits):
                    self.assertTrue(runtime_is_supported(version, bits, bits))
                    self.assertFalse(runtime_is_supported(version, bits, 32 if bits == 64 else 64))
                    self.assertFalse(runtime_is_supported(version, bits, bits, gil_disabled=True))
                    self.assertFalse(runtime_is_supported(version, bits, bits, implementation='pypy'))
        for version in ((2, 7), (3, 12), (3, 15)):
            self.assertFalse(runtime_is_supported(version, BITS, BITS))

    def test_build_accepts_supported_versions_then_enforces_release_gate(self):
        import build_windows
        import os
        from unittest.mock import patch
        cwd = Path.cwd()
        try:
            for version in ((3, 13, 0), (3, 14, 0)):
                with self.subTest(version=version), patch.dict(os.environ), \
                        patch.object(sys, 'platform', 'win32'), \
                        patch.object(sys, 'version_info', version), \
                        patch.object(struct, 'calcsize', return_value=build_windows.EXPECTED_BITS // 8), \
                        patch.object(build_windows.subprocess, 'run') as run:
                    with self.assertRaisesRegex(SystemExit, 'Entrega bloqueada'):
                        build_windows.main()
                    run.assert_not_called()
        finally:
            os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()
