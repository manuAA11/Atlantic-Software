from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import diagnostico


class DiagnosticArchitectureTests(unittest.TestCase):
    def test_correct_windows_architecture_is_accepted(self):
        with patch.object(sys, 'platform', 'win32'), \
                patch.object(sys, 'getwindowsversion', return_value=SimpleNamespace(major=10, minor=0, build=26300), create=True), \
                patch.object(diagnostico.struct, 'calcsize', return_value=diagnostico.EXPECTED_BITS // 8):
            self.assertIn(f'proceso de {diagnostico.EXPECTED_BITS} bits', diagnostico.check_system())

    def test_other_process_architecture_is_rejected(self):
        with patch.object(sys, 'platform', 'win32'), \
                patch.object(sys, 'getwindowsversion', return_value=SimpleNamespace(major=10, minor=0, build=26300), create=True), \
                patch.object(diagnostico.struct, 'calcsize', return_value=4 if diagnostico.EXPECTED_BITS == 64 else 8):
            with self.assertRaisesRegex(RuntimeError, f'{diagnostico.EXPECTED_BITS} bits'):
                diagnostico.check_system()

    def test_old_windows_is_rejected(self):
        with patch.object(sys, 'platform', 'win32'), \
                patch.object(sys, 'getwindowsversion', return_value=SimpleNamespace(major=6, minor=3, build=9600), create=True), \
                patch.object(diagnostico.struct, 'calcsize', return_value=diagnostico.EXPECTED_BITS // 8):
            with self.assertRaisesRegex(RuntimeError, 'Windows 10'):
                diagnostico.check_system()

    def test_development_platform_is_not_reported_as_windows(self):
        with patch.object(sys, 'platform', 'linux'):
            self.assertEqual(diagnostico.check_system(), 'Entorno de desarrollo linux')


if __name__ == '__main__':
    unittest.main()
