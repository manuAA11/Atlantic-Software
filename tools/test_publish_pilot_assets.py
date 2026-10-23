"""Publication guards with explicitly non-executable installer fixtures."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from tools import test_windows_configuration_delivery as fixtures
from tools.publish_pilot_assets import stage


class PilotAssets(unittest.TestCase):
    def packages(self, folder):
        helper=fixtures.ClientConfigurationDelivery()
        source=Path(folder)/'input';source.mkdir()
        for edition in fixtures.delivery.EDITIONS:
            fixture=helper.fixture(folder,edition)
            with patch.dict(os.environ,{'GITHUB_SHA':'a'*40,'GITHUB_RUN_ID':'123456789'},clear=True):
                fixtures.delivery.create_delivery(fixture['edition'],source)
        return source,fixture['version']

    def publish(self, source, output, version):
        return stage(source,output,version=version,source_commit='a'*40,run_id='123456789',tag='synthetic-pilot')

    def test_only_three_authenticated_client_installers_are_staged(self):
        with tempfile.TemporaryDirectory() as folder:
            source,version=self.packages(folder);output=Path(folder)/'publication'
            result=self.publish(source,output,version)
            self.assertIs(result['final'],False);self.assertEqual(len(result['releases']),3)
            self.assertTrue(all(r['file'].startswith('AtlanticGym_') and 'ZTATTUZ' not in r['file'] for r in result['releases']))
            self.assertEqual({r['architecture'] for r in result['releases']},{'windows-x86','windows-x64'})
            self.assertFalse(any('PROPIETARIO' in p.name or p.suffix=='.zip' for p in output.iterdir()))
            self.assertEqual(json.loads((output/'PILOT_UPDATE_MANIFEST.json').read_text())['source_commit'],'a'*40)
            with self.assertRaisesRegex(ValueError,'sobrescribe'):self.publish(source,output,version)

    def test_missing_architecture_or_wrong_source_commit_blocks_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source,version=self.packages(folder);output=Path(folder)/'publication'
            with self.assertRaisesRegex(ValueError,'commit'):
                stage(source,output,version=version,source_commit='b'*40,run_id='123456789',tag='test')
            self.assertFalse(output.exists())
            next(source.glob('*x86*.zip')).unlink()
            with self.assertRaisesRegex(ValueError,'tres perfiles'):self.publish(source,output,version)
            self.assertFalse(output.exists())

    def test_changed_executable_is_not_published(self):
        with tempfile.TemporaryDirectory() as folder:
            source,version=self.packages(folder);output=Path(folder)/'publication'
            archive=next(source.glob('*.zip'))
            with zipfile.ZipFile(archive) as original:entries={n:original.read(n) for n in original.namelist()}
            executable=next(n for n in entries if n.endswith('.exe'));entries[executable]=b'CORRUPTED NONEXECUTABLE FIXTURE'
            with zipfile.ZipFile(archive,'w') as changed:
                for name,data in entries.items():changed.writestr(name,data)
            with self.assertRaisesRegex(RuntimeError,'SHA256'):self.publish(source,output,version)
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
