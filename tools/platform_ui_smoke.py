"""Real Tk platform controls with synthetic service responses, no account or hardware."""
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import httpx
import tkinter as tk
from tkinter import ttk

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'GymSoft_Comercial_3.6.0'))
from desktop_ui import configure_dark_styles
from owner_panel import OwnerPanel
from common.core_admin_ui import CoreAdmin
from common.platform_ui import SystemPanel, application_busy, other_windows_apps
from common.session_ui import SessionStatus
from common.updater import Updater


def settle(root):
    end=time.monotonic()+.25
    while time.monotonic()<end:root.update();time.sleep(.01)


def main():
    checks=0
    with tempfile.TemporaryDirectory() as temporary:
        for scale in (1,1.25):
            root=tk.Tk();callback_errors=[]
            root.report_callback_exception=lambda *error:callback_errors.append(error)
            root.tk.call('tk','scaling',96/72*scale);root.geometry('1100x800')
            configure_dark_styles(root);root.ready=True;root.pages={};root._foreground_io=False
            cloud=NS(role='admin',gym_id='synthetic-gym',sessions=NS(state='ONLINE'))
            core=NS(cloud=cloud,architecture='windows-x64',device_id='a'*64,state='CORE_OFFLINE',
                snapshot={'configuration':{'update_channel':'beta'},'notifications':[dict(id='synthetic-notification',title='Aviso de prueba',message='Synthetic only',type='INFO',read_at=None)],'releases':[]},
                sync=Mock(),grace_state=lambda:'WITHIN_GRACE')
            updater=Updater(Path(temporary)/str(scale),'windows-x64','beta','3.7.0',schema_supported=lambda _:True,variant='commercial',http=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(503))))
            control=NS(root=root,core=core,updater=updater,info=dict(build_date='synthetic',commit='synthetic-commit'))
            panel=SystemPanel(control);settle(root)
            assert panel.notifications.get_children()==('synthetic-notification',);checks+=1
            assert str(panel.update_button.cget('state'))=='disabled';checks+=1
            assert not application_busy(root,panel);checks+=1
            root._foreground_io=True;assert application_busy(root,panel);checks+=1;root._foreground_io=False
            root.pages={'store':NS(pos=NS(cart=NS(rows={1:{}}),pending=None,inventory_pending=None))}
            assert application_busy(root,panel);checks+=1;root.pages={}
            panel.destroy()
            status=SessionStatus(root,cloud)
            def poll_status(state):
                if status.job:root.after_cancel(status.job);status.job=None
                cloud.sessions.state=state;status.poll()
            poll_status('OFFLINE');settle(root)
            assert status.frame.winfo_manager()=='pack';checks+=1
            poll_status('AUTH_REQUIRED');assert status.button.cget('text')=='Iniciar sesión';checks+=1
            poll_status('ONLINE');assert not status.frame.winfo_manager();checks+=1
            status.closed=True
            if status.job:root.after_cancel(status.job);status.job=None
            status.frame.destroy()
            row=dict(gym_id='synthetic-gym',source_project_ref='syntheticprojectref0',product_variant='ztattuz',name='Synthetic Gym',status='ACTIVE',license_status='ACTIVE',
                price=200000,currency='COP',renewal_day=19,next_renewal_date='2026-10-19',last_payment=None,devices=0,configuration={'update_channel':'beta'})
            root.cloud=NS(client=Mock());root.busy=False
            root.table=lambda parent,columns,height:OwnerPanel.table(root,parent,columns,height)
            root.run=lambda operation,done:(done(operation()),True)[1]
            root.cloud.client.rpc.return_value.execute.return_value.data=[row]
            owner=CoreAdmin(root);settle(root)
            assert owner.tree.get_children()==('synthetic-gym',);checks+=1
            for widget in owner.viewport.body.winfo_children():
                for child in widget.winfo_children():
                    if isinstance(child,ttk.Button) and child.winfo_ismapped():
                        assert child.winfo_x()>=0 and child.winfo_x()+child.winfo_width()<=widget.winfo_width()+2,child.cget('text');checks+=1
            owner.destroy();settle(root)
            assert not callback_errors,callback_errors;checks+=1
            root.destroy();updater.http.close()
    assert isinstance(other_windows_apps(),list);checks+=1
    print(f'PLATFORM UI {checks} CHECKS PASS: actual Tk 100/125%, Core owner list, session state, no modal loops, POS/critical gating; synthetic network only.')

if __name__=='__main__':main()
