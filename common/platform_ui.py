"""System information, notifications and controlled updates using Atlantic UI Kit."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import struct
import sys
import tkinter as tk
from tkinter import ttk
from dark_files import filedialog
import zipfile

from desktop_ui import decorate_window, messagebox, friendly_error
from responsive_ui import ScrollArea, fit_window, UI_FONT
from ui_tasks import run_io
from product_config import load_config, PRODUCT_NAME
from release_info import VERSION, CHANNEL, SUPPORTED_SCHEMAS, runtime_metadata
from core_client import CoreClient
from updater import Updater


def other_windows_apps():
    """Conservative process-name check; no process termination or remote commands."""
    if sys.platform!='win32':return []
    import ctypes as C
    from ctypes import wintypes as W
    class Entry(C.Structure):
        _fields_=[('size',W.DWORD),('usage',W.DWORD),('pid',W.DWORD),('heap',C.c_size_t),('module',W.DWORD),
            ('threads',W.DWORD),('parent',W.DWORD),('priority',W.LONG),('flags',W.DWORD),('name',W.WCHAR*260)]
    api=C.WinDLL('kernel32',use_last_error=True)
    api.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD];api.CreateToolhelp32Snapshot.restype=W.HANDLE
    api.Process32FirstW.argtypes=[W.HANDLE,C.POINTER(Entry)];api.Process32FirstW.restype=W.BOOL
    api.Process32NextW.argtypes=[W.HANDLE,C.POINTER(Entry)];api.Process32NextW.restype=W.BOOL
    api.CloseHandle.argtypes=[W.HANDLE];api.CloseHandle.restype=W.BOOL
    handle=api.CreateToolhelp32Snapshot(2,0)
    if handle==C.c_void_p(-1).value:raise OSError('No se pudo comprobar qué aplicaciones siguen abiertas.')
    names={'ztatuz admin.exe','ztattuz admin.exe','ztattuz recepcion.exe','gymsoftadmin.exe','gymsoftrecepcion.exe','gymsoftcontrol.exe'}
    result=[]
    try:
        entry=Entry();entry.size=C.sizeof(Entry)
        found=api.Process32FirstW(handle,C.byref(entry))
        while found:
            if entry.pid!=os.getpid() and entry.name.casefold() in names:result.append(entry.name)
            found=api.Process32NextW(handle,C.byref(entry))
    finally:api.CloseHandle(handle)
    return result


def application_busy(root, panel=None):
    if getattr(root,'_foreground_io',False) and not getattr(root,'_update_preparing',False):return True
    door=getattr(root,'door',None)
    if door is not None and door.is_busy:return True
    biometric=getattr(getattr(root,'biometric_access',None),'native_reader',None)
    service=getattr(biometric,'service',None)
    if service is not None and (service.target is not None or service.pending is not None):return True
    for page in getattr(root,'pages',{}).values():
        pos=getattr(page,'pos',None)
        if pos is not None and (getattr(pos,'pending',None) or getattr(pos,'inventory_pending',None) or getattr(getattr(pos,'cart',None),'rows',{})):return True
    for child in root.winfo_children():
        if isinstance(child,tk.Toplevel) and child is not panel and child.winfo_exists():
            if not (getattr(root,'_update_preparing',False) and child.title()=='Preparando actualización'):return True
    try:return bool(other_windows_apps())
    except OSError:return True


class SystemPanel(tk.Toplevel):
    def __init__(self, controls):
        self.controls=controls;self.root=controls.root
        super().__init__(self.root)
        self.title('Atlantic Gym · Sistema y avisos');decorate_window(self)
        fit_window(self,900,700,parent=self.root)
        area=ScrollArea(self,padding=20);area.pack(fill='both',expand=True);body=area.body
        ttk.Label(body,text='Sistema y avisos',font=(UI_FONT,23,'bold')).pack(anchor='w')
        self.summary=ttk.Label(body,justify='left',wraplength=760);self.summary.pack(anchor='w',fill='x',pady=12)
        actions=ttk.Frame(body);actions.pack(fill='x',pady=6)
        for text,command in [('Buscar actualizaciones',self.check),('Actualizar',self.update),('Exportar diagnóstico',self.export)]:
            button=ttk.Button(actions,text=text,command=command);button.pack(side='left',padx=(0,8))
            if text=='Actualizar':self.update_button=button
        self.status=ttk.Label(body,text='',wraplength=760);self.status.pack(anchor='w',fill='x',pady=10)
        tabs=ttk.Notebook(body);tabs.pack(fill='both',expand=True)
        self.notifications=ttk.Treeview(tabs,columns=('title','type','read'),show='headings',height=8)
        for key,title,width in [('title','Aviso',440),('type','Tipo',120),('read','Leído',130)]:self.notifications.heading(key,text=title);self.notifications.column(key,width=width)
        tabs.add(self.notifications,text='Avisos')
        self.notifications.bind('<Double-1>',self.read_notification)
        self.history=ttk.Treeview(tabs,columns=('at','version','state'),show='headings',height=8)
        for key,title,width in [('at','Fecha',250),('version','Versión',130),('state','Estado',300)]:self.history.heading(key,text=title);self.history.column(key,width=width)
        tabs.add(self.history,text='Actualizaciones')
        self.release=None;self.render()

    def render(self):
        control=self.controls;core=control.core;value=core.snapshot or {}
        channel=value.get('configuration',{}).get('update_channel',CHANNEL)
        control.updater.channel=channel
        info=control.info
        self.summary.configure(text=f"{PRODUCT_NAME}\nVersión: {VERSION} · {core.architecture} · Canal: {channel}\nGimnasio: {str(core.cloud.gym_id)[:8]}… · Equipo: {core.device_id[:8]}…\nCompilación: {info['build_date']} · Commit: {info['commit'][:12]}\nSesión: {core.cloud.sessions.state} · Core: {core.state}\nÚltimo inicio correcto: {control.updater.journal.value.get('last_known_good') or 'Sin registro'}")
        self.notifications.delete(*self.notifications.get_children())
        if value.get('configuration',{}).get('notifications_enabled',True):
            for row in value.get('notifications',[]):self.notifications.insert('','end',iid=row['id'],values=(row['title'],row['type'],'Sí' if row.get('read_at') else 'No'))
        self.history.delete(*self.history.get_children())
        for index,row in enumerate(reversed(control.updater.journal.value['history'])):self.history.insert('','end',iid=str(index),values=(row['at'],row.get('version',''),row['state']))
        self.release=control.updater.select(value.get('releases',[]))
        self.status.configure(text=('Disponible: '+self.release.version+' · '+self.release.policy+'\n'+self.release.notes) if self.release else
            'No hay una versión posterior publicada para este equipo.' if core.state=='ONLINE' else 'No se pudo consultar Core. Puedes seguir usando las funciones disponibles del gimnasio.')
        self.update_button.configure(state='normal' if self.release and core.cloud.role=='admin' else 'disabled')

    def check(self):
        run_io(self,self.controls.core.sync,title='Consultando actualizaciones');self.render()

    def read_notification(self,event=None):
        selected=self.notifications.selection()
        if not selected:return
        row=next((item for item in (self.controls.core.snapshot or {}).get('notifications',[]) if item['id']==selected[0]),None)
        if row:
            messagebox.showinfo(row['title'],row['message'],parent=self)
            run_io(self,lambda:self.controls.core.sync(read_id=row['id']),title='Marcando aviso leído');self.render()

    def update(self):
        release=self.release;control=self.controls
        if not release:return
        if sys.platform!='win32' or not getattr(sys,'frozen',False):
            messagebox.showinfo('Actualización','La instalación se realiza desde el paquete Windows instalado.',parent=self);return
        if control.core.cloud.role!='admin' or application_busy(self.root,self):
            messagebox.showinfo('Finaliza las operaciones','Finaliza ventas, lecturas y formularios; cierra las otras ventanas de Atlantic Gym antes de actualizar.',parent=self);return
        if not messagebox.askyesno('Actualizar Atlantic Gym',f'¿Descargar y preparar la versión {release.version}?\n\nSe verificará SHA256 y se respaldará la configuración y los datos locales antes de cerrar.',parent=self):return
        try:
            run_io(self,lambda:control.updater.download(release),title='Descargando actualización')
            control.core.update_status=control.updater.journal.value['state']
            self.root._update_preparing=True
            try:
                roots=[Path(os.environ['LOCALAPPDATA'])/name for name in ('GymControl','GymSoft')]
                run_io(self,lambda:control.updater.prepare(release,roots,quiesce=control.core.cloud.sessions.quiesce),title='Preparando actualización')
            finally:self.root._update_preparing=False
            control.updater.launch()
            self.destroy();self.root.close_app()
        except Exception as error:
            control.updater.cancel()
            control.core.update_status=control.updater.journal.value['state']
            messagebox.showerror('Actualización no completada',friendly_error(error),parent=self)

    def export(self):
        target=filedialog.asksaveasfilename(parent=self,title='Exportar diagnóstico',defaultextension='.zip',initialfile='AtlanticGym_diagnostico.zip',filetypes=[('Diagnóstico ZIP','*.zip')])
        if not target:return
        control=self.controls
        report=dict(product=PRODUCT_NAME,version=VERSION,architecture=control.core.architecture,
            gym_id_partial=str(control.core.cloud.gym_id)[:8],device_id_partial=control.core.device_id[:8],
            session_state=control.core.cloud.sessions.state,core_state=control.core.state,grace_state=control.core.grace_state(),
            update_state=control.updater.journal.value['state'],build=control.info,
            update_history=control.updater.journal.value['history'],categories=['AUTH','NETWORK','UPDATE','CORE','DATABASE','WHATSAPP','WOMPI','ACCESS','RELAY','FINGERPRINT','STORE','SYNC'])
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:archive.writestr('diagnostico.json',json.dumps(report,ensure_ascii=False,indent=2))
        messagebox.showinfo('Diagnóstico','Diagnóstico exportado sin contraseñas, tokens, biometría ni registros de clientes.',parent=self)


class PlatformControls:
    def __init__(self,root,sidebar,cloud,edition):
        self.root=root
        config=load_config()
        from common.deployment_profile import PROFILE
        variant=PROFILE.installation_profile
        self.core=CoreClient(cloud,config.get('core_endpoint',''),VERSION,edition,variant=variant)
        cloud.client.core_control=self.core
        bits=struct.calcsize('P')*8
        self.info=runtime_metadata(PRODUCT_NAME,bits,repository=Path(__file__).resolve().parents[1] if not getattr(sys,'frozen',False) else None)
        base=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'GymControl'/'platform'/self.core.project_ref
        self.panel=None
        self.updater=Updater(base/'updates'/self.core.architecture,self.core.architecture,CHANNEL,VERSION,
            schema_supported=lambda schema:schema in SUPPORTED_SCHEMAS,busy=self.critical_busy,variant=variant)
        self.button=ttk.Button(sidebar,text='Sistema y avisos',command=self.open)
        self.button.pack(side='bottom',fill='x',padx=16,pady=10)
        self.update_notice=ttk.Frame(sidebar)
        ttk.Label(self.update_notice,text='Nueva versión disponible',wraplength=160).pack(anchor='w',pady=(0,5))
        self.notice_button=ttk.Button(self.update_notice,style='Primary.TButton',command=self.open_update)
        self.notice_button.pack(fill='x')
        self._release_identity=None
        self.available_release=None
        root.bind('<Destroy>',self.close,add='+')
        self.job=root.after(1500,self.start)

    def critical_busy(self):
        # Called by the preparation worker: inspect only plain state / OS APIs,
        # never Tk widgets or Tk variables from this thread.
        root=self.root
        if getattr(root,'_foreground_io',False) and not getattr(root,'_update_preparing',False):return True
        door=getattr(root,'door',None)
        if door is not None and door.is_busy:return True
        for page in getattr(root,'pages',{}).values():
            pos=getattr(page,'pos',None)
            if pos is not None and (getattr(pos,'pending',None) or getattr(pos,'inventory_pending',None) or getattr(getattr(pos,'cart',None),'rows',{})):return True
        biometric=getattr(getattr(root,'biometric_access',None),'native_reader',None)
        service=getattr(biometric,'service',None)
        if service is not None and (service.target is not None or service.pending is not None):return True
        try:return bool(other_windows_apps())
        except OSError:return True

    def start(self):
        self.job=None
        if not getattr(self.root,'ready',False):self.job=self.root.after(500,self.start);return
        self.updater.confirm_started(healthy=self.core.cloud.sessions.state=='ONLINE')
        self.core.update_status=self.updater.journal.value['state']
        door=getattr(self.root,'door',None)
        if door is not None:
            try:self.core.hardware_metadata['relay_configured']=bool(door.store.load().enabled)
            except Exception:pass
        biometric=getattr(getattr(self.root,'biometric_access',None),'native_reader',None)
        self.core.hardware_metadata['fingerprint_configured']=biometric is not None
        if os.environ.get('GYMSOFT_OFFLINE_QA')!='1':self.core.start()
        self.job=self.root.after(5000,self.poll)

    def poll(self):
        self.job=None
        count=sum(not row.get('read_at') for row in (self.core.snapshot or {}).get('notifications',[]))
        self.button.configure(text=f'Sistema y avisos ({count})' if count else 'Sistema y avisos')
        snapshot=self.core.snapshot or {}
        channel=snapshot.get('configuration',{}).get('update_channel',CHANNEL)
        releases=snapshot.get('releases',[])
        identity=(channel,json.dumps(releases,sort_keys=True,separators=(',',':')))
        if identity!=self._release_identity:
            self.updater.channel=channel
            self.available_release=self.updater.select(releases)
            self._release_identity=identity
        release=self.available_release
        if release:
            self.notice_button.configure(text=('Actualizar a ' if self.core.cloud.role=='admin' else 'Ver versión ')+release.version)
            if not self.update_notice.winfo_manager():
                self.update_notice.pack(side='bottom',fill='x',padx=16,pady=(2,6))
        else:self.update_notice.pack_forget()
        self.job=self.root.after(5000,self.poll)

    def open_update(self):
        panel=self.open()
        if self.core.cloud.role=='admin':
            panel.after_idle(panel.update)

    def open(self):
        if self.panel is not None and self.panel.winfo_exists():self.panel.lift();return self.panel
        self.panel=SystemPanel(self)
        return self.panel

    def close(self,event):
        if event.widget is not self.root:return
        if self.job:self.root.after_cancel(self.job);self.job=None
        self.core.close()
        if not self.updater.prepared:self.updater.cancel()


def install_controls(root,sidebar,cloud,edition):
    # View-only regression shells do not construct an authenticated cloud client.
    if not hasattr(cloud,'sessions'):return None
    try:
        root.platform_controls=PlatformControls(root,sidebar,cloud,edition)
        return root.platform_controls
    except Exception as error:
        import logging
        logging.getLogger('Atlantic.CORE').warning('System controls unavailable (%s).',type(error).__name__)
        ttk.Button(sidebar,text='Información de plataforma',command=lambda:messagebox.showinfo(
            'Plataforma no disponible','No se pudo iniciar el servicio de plataforma. Las funciones disponibles del gimnasio siguen abiertas. Contacta al soporte.',parent=root)).pack(side='bottom',fill='x',padx=16,pady=10)
        return None
