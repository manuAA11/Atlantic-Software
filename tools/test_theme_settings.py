import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from common.theme_settings import load_theme, save_theme

class AppearancePreferences(unittest.TestCase):
    def test_preferences_survive_new_reads_and_reject_unknown_values(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'nested'/'appearance.json'
            self.assertEqual(load_theme(path),'dark')
            for theme in ('minimal','league_light','league_dark','dark'):
                save_theme(theme,path)
                self.assertEqual(load_theme(path),theme)
                self.assertEqual(json.loads(path.read_text()),{'theme':theme})
            with self.assertRaises(ValueError):save_theme('unknown',path)
            self.assertEqual(load_theme(path),'dark')
            for value in ('{invalid','null','[]','{"theme":"unknown"}'):
                path.write_text(value)
                self.assertEqual(load_theme(path),'dark')

    def test_each_edition_reloads_one_shared_saved_theme(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as folder:
            # Redirect the platform's preference root for a fresh process.
            env=dict(os.environ,LOCALAPPDATA=folder,XDG_CONFIG_HOME=folder)
            if sys.platform == 'darwin':
                self.skipTest('macOS preference path uses the real home folder')
            path=Path(folder)/'AtlanticGym'/'appearance.json'
            save_theme('minimal',path)
            for edition in ('GymSoft_Comercial_3.6.0','GymSoft_ZTATTUZ_3.6.1_x86','GymSoft_ZTATTUZ_3.6.1_x64'):
                with self.subTest(edition=edition):
                    result=subprocess.run([sys.executable,'-c',
                        'import atlantic_ui; from common import atlantic_ui as shared; '
                        'assert atlantic_ui is shared; print(shared.THEME,shared.COLORS["background"])'],
                        cwd=root/edition,env=env,capture_output=True,text=True,check=True)
                    self.assertEqual(result.stdout.strip(),'minimal #152338')

    def test_failed_atomic_replace_keeps_previous_preference(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'appearance.json'
            save_theme('dark',path)
            with patch('common.theme_settings.os.replace',side_effect=OSError('disk unavailable')):
                with self.assertRaises(OSError):save_theme('minimal',path)
            self.assertEqual(load_theme(path),'dark')
            self.assertEqual(sorted(x.name for x in path.parent.iterdir()),['appearance.json'])

if __name__=='__main__':unittest.main()
