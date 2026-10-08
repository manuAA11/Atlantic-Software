"""Editor privado: identidad de destino fija, consultas paginadas y tareas en cola."""
from __future__ import annotations

from responsive_ui import AutoScrollbar
from datetime import datetime
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk
from responsive_ui import UI_FONT
from desktop_ui import Modal, BG, SURFACE, TEXT, MUTED, button, friendly_error, messagebox
from dark_files import filedialog
from owner_editor_forms import (TABLES,LABELS,ENUMS,confirmation,email_params,profile_params,
                                 record_patch,read_backup,write_backup)
from owner_forms import required
from ui_text import state_text, readable


class RecordForm(Modal):
    def __init__(self,parent,item,columns,table):
        super().__init__(parent,'Editar registro · '+str(item['data']['id']))
        self.columns=columns;self.item=item;self.entries={};self.table=table
        ttk.Label(self.body,text='Edita los datos necesarios e indica el motivo. Los identificadores y las relaciones se conservan.',
                  wraplength=630).pack(anchor='w',pady=(0,10))
        if table=='memberships':
            ttk.Label(self.body,text='Anular excluye el pago de los ingresos y de la vigencia. Corregir el valor también actualiza el importe pagado.',
                      wraplength=630).pack(anchor='w',pady=(0,8))
        box=ttk.Frame(self.body);box.pack(fill='both',expand=True)
        height=min(450,max(180,self.winfo_screenheight()-330))
        canvas=tk.Canvas(box,bg=BG,highlightthickness=0,width=640,height=height)
        scroll=AutoScrollbar(box,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(side='left',fill='both',expand=True)
        box._responsive_skip=True
        fields=ttk.Frame(canvas);handle=canvas.create_window((0,0),window=fields,anchor='nw')
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(handle,width=e.width))
        fields.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        fields.columnconfigure(1,weight=1)
        row=0
        for col in columns:
            if not col['editable']:continue
            key=col['name'];val=item['data'].get(key)
            ttk.Label(fields,text=LABELS.get(key,key)).grid(row=row,column=0,sticky='w',padx=(0,14),pady=7)
            if col['type']=='boolean':val='Sí' if val else 'No'
            var=tk.StringVar(self,value='' if val is None else str(state_text(key,val)))
            options=['Sí','No'] if col['type']=='boolean' else ENUMS.get(key)
            if key=='status' and table=='classes':options=['PROGRAMADA','CANCELADA','COMPLETADA']
            if key=='status' and table=='reservations':options=['RESERVADA','CANCELADA']
            if options:options=[state_text(key,v) for v in options]
            entry=(ttk.Combobox(fields,textvariable=var,values=options,state='readonly') if options else ttk.Entry(fields,textvariable=var))
            entry.grid(row=row,column=1,sticky='ew',pady=7);self.entries[key]=var
            if row==0:self.initial_focus=entry
            row+=1
        ttk.Label(self.body,text='Motivo del cambio (obligatorio)').pack(anchor='w',pady=(12,3))
        self.reason=tk.StringVar(self);ttk.Entry(self.body,textvariable=self.reason).pack(fill='x')
        self.feedback=tk.StringVar(self)
        tk.Label(self.body,textvariable=self.feedback,bg=BG,fg='#fbbf24',wraplength=640,justify='left').pack(fill='x',pady=8)
        bar=ttk.Frame(self.body);bar.pack(fill='x')
        button(bar,text='Cancelar',command=self.close).pack(side='left')
        button(bar,text='Guardar cambio',command=self.accept,primary=True).pack(side='right')
        self.show()

    def accept(self):
        try:
            reason=required(self.reason.get(),'Motivo',3,500)
            patch=record_patch(self.columns,self.item['data'],{k:v.get() for k,v in self.entries.items()})
        except ValueError as error:self.feedback.set(str(error));return
        self.close({'p_patch':patch,'p_reason':reason})


