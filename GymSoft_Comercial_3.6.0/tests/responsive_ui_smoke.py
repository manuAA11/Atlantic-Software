"""Prueba real Tk de diseño al 100/125 %, sin cuentas, red ni cambios reales."""
from pathlib import Path
import os
import sys
import tempfile
import time
from datetime import date
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import tkinter as tk
from tkinter import ttk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as admin
import reception_app as reception
from owner_panel import OwnerPanel
from biometric import BiometricAccessController, BiometricAccessControl
from responsive_ui import ScrollArea, adapt_tree
from ui_assertions import (assert_content_exposed, click, destroy_root,
                           enable_dpi_awareness, resize_test_window)


def pump(root, seconds=.10):
    until=time.monotonic()+seconds
    while time.monotonic()<until:
        root.update();time.sleep(.005)


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def assert_buttons_fit(root):
    for w in descendants(root):
        if not isinstance(w,(ttk.Button,tk.Button)) or not w.winfo_viewable():continue
        # Los botones pueden quedar debajo del visor y seguir accesibles por scroll.
        parent=w.master
        if w.winfo_manager()=='grid':parent=w.grid_info().get('in',parent)
        if w.winfo_manager()=='pack':parent=w.pack_info().get('in',parent)
        assert w.winfo_width()+3>=w.winfo_reqwidth(), f'Botón recortado: {w.cget("text")} ({w.winfo_width()} < {w.winfo_reqwidth()}); {w} padre {parent.winfo_width()}'
        assert w.winfo_x()+w.winfo_width()<=parent.winfo_width()+3, f'Botón fuera del ancho: {w.cget("text")}'


def fake_db():
    db=Mock();db._today.return_value=date(2026,9,8)
    db.list_clients.return_value=[];db.list_checkins.return_value=[]
    db._execute.return_value.data={"conversations":[],"links":[],"connected":False}
    db.marketing_settings.return_value={}
    db.marketing_workspace.return_value={"summary":{"settings":{},"connections":[]},"automations":[],"templates":[],"messages":[],"payments":[],"conversations":[],"links":[],"plans":[],"health":{}}
    return db


def shell(cls, factor):
    enable_dpi_awareness()
    root=cls.__new__(cls);tk.Tk.__init__(root)
    root.tk.call('tk','scaling',96/72*factor)
    resize_test_window(root, '1366x768');root.ready=False
    root.db=fake_db();root.cloud=NS(gym_name='Gimnasio de demostración',gym_id='00000000-0000-4000-8000-000000000001',email='demo@example.test',role='admin')
    root.pages={};root.nav_buttons={};root.current_page=''
    root.configure_styles();ttk.Style(root).configure('Sidebar.TFrame',background=admin.COLORS['sidebar'])
    root.load_logo=lambda:None
    root.build_shell()
    root.biometric_access=BiometricAccessController(root,lambda code:None,lambda c:None,lambda c:None,lambda e:None)
    return root


