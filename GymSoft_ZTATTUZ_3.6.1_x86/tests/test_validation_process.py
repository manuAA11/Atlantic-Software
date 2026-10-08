"""Subprocesos reales: un bloqueo o un error nunca cuentan como PASS."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from validation_process import run_stage


class ValidationProcessTests(unittest.TestCase):
    def run_script(self, code, *, timeout=3):
        self.output = []
        with tempfile.TemporaryDirectory() as folder:
            return run_stage([sys.executable, '-u', '-c', code], cwd=folder,
                             env=dict(os.environ, PYTHONIOENCODING='utf-8'), name='regresión',
                             emit=self.output.append, timeout=timeout, heartbeat=.1)

    def test_success_preserves_output(self):
        result = self.run_script("print('PASS: huella registrada')")
        self.assertEqual(result.returncode, 0)
        self.assertIn('huella registrada', ''.join(self.output))

    def test_nonzero_is_failure(self):
        self.assertEqual(self.run_script('raise SystemExit(7)').returncode, 7)

    def test_callback_error_is_failure_even_with_zero_exit(self):
        result = self.run_script("print('Exception in Tkinter callback'); print('PASS')")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(result.callback_failure)

    def test_silent_block_is_stopped_and_reports_progress(self):
        result = self.run_script('import time; time.sleep(30)', timeout=.35)
        self.assertTrue(result.timed_out)
        self.assertNotEqual(result.returncode, 0)
        self.assertLess(result.seconds, 6)
        self.assertIn('EN CURSO:', ''.join(self.output))

    def test_partial_line_does_not_block_deadline(self):
        result = self.run_script("import sys,time; sys.stdout.write('último paso'); sys.stdout.flush(); time.sleep(30)", timeout=.35)
        self.assertTrue(result.timed_out)
        self.assertIn('último paso', ''.join(self.output))

    def test_infinite_output_does_not_reset_deadline(self):
        result = self.run_script("import time\nwhile True:\n print('trabajando'); time.sleep(.01)", timeout=.35)
        self.assertTrue(result.timed_out)
        self.assertNotEqual(result.returncode, 0)

    def test_deadline_cannot_be_disabled(self):
        with self.assertRaises(ValueError): self.run_script('pass', timeout=0)


if __name__ == '__main__': unittest.main()
