"""Real Tk controls and local dates, without accounts, USB or external providers."""
from copy import deepcopy
from pathlib import Path
import os
import sys
from types import SimpleNamespace as NS
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from membership_freeze_ui import FreezeManager
from desktop_ui import Modal, configure_dark_styles
from ui_assertions import pump, assert_exposed, destroy_root

def descendants(widget):
    for w in widget.winfo_children():
        yield w
        yield from descendants(w)

class Fixture:
    def __init__(self,role):
        self.gym_id='gym';self.cloud=NS(role=role,timezone='America/Bogota');self.client=self;self.calls=[]
        self.info={'membership':{'membership_id':1,'plan_id':2,'plan_name':'Mensual','membership_end':'2026-10-20',
             'status':'AL DÍA','allowed':True,'can_freeze':True,'frozen':False},
             'policy':{'enabled':True,'duration_days':7,'max_per_membership':1},'history':[]}
    def rpc(self,name,args):return (name,args)
    def _execute(self,query):
        name,args=query
        if name=='membership_freeze_info':return NS(data=deepcopy(self.info))
        self.calls.append((name,args))
        if name=='membership_freeze':
            f={'id':'freeze','start_date':'2026-10-08','resume_date':'2026-10-15','days_added':7,'days_reversed':0,
               'status':'ACTIVE','created_at':'2026-10-08T14:00:00Z'}
            self.info['membership'].update(status='FROZEN',frozen=True,allowed=False,can_freeze=False,
                membership_end='2026-10-27',freeze_last_date='2026-10-14',resume_date='2026-10-15',freeze=f)
            self.info['history']=[f]
        return NS(data={})

def main():
    checks=0
    for factor in (1,1.25):
        for role in ('admin','receptionist'):
            root=tk.Tk();root.tk.call('tk','scaling',96/72*factor);root.geometry('1100x780')
            configure_dark_styles(root);db=Fixture(role);changed=[]
            manager=FreezeManager(root,db,1,'Ana de prueba',lambda:changed.append(True))
            failures=[]
            root.report_callback_exception=lambda k,e,t:failures.append(repr(e))
            original=Modal.show
            def show(win):
                def inspect():
                    try:
                        for w in descendants(win):
                            if isinstance(w,ttk.Button):assert_exposed(w)
                        if win.title()=='Confirmar congelación':
                            text='\n'.join(str(w.cget('text')) for w in descendants(win) if isinstance(w,ttk.Label))
                            assert '7 días' in text and 'no podrá registrar entradas' in text and 'extenderá 7 días' in text
                            button=next(w for w in descendants(win) if isinstance(w,ttk.Button) and w.cget('text')==choice[0])
                            button.invoke()
                        else:win.close()
                    except BaseException as e:failures.append(repr(e));win.close()
                win.after(180,inspect)
                return original(win)
            try:
                manager.window.after(160,manager.window.close);original(manager.window)
                # Show the real manager again, then test confirmation cancellation and acceptance.
                manager=FreezeManager(root,db,1,'Ana de prueba',lambda:changed.append(True))
                def act():
                    try:
                        buttons=[w for w in descendants(manager.controls) if isinstance(w,ttk.Button)]
                        assert any(w.cget('text')=='CONGELAR 7 DÍAS' for w in buttons)
                        assert any(w.cget('text')=='Política de congelación' for w in buttons)==(role=='admin')
                        choice[0]='Cancelar'
                        with patch.object(Modal,'show',show):manager.confirm()
                        assert not db.calls
                        choice[0]='Congelar'
                        with patch.object(Modal,'show',show):manager.confirm()
                        assert len(db.calls)==1 and len(changed)==1
                        assert db.calls[0][1]['p_request_id']
                        assert 'CONGELADA' in manager.status.get() and '14/10/2026' in manager.status.get()
                        assert '15/10/2026' in manager.status.get() and '27/10/2026' in manager.status.get()
                        assert not any(w.cget('text').startswith('CONGELAR') for w in descendants(manager.controls) if isinstance(w,ttk.Button))
                        assert '2026-10-08 09:00:00' in manager.table.item('freeze','values')
                        for w in descendants(manager.controls):
                            if isinstance(w,ttk.Button):assert_exposed(w)
                        if os.environ.get('GYMSOFT_QA_IMAGES'):
                            from PIL import ImageGrab
                            target=Path(os.environ['GYMSOFT_QA_IMAGES']);target.mkdir(parents=True,exist_ok=True)
                            ImageGrab.grab(xdisplay=os.environ['DISPLAY']).crop((manager.window.winfo_rootx(),manager.window.winfo_rooty(),
                                manager.window.winfo_rootx()+manager.window.winfo_width(),manager.window.winfo_rooty()+manager.window.winfo_height())).save(target/f'freeze_{role}_{int(factor*100)}.png')
                    except BaseException as e:failures.append(repr(e))
                    finally:manager.window.close()
                choice=['Cancelar'];manager.window.after(180,act);original(manager.window)
                assert not failures,failures
                checks+=12
            finally:destroy_root(root)
    print(f'PASS: {checks} freeze UI checks: admin/reception, 100/125%, confirm/cancel, eligibility, local timestamps.')

if __name__=='__main__':main()
