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
    configure_dark_styles(root);GymSoftApp.configure_styles(root);decorate_window(root);root.update()
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
        gym={'id':'a0000000-0000-4000-8000-000000000001'}
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
            assert picker.show()==str(Path(folder)/'respaldo.json')
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
        # Los accesos de Clientes y Finanzas existen y enlazan a sus controladores.
        GymSoftApp.configure_styles(root)
        fake=NS(db=NS(list_clients=lambda *_:[]),cloud=NS())
        with patch.object(AdminClients,'refresh',lambda self:None):
            page=AdminClients(root,fake);page.pack();root.update()
            assert any('Consultar y editar pagos' in str(w.cget('text')) for w in children(page) if isinstance(w,ttk.Button))
            page.destroy()
        assert not failures,'; '.join(failures)
        print('PASS: ventanas login, Sí/No, formularios, modo oscuro, archivos, pagos y gastos de ZTATTUZ.')
    finally:
        if root.winfo_exists():root.after_cancel(watchdog);root.destroy()


if __name__=='__main__':main()
