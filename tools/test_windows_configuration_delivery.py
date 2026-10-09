"""Portable client ZIP contracts using explicit receipts and non-executable fixtures."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('configuration_delivery', ROOT / 'tools/windows_configuration_delivery.py')
delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery)


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


class ClientConfigurationDelivery(unittest.TestCase):
    def fixture(self, folder, edition_name='GymSoft_Comercial_3.6.0'):
        edition = Path(folder) / edition_name
        edition.mkdir(parents=True)
        # Read the actual edition's declared stage list without executing it.
        for name in ('build_windows.py', 'product_config.py', 'run_validation.py'):
            (edition / name).write_bytes((ROOT / edition_name / name).read_bytes())
        (edition / 'release_readiness.json').write_text('{"unit_fixture":true,"final":false}\n')
        version = delivery.literal_constants(edition / 'product_config.py', ('VERSION',))['VERSION']
        constants = delivery.literal_constants(edition / 'run_validation.py', ('SQL_TESTS', 'UI_TESTS'))
        stage_names = ['python', 'contratos_extraidos', *constants['SQL_TESTS'],
                       'marketing_backend', 'recorrido_huellas', 'simulacion_gimnasio', *constants['UI_TESTS']]
        self.assertEqual(len(stage_names), 37)
        validation = edition / 'salida/validacion'
        validation.mkdir(parents=True)
        stages = []
        logs = []
        for name in stage_names:
            log = validation / (name + '.log')
            log.write_text('UNIT FIXTURE ONLY; NOT A REAL WINDOWS RUN\n', encoding='utf-8')
            stages.append({'name': name, 'status': 'PASS', 'log': log.name,
                           'timed_out': False, 'callback_failure': False})
            logs.append({'path': log.name, 'sha256': delivery.sha256_file(log)})
        suite = {'status': 'PASS', 'version': version, 'scope': 'all', 'platform': 'win32',
                 'started_at': '2026-10-09T19:01:00+00:00', 'stages': stages}
        suite_path = validation / 'resultado_pruebas_all.json'
        write_json(suite_path, suite)
        suite['evidence'] = {'report': str(suite_path), 'sha256': delivery.sha256_file(suite_path), 'logs': logs}
        run_id = '20261009T190000Z-1234'
        qa_root = validation / 'paquete-tecnico/ejecuciones' / run_id
        copies = edition / 'salida/PRUEBAS_PARA_CONFIGURAR' / run_id
        mapping = delivery.expected_configuration_files(edition_name, version)
        files, installers = [], []
        for script, relative in mapping.items():
            data = ('NON-EXECUTABLE UNIT INSTALLER FIXTURE: ' + script).encode('ascii')
            original = qa_root / 'instaladores' / Path(relative).name
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(data)
            copied = copies / relative
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(data)
            checksum = delivery.sha256_file(original)
            files.append({'path': relative, 'sha256': checksum, 'bytes': len(data)})
            installers.append({'script': script, 'status': 'PASS', 'final': False,
                               'sha256': checksum, 'executable': str(original)})
        manifest = {'type': 'INSTALLERS_CONFIGURATION_VALIDATION', 'final': False,
                    'edition': edition_name, 'version': version, 'run_id': run_id,
                    'full_local_validation': suite, 'files': files}
        write_json(copies / 'MANIFIESTO.json', manifest)
        packaged = {'status': 'PASS', 'final': False, 'mode': 'installers',
                    'edition': edition_name, 'version': version, 'run_id': run_id,
                    'release_gate_modified': False, 'full_local_validation': suite,
                    'installers': installers,
                    'configuration_installers': {'directory': str(copies), 'final': False, 'files': files}}
        packaging_path = validation / 'paquete-tecnico/informe_empaquetado.json'
        write_json(packaging_path, packaged)
        installation = {'status': 'PASS', 'final': False, 'edition': edition_name, 'version': version,
                        'scope': 'UNIT FIXTURE technical installation; NO FINAL',
                        'release_gate_modified': False, 'native_windows_architecture': 'x64',
                        'packaging_report_sha256': delivery.sha256_file(packaging_path),
                        'runner': {'environment': 'github-hosted', 'github_run_id': '123456789'},
                        'commands': [], 'installed_executables': [],
                        **{stage: {'status': 'PASS'} for stage in
                           ('fresh_installation', 'runtime', 'shortcuts', 'update', 'cleanup')}}
        if edition_name.endswith('_x86'):
            installation['status'] = 'NOT_RUN'
            installation['reason'] = ('El MSI DigitalPersona x86 exige NOT VersionNT64. '
                                      'El runner Windows x64 no acredita instalación en Windows de 32 bits.')
        installation_path = validation / 'instalacion-tecnica/informe_instalacion.json'
        write_json(installation_path, installation)
        return {'edition': edition, 'version': version, 'suite': suite, 'suite_path': suite_path,
                'copies': copies, 'manifest': manifest, 'packaged': packaged,
                'packaging_path': packaging_path, 'installation': installation,
                'installation_path': installation_path, 'output': Path(folder) / 'entrega'}

    def rewrite_archive(self, archive, replacements=None, additions=None):
        with zipfile.ZipFile(archive) as source:
            entries = {name: source.read(name) for name in source.namelist()}
        entries.update(replacements or {})
        entries.update(additions or {})
        target = archive.with_name('changed-' + archive.name)
        with zipfile.ZipFile(target, 'w') as changed:
            for name, data in entries.items():
                changed.writestr(name, data)
        return target

    def test_three_client_deliveries_exclude_owner_and_components_and_verify_every_file(self):
        for edition_name in delivery.EDITIONS:
            with self.subTest(edition=edition_name), tempfile.TemporaryDirectory() as folder:
                fixture = self.fixture(folder, edition_name)
                acceptance = (fixture['edition'] / 'release_readiness.json').read_bytes()
                with patch.dict(os.environ, {}, clear=True):
                    result = delivery.create_delivery(fixture['edition'], fixture['output'])
                self.assertEqual(result['status'], 'PASS')
                self.assertIs(result['final'], False)
                archive = Path(result['path'])
                self.assertEqual(delivery.verify_delivery(archive), result)
                with zipfile.ZipFile(archive) as package:
                    names = package.namelist()
                    self.assertEqual(len(names), 4)
                    self.assertEqual(len([name for name in names if name.endswith('.exe')]), 1)
                    self.assertFalse(any('PRIVADO' in name or 'COMPONENTES' in name for name in names))
                    manifest = json.loads(package.read(delivery.MANIFEST))
                    self.assertEqual(manifest['local_validation']['stages'], 37)
                    self.assertEqual(manifest['github_run_id'], '123456789')
                    self.assertIs(manifest['release_gate_modified'], False)
                    self.assertEqual(package.read(manifest['files'][0]['path']),
                                     (fixture['copies'] / manifest['files'][0]['path']).read_bytes())
                    readme = package.read(delivery.README).decode('utf-8')
                    self.assertIn('no necesita Python ni Node.js', readme)
                    if edition_name.endswith('_x86'):
                        self.assertEqual(manifest['installation']['status'], 'NOT_RUN')
                        self.assertIn('instalación en Windows de 32 bits sigue pendiente', readme)
                self.assertEqual((fixture['edition'] / 'release_readiness.json').read_bytes(), acceptance)

    def test_changed_copy_or_missing_private_component_blocks_complete_delivery(self):
        for change in ('tamper', 'missing'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                fixture = self.fixture(folder)
                selected = fixture['copies'] / fixture['manifest']['files'][1]['path']
                selected.write_bytes(b'ALTERED') if change == 'tamper' else selected.unlink()
                with patch.dict(os.environ, {}, clear=True), self.assertRaises((RuntimeError, FileNotFoundError)):
                    delivery.create_delivery(fixture['edition'], fixture['output'])
                self.assertFalse(fixture['output'].exists())

    def test_old_installation_report_cannot_accredit_a_new_packaging(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = self.fixture(folder)
            fixture['installation']['packaging_report_sha256'] = '0' * 64
            write_json(fixture['installation_path'], fixture['installation'])
            with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, 'no acredita este empaquetado'):
                delivery.create_delivery(fixture['edition'], fixture['output'])
            self.assertFalse(fixture['output'].exists())

    def test_changed_stage_log_and_partial_suite_are_rejected(self):
        for change in ('log', 'stage'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                fixture = self.fixture(folder)
                if change == 'log':
                    (fixture['suite_path'].parent / 'python.log').write_text('CHANGED')
                else:
                    fixture['suite']['stages'].pop()
                    fixture['packaged']['full_local_validation'] = fixture['suite']
                    write_json(fixture['packaging_path'], fixture['packaged'])
                with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, 'SHA256|37 etapas'):
                    delivery.create_delivery(fixture['edition'], fixture['output'])
                self.assertFalse(fixture['output'].exists())

    def test_x64_failed_installation_or_cleanup_is_not_delivered(self):
        for replacement in ({'status': 'FAIL'}, {'cleanup': {'status': 'FAIL'}}):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as folder:
                fixture = self.fixture(folder)
                fixture['installation'].update(replacement)
                write_json(fixture['installation_path'], fixture['installation'])
                with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, 'instalación, actualización y limpieza'):
                    delivery.create_delivery(fixture['edition'], fixture['output'])
                self.assertFalse(fixture['output'].exists())

    def test_x86_requires_exact_not_run_scope_and_no_installed_programs(self):
        for replacement in ({'status': 'PASS'}, {'reason': 'Skipped'},
                            {'installed_executables': [{'name': 'claimed.exe'}]}):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as folder:
                fixture = self.fixture(folder, 'GymSoft_ZTATTUZ_3.6.1_x86')
                fixture['installation'].update(replacement)
                write_json(fixture['installation_path'], fixture['installation'])
                with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(RuntimeError, 'alcance explícito NOT_RUN'):
                    delivery.create_delivery(fixture['edition'], fixture['output'])
                self.assertFalse(fixture['output'].exists())

    def test_repeated_delivery_does_not_overwrite_existing_zip(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = self.fixture(folder)
            with patch.dict(os.environ, {}, clear=True):
                first = delivery.create_delivery(fixture['edition'], fixture['output'])
                saved = Path(first['path']).read_bytes()
                with self.assertRaisesRegex(RuntimeError, 'no se sobrescribe'):
                    delivery.create_delivery(fixture['edition'], fixture['output'])
            self.assertEqual(Path(first['path']).read_bytes(), saved)

    def test_failed_zip_write_does_not_leave_a_partial_download(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = self.fixture(folder)
            with patch.dict(os.environ, {}, clear=True), patch.object(zipfile.ZipFile, 'write', side_effect=OSError('UNIT simulated disk error')):
                with self.assertRaisesRegex(OSError, 'disk error'):
                    delivery.create_delivery(fixture['edition'], fixture['output'])
            self.assertEqual(list(fixture['output'].iterdir()), [])

    def test_zip_verifier_rejects_changed_installer_unexpected_owner_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = self.fixture(folder)
            with patch.dict(os.environ, {}, clear=True):
                created = delivery.create_delivery(fixture['edition'], fixture['output'])
            archive = Path(created['path'])
            executable = delivery.expected_installer(fixture['edition'].name, fixture['version'])
            changed = self.rewrite_archive(archive, {executable: b'ALTERED INSTALLER'})
            with self.assertRaisesRegex(RuntimeError, 'SHA256 o tamaño incorrecto'):
                delivery.verify_delivery(changed)
            extra_owner = self.rewrite_archive(archive, additions={'PRIVADO_PROPIETARIO.exe': b'PRIVATE FIXTURE'})
            with self.assertRaisesRegex(RuntimeError, 'archivos incompletos o ajenos'):
                delivery.verify_delivery(extra_owner)
            traversal = self.rewrite_archive(archive, additions={'../outside.exe': b'BAD FIXTURE'})
            with self.assertRaisesRegex(RuntimeError, 'rutas o enlaces no autorizados'):
                delivery.verify_delivery(traversal)

    def test_ci_run_identity_must_match_recorded_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = self.fixture(folder)
            with patch.dict(os.environ, {'GITHUB_RUN_ID': '987654321'}, clear=True), self.assertRaisesRegex(RuntimeError, 'otra ejecución'):
                delivery.create_delivery(fixture['edition'], fixture['output'])
            self.assertFalse(fixture['output'].exists())

    def test_verifier_rejects_an_x86_installation_claim_changed_to_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            fixture = self.fixture(folder, 'GymSoft_ZTATTUZ_3.6.1_x86')
            with patch.dict(os.environ, {}, clear=True):
                created = delivery.create_delivery(fixture['edition'], fixture['output'])
            archive = Path(created['path'])
            with zipfile.ZipFile(archive) as source:
                manifest = json.loads(source.read(delivery.MANIFEST))
            manifest['installation']['status'] = 'PASS'
            changed = self.rewrite_archive(archive, {delivery.MANIFEST: json.dumps(manifest).encode('utf-8')})
            with self.assertRaisesRegex(RuntimeError, 'alcance real de sus pruebas'):
                delivery.verify_delivery(changed)

    def test_verifier_cli_returns_failure_without_installing_or_contacting_network(self):
        with tempfile.TemporaryDirectory() as folder:
            broken = Path(folder) / 'broken.zip'
            broken.write_bytes(b'NOT A ZIP')
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(delivery.main(['--verify-delivery', str(broken)]), 1)


if __name__ == '__main__':
    unittest.main()