class OwnerEditor(Modal):
    def __init__(self,parent,gym,form_class):
        super().__init__(parent,'Editor del propietario · '+gym['name'])
        self.preferred_width=1040
        self.panel=parent;self.gym=dict(gym);self.form=form_class
        self.busy=False;self.queue=queue.Queue();self.ending=False;self.poll_id=None
        self.users_loaded=False
        self.items={};self.columns=[];self.offset=0;self.total=0;self.loaded_table=None
        self.title_var=tk.StringVar(self,value=gym['name'])
        ttk.Label(self.body,textvariable=self.title_var,font=(UI_FONT,22,'bold')).pack(anchor='w')
        ttk.Label(self.body,text='ID del gimnasio: '+gym['id'],foreground=MUTED).pack(anchor='w',pady=(3,10))
        tabs=ttk.Notebook(self.body);tabs.pack(fill='both',expand=True)
        profile=ttk.Frame(tabs,padding=14);tabs.add(profile,text='Gimnasio y correos')
        ttk.Label(profile,text='Edita los datos del gimnasio y asigna el correo de cada responsable.',wraplength=780).pack(anchor='w',pady=(0,12))
        bar=ttk.Frame(profile);bar.pack(fill='x')
        ttk.Button(bar,text='✎  Nombre y datos del gimnasio',command=self.edit_profile).pack(side='left',padx=(0,8))
        ttk.Button(bar,text='＋  Asignar correo y rol',command=self.assign_email).pack(side='left')
        ttk.Label(profile,text='Las cuentas existentes conservan su contraseña. Para un correo nuevo, entrega el código de activación.\nPuedes cambiar el rol volviendo a asignar ese correo. Los equipos siguen necesitando autorización.',wraplength=780,foreground=MUTED).pack(anchor='w',pady=14)
        self.access_items={}
        self.users=self.make_tree(profile,['email','role','enabled','expires'],['Correo','Rol','Estado','Vencimiento invitación (UTC)'],height=8)
        userbar=ttk.Frame(profile);userbar.pack(fill='x',pady=8)
        ttk.Button(userbar,text='↻  Actualizar usuarios',command=self.load_users).pack(side='left')
        ttk.Button(userbar,text='Revocar invitación pendiente',command=self.revoke_invite).pack(side='left',padx=8)
        records=ttk.Frame(tabs,padding=12);tabs.add(records,text='Registros')
        bar=ttk.Frame(records);bar.pack(fill='x',pady=(0,10))
        self.table_var=tk.StringVar(self,value='Clientes');self.search_var=tk.StringVar(self)
        picker=ttk.Combobox(bar,textvariable=self.table_var,values=list(TABLES),state='readonly',width=25)
        picker.pack(side='left');picker.bind('<<ComboboxSelected>>',lambda _:self.load_records(reset=True))
        self.picker=picker
        ttk.Entry(bar,textvariable=self.search_var,width=24).pack(side='left',padx=8)
        ttk.Button(bar,text='Buscar / actualizar',command=lambda:self.load_records(reset=True)).pack(side='left')
        self.tree=self.make_tree(records,['id'],['ID'],height=9)
        self.tree.bind('<Double-1>',lambda _:self.edit_record())
        nav=ttk.Frame(records);nav.pack(fill='x',pady=9)
        ttk.Button(nav,text='Anterior',command=lambda:self.page(-1)).pack(side='left')
        ttk.Button(nav,text='Siguiente',command=lambda:self.page(1)).pack(side='left',padx=8)
        self.page_var=tk.StringVar(self,value='Selecciona Buscar / actualizar para cargar.')
        ttk.Label(nav,textvariable=self.page_var,foreground=MUTED).pack(side='left')
        action=ttk.Frame(records);action.pack(fill='x')
        for label,command in [('✎  Editar seleccionado',self.edit_record),('Ver detalle',self.show_record),('Eliminar registro…',self.delete_record)]:
            ttk.Button(action,text=label,command=command).pack(side='left',padx=(0,8))
        ttk.Label(records,text='Los registros con dependencias deben revisarse antes de eliminarlos. Corregir o eliminar una venta ajusta el inventario.',wraplength=840,foreground=MUTED).pack(anchor='w',pady=(10,0))
        database=ttk.Frame(tabs,padding=16);tabs.add(database,text='Base de datos y eliminación')
        ttk.Label(database,text='Descargar base de datos',font=(UI_FONT,15,'bold')).pack(anchor='w')
        ttk.Label(database,text='Copia JSON con datos operativos, contrato, mensualidades, usuarios, equipos e historial.\nNo contiene contraseñas ni claves de acceso.',wraplength=790).pack(anchor='w',pady=8)
        ttk.Button(database,text='↓  Descargar respaldo completo',command=self.download).pack(anchor='w')
        ttk.Label(database,text='Importar / restaurar',font=(UI_FONT,15,'bold')).pack(anchor='w',pady=(20,0))
        ttk.Label(database,text='Reemplaza los datos operativos del gimnasio seleccionado desde un respaldo JSON de Gym soft.\nConserva su identificador, contrato, mensualidades y usuarios. La auditoría anterior se conserva.\nWhatsApp queda pausado. Suspende o cancela primero el gimnasio desde el panel principal.',wraplength=790).pack(anchor='w',pady=8)
        ttk.Button(database,text='↑  Importar respaldo…',command=self.import_data).pack(anchor='w')
        ttk.Label(database,text='Eliminar completamente',font=(UI_FONT,15,'bold'),foreground='#fb7185').pack(anchor='w',pady=(20,0))
        ttk.Label(database,text='Borra el gimnasio, sus registros, contrato, mensualidades, historial y permisos de acceso.\nCancelar contrato mantiene los datos. Esta opción los elimina y sólo podrás recuperarlos desde tu copia.\nLas cuentas de inicio de sesión quedan desvinculadas y pierden el acceso al gimnasio.',wraplength=790).pack(anchor='w',pady=8)
        ttk.Button(database,text='Eliminar gimnasio completamente…',command=self.delete_gym).pack(anchor='w')
        footer=ttk.Frame(self.body);footer.pack(fill='x',pady=(12,0))
        self.status=tk.StringVar(self,value='Conectado · Editor exclusivo del propietario')
        ttk.Label(footer,textvariable=self.status,wraplength=760,foreground=MUTED).pack(side='left')
        ttk.Button(footer,text='Cerrar editor',command=self.close).pack(side='right')
        self.poll_id=self.after(100,self.poll)
        # Inicia la consulta antes de mostrar el editor. No hay un intervalo
        # en el que los controles parezcan disponibles sin haber cargado nada.
        self.load_users()
        self.show()

    def make_tree(self,parent,columns,labels,height):
        frame=ttk.Frame(parent);frame.pack(fill='both',expand=True)
        tree=ttk.Treeview(frame,columns=columns,show='headings',selectmode='browse',height=height)
        for col,label in zip(columns,labels):tree.heading(col,text=label);tree.column(col,width=230)
        sy=AutoScrollbar(frame,orient='vertical',command=tree.yview);sx=AutoScrollbar(frame,orient='horizontal',command=tree.xview)
        tree.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        tree.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
        frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
        return tree

    def call(self,name,params):return self.panel.rpc(name,params)

    def run(self,work,done):
        if self.busy or self.ending:return
        self.busy=True;self.status.set('Procesando… Espera antes de cerrar.')
        self.controls(False)
        def worker():
            try:self.queue.put((True,work(),done))
            except Exception as error:self.queue.put((False,error,done))
        threading.Thread(target=worker,daemon=True).start()

    def controls(self,enabled):
        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child,ttk.Button):child.configure(state='normal' if enabled else 'disabled')
                walk(child)
        walk(self.body)
        self.picker.configure(state='readonly' if enabled else 'disabled')

    def poll(self):
        if self.ending:return
        try:
            ok,data,done=self.queue.get_nowait();self.busy=False;self.controls(True)
            self.status.set('Operación completada' if ok else 'No se completó la operación')
            if ok:done(data)
            else:messagebox.showerror('Editor del propietario',friendly_error(data),parent=self)
        except queue.Empty:pass
        except Exception as error:messagebox.showerror('Editor del propietario',friendly_error(error),parent=self)
        finally:
            if not self.ending:self.poll_id=self.after(100,self.poll)

    def close(self,result=None):
        if getattr(self,'busy',False):
            self.status.set('Espera a que termine la operación antes de cerrar.');return
        self.ending=True
        if getattr(self,'poll_id',None):self.after_cancel(self.poll_id)
        super().close(result)

    def load_users(self):
        if self.busy:return
        self.users_loaded=False
        self.access_items={};self.users.delete(*self.users.get_children())
        def done(data):
            self.users.delete(*self.users.get_children())
            for row in data.get('users',[]):
                key=self.users.insert('','end',values=(row['email'],'Administración' if row['role']=='admin' else 'Recepción','Habilitado' if row['enabled'] else 'Deshabilitado','—'))
                self.access_items[key]={**row,'pending':False}
            for row in data.get('invitations',[]):
                key=self.users.insert('','end',values=(row['email'],'Administración' if row['role']=='admin' else 'Recepción','Invitación vencida' if row['expired'] else 'Activación pendiente',row['expires_at'][:19].replace('T',' ')))
                self.access_items[key]={**row,'pending':True}
            self.users_loaded=True
        self.run(lambda:self.call('owner_editor_access',{'p_gym_id':self.gym['id']}),done)

    def revoke_invite(self):
        if self.busy:return
        ids=self.users.selection();item=self.access_items.get(ids[0]) if ids else None
        if not item or not item['pending']:
            messagebox.showinfo('Invitación','Selecciona una invitación pendiente. Los usuarios activos se deshabilitan desde el panel principal.',parent=self);return
        raw=self.form(self,'Revocar invitación',[('reason','Motivo','')],
            validate=lambda f:required(f.get('reason'),'Motivo',3,500),hint=f"Gimnasio: {self.gym['name']}\nCorreo: {item['email']}\nSu código dejará de funcionar.").result
        if not raw:return
        params={'p_gym_id':self.gym['id'],'p_email':item['email'],'p_reason':raw}
        self.run(lambda:self.call('owner_editor_revoke_invite',params),lambda _:self.load_users())

    def edit_profile(self):
        if self.busy:return
        g=self.gym
        result=self.form(self,'Nombre y datos del gimnasio',[
            ('name','Nombre',g['name']),('email','Correo de contacto',g['contact_email']),
            ('timezone','Zona horaria',g['timezone']),('plan','Plan comercial',g['plan']),('reason','Motivo','')],
            validate=lambda raw:profile_params(g,raw),hint='El correo de contacto no cambia la cuenta de inicio de sesión. Asigna las cuentas por separado.').result
        if not result:return
        def done(data):
            self.gym.update(name=result['p_name'],contact_email=result['p_email'],timezone=result['p_timezone'],plan=result['p_plan'])
            self.title_var.set(self.gym['name']);self.status.set('Datos del gimnasio guardados')
        self.run(lambda:self.call('owner_editor_profile',result),done)

    def assign_email(self):
        if self.busy:return
        ids=self.users.selection();item=self.access_items.get(ids[0],{}) if ids else {}
        result=self.form(self,'Asignar correo y rol',[
            ('email','Correo de la persona',item.get('email','')),('role','Rol','Administración' if item.get('role')=='admin' else 'Recepción'),('reason','Motivo','')],
            choices={'role':['Administración','Recepción']},validate=lambda raw:email_params(self.gym,raw),
            hint='Una cuenta confirmada recibirá acceso; para un correo nuevo obtendrás un código. Si ya tenía uno pendiente, se reemplaza. No se envía correo automáticamente.').result
        if not result:return
        role='Administración' if result['p_role']=='admin' else 'Recepción'
        if not messagebox.askyesno('Confirmar acceso',f"Gimnasio: {self.gym['name']}\nCorreo: {result['p_email']}\nRol: {role}\n\n¿Asignar este acceso?",parent=self):return
        def done(data):
            if data['state']=='invited':
                try:self.clipboard_clear();self.clipboard_append(data['activation_code'])
                except tk.TclError:pass
                messagebox.showinfo('Código de activación',f"{data['email']} · {role}\n\n{data['activation_code']}\n\nEntrega el código únicamente a esta persona. Tiene 7 días para crear o confirmar su cuenta y activar el acceso.",parent=self)
            else:messagebox.showinfo('Acceso asignado',f"{data['email']} ya tiene acceso como {role}.\nDebe iniciar sesión de nuevo. El equipo necesita autorización.",parent=self)
            self.load_users()
        self.run(lambda:self.call('owner_editor_email',result),done)

    def load_records(self,reset=False):
        if self.busy:return
        if reset:self.offset=0
        table=TABLES[self.table_var.get()];search=self.search_var.get().strip();offset=self.offset
        self.items={};self.loaded_table=None;self.tree.delete(*self.tree.get_children())
        def done(data):
            self.loaded_table=table;self.columns=data['columns'];self.total=data['total']
            visible=[c['name'] for c in self.columns if c['name'] not in ('gym_id','photo_path','image_data') and
                     (c['editable'] or c['name'] in ('id','client_id','plan_id','product_id','trainer_id','full_name','created_at','action','summary','status','client_name','phone'))]
            self.tree.configure(columns=visible)
            for col in visible:self.tree.heading(col,text=LABELS.get(col,col));self.tree.column(col,width=150,minwidth=65)
            for item in data['rows']:
                key=str(item['data']['id']);self.items[key]=item
                self.tree.insert('','end',iid=key,values=[self.display(item['data'].get(c),c) for c in visible])
            self.page_var.set(f"{offset+1 if data['rows'] else 0}–{offset+len(data['rows'])} de {self.total}")
        self.run(lambda:self.call('owner_editor_rows',{'p_gym_id':self.gym['id'],'p_table':table,'p_search':search,'p_offset':offset,'p_limit':50}),done)

    @staticmethod
    def display(value,field=''):
        if value is None:return '—'
        if isinstance(value,bool):return 'Sí' if value else 'No'
        return str(state_text(field,value)).replace('\n',' ')[:120]

    def page(self,step):
        if self.busy:return
        nxt=self.offset+step*50
        if nxt<0 or nxt>=self.total:return
        self.offset=nxt;self.load_records()

    def selected(self):
        if self.busy:return None
        selected=self.tree.selection()
        if not selected or self.loaded_table!=TABLES[self.table_var.get()]:
            messagebox.showinfo('Registro','Busca y selecciona un registro de esta tabla.',parent=self);return None
        return self.items.get(selected[0])

    def show_record(self):
        item=self.selected()
        if not item:return
        modal=Modal(self,'Detalle del registro')
        text=tk.Text(modal.body,width=90,height=22,bg=SURFACE,fg=TEXT,insertbackground=TEXT,wrap='word',highlightthickness=0)
        text.pack(fill='both',expand=True)
        text.insert('1.0','\n\n'.join(f'{LABELS.get(k,k.replace("_"," ").capitalize())}: {readable(v,k)}' for k,v in item['data'].items()))
        text.configure(state='disabled')
        button(modal.body,text='Cerrar',command=modal.close).pack(anchor='e',pady=(12,0));modal.show()

    def edit_record(self):
        item=self.selected()
        if not item:return
        if not any(c['editable'] for c in self.columns):self.show_record();return
        result=RecordForm(self,item,self.columns,self.loaded_table).result
        if not result:return
        params={'p_gym_id':self.gym['id'],'p_table':self.loaded_table,'p_id':item['data']['id'],'p_expected':item['version'],**result}
        self.run(lambda:self.call('owner_editor_record',params),lambda _:self.load_records())

    def backup_path(self,purpose='Respaldo'):
        return filedialog.asksaveasfilename(title=purpose,defaultextension='.json',
            initialfile='GymSoft-'+self.gym['id']+'-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json',parent=self)

    def download(self):
        if self.busy:return
        path=self.backup_path()
        if not path:return
        def work():
            data=self.call('owner_editor_backup',{'p_gym_id':self.gym['id']});write_backup(path,data);return data
        self.run(work,lambda _:messagebox.showinfo('Respaldo guardado',str(path),parent=self))

    def with_backup(self,done):
        path=self.backup_path('Guardar copia ANTES de reemplazar o eliminar')
        if not path:return
        def work():
            data=self.call('owner_editor_backup',{'p_gym_id':self.gym['id']});write_backup(path,data);return data
        self.run(work,lambda snapshot:done(snapshot,path))

    def delete_record(self):
        item=self.selected()
        if not item:return
        if not any(c['editable'] for c in self.columns):
            messagebox.showinfo('Sólo consulta','Esta tabla conserva el historial y no permite borrar filas desde el editor.',parent=self);return
        table=self.loaded_table
        def ready(snapshot,path):
            result=self.form(self,'Eliminar registro',[
                ('name','Nombre exacto del gimnasio',''),('reason','Motivo','')],
                validate=lambda raw:confirmation(self.gym,raw),
                hint=f"{self.gym['name']} · {self.table_var.get()} · ID {item['data']['id']}\nCopia guardada: {path}\nLos registros con dependencias no se eliminan.").result
            if not result:return
            params={'p_gym_id':self.gym['id'],'p_table':table,'p_id':item['data']['id'],'p_expected':item['version'],'p_patch':{},'p_reason':result['p_reason'],'p_delete':True}
            self.run(lambda:self.call('owner_editor_record',params),lambda _:self.load_records())
        self.with_backup(ready)

    def delete_gym(self):
        if self.busy:return
        if not messagebox.askyesno('Eliminar gimnasio',f"Se eliminará completamente {self.gym['name']}.\nPrimero debes haberlo suspendido o cancelado desde el panel.\n\n¿Continuar para guardar una copia y revisar el borrado?",parent=self):return
        def ready(snapshot,path):
            counts=' · '.join(f'{TABLES_LABEL.get(k,k)}: {v}' for k,v in snapshot['counts'].items() if v)
            result=self.form(self,'Confirmar borrado completo',[
                ('name','Escribe el nombre del gimnasio',''),('reason','Motivo del borrado','')],
                validate=lambda raw:confirmation(self.gym,raw),
                hint=f"Gimnasio: {self.gym['name']}\n{counts}\nCopia: {path}\nSe borrarán también contrato, mensualidades, historial, invitaciones y accesos.").result
            if not result:return
            if not messagebox.askyesno('Última confirmación',f"¿Eliminar ahora {self.gym['name']} y todos sus datos de la base comercial?\nEsta operación no se deshace desde el panel.",parent=self):return
            params={'p_gym_id':self.gym['id'],'p_expected':snapshot['fingerprint'],**result}
            def done(data):
                messagebox.showinfo('Gimnasio eliminado',f"Se eliminó {self.gym['name']}.\nTu respaldo está en: {path}",parent=self)
                self.close(True)
            self.run(lambda:self.call('owner_editor_delete_gym',params),done)
        self.with_backup(ready)

    def import_data(self):
        if self.busy:return
        path=filedialog.askopenfilename(title='Importar respaldo de Gym soft',filetypes=[('Respaldo JSON','*.json')],parent=self)
        if not path:return
        try:data=read_backup(path)
        except (ValueError,OSError) as error:messagebox.showerror('Respaldo inválido',str(error),parent=self);return
        def validated(preview):
            if not messagebox.askyesno('Revisar importación',f"Origen: {preview['source_name']}\nID del gimnasio de origen: {preview['source_gym_id']}\nDestino: {self.gym['name']}\nID del gimnasio de destino: {self.gym['id']}\nFilas en el archivo: {preview['total']}\n\nSe reemplazarán los datos operativos. Contrato, cuentas y auditoría no se importan.\n¿Guardar una copia del destino y continuar?",parent=self):return
            def ready(snapshot,backup_path):
                result=self.form(self,'Confirmar reemplazo de datos',[
                    ('name','Nombre del gimnasio de DESTINO',''),('reason','Motivo','')],
                    validate=lambda raw:confirmation(self.gym,raw),
                    hint=f"Destino: {self.gym['name']}\nOrigen: {preview['source_name']} · {preview['source_gym_id']}\nCopia anterior: {backup_path}\nEl gimnasio debe estar suspendido o cancelado. WhatsApp quedará pausado.").result
                if not result:return
                params={'p_gym_id':self.gym['id'],'p_data':data,'p_expected':snapshot['fingerprint'],**result}
                def done(result):
                    messagebox.showinfo('Importación completada',f"Se importaron {result['imported']} registros en {self.gym['name']}.\nRevisa los datos antes de reactivar el gimnasio. WhatsApp permanece pausado.",parent=self)
                    self.offset=0;self.load_records()
                self.run(lambda:self.call('owner_editor_import',params),done)
            self.with_backup(ready)
        self.run(lambda:self.call('owner_editor_validate_import',{'p_data':data}),validated)


TABLES_LABEL={v:k for k,v in TABLES.items()}
