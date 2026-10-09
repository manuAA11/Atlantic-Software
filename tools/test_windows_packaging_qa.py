"""Portable contracts for the Windows packaging QA recipe; no release acceptance."""
import importlib.util
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('windows_packaging_qa', ROOT / 'tools/windows_packaging_qa.py')
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)
EDITIONS = {'GymSoft_Comercial_3.6.0': 64, 'GymSoft_ZTATTUZ_3.6.1_x64': 64,
            'GymSoft_ZTATTUZ_3.6.1_x86': 32}


class PackagingQaContracts(unittest.TestCase):
    def run_edition_script(self, edition, body):
        process = subprocess.run([sys.executable, '-c', body], cwd=ROOT / edition,
                                 text=True, capture_output=True)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)

    def test_production_gate_blocks_before_compilation_for_all_editions(self):
        # Use the actual unaccepted manifests. No flags or evidence are changed.
        for edition in EDITIONS:
            with self.subTest(edition=edition):
                self.run_edition_script(edition, '''
from unittest.mock import patch
import build_windows as build
with patch.object(build, 'require_runtime'), patch.object(build.sys, 'platform', 'win32'), patch.object(build.subprocess, 'run') as command:
    try:
        build.main()
    except SystemExit as error:
        assert 'Entrega bloqueada' in str(error), str(error)
    else:
        raise AssertionError('The actual production gate did not block an unaccepted release.')
    command.assert_not_called()
''')

    def test_recipe_uses_real_entry_points_absolute_resources_and_matching_architecture(self):
        for edition, bits in EDITIONS.items():
            with self.subTest(edition=edition):
                self.run_edition_script(edition, f'''
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
import build_windows as build
assert build.EXPECTED_BITS == {bits}
expected_entries = {{'app.py', 'reception_app.py'}}
if 'Comercial' in build.ROOT.name:
    expected_entries.add('owner_panel.py')
assert {{entry for name, entry in build.EXECUTABLES}} == expected_entries
with TemporaryDirectory() as folder:
    target = Path(folder).resolve()
    with patch.object(build, 'version_file', return_value=target/'version.txt'):
        for name, entry in build.EXECUTABLES:
            command = build.pyinstaller_command(name, entry, dist_root=target/'dist', build_root=target/'build')
            assert command[-1] == str(build.ROOT/entry)
            assert command[command.index('--specpath')+1] == str(target/'build'/'spec')
            assert command[command.index('--distpath')+1] == str(target/'dist')
            role_icon = 'icono_recepcion.ico' if entry == 'reception_app.py' else 'icono.ico'
            assert command[command.index('--icon')+1] == str(build.ROOT/role_icon)
            assert '--windowed' in command and '--onedir' in command
            resources = [command[index+1] for index, arg in enumerate(command) if arg == '--add-data']
            assert resources == [str(build.ROOT/resource)+os.pathsep+'.' for resource in ('gymsoft_config.json', 'icono.ico', 'icono_recepcion.ico')]
            assert 'PIL._tkinter_finder' in command
''')

    def test_wrong_pe_architecture_is_rejected(self):
        for edition, bits in EDITIONS.items():
            with self.subTest(edition=edition):
                self.run_edition_script(edition, f'''
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
import sys
import build_windows as build
binary = MagicMock()
binary.__enter__.return_value = binary
binary.FILE_HEADER.Machine = {0x14c if bits == 64 else 0x8664}
with patch.dict(sys.modules, {{'pefile': SimpleNamespace(PE=MagicMock(return_value=binary))}}):
    try:
        build.verify_executable_architecture(Path('wrong.exe'))
    except RuntimeError as error:
        assert '{bits} bits' in str(error)
    else:
        raise AssertionError('Wrong PE architecture was accepted.')
''')

    def test_corrupt_or_missing_runtime_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            edition = root / 'GymSoft_ZTATTUZ_3.6.1_x86'
            runtime = edition / 'DigitalPersonaRuntime'
            runtime.mkdir(parents=True)
            authority = root / 'docs/vendor/digitalpersona/sdk-manifest.json'
            authority.parent.mkdir(parents=True)
            file = {'path': 'setup.exe', 'bytes': 8, 'sha256': '0' * 64}
            authority.write_text(json.dumps({'runtimes': {'x86': {'files': [file]}},
                                            'license': {'path': 'Licenses/EULA SDK.rtf',
                                                        'bytes': 9, 'sha256': '1' * 64}}))
            with self.assertRaisesRegex(RuntimeError, 'Falta el archivo original'):
                qa.require_runtime_files(edition, 32)
            (runtime / 'setup.exe').write_bytes(b'alterado')
            with self.assertRaisesRegex(RuntimeError, 'Integridad incorrecta'):
                qa.require_runtime_files(edition, 32)

    def test_explicit_mode_is_required(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            qa.main([])
        self.assertEqual(error.exception.code, 2)

    def test_frozen_diagnostic_never_accepts_a_stale_or_failed_report(self):
        for edition in EDITIONS:
            with self.subTest(edition=edition):
                self.run_edition_script(edition, """
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import build_windows as build
with TemporaryDirectory() as folder:
    report = Path(folder)/'diagnostic.json'
    report.write_text(json.dumps({'estado':'OK'}))
    def missing(command, **kwargs):
        assert '--diagnostico' in command and '--sin-red' in command
        assert '--silencioso' in command
        assert command[command.index('--informe')+1] == str(report)
    try:
        build.diagnose_frozen_executable(Path('actual.exe'), report, runner=missing)
    except RuntimeError as error:
        assert 'no generó su informe' in str(error)
    else:
        raise AssertionError('A stale diagnostic was accepted.')
    def failed(command, **kwargs):
        report.write_text(json.dumps({'estado':'REVISAR'}))
    try:
        build.diagnose_frozen_executable(Path('actual.exe'), report, runner=failed)
    except RuntimeError as error:
        assert 'no pasó el diagnóstico' in str(error)
    else:
        raise AssertionError('A failed diagnostic was accepted.')
""")

    def configuration_fixture(self, folder):
        edition = Path(folder) / 'GymSoft_Comercial_3.6.0'
        qa_root = edition / 'salida/validacion/paquete-tecnico/ejecuciones/prueba'
        qa_root.mkdir(parents=True)
        scripts = ('instalador_clientes.iss', 'instalador_propietario.iss')
        entries = (('Admin', 'app.py'), ('Recepcion', 'reception_app.py'), ('Propietario', 'owner_panel.py'))
        build = SimpleNamespace(ROOT=edition, VERSION='3.6.0', INSTALLER_SCRIPTS=scripts, EXECUTABLES=entries)
        report = {'status': 'PASS', 'final': False, 'mode': 'installers',
                  'edition': edition.name, 'version': build.VERSION, 'run_id': '20261008T180000Z-123',
                  'full_local_validation': {'status': 'PASS', 'scope': 'all', 'platform': 'win32',
                                            'version': build.VERSION,
                                            'stages': [{'name': 'fixture', 'status': 'PASS'}]},
                  'executables': [{'entry': entry, 'status': 'PASS', 'diagnostic': {'estado': 'OK'}}
                                  for name, entry in entries], 'installers': []}
        for index, script in enumerate(scripts):
            source = qa_root / f'VALIDACION_NO_FINAL_installer_{index}.exe'
            source.write_bytes(b'TECHNICAL INSTALLER UNIT FIXTURE ' + bytes([index]))
            report['installers'].append({'script': script, 'executable': str(source),
                                         'status': 'PASS', 'final': False, 'sha256': qa.sha256_file(source)})
        return build, report, qa_root

    def test_configuration_publication_validates_hashes_and_separates_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            build, report, qa_root = self.configuration_fixture(folder)
            result = qa.publish_configuration_installers(build, report, qa_root)
            target = Path(result['directory'])
            files = result['files']
            self.assertEqual(len(files), 2)
            self.assertEqual(Path(files[0]['path']).parent, Path('.'))
            self.assertEqual(Path(files[1]['path']).parent, Path('PRIVADO_PROPIETARIO'))
            for item in files:
                self.assertTrue(Path(item['path']).name.startswith('VALIDACION_NO_FINAL_'))
                self.assertEqual(qa.sha256_file(target / item['path']), item['sha256'])
            manifest = (target / 'MANIFIESTO.json').read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'no se sobrescribe'):
                qa.publish_configuration_installers(build, report, qa_root)
            self.assertEqual((target / 'MANIFIESTO.json').read_bytes(), manifest)

    def test_altered_or_missing_installer_does_not_publish(self):
        with tempfile.TemporaryDirectory() as folder:
            build, report, qa_root = self.configuration_fixture(folder)
            Path(report['installers'][1]['executable']).write_bytes(b'ALTERED')
            with self.assertRaisesRegex(RuntimeError, 'alterado'):
                qa.publish_configuration_installers(build, report, qa_root)
            self.assertFalse((build.ROOT / 'salida/PRUEBAS_PARA_CONFIGURAR').exists())
            report['installers'].pop()
            with self.assertRaisesRegex(RuntimeError, 'selección de instaladores está incompleta'):
                qa.publish_configuration_installers(build, report, qa_root)
            self.assertFalse((build.ROOT / 'salida/PRUEBAS_PARA_CONFIGURAR').exists())

    def test_copy_failure_never_publishes_a_partial_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            build, report, qa_root = self.configuration_fixture(folder)
            original_copy = qa.shutil.copyfile
            copied = []
            def failing_copy(source, destination):
                copied.append(source)
                if len(copied) == 2:
                    raise OSError('Simulated disk failure')
                return original_copy(source, destination)
            with patch.object(qa.shutil, 'copyfile', side_effect=failing_copy):
                with self.assertRaisesRegex(OSError, 'disk failure'):
                    qa.publish_configuration_installers(build, report, qa_root)
            target_base = build.ROOT / 'salida/PRUEBAS_PARA_CONFIGURAR'
            self.assertEqual(list(target_base.iterdir()), [])

    def test_configuration_requires_complete_local_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            build, report, qa_root = self.configuration_fixture(folder)
            report['full_local_validation']['status'] = 'FAIL'
            with self.assertRaisesRegex(RuntimeError, 'sin pruebas locales'):
                qa.publish_configuration_installers(build, report, qa_root)
            self.assertFalse((build.ROOT / 'salida/PRUEBAS_PARA_CONFIGURAR').exists())

    def test_configuration_rejects_partial_or_wrong_version_validation_before_copying(self):
        for replacement in ({'scope': 'data'}, {'platform': 'linux'}, {'version': '0.0.0'},
                            {'stages': []}, {'stages': [{'name': 'fixture', 'status': 'FAIL'}]},
                            {'stages': [{'name': 'fixture', 'status': 'PASS', 'timed_out': True}]}):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as folder:
                build, report, qa_root = self.configuration_fixture(folder)
                report['full_local_validation'].update(replacement)
                with patch.object(qa.shutil, 'copyfile') as copy:
                    with self.assertRaisesRegex(RuntimeError, 'sin pruebas locales'):
                        qa.publish_configuration_installers(build, report, qa_root)
                copy.assert_not_called()
                self.assertFalse((build.ROOT / 'salida/PRUEBAS_PARA_CONFIGURAR').exists())

    def test_configuration_rejects_unsafe_run_id_and_duplicate_program(self):
        with tempfile.TemporaryDirectory() as folder:
            build, report, qa_root = self.configuration_fixture(folder)
            report['run_id'] = '../outside'
            with self.assertRaisesRegex(RuntimeError, 'identidad de ejecución inválida'):
                qa.publish_configuration_installers(build, report, qa_root)
            self.assertFalse((build.ROOT / 'salida/PRUEBAS_PARA_CONFIGURAR').exists())
            report['run_id'] = '20261008T180000Z-123'
            report['executables'].append(report['executables'][0])
            with self.assertRaisesRegex(RuntimeError, 'Falta verificar un programa'):
                qa.publish_configuration_installers(build, report, qa_root)
            self.assertFalse((build.ROOT / 'salida/PRUEBAS_PARA_CONFIGURAR').exists())

    def test_configuration_flag_requires_installers(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            qa.main(['--freeze-only', '--para-configurar'])
        self.assertEqual(error.exception.code, 2)

    def test_configuration_validation_rejects_stale_or_partial_suite(self):
        validation = SimpleNamespace(SQL_TESTS=('membership_freezes',), UI_TESTS=('atlantic_branding_ui_smoke',))
        expected = ['python', 'contratos_extraidos', 'membership_freezes', 'marketing_backend',
                    'recorrido_huellas', 'simulacion_gimnasio', 'atlantic_branding_ui_smoke']
        with tempfile.TemporaryDirectory() as folder:
            build = SimpleNamespace(ROOT=Path(folder), VERSION='3.6.0')
            target = build.ROOT / 'salida/validacion'
            target.mkdir(parents=True)
            def suite_report(scope='all', started=None, **changes):
                result = {'version': build.VERSION, 'scope': scope, 'platform': 'win32', 'status': 'PASS',
                          'started_at': started or qa.datetime.now(qa.timezone.utc).isoformat(),
                          'stages': [{'name': name, 'status': 'PASS', 'log': name + '.log'} for name in expected]}
                result.update(changes)
                for stage in result['stages']:
                    (target / stage['log']).write_text('LOCAL UNIT FIXTURE\n')
                (target / 'resultado_pruebas_all.json').write_text(json.dumps(result))
                return subprocess.CompletedProcess([], 0)
            def fresh(command, **kwargs):
                self.assertEqual(command, [sys.executable, str(build.ROOT / 'run_validation.py')])
                self.assertTrue(kwargs['live_output'])
                return suite_report()
            with patch.dict(sys.modules, {'run_validation': validation}), contextlib.redirect_stdout(io.StringIO()):
                result = qa.run_configuration_validation(build, fresh)
                self.assertEqual(result['scope'], 'all')
                self.assertEqual(len(result['evidence']['logs']), len(expected))
                self.assertEqual(result['evidence']['sha256'], qa.sha256_file(target / 'resultado_pruebas_all.json'))
                # A previous successful report is preserved but cannot satisfy
                # a skipped run, even if the replacement command returns zero.
                with self.assertRaisesRegex(RuntimeError, 'no están aprobadas'):
                    qa.run_configuration_validation(build, lambda *args, **kwargs: subprocess.CompletedProcess([], 0))
                with self.assertRaisesRegex(RuntimeError, 'no están aprobadas'):
                    qa.run_configuration_validation(build, lambda *args, **kwargs: suite_report(scope='data'))
                with self.assertRaisesRegex(RuntimeError, 'no están aprobadas'):
                    qa.run_configuration_validation(build, lambda *args, **kwargs: suite_report(started='2000-01-01T00:00:00+00:00'))
                with self.assertRaisesRegex(RuntimeError, 'no están aprobadas'):
                    qa.run_configuration_validation(build, lambda *args, **kwargs: suite_report(started='2999-01-01T00:00:00+00:00'))
                with self.assertRaisesRegex(RuntimeError, 'no están aprobadas'):
                    qa.run_configuration_validation(build, lambda *args, **kwargs: suite_report(stages=[{'name': 'python', 'status': 'PASS', 'log': 'python.log'}]))
                def missing_log(*args, **kwargs):
                    outcome = suite_report()
                    (target / (expected[-1] + '.log')).unlink()
                    return outcome
                with self.assertRaisesRegex(RuntimeError, 'Falta un registro'):
                    qa.run_configuration_validation(build, missing_log)
                with self.assertRaisesRegex(RuntimeError, 'no terminó correctamente'):
                    qa.run_configuration_validation(build, lambda *args, **kwargs: subprocess.CompletedProcess([], 1))


if __name__ == '__main__':
    unittest.main()
