"""Real Atlantic controls, with database/provider calls simulated explicitly."""
import os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['GYMSOFT_OFFLINE_QA']='1'
import tkinter as tk
from tkinter import ttk
from datetime import date
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
import app
from plan_editor_ui import OwnerPlanDialog
from desktop_ui import configure_dark_styles
from ui_assertions import pump, destroy_root

def main():
    checks=0
    for factor in (1,1.25):
        root=tk.Tk();root.tk.call('tk','scaling',96/72*factor);root.geometry('1000x780')
        app.GymSoftApp.configure_styles(root)
        failures=[];root.report_callback_exception=lambda typ,error,tb:failures.append(str(error))
        try:
            for factory in (app.PlanDialog,OwnerPlanDialog):
                win=factory(root);pump(root)
                assert win.name.get()=='';win.name.set('STAFF');win.plan_type.set('Interno / No comercial');pump(root)
                assert win.price.get()=='0' and win.unlimited.get() and win.indefinite.get()
                assert win.price_entry.instate(['disabled']) and not win.duration_entry.winfo_ismapped()
                win.save();assert win.result==('STAFF',None,0,None,None,'INTERNAL',True,False,False);checks+=5
                win=factory(root,{'name':'Invitado','plan_type':'INTERNAL','duration_days':2,'has_expiration':True,'price':0,'entry_limit':2,'unlimited_access':False})
                pump(root);assert win.entries_entry.winfo_ismapped() and win.duration_entry.winfo_ismapped()
                win.save();assert win.result==('Invitado',2,0,2,None,'INTERNAL',False,True,False);checks+=2
            plan={'id':1,'name':'STAFF','price':0,'plan_type':'INTERNAL','duration_days':None,'entry_limit':None,'has_expiration':False,'unlimited_access':True}
            paid={'id':2,'name':'Mensual','price':70000,'duration_days':30,'entry_limit':None}
            db=Mock();db.list_plans.return_value=[plan,paid];db._today.return_value=date(2026,10,20)
            win=app.MembershipDialog(root,db,'Personal');pump(root)
            assert win.amount.get()=='0' and not win.amount_entry.winfo_ismapped() and not win.ticket_fields.winfo_ismapped()
            win.plan.set(next(label for label,p in win.plan_by_label.items() if p['id']==2));win.sync_amount();pump(root)
            assert win.amount.get()=='70000' and win.amount_entry.winfo_ismapped()
            win.plan.set(next(label for label,p in win.plan_by_label.items() if p['id']==1));win.sync_amount();pump(root)
            win.save();assert win.result['internal'] and win.result['amount']==0 and win.result['request_id'];checks+=4
            page=ttk.Frame(root);page.db=db;page.pack(fill='both',expand=True)
            common=dict(first_name='Persona',last_name='Prueba',phone='3001234567',birthdate='1990-10-21',active=True)
            db.list_clients.return_value=[dict(common,id=1,membership_type='INTERNAL',membership_end='2026-10-21'),
                dict(common,id=2,membership_type='COMMERCIAL',frozen=True,membership_end='2026-10-19'),
                dict(common,id=3,membership_type='COMMERCIAL',membership_end='2026-10-22'),
                dict(common,id=4,membership_type='COMMERCIAL',membership_end='2026-10-19')]
            app.ClientsPage.show_notifications(page);pump(root)
            notices=next(w for w in page.winfo_children() if isinstance(w,tk.Toplevel))
            notebook=next(w for w in notices.body.winfo_children() if isinstance(w,ttk.Notebook))
            titles=[notebook.tab(tab,'text') for tab in notebook.tabs()]
            assert titles==['Cumpleaños próximos (4)','Vencen en 5 días (1)','Membresías vencidas (1)'],titles
            notices.destroy();page.destroy();checks+=1
            assert not failures,failures
        finally:destroy_root(root)
    print(f'PASS: {checks} internal plan UI checks at 100/125%, Admin and Owner, optional names and no payment controls.')

if __name__=='__main__':main()
