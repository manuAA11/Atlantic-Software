"""Real client forms with a fake reader; no USB or SDK needed."""
import os
os.environ['GYMSOFT_OFFLINE_QA']='1'
import sys,time,queue
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch
from tkinter import ttk
import app as admin
import reception_app as reception
import fingerprint_ui as fp
import client_fingerprint as inline
from responsive_ui_smoke import shell,pump,assert_buttons_fit
from ui_assertions import destroy_root
class Service:
 def __init__(self,*args):self.events=queue.Queue();self.commands=[]
 def start(self):pass
 def pause(self,*args):pass
 def send(self,*args):self.commands.append(args)
 def close(self):pass
def until(root,fn):
 end=time.monotonic()+4
 while not fn():
  assert time.monotonic()<end,'No terminó la operación del formulario.'
  pump(root,.04)
def fill(d,doc='101'):
 v=getattr(d,'vars',getattr(d,'variables',{}))
 for k,x in dict(document=doc,first_name='Ana',last_name='Prueba',birthdate='17/04/1998').items():v[k].set(x)
 return v
count=0
for module,cls in ((admin,admin.GymSoftApp),(reception,reception.ReceptionApp)):
 for factor in (1,1.25):
  with patch.object(reception.branding,'show_reception_logo',lambda *_:None):root=shell(cls,factor)
  errors=[];root.report_callback_exception=lambda kind,error,tb:errors.append(str(error));root.ready=True
  records=[]
  def store(payload,client_id=None):records.append((dict(payload),client_id));return client_id or 701
  root.db.save_client.side_effect=store
  try:
   with patch.object(fp,'FingerprintService',Service):panel=fp.FingerprintPanel(root.biometric_access)
   root.biometric_access.native_reader=panel
   with patch.object(root.page_types['clients'],'refresh',lambda *_:None):root.show_page('clients')
   page=root.pages['clients'];page.refresh=lambda:None;page.when_loaded=lambda fn:None
   if hasattr(root,'refresh_all'):root.refresh_all=lambda **kw:None
   with patch.object(inline.messagebox,'askyesno',return_value=True),patch.object(inline.messagebox,'showerror') as error_popup,patch.object(inline.messagebox,'showinfo') as success_popup,patch.object(module.messagebox,'showwarning'):
    d=module.ClientDialog(page);fill(d);d.save()
    assert d.result['birthdate']=='1998-04-17' and not d.client_saved and not records;count+=1
    d=module.ClientDialog(page);d.fingerprint_form.enroll();pump(root,.08)
    assert not records and not panel.service.commands;count+=1;d.destroy()
    original=module.ClientDialog;started=[]
    def factory(parent,*args,**kw):
     d=original(parent,*args,**kw);fill(d);started.append(d)
     def progress():
      if d.fingerprint_form.operation=='enroll':
       panel.service.events.put(('templates',[701]));panel.service.events.put(('enrollment_end',{'result':'saved','message':'Huella registrada y verificada correctamente.'}));d.after(180,d.save)
      else:d.after(40,progress)
     d.after(60,d.fingerprint_form.enroll);d.after(100,progress)
     return d
    with patch.object(module,'ClientDialog',factory):page.new_client()
    assert len(records)==1 and records[0][1] is None and started[0].saved_client_id==701;count+=1
    assert panel.window is None and not panel.enrolling;count+=1
    data=dict(id=701,document='101',first_name='Ana',last_name='Prueba')
    d=original(page,data);v=fill(d);form=d.fingerprint_form;pump(root,.12);assert_buttons_fit(d);count+=1
    assert form.enroll_button.cget('text')=='Reemplazar huella';count+=1
    form.enroll();until(root,lambda:form.operation=='enroll')
    assert records[-1][1]==701 and d.winfo_exists();count+=1
    assert form.locked_fields and all('disabled' in w.state() for w in form.locked_fields);count+=1
    panel.service.events.put(('templates',[701]));panel.service.events.put(('enrollment_end',{'result':'saved','message':'Huella registrada y verificada correctamente.'}));until(root,lambda:form.operation is None)
    assert not form.locked_fields;count+=1
    assert success_popup.call_args[0][0]=='Huella registrada';count+=1
    before=len(records);form.verify();assert panel.service.commands[-1]==('verify',701);count+=1
    panel.service.events.put(('enrollment_end',{'result':'verified','message':'Huella reconocida correctamente.'}));until(root,lambda:form.operation is None)
    assert success_popup.call_args[0][0]=='Huella comprobada' and len(records)==before;count+=1
    form.verify();panel.service.events.put(('enrollment_end',{'result':'failed','message':'Error de lectura 0x05BA0014'}));until(root,lambda:form.operation is None)
    assert '0x05BA0014' in error_popup.call_args[0][1];count+=1
    v['phone'].set('3001234567');d.save();until(root,lambda:not d.winfo_exists())
    assert records[-1][0]['phone']=='3001234567' and records[-1][1]==701;count+=1
    d=original(page,data);form=d.fingerprint_form;before=len(records);form.delete()
    assert panel.service.commands[-1]==('delete',701);count+=1
    panel.service.events.put(('templates',[]));panel.service.events.put(('template_deleted',701));until(root,lambda:form.operation is None)
    assert len(records)==before and d.winfo_exists() and form.enroll_button.cget('text')=='Registrar huella';count+=1;d.destroy()
    d=original(page);fill(d,'102');form=d.fingerprint_form;form.enroll();until(root,lambda:form.operation=='enroll')
    form.cancel();assert panel.service.commands[-1]==('cancel',);count+=1
    panel.service.events.put(('enrollment_end','Registro cancelado.'));until(root,lambda:form.operation is None)
    assert d.client_saved;count+=1;d.destroy()
    root.db.save_client.side_effect=ConnectionError('test')
    d=original(page);fill(d,'103');form=d.fingerprint_form;before=len(panel.service.commands)
    form.enroll();until(root,lambda:form.uncertain)
    calls=root.db.save_client.call_count;form.enroll();d.save();pump(root,.1)
    assert root.db.save_client.call_count==calls and len(panel.service.commands)==before and d.winfo_exists();count+=1;d.destroy()
    assert not errors,errors;count+=1
  finally:destroy_root(root)
print(f'PASS: {count} comprobaciones de huella opcional integrada, alta sin duplicados, edición, cancelación, eliminación y fallo de red; 100 % y 125 %, lector simulado.')
