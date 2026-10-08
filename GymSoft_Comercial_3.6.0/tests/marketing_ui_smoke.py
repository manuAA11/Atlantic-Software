"""Exercise all eight Marketing sections in the actual desktop shell."""
from pathlib import Path
import os
import sys
from types import SimpleNamespace as NS
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app
from responsive_ui_smoke import shell, descendants, assert_buttons_fit
from ui_assertions import pump, destroy_root, assert_content_exposed, resize_test_window
from marketing_ui import RuleDialog, MessageDialog

def main():
    checks=0
    data={'summary':{'settings':{'whatsapp_enabled':False,'chatbot_enabled':False,'online_payments_enabled':False,
                'marketing_automation_enabled':False},'connections':[]},
          'plans':[{'id':2,'name':'Mensual','active':True,'price':70000}],
          'automations':[{'id':'rule','name':'Vence en 3 días','enabled':False,'trigger_type':'MEMBERSHIP_BEFORE'}],
          'templates':[],'links':[],'conversations':[],
          'messages':[{'id':1,'created_at':'2026-10-08T02:30:00Z','client_name':'Ana','body':'Mensaje de prueba','status':'SKIPPED'}],
          'payments':[{'id':'payment','created_at':'2026-10-07T14:00:00Z','paid_at':'2026-10-08T02:31:00Z','provider_created_at':'2026-10-08T02:30:00Z','client_name':'Ana','plan_snapshot':{'name':'Mensual'},'amount_in_cents':7000000,'status':'APPROVED','reference':'GS-'+'a'*32,'transaction_id':'SANDBOX-PRUEBA'}],
          'health':{'last_worker_at':'2026-10-08T02:30:00Z','recent_errors':0}}
    for factor in (1,1.25):
        root=shell(app.GymSoftApp,factor);root.db.cloud=NS(role='admin',timezone='America/Bogota')
        failures=[];root.report_callback_exception=lambda k,e,t:failures.append(repr(e))
        try:
            with patch.object(app.MarketingPage,'refresh',lambda self:None):root.show_page('marketing')
            page=root.pages['marketing'];page.render(data);pump(root)
            assert len(page.TABS)==8 and page.chat_state.get()=='Asistente desactivado'
            assert page.stamp('2026-10-08T02:30:00Z')=='2026-10-07 21:30:00'
            assert '2026-10-07 21:30:00' in page.trees['messages'].item('1','values')
            assert '2026-10-07 09:00:00' in page.trees['payments'].item('payment','values')
            checks+=4
            page.trees['payments'].selection_set('payment')
            original=MessageDialog.show
            def show_detail(win):
                def inspect_detail():
                    try:
                        text=next(w for w in descendants(win) if isinstance(w,tk.Text)).get('1.0','end')
                        assert 'Fecha de la transacción Wompi: 2026-10-07 21:30:00' in text
                        assert 'Pagado: 2026-10-07 21:31:00' in text
                        if os.environ.get('GYMSOFT_QA_IMAGES'):
                            from PIL import ImageGrab
                            target=Path(os.environ['GYMSOFT_QA_IMAGES']);target.mkdir(parents=True,exist_ok=True)
                            ImageGrab.grab(xdisplay=os.environ['DISPLAY']).crop((win.winfo_rootx(),win.winfo_rooty(),win.winfo_rootx()+win.winfo_width(),win.winfo_rooty()+win.winfo_height())).save(target/f'wompi_timestamps_{int(factor*100)}.png')
                    except BaseException as error:failures.append(repr(error))
                    finally:win.close()
                win.after(180,inspect_detail)
                return original(win)
            with patch.object(MessageDialog,'show',show_detail):page.history_detail('payments')
            checks+=2
            for name in page.TABS:
                page.select(name);pump(root)
                for size in ('1366x768','1000x700'):
                    resize_test_window(root,size);pump(root);assert_buttons_fit(root)
                    checks+=1+assert_content_exposed(page.sections[name])
                if os.environ.get('GYMSOFT_QA_IMAGES') and name in ('Resumen','Historial','Estado de integraciones'):
                    from PIL import ImageGrab
                    target=Path(os.environ['GYMSOFT_QA_IMAGES']);target.mkdir(parents=True,exist_ok=True)
                    ImageGrab.grab(xdisplay=os.environ['DISPLAY']).crop((root.winfo_rootx(),root.winfo_rooty(),
                        root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(target/f'marketing_{name.replace(" ","_")}_{int(factor*100)}.png')
            d=RuleDialog(root,{},[],data['plans'],False)
            def inspect():
                try:
                    assert d.time.get()=='09:00' and not d.enabled.get()
                    assert not d.link.get()
                    d.name.set('Regla de prueba');d.accept()
                except BaseException as e:failures.append(repr(e));d.close()
            d.after(180,inspect);result=d.show()
            assert result['trigger_options']['time']=='09:00' and result['enabled'] is False
            checks+=4
            assert not failures,failures
        finally:destroy_root(root)
    print(f'PASS: {checks} Marketing UI checks: eight sections, disabled flags, timestamps, rule editor, 100/125%.')

if __name__=='__main__':main()
