"""Portable refusal and integrity tests; these do not accredit Windows installs."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location('windows_installation_qa',
                                             Path(__file__).with_name('windows_installation_qa.py'))
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


class InstallationQaGuards(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.workspace = self.root / 'checkout'
        self.workspace.mkdir()
        self.edition = self.workspace / 'GymSoft_Comercial_3.6.0'
        self.edition.mkdir()
        (self.edition / 'build_windows.py').write_text('# original build')
        self.runner_temp = self.root / 'runner-temp'
        self.runner_temp.mkdir()
        self.env = {'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
                    'RUNNER_OS': 'Windows', 'GITHUB_RUN_ID': '123456',
                    'GITHUB_WORKSPACE': str(self.workspace), 'RUNNER_TEMP': str(self.runner_temp)}

    def tearDown(self):
        self.temporary.cleanup()

    def make_report(self):
        validation = self.edition / 'salida/validacion'
        source = validation / 'paquete-tecnico/ejecuciones/20261009T030000Z-12/instaladores'
        source.mkdir(parents=True)
        exe = source / 'VALIDACION_NO_FINAL_cliente.exe'
        exe.write_bytes(b'installer fixture; not executable')
        item = {'script': 'instalador_clientes.iss', 'executable': str(exe),
                'sha256': hashlib.sha256(exe.read_bytes()).hexdigest(), 'status': 'PASS', 'final': False}
        report = {'status': 'PASS', 'final': False, 'mode': 'installers',
                  'edition': self.edition.name, 'run_id': '20261009T030000Z-12',
                  'installers': [item], 'executables': []}
        path = validation / 'paquete-tecnico/informe_empaquetado.json'
        path.write_text(json.dumps(report))
        return path, report, exe

    def test_refusal_never_creates_outputs_or_starts_a_process(self):
        before = sorted(str(path.relative_to(self.root)) for path in self.root.rglob('*'))
        output = io.StringIO()
        with patch.object(qa.subprocess, 'Popen') as process, contextlib.redirect_stdout(output):
            result = qa.main(['--edition', str(self.edition)])
        self.assertEqual(result, 1)
        process.assert_not_called()
        report = json.loads(output.getvalue())
        self.assertEqual(report['status'], 'FAIL')
        self.assertIs(report['final'], False)
        self.assertEqual(report['commands'], [])
        self.assertEqual(before, sorted(str(path.relative_to(self.root)) for path in self.root.rglob('*')))

    def test_only_explicit_hosted_windows_checkout_is_accepted(self):
        self.assertEqual(qa.require_ephemeral_runner(self.edition, True, environ=self.env,
                                                     platform='win32')['github_run_id'], '123456')
        changes = [{'GITHUB_ACTIONS': 'false'}, {'RUNNER_ENVIRONMENT': 'self-hosted'},
                   {'RUNNER_OS': 'Linux'}, {'GITHUB_RUN_ID': ''},
                   {'RUNNER_TEMP': str(self.workspace)}, {'GITHUB_WORKSPACE': str(self.root)}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                qa.require_ephemeral_runner(self.edition, True, environ={**self.env, **change}, platform='win32')
        with self.assertRaises(RuntimeError):
            qa.require_ephemeral_runner(self.edition, False, environ=self.env, platform='win32')

    def test_authentication_rejects_changed_bytes(self):
        path, report, exe = self.make_report()
        loaded, loaded_path = qa.load_technical_report(self.edition)
        self.assertEqual(loaded_path, path)
        self.assertEqual(loaded['installers'][0]['sha256'], report['installers'][0]['sha256'])
        exe.write_bytes(b'changed after packaging')
        with self.assertRaisesRegex(RuntimeError, 'SHA256 incorrecto'):
            qa.load_technical_report(self.edition)

    def test_authentication_rejects_external_paths_even_with_matching_hash(self):
        path, report, exe = self.make_report()
        external = self.root / 'external.exe'
        external.write_bytes(exe.read_bytes())
        report['installers'][0]['executable'] = str(external)
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(RuntimeError, 'Ruta fuera'):
            qa.load_technical_report(self.edition)

    def test_authentication_rejects_final_or_incomplete_packages(self):
        path, report, exe = self.make_report()
        for change in ({'status': 'FAIL'}, {'final': True}, {'mode': 'freeze-only'}):
            path.write_text(json.dumps({**report, **change}))
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                qa.load_technical_report(self.edition)

    def test_symlink_inside_validation_is_rejected(self):
        root = self.root / 'validation'
        root.mkdir()
        original = root / 'original.exe'
        original.write_bytes(b'fixture')
        alias = root / 'alias.exe'
        try:
            alias.symlink_to(original)
        except OSError:
            self.skipTest('Symlink creation is unavailable on this test machine.')
        with self.assertRaisesRegex(RuntimeError, 'enlaces'):
            qa.confined_path(alias, root, require_file=True)

    def test_registry_validation_rejects_external_cleanup_targets(self):
        installed = self.root / 'technical/client'
        installed.mkdir(parents=True)
        uninstaller = installed / 'unins000.exe'
        uninstaller.write_bytes(b'fixture')
        row = {'role': 'client', 'hive': 'HKCU', 'view': 0, 'key': 'fixture',
               'display_name': 'Atlantic Gym · Validación técnica (no final)',
               'install_location': str(installed), 'uninstall_command': '"' + str(uninstaller) + '"'}
        qa.validate_registered_apps([row], {'client': installed})
        outside = self.root / 'customer/unins000.exe'
        outside.parent.mkdir()
        outside.write_bytes(b'fixture')
        row['uninstall_command'] = '"' + str(outside) + '"'
        with self.assertRaisesRegex(RuntimeError, 'Ruta fuera'):
            qa.validate_registered_apps([row], {'client': installed})

    def test_registry_validation_rejects_duplicate_registrations(self):
        installed = self.root / 'technical/client'
        installed.mkdir(parents=True)
        uninstaller = installed / 'unins000.exe'
        uninstaller.write_bytes(b'fixture')
        row = {'role': 'client', 'hive': 'HKCU', 'view': 0, 'key': 'fixture',
               'display_name': 'Atlantic Gym · Validación técnica (no final)',
               'install_location': str(installed), 'uninstall_command': '"' + str(uninstaller) + '"'}
        with self.assertRaisesRegex(RuntimeError, 'duplicados'):
            qa.validate_registered_apps([row, {**row, 'hive': 'HKLM', 'view': 64}], {'client': installed})


if __name__ == '__main__':
    unittest.main()
