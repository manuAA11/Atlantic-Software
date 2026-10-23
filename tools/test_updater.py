from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock
import zipfile

import httpx
from common.updater import Updater, Release
from common.session_manager import SessionManager, MemorySessionStore

BODY=b'synthetic-executable-bytes'
META=dict(variant='ztattuz',version='3.7.0',architecture='windows-x86',channel='beta',installer_url='https://github.com/manuAA11/Atlantic-Software/releases/download/test/synthetic.exe',sha256=hashlib.sha256(BODY).hexdigest(),bytes=len(BODY),minimum_schema='core-1')


class Updates(unittest.TestCase):
    def setup_updater(self, handler=None, **kwargs):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.root=Path(folder.name)
        http=httpx.Client(transport=httpx.MockTransport(handler or (lambda request:httpx.Response(200,content=BODY))))
        self.addCleanup(http.close)
        self.launcher=Mock()
        return Updater(self.root/'updates','windows-x86','beta','3.6.1',schema_supported=lambda value:value=='core-1',http=http,launcher=self.launcher,**kwargs)

    def release(self, **changes):
        return Release.parse(dict(META,**changes),architecture='windows-x86',channel='beta')

    def test_architecture_checksum_size_and_paths_are_validated(self):
        for changes in ({'variant':'commercial'},{'architecture':'windows-x64'},{'installer_url':'https://evil.invalid/a.exe'},
            {'installer_url':'https://github.com/manuAA11/Atlantic-Software/releases/download/../a.exe'},
            {'version':'../3.7.0'},{'sha256':'not-hash'},{'bytes':True},{'bytes':0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):self.release(**changes)

    def test_version_selection_never_installs_wrong_architecture_or_channel(self):
        updater=self.setup_updater()
        release=updater.select([dict(META,architecture='windows-x64'),dict(META,channel='stable'),META])
        self.assertEqual(release.version,'3.7.0')
        self.assertIsNone(updater.select([dict(META,version='3.6.0')]))
        self.launcher.assert_not_called()

    def test_bad_checksum_deletes_partial_and_manual_retry_succeeds(self):
        count=0
        def handler(request):
            nonlocal count
            count+=1
            return httpx.Response(200,content=b'x'*len(BODY) if count==1 else BODY)
        updater=self.setup_updater(handler);release=self.release()
        with self.assertRaises(ValueError):updater.download(release)
        self.assertFalse(list(updater.journal.folder.glob('*.part')))
        self.assertEqual(updater.journal.value['state'],'UPDATE_FAILED')
        self.assertEqual(updater.download(release).read_bytes(),BODY)
        self.assertEqual(updater.journal.value['state'],'UPDATE_VERIFIED')

    def test_interrupted_download_does_not_leave_installable_file(self):
        def handler(request):raise httpx.ReadError('interrupted')
        updater=self.setup_updater(handler)
        with self.assertRaises(httpx.ReadError):updater.download(self.release())
        self.assertFalse(updater.path(self.release()).exists())
        self.assertFalse(list(updater.journal.folder.glob('*.part')))

    def test_redirect_cannot_escape_controlled_asset_hosts(self):
        updater=self.setup_updater(lambda request:httpx.Response(302,headers={'location':'http://evil.invalid/payload.exe'}))
        with self.assertRaises(ValueError):updater.download(self.release())
        self.launcher.assert_not_called()

    def test_tamper_after_verification_is_rejected_before_launch(self):
        updater=self.setup_updater();release=self.release();updater.download(release)
        with self.assertRaises(RuntimeError):updater.launch()
        updater.path(release).write_bytes(b'tampered')
        with self.assertRaises(ValueError):updater.verify(release,updater.path(release))
        self.launcher.assert_not_called()

    def test_busy_application_is_not_interrupted(self):
        updater=self.setup_updater(busy=lambda:True)
        with self.assertRaises(RuntimeError):updater.prepare(self.release(),[],quiesce=lambda:None)
        self.assertIsNone(updater.journal.value['pending'])

    def test_sqlite_backup_preserves_data_and_encrypted_session_bytes(self):
        updater=self.setup_updater();release=self.release();updater.download(release)
        data=self.root/'GymControl';data.mkdir();(data/'session.dpapi').write_bytes(b'encrypted-synthetic')
        with sqlite3.connect(data/'gymcontrol.db') as db:db.execute('create table important(value text)');db.execute("insert into important values('keep')")
        db.close()
        active=[]
        @contextmanager
        def quiesce():
            active.append(True)
            try:yield
            finally:active.pop()
        backup=updater.prepare(release,[data],quiesce=quiesce)
        self.assertEqual(active,[True])
        with zipfile.ZipFile(backup) as archive:
            self.assertEqual(archive.read('0-GymControl/session.dpapi'),b'encrypted-synthetic')
            restored=self.root/'restored.db';restored.write_bytes(archive.read('0-GymControl/gymcontrol.db'))
        with sqlite3.connect(restored) as db:self.assertEqual(db.execute('select value from important').fetchone(),('keep',))
        db.close()
        updater.launch();self.launcher.assert_called_once_with(updater.path(release))
        self.assertNotEqual(updater.journal.value['state'],'UPDATE_INSTALLED')
        updater.current_version='3.7.0';updater.confirm_started(healthy=True)
        self.assertEqual(updater.journal.value['state'],'UPDATE_INSTALLED')
        updater.cancel();self.assertEqual(active,[])

    def test_quiescence_blocks_new_cloud_requests_and_recovers_on_cancel(self):
        manager=SessionManager(Mock(),MemorySessionStore())
        with manager.quiesce():
            with self.assertRaises(RuntimeError):
                with manager.request():pass
        with manager.request():self.assertEqual(manager.active_requests,1)
        self.assertEqual(manager.active_requests,0)
