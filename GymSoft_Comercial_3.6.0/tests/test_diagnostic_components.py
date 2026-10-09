"""El modo de diagnóstico permite comprobar el paquete sin usar cuentas ni red."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
import diagnostico
import owner_panel
import reception_app
import runtime_cloud


class DiagnosticComponentsTests(unittest.TestCase):
    def test_correct_windows_architecture_is_accepted(self):
        with patch.object(sys, 'platform', 'win32'), \
                patch.object(sys, 'getwindowsversion',
                             return_value=SimpleNamespace(major=10, minor=0, build=26300), create=True), \
                patch.object(diagnostico.struct, 'calcsize', return_value=8):
            self.assertIn('proceso de 64 bits', diagnostico.check_system())

    def test_other_process_architecture_is_rejected(self):
        with patch.object(sys, 'platform', 'win32'), \
                patch.object(sys, 'getwindowsversion',
                             return_value=SimpleNamespace(major=10, minor=0, build=26300), create=True), \
                patch.object(diagnostico.struct, 'calcsize', return_value=4):
            with self.assertRaisesRegex(RuntimeError, '64 bits'):
                diagnostico.check_system()

    def test_old_windows_is_rejected(self):
        with patch.object(sys, 'platform', 'win32'), \
                patch.object(sys, 'getwindowsversion',
                             return_value=SimpleNamespace(major=6, minor=3, build=9600), create=True), \
                patch.object(diagnostico.struct, 'calcsize', return_value=8):
            with self.assertRaisesRegex(RuntimeError, 'Windows 10'):
                diagnostico.check_system()

    def test_development_platform_is_not_reported_as_windows(self):
        with patch.object(sys, 'platform', 'linux'):
            self.assertEqual(diagnostico.check_system(), 'Entorno de desarrollo linux')

    def test_data_directory_uses_existing_commercial_storage(self):
        with tempfile.TemporaryDirectory() as temporary:
            for platform, variable in (('win32', 'LOCALAPPDATA'), ('linux', 'XDG_DATA_HOME')):
                with self.subTest(platform=platform), patch.object(sys, 'platform', platform), \
                        patch.dict(os.environ, {variable: temporary}):
                    self.assertEqual(diagnostico.data_directory(), Path(temporary) / 'GymSoft')

    def test_each_entry_point_diagnoses_without_starting_app_or_cloud(self):
        with tempfile.TemporaryDirectory() as temporary:
            for module, constructor in ((app, 'GymSoftApp'), (reception_app, 'ReceptionApp'),
                                        (owner_panel, 'OwnerPanel')):
                report_path = Path(temporary) / module.__name__ / 'diagnostico.json'
                with self.subTest(entry_point=module.__name__), \
                        patch.object(sys, 'argv', [module.__name__, '--diagnostico', '--sin-red',
                                                  '--silencioso', '--informe', str(report_path)]), \
                        patch.object(diagnostico, 'data_directory', return_value=Path(temporary) / 'GymSoft'), \
                        patch.object(diagnostico, 'check_interface', return_value='Interfaz fuera de esta prueba'), \
                        patch.object(module, constructor) as create_app, \
                        patch.object(runtime_cloud, 'CloudService') as create_cloud, \
                        patch('urllib.request.urlopen', side_effect=AssertionError('Red prohibida')) as request:
                    with self.assertRaises(SystemExit) as outcome:
                        module.main()
                    self.assertEqual(outcome.exception.code, 0)
                    create_app.assert_not_called()
                    create_cloud.assert_not_called()
                    request.assert_not_called()
                    report = json.loads(report_path.read_text(encoding='utf-8'))
                    self.assertEqual(report['estado'], 'OK')
                    self.assertEqual(len(report['comprobaciones']), 5)
                    self.assertIn('no incluye relé', report['alcance'])
                    config = diagnostico.load_config()
                    self.assertNotIn(config['supabase_publishable_key'], report_path.read_text(encoding='utf-8'))

    def test_component_failure_is_reported_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / 'fallo.json'
            with patch.object(sys, 'argv', ['diagnostico', '--sin-red', '--silencioso',
                                           '--informe', str(report_path)]), \
                    patch.object(diagnostico, 'data_directory', return_value=Path(temporary)), \
                    patch.object(diagnostico, 'check_interface', side_effect=FileNotFoundError('icono.ico')):
                self.assertEqual(diagnostico.main(), 1)
            report = json.loads(report_path.read_text(encoding='utf-8'))
            self.assertEqual(report['estado'], 'REVISAR')
            errors = [check for check in report['comprobaciones'] if check['estado'] == 'ERROR']
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]['comprobacion'], 'Interfaz')


if __name__ == '__main__':
    unittest.main()