def main():
    from visibility_ui_smoke import main as check_visibility_probe
    check_visibility_probe()
    checked=0;failures=[]
    def callback_error(kind,error,tb):
        import traceback
        failures.append(str(error));traceback.print_exception(kind,error,tb)
    for factor in [1,1.25]:
        for cls in [admin.GymSoftApp,reception.ReceptionApp]:
            with patch.object(reception.branding,'show_reception_logo',lambda *_:None):root=shell(cls,factor)
            root.report_callback_exception=callback_error
            try:
                assert list(root.nav_buttons)[:3]==(['dashboard','checkin','clients'] if cls is admin.GymSoftApp else ['access','clients','shop'])
                for key,page_type in root.page_types.items():
                    with patch.object(page_type,'refresh',lambda self,*args,**kwargs:None):
                        root.show_page(key)
                    page=root.pages[key]
                    for size in ['1366x768','960x640','800x550','1366x768']:
                        root._ui_test_context=f'{cls.__name__} / {key} / {factor*100:g} % / solicitado {size}'
                        resize_test_window(root,size);pump(root,.16)
                        try:assert_buttons_fit(root)
                        except AssertionError:
                            print(cls.__name__,key,factor,size,flush=True)
                            for w in descendants(page):
                                if isinstance(w,ttk.Button) and w.cget('text')=='Actualizar':
                                    print('MANAGER',w.winfo_manager(),'parent',w.master,'reflow',getattr(w.master,'_responsive_reflow',None),flush=True)
                                    print([(str(c),c.winfo_manager(),c.winfo_width(),c.winfo_reqwidth()) for c in w.master.winfo_children()],flush=True)
                            raise
                        checked+=1+assert_content_exposed(page)
                    # Recorrer pestañas para instalar y comprobar contenidos diferidos.
                    for notebook in [w for w in descendants(page) if isinstance(w,ttk.Notebook)]:
                        for tab in notebook.tabs():
                            notebook.select(tab);pump(root,.08);adapt_tree(page);pump(root,.08)
                            assert_buttons_fit(root)
                            checked+=assert_content_exposed(page)
                    for control in [w for w in descendants(page) if isinstance(w,BiometricAccessControl)]:
                        click(control.button)
                        assert not root.biometric_access.enabled.get()
                        assert control.button.cget('text')=='Activar lectura'
                        assert control.status.cget('text').endswith('pausada')
                        click(control.button)
                        assert root.biometric_access.enabled.get()
                        assert control.button.cget('text')=='Pausar lectura'
                        assert control.status.cget('text').endswith('activada')
                        checked+=2
                    if key in ['dashboard','checkin','access','settings','statistics'] and os.environ.get('GYMSOFT_QA_IMAGES'):
                        from PIL import ImageGrab
                        resize_test_window(root,'960x640');pump(root)
                        for notebook in [w for w in descendants(page) if isinstance(w,ttk.Notebook)]:
                            notebook.select(notebook.tabs()[0])
                        root.content_area.canvas.yview_moveto(0);pump(root)
                        folder=Path(os.environ['GYMSOFT_QA_IMAGES']);folder.mkdir(exist_ok=True,parents=True)
                        ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).crop((root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(), root.winfo_rooty()+root.winfo_height())).save(folder/f'{cls.__name__}_{key}_{int(factor*100)}.png')
                    page.pack_forget();pump(root,.04)
                # Volver a pantallas ya creadas no debe ocultar pestañas ni tablas.
                root.biometric_access.enabled.set(False)
                for key in reversed(root.page_types):
                    root._ui_test_context=f'{cls.__name__} / regreso a {key} / {factor*100:g} %'
                    with patch.object(root.page_types[key],'refresh',lambda self,*args,**kwargs:None):
                        root.show_page(key)
                    pump(root)
                    checked+=assert_content_exposed(root.pages[key])
                    for control in [w for w in descendants(root.pages[key]) if isinstance(w,BiometricAccessControl)]:
                        assert not root.biometric_access.enabled.get()
                        assert control.status.cget('text').endswith('pausada')
                        checked+=1
                root.biometric_access.enabled.set(True)
                # Los formularios siguen permitiendo guardar un cliente sin huella.
                dialog_type=admin.ClientDialog if cls is admin.GymSoftApp else reception.ClientDialog
                win=dialog_type(root);pump(root)
                vars=win.vars if cls is admin.GymSoftApp else win.variables
                vars['document'].set('PRUEBA-001');vars['first_name'].set('Ana');vars['last_name'].set('Prueba')
                win.geometry('480x400');pump(root);assert_buttons_fit(root)
                win.save();assert win.result['biometric_identifier']==''
                checked+=1
                if cls is admin.GymSoftApp:
                    for limit in [15,20,None]:
                        win=admin.PlanDialog(root,{'name':'Prueba','duration_days':30,'price':50000,'entry_limit':limit})
                        win.geometry('460x380');pump(root);assert_buttons_fit(root)
                        win.save();assert win.result==( 'Prueba',30,50000,limit,None);checked+=1
            finally:destroy_root(root)
        root=OwnerPanel.__new__(OwnerPanel);tk.Tk.__init__(root)
        root.tk.call('tk','scaling',96/72*factor);resize_test_window(root,'1340x850')
        root.report_callback_exception=callback_error;root.configure_style()
        root.cloud=NS(email='owner@example.test');root.rows={};root.detail={};root.busy=False
        root.build_ui()
        try:
            for size in ['1340x850','960x640','800x550','1340x850']:
                root._ui_test_context=f'Propietario / {factor*100:g} % / solicitado {size}'
                resize_test_window(root,size);pump(root,.2);assert_buttons_fit(root)
                checked+=1+assert_content_exposed(root)
        finally:destroy_root(root)
    assert not failures,'; '.join(failures)
    print(f'PASS: {checked} comprobaciones de tamaños, navegación y formularios al 100 % y 125 %.')

if __name__=='__main__':main()
