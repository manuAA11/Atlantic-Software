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


if __name__ == '__main__':
    unittest.main()
