from gym_time import display_timestamp, timezone_for, ticket_access_note, checkin_label
"""Tk frontend for a worker-owned DigitalPersona reader."""
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
from desktop_ui import messagebox, decorate_window
from fingerprint_service import FingerprintService
from fingerprint_store import CloudTemplateStore

class FingerprintPanel:
    def __init__(self, controller):
        self.controller = controller; self.root = controller.root
        self.state = tk.StringVar(self.root,value='DigitalPersona: iniciando…')
        self.templates = set(); self.window = None; self.enrolling = False; self.inline_editor = None
        self.clients = {}; self.ui_events = queue.Queue(); self.closed = False
        self.service = FingerprintService(CloudTemplateStore(self.root.db),self.root.db.register_checkin)
        self.root.bind('<Destroy>',self.destroy,add='+')
        self.service.pause(True); self.service.start(); self.job = self.root.after(100,self.poll)
    def destroy(self,event):
        if event.widget is self.root:
            self.closed = True; self.service.close()
            self.root.after_cancel(self.job)
    def poll(self):
        try:
            while True:
                kind,value = self.service.events.get_nowait()
                if kind == 'status':
                    self.state.set(value)
                    if self.inline_editor: self.inline_editor.reader_status(value)
                elif kind == 'templates':
                    self.templates = set(value); self.fill()
                    if self.inline_editor: self.inline_editor.templates_updated()
                elif kind == 'template_deleted':
                    if self.inline_editor:
                        self.inline_editor.template_deleted(value)
                        self.inline_editor = None
                elif kind == 'enrollment_end':
                    self.enrolling = False
                    result = value if isinstance(value, dict) else {'message':str(value)}
                    self.state.set(result['message'])
                    editor = self.inline_editor; self.inline_editor = None
                    if editor and not editor.closed:
                        editor.enrollment_finished(result)
                    elif self.window and self.window.winfo_exists():
                        self.show_completion(result, self.window)
                elif kind == 'uncertain':
                    self.controller.enabled.set(False); self.state.set(value)
                    messagebox.showwarning('No se confirmó el ingreso', value, parent=self.root)
                elif kind == 'unrecognized': self.show_unrecognized(value)
                elif kind == 'access': self.show_access(value)
        except queue.Empty: pass
        try:
            while True:
                kind,value = self.ui_events.get_nowait()
                if kind == 'clients':
                    self.clients = {int(c['id']):c for c in value}; self.fill()
                elif kind == 'error': self.state.set(value)
        except queue.Empty: pass
        from tk_window_state import grab_path
        paused = (not self.controller.enabled.get() or not getattr(self.root,'ready',True)
                  or bool(grab_path(self.root)) or bool(self.window and self.window.winfo_exists()))
        self.service.pause(paused)
        if not self.closed: self.job = self.root.after(100,self.poll)
    def show_access(self,result):
        key = 'checkin' if 'checkin' in self.root.page_types else 'access'
        self.root.show_page(key); page = self.root.pages[key]
        page.access_tabs.select(page.entry_tab)
        if hasattr(page,'show_result'): page.show_result(result)
        else:
            page._access_result_visible = True; page._result_search = page.search.get()
            allowed = result.get('result') == 'PERMITIDA'
            page.status_name.set(str(result.get('client_name','Cliente')))
            page.status_label.configure(text='INGRESO REGISTRADO' if allowed else 'INGRESO NO AUTORIZADO',fg='#34D399' if allowed else '#F87171')
            page.status_detail.set(ticket_access_note(result) or str(result.get('status','')))
            page.refresh_clients()
        page.refresh_history()
        if hasattr(self.root, 'refresh_all'): self.root.refresh_all(except_page=page)
    def show_completion(self, result, parent):
        outcome = result.get('result')
        if outcome in ('saved', 'verified'):
            messagebox.showinfo('Huella registrada' if outcome == 'saved' else 'Huella comprobada', result['message'], parent=parent)
        elif outcome == 'failed':
            messagebox.showerror('No se completó la lectura', result['message'], parent=parent)
    def show_unrecognized(self, message):
        key = 'checkin' if 'checkin' in self.root.page_types else 'access'
        self.root.show_page(key); page = self.root.pages[key]
        page.access_tabs.select(page.entry_tab)
        text = message + ' No se registró ninguna entrada.'
        if hasattr(page, 'badge'):
            page.badge.configure(text='HUELLA NO RECONOCIDA', bg='#3d1f2d', fg='#F87171')
            page.result_name.configure(text='Sin identificación'); page.result_details.configure(text=text)
            page.last_denied_client = None; page.override_button.configure(state='disabled')
        else:
            page._access_result_visible = True; page._result_search = page.search.get()
            page.status_name.set('Sin identificación')
            page.status_label.configure(text='HUELLA NO RECONOCIDA', fg='#F87171'); page.status_detail.set(text)
    def open(self):
        if self.window and self.window.winfo_exists(): self.window.lift(); return
        self.service.pause(True)
        win = self.window = tk.Toplevel(self.root)
        win.title('Huellas · DigitalPersona U.are.U 4500'); decorate_window(win); win.configure(bg='#0B1220')
        win.geometry('780x540'); win.minsize(600,420); win.transient(self.root)
        body = ttk.Frame(win,padding=16); body.pack(fill='both',expand=True)
        ttk.Label(body,text='Registra una huella por cliente. Se sincroniza con los equipos del gimnasio.').pack(anchor='w')
        ttk.Label(body,text='Se guarda la plantilla biométrica en la base del gimnasio, sin fotografías y con acceso restringido.',wraplength=700).pack(anchor='w',pady=(4,12))
        self.search = tk.StringVar(win)
        entry = ttk.Entry(body,textvariable=self.search); entry.pack(fill='x')
        self.search.trace_add('write',lambda *_:self.fill())
        area = ttk.Frame(body); area.pack(fill='both',expand=True,pady=12)
        self.tree = ttk.Treeview(area,columns=('name','finger'),show='headings',selectmode='browse')
        self.tree.heading('name',text='Cliente'); self.tree.heading('finger',text='Huella en la nube')
        self.tree.column('name',width=400); self.tree.column('finger',width=160)
        bar = ttk.Scrollbar(area,command=self.tree.yview); self.tree.configure(yscrollcommand=bar.set)
        self.tree.pack(side='left',fill='both',expand=True); bar.pack(side='right',fill='y')
        ttk.Label(body,textvariable=self.state,wraplength=700).pack(fill='x',pady=8)
        actions = ttk.Frame(body); actions.pack(fill='x')
        ttk.Button(actions,text='Registrar / reemplazar',command=self.enroll).pack(side='left')
        ttk.Button(actions,text='Eliminar huella',command=self.delete).pack(side='left',padx=6)
        ttk.Button(actions,text='Cancelar lectura',command=lambda:self.service.send('cancel')).pack(side='left')
        ttk.Button(body,text='Instalar controlador DigitalPersona',command=self.install).pack(anchor='w',pady=(10,0))
        tools = ttk.Frame(body); tools.pack(fill='x', pady=(6,0))
        ttk.Button(tools,text='Comprobar huella',command=self.verify).pack(side='left')
        ttk.Button(tools,text='Copiar diagnóstico',command=self.copy_diagnostic).pack(side='left',padx=6)
        def close():
            self.service.send('cancel'); self.enrolling = False; win.destroy(); self.window = None
        win.protocol('WM_DELETE_WINDOW',close)
        self.fill()
        def load():
            try: self.ui_events.put(('clients',self.root.db.list_clients()))
            except Exception: self.ui_events.put(('error','No se pudo cargar la lista de clientes. Cierra y vuelve a abrir Huellas.'))
        threading.Thread(target=load,daemon=True).start()
    def fill(self):
        if not self.window or not self.window.winfo_exists() or not hasattr(self,'tree'): return
        selected = self.tree.selection(); self.tree.delete(*self.tree.get_children())
        term = self.search.get().casefold()
        for client,c in self.clients.items():
            name = str(c.get('client_name') or c.get('full_name') or (' '.join(str(c.get(k) or '') for k in ('first_name','last_name')).strip()) or c.get('name') or client)
            if term and term not in name.casefold(): continue
            self.tree.insert('', 'end',iid=str(client),values=(name,'Registrada' if client in self.templates else 'Sin registrar'))
        if selected and self.tree.exists(selected[0]): self.tree.selection_set(selected)
    def selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo('Selecciona un cliente','Selecciona el cliente de la lista.',parent=self.window); return None
        return int(selected[0])
    def enroll(self):
        if self.enrolling: return
        client = self.selected()
        if client is None: return
        if not messagebox.askyesno('Registrar huella','Confirma que seleccionaste a la persona correcta y que autoriza registrar su huella.\n\nLa huella anterior se conservará hasta completar el nuevo registro.',parent=self.window): return
        self.enrolling = True; self.service.send('enroll',client)
    def delete(self):
        if self.enrolling: return
        client = self.selected()
        if client is not None and messagebox.askyesno('Eliminar huella','¿Eliminar la huella de este cliente en todos los equipos del gimnasio? Sus pagos y asistencias se conservan.',parent=self.window):
            self.service.send('delete',client)
    def verify(self):
        if self.enrolling: return
        client = self.selected()
        if client is None: return
        self.enrolling = True; self.service.send('verify',client)
    def copy_diagnostic(self):
        from fingerprint_diagnostics import log_path
        from product_config import VERSION
        path = log_path()
        history = path.read_text(encoding='utf-8',errors='replace')[-18000:] if path.is_file() else 'Sin eventos registrados.'
        text = f'Gym soft {VERSION}\nHuellas sincronizadas: {len(self.templates)}\nEstado: {self.state.get()}\n\n{history}'
        self.root.clipboard_clear(); self.root.clipboard_append(text)
        messagebox.showinfo('Diagnóstico copiado', 'Puedes pegar este informe en el mensaje de soporte. No incluye huellas, nombres ni contraseñas.',parent=self.window)
    def install(self):
        base = Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent
        candidates = [base/'DigitalPersonaRuntime'/'setup.exe',base.parent/'DigitalPersonaRuntime'/'setup.exe']
        target = next((p for p in candidates if p.is_file()),None)
        if target is None:
            messagebox.showerror('Controlador no disponible','Reinstala el paquete completo con el componente DigitalPersona.',parent=self.window); return
        # Official setup handles elevation and license. No hardware test is invoked.
        os.startfile(str(target))
        self.state.set('Completa el instalador del controlador. Después cierra y vuelve a abrir Gym soft.')

def install(controller):
    # QA builds simulate the reader separately and never access USB hardware.
    if os.environ.get('GYMSOFT_OFFLINE_QA') == '1' or sys.platform != 'win32': return
    if not getattr(getattr(controller.root,'db',None),'gym_id',None): return
    controller.native_reader = FingerprintPanel(controller)
