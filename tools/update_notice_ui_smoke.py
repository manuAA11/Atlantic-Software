"""Visible update notice, synthetic releases, no download or installation."""
from pathlib import Path
import sys
import tempfile
import httpx
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import tkinter as tk
from tkinter import ttk

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'GymSoft_Comercial_3.6.0'));sys.path.insert(0,str(ROOT))
from common.platform_ui import PlatformControls
from common.updater import Updater
from desktop_ui import configure_dark_styles


def main():
    with tempfile.TemporaryDirectory() as folder:
        root=tk.Tk();configure_dark_styles(root)
        control=PlatformControls.__new__(PlatformControls)
        control.root=root;control.button=ttk.Button(root);control.button.pack()
        control.update_notice=ttk.Frame(root);control.notice_button=ttk.Button(control.update_notice);control.notice_button.pack()
        release=dict(id='synthetic',product='Atlantic Gym',variant='commercial',version='9.0.0',architecture='windows-x64',channel='stable',
            installer_url='https://github.com/manuAA11/Atlantic-Software/releases/download/test/synthetic.exe',
            bytes=1,sha256='a'*64,minimum_schema='core-1',policy='OPTIONAL')
        control.core=NS(cloud=NS(role='admin'),snapshot={'configuration':{'update_channel':'stable'},'notifications':[],'releases':[release]})
        control.updater=Updater(Path(folder),'windows-x64','beta','3.7.0',schema_supported=lambda _:True,variant='commercial',http=httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(503))))
        control._release_identity=None;control.available_release=None
        def poll():
            control.poll();root.after_cancel(control.job);root.update()
        poll()
        assert control.update_notice.winfo_manager()=='pack'
        assert control.notice_button.cget('text')=='Actualizar a 9.0.0'
        history=len(control.updater.journal.value['history']);poll()
        assert len(control.updater.journal.value['history'])==history
        panel=NS(after_idle=Mock(),update=Mock())
        with patch.object(control,'open',return_value=panel):
            control.open_update();panel.after_idle.assert_called_once_with(panel.update)
            panel.after_idle.reset_mock();control.core.cloud.role='receptionist';poll()
            assert control.notice_button.cget('text')=='Ver versión 9.0.0'
            control.open_update();panel.after_idle.assert_not_called()
        control.core.snapshot['releases']=[dict(release,architecture='windows-x86')];poll()
        assert not control.update_notice.winfo_manager()
        root.destroy();control.updater.http.close()
    print('PASS: visible update notice, role/architecture/channel guards, direct user action and no automatic install.')


if __name__=='__main__':main()
