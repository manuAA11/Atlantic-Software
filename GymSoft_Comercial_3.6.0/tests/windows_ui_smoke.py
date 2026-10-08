"""Prueba gráfica automática local, SIN conectar a Supabase ni usar cuentas.

Se ejecuta antes de compilar en Windows. También admite Linux con pantalla.
Si una ventana deja de aparecer o surge un error Tkinter, se detiene el build.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import date
import tempfile
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, patch
from types import SimpleNamespace as NS
from desktop_ui import configure_dark_styles,decorate_window,messagebox,simpledialog,Modal,BG
from dark_files import FilePicker
from runtime_cloud import LoginDialog
from owner_panel import Form,OwnerPanel
from owner_forms import renewal_params
from owner_editor import OwnerEditor,RecordForm
from app import BaseDialog as AdminDialog,ClientsPage as AdminClients,FinancePage,GymSoftApp
from reception_app import BaseDialog as ReceptionDialog,ClientsPage as ReceptionClients
from payment_revision import open_payment_manager
from reception_expense_revision import open_reception_expense_manager
from ui_assertions import enable_dpi_awareness, resize_test_window


def children(widget):
    for child in widget.winfo_children():
        yield child
        yield from children(child)


def main():
    enable_dpi_awareness()
    root=tk.Tk();root.title('Gym soft · Verificación de ventanas');resize_test_window(root,'1100x720')
    failures=[]
    def callback_error(kind,error,tb):
        traceback.print_exception(kind,error,tb)
        failures.append(str(error))
        for w in list(root.winfo_children()):
            if isinstance(w,tk.Toplevel):w.destroy()
    root.report_callback_exception=callback_error
    configure_dark_styles(root);OwnerPanel.configure_style(root);decorate_window(root);root.update()
    # Timeout de seguridad: ningún modal puede dejar la compilación colgada.
    def timeout():
        failures.append('La prueba gráfica excedió 30 segundos.')
        root.destroy()
    watchdog=root.after(30000,timeout)
    try:
        for hidden in [False,True]:
            if hidden:root.withdraw()
            for creating in [False,True]:
                login=LoginDialog(root,creating_account=creating)
                root.update()
                assert login.winfo_viewable(),'La ventana de acceso quedó oculta.'
                login.email.set('demo@example.test');login.password.set('SoloPrueba12345')
                login.accept();assert login.result[0]=='demo@example.test'
            root.deiconify();root.update()
        login=LoginDialog(root,owner=True);root.update();assert login.winfo_viewable();login.destroy()
        gym={'id':'a0000000-0000-4000-8000-000000000001','currency':'COP'}
        def fill_form():
            f=next(w for w in root.winfo_children() if isinstance(w,Form))
            assert f.winfo_viewable(),'Formulario oculto'
            f.accept();assert f.winfo_exists() and f.result is None,'Se cerró el formulario inválido'
            f.vars['reference'].set('TEST-001');f.accept()
        root.after(120,fill_form)
        form=Form(root,'Registrar mensualidad',[('months','Meses',1),('amount','Valor','200000'),('reference','Referencia','')],validate=lambda f:renewal_params(gym,f))
        assert form.result and form.result['p_amount']=='200000.00'
        # Las preguntas conservan Sí/No distintos y ambos continúan a login.
        for choice in [True,False]:
            def choose(value=choice):
                win=next(w for w in root.winfo_children() if isinstance(w,Modal))
                assert win.winfo_viewable() and win.cget('bg')==BG
                next(b for b in children(win) if isinstance(b,tk.Button) and b.cget('text')==('Sí' if value else 'No')).invoke()
            root.after(120,choose)
            assert messagebox.askyesno('Cuenta','¿Ya tienes una cuenta?',parent=root) is choice
            login=LoginDialog(root,creating_account=not choice);root.update();assert login.winfo_viewable();login.destroy()
        def cancel_prompt():
            next(w for w in root.winfo_children() if isinstance(w,Modal)).close()
        root.after(120,cancel_prompt)
        assert simpledialog.askstring('Motivo','Motivo:',parent=root) is None
        with tempfile.TemporaryDirectory(prefix='gymsoft_ui_') as folder:
            picker=FilePicker(root,save=True,initialdir=folder,initialfile='respaldo',defaultextension='.json')
            root.after(120,picker.accept)
            selected=picker.show()
            expected=(Path(folder)/'respaldo.json').resolve()
            assert selected and Path(selected)==expected,(selected,str(expected))
        # Abrir pagos de un cliente en cada aplicación con respuesta simulada.
        for dialog_class in [AdminDialog,ReceptionDialog]:
            db=NS(gym_id=gym['id'],client=NS(rpc=lambda *args,**kw:None),
                  _execute=lambda _:NS(data={'rows':[],'has_more':False}))
            open_payment_manager(root,db,1,'Cliente de prueba',dialog_class,str,str,lambda:None)
            root.update()
            win=next(w for w in root.winfo_children() if isinstance(w,dialog_class))
            assert win.winfo_viewable();win.destroy()
        # Construcción del formulario completo Crear gasto sin grabar nada.
        def cancel_expense():
            next(w for w in root.winfo_children() if isinstance(w,ReceptionDialog)).destroy()
        root.after(150,cancel_expense)
        assert open_reception_expense_manager(root,NS(today=lambda:date(2026,10,8)),ReceptionDialog) is False
        # Editor completo: navegación, fila, formulario desplazable y cola sin red.
        access_data={'users':[{'email':'admin@example.test','role':'admin','enabled':True}],
                     'invitations':[{'email':'new@example.test','role':'receptionist','expired':False,'expires_at':'2026-09-14T00:00:00Z'}]}
        response_gate=threading.Event()
        def delayed_access(*_args,**_kwargs):
            if not response_gate.wait(8):
                raise RuntimeError('La prueba no liberó la respuesta de usuarios.')
            return access_data
        root.rpc=Mock(side_effect=delayed_access)
        editor_gym={**gym,'name':'Prueba editor','contact_email':'gym@example.test','timezone':'America/Bogota','plan':'Pro'}
        deadline=time.monotonic()+10
        def check_editor():
            editor=next((w for w in root.winfo_children() if isinstance(w,OwnerEditor)),None)
            if editor is None or not editor.winfo_viewable() or not editor.users_loaded:
                assert time.monotonic()<deadline,'El editor no terminó de cargar usuarios en 10 segundos.'
                root.after(50,check_editor);return
            assert not editor.busy,'El editor dejó bloqueados los controles.'
            rows=[editor.users.item(key,'values') for key in editor.users.get_children()]
            assert sorted(row[0] for row in rows)==['admin@example.test','new@example.test'],'No cargaron usuarios e invitaciones'
            assert {row[2] for row in rows}=={'Habilitado','Activación pendiente'},rows
            root.rpc.assert_called_once_with('owner_editor_access',{'p_gym_id':gym['id']})
            notebook=next(w for w in children(editor) if isinstance(w,ttk.Notebook))
            from ui_assertions import assert_content_exposed
            for index in range(3):
                notebook.select(index);root.update_idletasks()
                assert_content_exposed(editor)
            assert notebook.winfo_viewable();editor.close()
        def release_editor_response():
            editor=next((w for w in root.winfo_children() if isinstance(w,OwnerEditor)),None)
            if editor is None or not editor.winfo_viewable():
                assert time.monotonic()<deadline,'El editor no se hizo visible.'
                root.after(50,release_editor_response);return
            assert editor.busy and not editor.users_loaded,'La carga inicial debe empezar antes de habilitar el editor.'
            assert len(editor.users.get_children())==0,'La prueba debe esperar a la respuesta.'
            response_gate.set()
        root.after(50,check_editor)
        root.after(450,release_editor_response)
        try:
            OwnerEditor(root,editor_gym,Form)
        finally:
            response_gate.set()
        columns=[{'name':'first_name','type':'text','nullable':False,'editable':True},
                 {'name':'active','type':'boolean','nullable':False,'editable':True}]
        def fill_record():
            win=next(w for w in root.winfo_children() if isinstance(w,RecordForm))
            assert win.winfo_viewable()
            win.accept();assert win.winfo_exists(),'No validó el motivo'
            win.entries['first_name'].set('Editado');win.reason.set('Prueba de edición');win.accept()
        root.after(120,fill_record)
        edited=RecordForm(root,{'data':{'id':1,'first_name':'Original','active':True}},columns,'clients')
        assert edited.result['p_patch']=={'first_name':'Editado'}
        # Los accesos de Clientes y Finanzas existen y enlazan a sus controladores.
        GymSoftApp.configure_styles(root)
        fake=NS(db=NS(list_clients=lambda *_:[]),cloud=NS())
        with patch.object(AdminClients,'refresh',lambda self:None):
            page=AdminClients(root,fake);page.pack();root.update()
            assert any('Consultar y editar pagos' in str(w.cget('text')) for w in children(page) if isinstance(w,ttk.Button))
            page.destroy()
        assert not failures,'; '.join(failures)
        print('PASS: ventanas login, Sí/No, formularios, modo oscuro, archivos, pagos, gastos y editor del propietario.')
    finally:
        if root.winfo_exists():root.after_cancel(watchdog);root.destroy()


if __name__=='__main__':main()
