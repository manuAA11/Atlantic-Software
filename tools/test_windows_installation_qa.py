"""Portable refusal and integrity tests; these do not accredit Windows installs."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
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

    def runner_context(self):
        return qa.require_ephemeral_runner(self.edition, True, environ=self.env, platform='win32')

    def test_short_installation_roots_are_exclusive_confined_and_separate_from_evidence(self):
        context = self.runner_context()
        first = qa.create_installation_root(context, self.edition)
        second = qa.create_installation_root(context, self.edition)
        self.assertNotEqual(first, second)
        for root in (first, second):
            self.assertEqual(root.parent, self.runner_temp)
            self.assertNotIn(self.workspace, root.parents)
            self.assertLessEqual(len(str(root).encode('utf-16-le')) // 2, 110)
            identity = json.loads((root / qa.INSTALLATION_MARKER).read_text())
            self.assertEqual(identity, qa.installation_identity(context, self.edition))
            self.assertIs(identity['final'], False)
        evidence = self.edition / 'salida/validacion/installation-fixture.log'
        evidence.parent.mkdir(parents=True)
        evidence.write_text('preserve installation evidence')
        (first / 'client').mkdir()
        (first / 'client/runtime.dll').write_bytes(b'owned installation fixture')
        qa.remove_installation_root(first, context, self.edition)
        self.assertFalse(first.exists())
        self.assertTrue(second.exists())
        self.assertEqual(evidence.read_text(), 'preserve installation evidence')

    def test_installation_root_rejects_unvalidated_context_before_mutation(self):
        context = self.runner_context()
        before = sorted(self.runner_temp.iterdir())
        for change in ({'environment': 'self-hosted'}, {'github_run_id': 'not-a-run'}):
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                qa.create_installation_root({**context, **change}, self.edition)
        self.assertEqual(before, sorted(self.runner_temp.iterdir()))

    def test_installation_root_rejects_long_vendor_paths_before_mutation(self):
        long_temp = self.runner_temp / ('long-runner-temp-' + 'x' * 100)
        long_temp.mkdir()
        context = {**self.runner_context(), 'runner_temp': str(long_temp)}
        with self.assertRaisesRegex(RuntimeError, 'demasiado largo'):
            qa.create_installation_root(context, self.edition)
        self.assertEqual(list(long_temp.iterdir()), [])

    def test_cleanup_rejects_other_run_and_modified_identity_without_deleting(self):
        context = self.runner_context()
        root = qa.create_installation_root(context, self.edition)
        with self.assertRaisesRegex(RuntimeError, 'ajena'):
            qa.remove_installation_root(root, {**context, 'github_run_id': '987654'}, self.edition)
        marker = root / qa.INSTALLATION_MARKER
        original = json.loads(marker.read_text())
        marker.write_text(json.dumps({**original, 'edition': 'another installation'}))
        with self.assertRaisesRegex(RuntimeError, 'no pertenece'):
            qa.remove_installation_root(root, context, self.edition)
        self.assertTrue(root.is_dir())
        marker.write_text(json.dumps(original))
        qa.remove_installation_root(root, context, self.edition)
        self.assertFalse(root.exists())

    def test_cleanup_rejects_external_and_nested_targets_before_deleting(self):
        context = self.runner_context()
        root = qa.create_installation_root(context, self.edition)
        nested = root / root.name
        nested.mkdir()
        (nested / qa.INSTALLATION_MARKER).write_text((root / qa.INSTALLATION_MARKER).read_text())
        with self.assertRaisesRegex(RuntimeError, 'ajena'):
            qa.remove_installation_root(nested, context, self.edition)
        outside = self.root / root.name
        outside.mkdir()
        (outside / qa.INSTALLATION_MARKER).write_text((root / qa.INSTALLATION_MARKER).read_text())
        with self.assertRaisesRegex(RuntimeError, 'Ruta fuera'):
            qa.remove_installation_root(outside, context, self.edition)
        self.assertTrue(nested.is_dir())
        self.assertTrue(outside.is_dir())

    def test_cleanup_rejects_linked_root_marker_and_descendants_without_deleting(self):
        context = self.runner_context()
        root = qa.create_installation_root(context, self.edition)
        outside = self.root / 'preserved-customer-installation'
        outside.mkdir()
        data = outside / 'customer.dll'
        data.write_bytes(b'customer installation must survive')
        alias = self.runner_temp / (root.name + '-alias')
        try:
            alias.symlink_to(root, target_is_directory=True)
        except OSError:
            self.skipTest('Symlink creation is unavailable on this test machine.')
        with self.assertRaisesRegex(RuntimeError, 'enlaces'):
            qa.remove_installation_root(alias, context, self.edition)
        alias.unlink()
        original = (root / qa.INSTALLATION_MARKER).read_text()
        external_marker = outside / 'marker.json'
        external_marker.write_text(original)
        marker = root / qa.INSTALLATION_MARKER
        marker.unlink()
        marker.symlink_to(external_marker)
        with self.assertRaises(RuntimeError):
            qa.remove_installation_root(root, context, self.edition)
        marker.unlink()
        marker.write_text(original)
        child = root / 'runtime-link'
        child.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            qa.remove_installation_root(root, context, self.edition)
        self.assertTrue(root.is_dir())
        self.assertEqual(data.read_bytes(), b'customer installation must survive')

    def test_preflight_failure_is_preserved_after_runner_guard_without_installing(self):
        output = io.StringIO()
        with patch.dict(qa.os.environ, self.env, clear=True), patch.object(qa.sys, 'platform', 'win32'), \
                patch.object(qa.subprocess, 'Popen') as process, contextlib.redirect_stdout(output):
            result = qa.main(['--edition', str(self.edition), '--ephemeral-runner'])
        self.assertEqual(result, 1)
        process.assert_not_called()
        path = self.edition / 'salida/validacion/instalacion-tecnica/informe_instalacion.json'
        self.assertTrue(path.is_file())
        report = json.loads(path.read_text())
        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['failed_stage'], 'authenticate_packaging')
        self.assertEqual(report['commands'], [])
        self.assertIs(report['final'], False)
        self.assertEqual(json.loads(output.getvalue()), report)

    def test_metadata_guard_accepts_complete_marker_and_retains_observed_names(self):
        name = 'Atlantic Gym · Validación técnica (no final)'
        table = SimpleNamespace(entries={b'ProductName': name.encode('utf-8')})
        info = SimpleNamespace(StringTable=[table])
        binary = SimpleNamespace(FileInfo=[[info]])
        class Resource:
            def __enter__(self):
                return binary
            def __exit__(self, *args):
                pass
        package = {'installers': [{'script': 'fixture.iss', 'executable': 'fixture.exe'}]}
        rows = []
        with patch.dict(sys.modules, {'pefile': SimpleNamespace(PE=lambda _: Resource())}):
            qa.verify_technical_installer_metadata(package, diagnostics=rows)
        self.assertEqual(rows[0]['status'], 'PASS')
        self.assertEqual(rows[0]['product_names'], [name])

    def test_metadata_guard_rejects_incomplete_marker_without_relaxing_acceptance(self):
        name = 'Atlantic Gym · ZTATTUZ Administrador · Validación técnica (no final)'[:64]
        self.assertNotIn('Validación técnica (no final)', name)
        table = SimpleNamespace(entries={b'ProductName': name.encode('utf-8')})
        info = SimpleNamespace(StringTable=[table])
        binary = SimpleNamespace(FileInfo=[[info]])
        class Resource:
            def __enter__(self):
                return binary
            def __exit__(self, *args):
                pass
        package = {'installers': [{'script': 'fixture.iss', 'executable': 'fixture.exe'}]}
        rows = []
        with patch.dict(sys.modules, {'pefile': SimpleNamespace(PE=lambda _: Resource())}), \
                self.assertRaisesRegex(RuntimeError, 'NO FINAL'):
            qa.verify_technical_installer_metadata(package, diagnostics=rows)
        self.assertEqual(rows[0]['status'], 'FAIL')
        self.assertEqual(rows[0]['product_names'], [name])

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
