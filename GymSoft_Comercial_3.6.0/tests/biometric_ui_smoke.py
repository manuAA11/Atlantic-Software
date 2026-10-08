"""Eventos Tk reales de lector, buscador, foco y protección de formularios."""
import sys,time,threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from biometric import BiometricAccessController,AutomaticHidScanner,BiometricAccessControl
import biometric
from ui_assertions import click, enable_dpi_awareness, resize_test_window
from ui_test_support import wait_for

def pump(root,seconds=.2):
 end=time.monotonic()+seconds
 wait_for(root,lambda:time.monotonic()>=end,'procesar eventos de lectura',timeout=seconds+8)

def scan(root,widget,code,enter=True):
 if root.focus_get() is not widget:
  focused=[]
  binding=widget.bind('<FocusIn>',lambda event:focused.append(True),add='+')
  try:
   widget.focus_force()
   wait_for(root,lambda:bool(focused) and root.focus_get() is widget,'foco del control de prueba')
  finally:widget.unbind('<FocusIn>',binding)
 # Eventos Tk reales, con el reloj de una ráfaga de hardware. El tiempo que
 # consume pintar la ventana no debe convertir el lector simulado en un humano.
 clock=[time.monotonic()]
 with patch.object(biometric,'monotonic',side_effect=lambda:clock[0]):
  for c in code:
   clock[0]+=.009
   widget.event_generate('<KeyPress>',keysym=c,when='now')
  if enter:widget.event_generate('<KeyPress>',keysym='Return',when='now')
 pump(root)

def main():
 enable_dpi_awareness()
 root=tk.Tk();resize_test_window(root,'700x480');root.ready=True
 matches=[];unknown=[];errors=[];callbacks=[]
 root.report_callback_exception=lambda kind,error,tb:callbacks.append(str(error))
 lookup=Mock(side_effect=lambda c:None if c=='ZZ999' else {'id':1,'code':c})
 controller=BiometricAccessController(root,lookup,matches.append,unknown.append,errors.append)
 control=BiometricAccessControl(root,controller);control.pack(fill='x')
 mirror=BiometricAccessControl(root,controller);mirror.pack(fill='x')
 var=tk.StringVar(root);entry=ttk.Entry(root,textvariable=var);entry.pack()
 button=ttk.Button(root,text='Acción');button.pack()
 other=ttk.Entry(root);other.pack()
 controller.attach_search(entry,var);pump(root)
 try:
  scan(root,button,'AB123');wait_for(root,lambda:len(matches)>=1,'identificar AB123');assert len(matches)==1 and matches[-1]['code']=='AB123'
  scan(root,button,'AB123');assert len(matches)==1,'Lectura repetida'
  scan(root,button,'NOENTER',enter=False);wait_for(root,lambda:len(matches)>=2,'lectura sin Enter');assert len(matches)==2
  entry.focus_force();pump(root,.05);var.set('MANUAL20');wait_for(root,lambda:len(matches)>=3,'búsqueda manual')
  assert len(matches)==3 and matches[-1]['code']=='MANUAL20'
  other.insert(0,'Texto anterior ');scan(root,other,'RESTORE');wait_for(root,lambda:len(matches)>=4,'lectura fuera del buscador')
  assert len(matches)==4 and other.get()=='Texto anterior '
  modal=tk.Toplevel(root);form=ttk.Entry(modal);form.pack();modal.grab_set();pump(root)
  scan(root,form,'FORM123');assert len(matches)==4 and form.get()=='FORM123'
  modal.destroy();button.focus_force();pump(root)
  click(control.button)
  assert not controller.enabled.get() and mirror.status.cget('text').endswith('pausada')
  scan(root,button,'PAUSED');assert len(matches)==4
  click(mirror.button)
  assert controller.enabled.get() and control.status.cget('text').endswith('activada')
  scan(root,button,'RESUMED');wait_for(root,lambda:len(matches)>=5,'lectura reactivada');assert len(matches)==5 and matches[-1]['code']=='RESUMED'
  scan(root,button,'ZZ999');wait_for(root,lambda:bool(unknown),'código desconocido');assert unknown==['ZZ999'] and len(matches)==5
  # Una consulta que pierde el foco queda invalidada, incluso si vuelve antes de responder.
  gate=threading.Event()
  controller.lookup=lambda code:(gate.wait(1),{'id':2})[1]
  scan(root,button,'PENDING',enter=True)
  modal=tk.Toplevel(root);form=ttk.Entry(modal);form.pack();modal.grab_set();form.focus_force();pump(root,.05)
  modal.destroy();button.focus_force();pump(root,.05);gate.set();pump(root,.2)
  assert len(matches)==5,'Resultado antiguo aplicado después de un formulario'
  mirror.destroy();click(control.button);click(control.button)
  assert not errors and not callbacks,(errors,callbacks)
  print('PASS: lectura con/sin Enter, búsqueda manual, repetición, foco fuera del buscador, formularios, pausa y resultados pendientes.')
 finally:root.destroy()

if __name__=='__main__':main()
