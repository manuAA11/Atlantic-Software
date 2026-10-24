"""Real Tk theme switching, no network/credentials/hardware required."""
from pathlib import Path
import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/os.environ.get('ATLANTIC_TEST_EDITION','GymSoft_ZTATTUZ_3.6.1_x86')))
sys.path.insert(0,str(ROOT))
from common import atlantic_ui as kit
from common.appearance import install, appearance_settings
from common.theme_settings import load_theme
from desktop_ui import configure_dark_styles
from app import GymSoftApp, SidebarButton, QuickActionButton
from reception_app import ReceptionApp, SidebarButton as ReceptionSidebar
from runtime_cloud import LoginDialog
from PIL import ImageGrab


def pump(root):
    root.update_idletasks()
    root.update()


def main():
    checks=0
    with tempfile.TemporaryDirectory() as folder, patch('common.theme_settings.preference_path',return_value=Path(folder)/'appearance.json'):
        for factor in (1,1.25):
            for cls in (GymSoftApp,ReceptionApp):
                kit.select_theme('dark')
                root=tk.Tk();root.geometry('1120x760+0+0')
                root.tk.call('tk','scaling',96/72*factor)
                errors=[]
                root.report_callback_exception=lambda k,e,t:errors.append(repr(e))
                try:
                    cls.configure_styles(root)
                    manager=install(root)
                    shell=tk.Frame(root,bg=kit.COLORS['background']);shell.pack(fill='both',expand=True)
                    side=tk.Frame(shell,bg=kit.COLORS['sidebar']);side.pack(side='left',fill='y')
                    called=[]
                    navcls=SidebarButton if cls is GymSoftApp else ReceptionSidebar
                    nav=navcls(side,'\uE716','Clientes',lambda:called.append('nav'));nav.pack(fill='x',pady=20)
                    frame=ttk.Frame(shell,style='Card.TFrame',padding=22);frame.pack(fill='both',expand=True,padx=16,pady=16)
                    title=ttk.Label(frame,text='Atlantic Gym · Apariencia',style='Section.TLabel');title.pack(anchor='w')
                    text=ttk.Label(frame,text='Resumen de ventas integrado al fondo azul');text.pack(anchor='w')
                    form=tk.StringVar(root,value='Cliente sin guardar')
                    entry=ttk.Entry(frame,textvariable=form);entry.pack(fill='x',pady=12)
                    checked=tk.BooleanVar(root,value=False)
                    check=ttk.Checkbutton(frame,text='Conservar selección',variable=checked);check.pack(anchor='w')
                    command=ttk.Button(frame,text='Comprobar acción',command=lambda:called.append('button'));command.pack(anchor='w',pady=12)
                    notebook=ttk.Notebook(frame);notebook.pack(fill='x')
                    tab=ttk.Frame(notebook,style='Card.TFrame',padding=16);notebook.add(tab,text='Movimientos')
                    tree=ttk.Treeview(tab,columns=('name',),show='headings',height=2)
                    tree.heading('name',text='Cliente');tree.insert('','end',iid='saved',values=('Laura Méndez',));tree.selection_set('saved');tree.pack(fill='x')
                    action=QuickActionButton(frame,'\uE716','Registrar cliente',lambda:called.append('quick'));action.pack(fill='x',pady=12)
                    original_background=action.cget('background')
                    preferences=appearance_settings(frame);preferences.pack(fill='x')
                    root.event_generate('<Motion>',x=1,y=1,warp=True)
                    pump(root)
                    original_layout=ttk.Style(root).layout('TButton')
                    with patch('common.appearance.save_theme',side_effect=OSError('disk unavailable')):
                        try:manager.change('minimal')
                        except OSError:pass
                        else:raise AssertionError('A failed save must be reported')
                    assert kit.THEME=='dark'
                    assert ttk.Style(root).layout('TButton')==original_layout
                    checks+=2
                    widgets=(entry,tree,nav)
                    for name in ('minimal','league_light','league_dark','dark','league_dark','league_light','minimal','dark'):
                        manager.change(name)
                        root.event_generate('<Motion>',x=1,y=1,warp=True)
                        pump(root)
                        assert form.get()=='Cliente sin guardar'
                        assert tree.selection()==('saved',)
                        assert tree.item('saved','values')==('Laura Méndez',)
                        assert all(w.winfo_exists() for w in widgets)
                        assert load_theme(Path(folder)/'appearance.json')==name
                        assert not errors,errors
                        check.invoke();assert checked.get();check.invoke();assert not checked.get()
                        root.focus_force();check.focus_force();pump(root)
                        check.event_generate('<KeyPress-space>');check.event_generate('<KeyRelease-space>');pump(root)
                        assert checked.get();check.invoke();assert not checked.get()
                        command.state(['disabled']);before=len(called);command.invoke();assert len(called)==before
                        command.state(['!disabled'])
                        command.invoke();assert called[-1]=='button'
                        nav.event_generate('<Button-1>');assert called[-1]=='nav'
                        nav.set_active(True);pump(root)
                        label=nav.text_label if cls is GymSoftApp else nav.label
                        assert label.cget('fg')==kit.COLORS['text']
                        nav.set_active(False);pump(root)
                        assert label.cget('fg')==kit.COLORS['muted']
                        if name!='dark':
                            assert str(text.cget('background'))==kit.COLORS['surface'],(text.cget('background'),kit.COLORS['surface'])
                            assert nav.icon_label.cget('image') if cls is GymSoftApp else nav.icon.cget('image')
                            assert 'Atlantic.Minimal' in str(ttk.Style(root).layout('TButton'))
                            if name.startswith('league_'):
                                assert ttk.Style(root).lookup('Primary.TButton','foreground')=='#FFFFFF'
                                assert kit.THEME in str(ttk.Style(root).layout('Primary.TButton'))
                                assert ttk.Style(root).lookup('Section.TLabel','foreground')==kit.COLORS['text']
                                assert ttk.Style(root).lookup('Treeview','foreground')==kit.COLORS['text']
                        else:
                            assert ttk.Style(root).layout('TButton')==original_layout
                            assert action.cget('background')==original_background,(action.cget('background'),original_background)
                        checks+=14
                    manager.change('league_light',persist=False);pump(root)
                    # Newly created widgets/dialogs also inherit the selected presentation.
                    login=LoginDialog(root);pump(root)
                    assert login.email_entry.winfo_viewable()
                    assert login.password_entry.cget('show')=='*'
                    login.email.set('prueba@example.test');login.password.set('SoloPruebas123')
                    login.accept();assert login.result==('prueba@example.test','SoloPruebas123')
                    pump(root)
                    checks+=3
                    if os.environ.get('ATLANTIC_THEME_IMAGES'):
                        target=Path(os.environ['ATLANTIC_THEME_IMAGES']);target.mkdir(parents=True,exist_ok=True)
                        ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).crop((0,0,1120,760)).save(target/f'{cls.__name__}_{round(factor*100)}.png')
                    assert not errors,errors
                finally:
                    root.destroy()
    kit.select_theme('dark')
    print(f'PASS: {checks} theme checks, Admin/Reception, 100/125%, no network or hardware.')

if __name__=='__main__':main()
