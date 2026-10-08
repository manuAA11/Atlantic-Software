"""El constructor no debe aceptar PASS si Tk informó un fallo de callback."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import run_validation


class ValidationFailureTest(unittest.TestCase):
    def reject(self, output, exit_code):
        with tempfile.TemporaryDirectory() as folder, patch.object(run_validation,'ROOT',Path(folder)), \
             patch.object(sys,'argv',['run_validation.py','--ui-only']), \
             patch.object(run_validation,'UI_TESTS',('fallo','no_debe_ejecutarse')), \
             contextlib.redirect_stdout(io.StringIO()):
            tests=Path(folder)/'tests';tests.mkdir()
            (tests/'fallo.py').write_text(f'import sys\nprint({output!r})\nsys.exit({exit_code})',encoding='utf-8')
            with self.assertRaises(RuntimeError):run_validation.main()
            report=json.loads((Path(folder)/'salida/validacion/resultado_pruebas.json').read_text(encoding='utf-8'))
            self.assertEqual(report['status'],'FAIL')
            self.assertEqual(report['stages'][0]['status'],'FAIL')
            self.assertEqual(len(report['stages']),1,'No deben continuar otras etapas tras el fallo.')
            self.assertFalse((Path(folder)/'salida/validacion/no_debe_ejecutarse.log').exists())

    def test_nonzero_exit_stops_validation(self):
        self.reject('No se pudo terminar la prueba.\n',1)

    def test_tcl_error_with_zero_exit_is_not_a_pass(self):
        self.reject('invalid command name "callback_resize"\nPASS: prueba terminada.\n',0)


if __name__=='__main__':unittest.main()
