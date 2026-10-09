from __future__ import annotations
from atlantic_ui import COPYRIGHT
from product_config import PRODUCT_NAME

from responsive_ui import AutoScrollbar
from ui_performance import DataTreeview, clear_tree

import csv
import json
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk
from responsive_ui import UI_FONT
from responsive_ui import ScrollArea, fit_window, enable_dpi_awareness
from dark_files import filedialog
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import uuid

from PIL import Image, ImageTk
from cloud import CloudService, LoginDialog
from product_config import VERSION
from desktop_ui import (Modal, button, configure_dark_styles, decorate_window,
                        friendly_error, messagebox, simpledialog, set_app_id)
from owner_forms import (amount, contract_params, grace_params, invite_params,
                         new_gym_params, renewal_params, required)
from owner_editor_forms import write_backup
from ui_text import OWNER_ACTIONS, readable
from gym_time import display_timestamp, DEFAULT_ZONE, parse_instant

STATUS = {'trial':'Prueba','active':'Activa','grace':'Gracia','expired':'Vencida','suspended':'Suspendida','cancelled':'Cancelada'}
BG, SURFACE, TEXT, MUTED, GREEN = '#0b1220', '#172235', '#f8fafc', '#94a3b8', '#34d399'

def resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / filename
    return Path(__file__).resolve().parent / filename

def set_window_icon(window):
    decorate_window(window)

def date_text(value, zone=DEFAULT_ZONE):
    if not value: return '—'
    if len(str(value)) == 10: return str(value)
    return display_timestamp(value, zone)

def money(value):
    return f'{Decimal(str(value or 0)):,.2f}'

class Form(Modal):
    def __init__(self, parent, title, fields, *, validate=None, choices=None, hint=''):
        super().__init__(parent, title)
        self.validate = validate
        self.raw = None
        self.vars = {}
        frame = self.body
        frame.columnconfigure(1, weight=1)
        tk.Label(frame, text=title, bg=BG, fg=TEXT, font=(UI_FONT,17,'bold')).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,18))
        first_entry = None
        for row,(key,label,default) in enumerate(fields,1):
            tk.Label(frame,text=label,bg=BG,fg=TEXT,font=(UI_FONT,10)).grid(row=row,column=0,sticky='w',padx=(0,20),pady=7)
            var=tk.StringVar(master=self,value='' if default is None else str(default)); self.vars[key]=var
            if choices and key in choices:
                entry=ttk.Combobox(frame,textvariable=var,values=choices[key],state='readonly',width=36)
            else:
                entry=ttk.Entry(frame,textvariable=var,width=38)
            entry.grid(row=row,column=1,sticky='ew',pady=7)
            if row==1:first_entry=entry
        self.feedback=tk.StringVar(master=self,value=hint)
        tk.Label(frame,textvariable=self.feedback,bg=BG,fg='#fbbf24',wraplength=580,
                 justify='left').grid(row=len(fields)+1,column=0,columnspan=2,sticky='ew',pady=(12,0))
        buttons=tk.Frame(frame,bg=BG);buttons.grid(row=len(fields)+2,column=0,columnspan=2,sticky='e',pady=(18,0))
        button(buttons,text='Cancelar',command=self.close).pack(side='left',padx=6)
        button(buttons,text='Continuar',command=self.accept,primary=True).pack(side='left')
        self.bind('<Return>',lambda _:self.accept())
        self.initial_focus=first_entry
        self.show()

    def accept(self):
        raw={k:v.get().strip() for k,v in self.vars.items()}
        try:
            result=self.validate(raw) if self.validate else raw
        except (ValueError,InvalidOperation) as error:
            self.feedback.set(friendly_error(error))
            return
        self.raw=raw
        self.close(result)

class OwnerPanel(tk.Tk):
    def __init__(self):
        enable_dpi_awareness()
        set_app_id('Propietario')
        super().__init__()
        from desktop_ui import install_error_handler
        install_error_handler(self)
        set_window_icon(self)
        self.title(f'Atlantic Gym · Control comercial {VERSION}')
        fit_window(self,1340,880,minimum=(760,480)); self.configure(bg=BG)
        self.rows={}; self.detail={}; self.detail_target=None; self.pending_detail=None
        self.pending_renewals={}; self.busy=False; self.queue=queue.Queue()
        self._populating=False; self._closing=False; self._poll_id=None
        self.configure_style()
        startup=ttk.Label(self,text='Atlantic Gym · Panel del propietario\nInicia sesión para administrar tus gimnasios.',anchor='center')
        startup.pack(fill='both',expand=True)
        self.update_idletasks()
        while True:
            try:
                dialog=LoginDialog(self,owner=True)
                self.wait_window(dialog)
                if not dialog.result:
                    self.destroy(); return
                self.cloud=CloudService()
                self.cloud.sign_in(*dialog.result)
                data=self.cloud.client.rpc('owner_list_gyms').execute().data
                break
            except Exception as error:
                if not messagebox.askretrycancel('Acceso al panel',friendly_error(error),parent=self):
                    self.destroy();return
        startup.destroy()
        self.build_ui(); self.render(data)
        self.protocol('WM_DELETE_WINDOW',self.close_panel)
        self._poll_id=self.after(150,self.poll)

    def configure_style(self):
        configure_dark_styles(self)
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',background=BG,foreground=TEXT,font=(UI_FONT,10))
        style.configure('TFrame',background=BG)
        style.configure('Card.TFrame',background=SURFACE)
        style.configure('TLabel',background=BG,foreground=TEXT)
        style.configure('Muted.TLabel',foreground=MUTED)
        style.configure('TButton',background='#24354f',foreground=TEXT,padding=(11,8),borderwidth=0)
        style.map('TButton',background=[('active','#305180')])
        style.configure('TEntry',fieldbackground=SURFACE,foreground=TEXT,insertcolor=TEXT,padding=6)
        style.configure('TCombobox',fieldbackground=SURFACE,foreground=TEXT)
        style.configure('Treeview',background=SURFACE,fieldbackground=SURFACE,foreground=TEXT,rowheight=32,borderwidth=0)
        style.configure('Treeview.Heading',background='#22314b',foreground=MUTED,padding=9)
        style.map('Treeview',background=[('selected','#214a70')])
        style.configure('TNotebook',background=BG,borderwidth=0)
        style.configure('TNotebook.Tab',padding=(18,10),background=SURFACE,foreground=TEXT)
        style.map('TNotebook.Tab',background=[('selected','#214a70')])

    def build_ui(self):
        self.viewport=ScrollArea(self,padding=22,minimum_width=420)
        self.viewport.pack(fill='both',expand=True);outer=self.viewport.body
        header=ttk.Frame(outer);header.pack(fill='x')
        ttk.Label(header,text='Atlantic Gym · Control comercial',font=(UI_FONT,25,'bold')).pack(side='left')
        ttk.Button(header,text='↻  Actualizar',command=self.refresh).pack(side='right')
        ttk.Button(header,text='✎  Editor del propietario',command=self.open_editor).pack(side='right',padx=10)
        ttk.Label(outer,text='Gimnasios, mensualidades y accesos desde tu cuenta de propietario.',style='Muted.TLabel').pack(anchor='w',pady=(4,18))
        ttk.Label(outer,text=COPYRIGHT,style='Muted.TLabel',wraplength=700).pack(anchor='w',pady=(0,12))
        cards=ttk.Frame(outer);cards.pack(fill='x',pady=(0,14))
        self.metrics=[]
        for title in ['GIMNASIOS','ACCESO ACTIVO','VENCEN EN 7 DÍAS','EQUIPOS PENDIENTES']:
            f=tk.Frame(cards,bg=SURFACE,padx=18,pady=12);f.pack(side='left',fill='x',expand=True,padx=(0,10))
            tk.Label(f,text=title,bg=SURFACE,fg=MUTED,font=(UI_FONT,9)).pack(anchor='w')
            label=tk.Label(f,text='0',bg=SURFACE,fg=GREEN,font=(UI_FONT,24,'bold'));label.pack(anchor='w');self.metrics.append(label)
        toolbar=ttk.Frame(outer);toolbar.pack(fill='x')
        for label,command in [('＋  Nuevo gimnasio',self.new_gym),('$  Registrar mensualidad',self.renew),('⚙  Contrato',self.contract),('✉  Invitar usuario',self.invite),('▣  Respaldo',self.backup)]:
            ttk.Button(toolbar,text=label,command=command).pack(side='left',padx=(0,7))
        second=ttk.Frame(outer);second.pack(fill='x',pady=(8,12))
        for label,command in [('Ⅱ  Suspender',lambda:self.status('suspended')),('▶  Reactivar',lambda:self.status('active')),('×  Cancelar contrato',lambda:self.status('cancelled')),('◷  Dar días de gracia',self.grace),('↓  Exportar listado',self.export_list)]:
            ttk.Button(second,text=label,command=command).pack(side='left',padx=(0,7))
        filterbar=ttk.Frame(outer);filterbar.pack(fill='x',pady=(0,10))
        self.search=tk.StringVar();self.filter=tk.StringVar(value='Todos')
        ttk.Label(filterbar,text='Buscar').pack(side='left',padx=(0,8))
        ttk.Entry(filterbar,textvariable=self.search,width=42).pack(side='left')
        ttk.Combobox(filterbar,textvariable=self.filter,values=['Todos']+list(STATUS.values()),state='readonly',width=18).pack(side='left',padx=10)
        self.search.trace_add('write',lambda *_:self.populate());self.filter.trace_add('write',lambda *_:self.populate())
        self.tree=self.table(outer,[('name','Gimnasio',175),('email','Contacto',180),('state','Estado',100),('expires','Vencimiento local',160),('fee','Mensualidad',150),('devices','Equipos',85)],height=5)
        self.tree.bind('<<TreeviewSelect>>',lambda _:self.load_detail())
        self.selection_label=ttk.Label(outer,text='Selecciona un gimnasio para administrar sus accesos.',style='Muted.TLabel')
        self.selection_label.pack(anchor='w',pady=12)
        tabs=ttk.Notebook(outer);tabs.pack(fill='both',expand=True)
        self.detail_trees={}
        definitions=[('devices','Equipos',[('name','Equipo',170),('state','Estado',100),('last_seen','Última conexión local',160),('id','ID del equipo',300)]),
          ('users','Usuarios',[('email','Correo',250),('role','Rol',130),('enabled','Estado',120),('user_id','ID de usuario',300)]),
          ('payments','Mensualidades',[('created_at','Registrado · hora local',160),('amount','Valor',130),('months','Meses',70),('reference','Referencia',190),('period_until','Vigente hasta',170)]),
          ('events','Historial',[('created_at','Fecha · hora del gimnasio',160),('action','Acción',170),('detail','Detalle',500)])]
        for key,title,columns in definitions:
            tab=ttk.Frame(tabs,padding=10);tabs.add(tab,text=title)
            if key in {'devices','users'}:
                bar=ttk.Frame(tab);bar.pack(fill='x',pady=(0,8))
                ttk.Button(bar,text='✓  Autorizar equipo' if key=='devices' else '✓  Habilitar usuario',command=lambda k=key:self.toggle(k,True)).pack(side='left',padx=(0,8))
                ttk.Button(bar,text='×  Desautorizar equipo' if key=='devices' else '×  Deshabilitar usuario',command=lambda k=key:self.toggle(k,False)).pack(side='left')
            self.detail_trees[key]=self.table(tab,columns,height=4)
        self.marketing_tab=ttk.Frame(tabs,padding=16)
        tabs.add(self.marketing_tab,text='Marketing')
        self.marketing_status=tk.StringVar(self,'Selecciona un gimnasio para consultar sus integraciones.')
        ttk.Label(self.marketing_tab,textvariable=self.marketing_status,justify='left',wraplength=760).pack(anchor='w',fill='x',pady=8)
        ttk.Button(self.marketing_tab,text='Actualizar integraciones',command=self.load_marketing).pack(anchor='w',pady=8)
        tabs.bind('<<NotebookTabChanged>>',lambda _:self.load_marketing() if tabs.select()==str(self.marketing_tab) else None,add='+')
        self.message=ttk.Label(outer,text='Conectado como '+self.cloud.email,style='Muted.TLabel');self.message.pack(anchor='w',pady=(12,0))

    def table(self,parent,columns,height):
        box=ttk.Frame(parent);box.pack(fill='both',expand=True)
        tree=DataTreeview(box,columns=[x[0] for x in columns],show='headings',selectmode='browse',height=height)
        for key,title,width in columns:tree.heading(key,text=title);tree.column(key,width=width,minwidth=60)
        scroll=AutoScrollbar(box,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0,column=1,sticky='ns');tree.grid(row=0,column=0,sticky='nsew')
        horizontal=AutoScrollbar(box,orient='horizontal',command=tree.xview);horizontal.grid(row=1,column=0,sticky='ew')
        tree.configure(xscrollcommand=horizontal.set);box.columnconfigure(0,weight=1);box.rowconfigure(0,weight=1)
        box._responsive_skip=True
        for key,title,width in columns:tree.column(key,minwidth=width)
        return tree

    def run(self,operation,done):
        if self.busy or self._closing:return False
        self.busy=True;self.message.configure(text='Procesando…')
        self.set_controls_enabled(False)
        def worker():
            try:self.queue.put((True,operation(),done))
            except Exception as error:self.queue.put((False,error,done))
        threading.Thread(target=worker,daemon=True).start()
        return True

    def set_controls_enabled(self,enabled):
        def visit(widget):
            for child in widget.winfo_children():
                if isinstance(child,ttk.Button):child.configure(state='normal' if enabled else 'disabled')
                visit(child)
        visit(self)

    def poll(self):
        if self._closing:return
        try:
            ok,result,done=self.queue.get_nowait();self.busy=False
            self.set_controls_enabled(True)
            self.message.configure(text='Conectado como '+self.cloud.email)
            if ok:done(result)
            else:messagebox.showerror('No se completó la operación',friendly_error(result),parent=self)
        except queue.Empty:pass
        except Exception as error:
            # Un callback de presentación no debe detener todo el panel.
            messagebox.showerror('No se pudo actualizar la pantalla',
                friendly_error(error)+'\n\nPulsa Actualizar para verificar el estado. No repitas un pago sin comprobar su referencia.',parent=self)
        finally:
            if not self._closing:
                if self.pending_detail and not self.busy:
                    self.pending_detail=None
                    self.load_detail()
                self._poll_id=self.after(150,self.poll)

    def close_panel(self):
        if self.busy and not messagebox.askyesno('Operación en curso',
                'Hay una operación en curso. Si cierras, comprueba después el historial antes de repetirla. ¿Cerrar?',parent=self):
            return
        self._closing=True
        if self._poll_id:self.after_cancel(self._poll_id)
        self.destroy()

    def rpc(self,name,params=None):
        data=self.cloud.client.rpc(name,params or {}).execute().data
        return json.loads(data) if isinstance(data,str) and data.lstrip().startswith(('{','[')) else data

    def selected(self):
        if self.busy:return None
        ids=self.tree.selection()
        if not ids:
            messagebox.showinfo('Gimnasio','Selecciona un gimnasio.',parent=self);return None
        return self.rows.get(ids[0])

    def refresh(self):self.run(lambda:self.rpc('owner_list_gyms'),self.render)

    def render(self,data):
        if isinstance(data,str):data=json.loads(data)
        if not isinstance(data,list):raise ValueError('El servidor devolvió un listado inválido.')
        self.rows={str(r['id']):r for r in data}
        upcoming=0
        for r in self.rows.values():
            if not r.get('server_now'):continue
            now=parse_instant(r['server_now'])
            expiry=parse_instant(r['expires_at'])
            upcoming+=int(now<=expiry<=now+timedelta(days=7) and r['effective_status'] in {'active','trial'})
        numbers=[len(self.rows),sum(r['effective_status'] in {'active','trial','grace'} for r in self.rows.values()),upcoming,sum(int(r.get('pending_devices',0)) for r in self.rows.values())]
        for widget,value in zip(self.metrics,numbers):widget.configure(text=str(value))
        self.populate()

    def populate(self):
        self._populating=True
        previous=self.tree.selection()
        clear_tree(self.tree)
        text=self.search.get().casefold()
        for id,r in self.rows.items():
            state=STATUS.get(r['effective_status'],r['effective_status'])
            if text not in (r['name']+' '+r['contact_email']+' '+id).casefold():continue
            if self.filter.get()!='Todos' and self.filter.get()!=state:continue
            self.tree.insert('', 'end',iid=id,values=(r['name'],r['contact_email'],state,date_text(r['expires_at'],r.get('timezone') or DEFAULT_ZONE),money(r['monthly_price'])+' '+r['currency'],f"{r['active_devices']}/{r['max_devices']}"))
        self.tree.finish_update()
        if previous and self.tree.exists(previous[0]):
            if self.tree.selection()!=previous:self.tree.selection_set(previous[0])
        else:
            self.selection_label.configure(text='Selecciona un gimnasio para administrar sus accesos.')
            for tree in self.detail_trees.values():tree.delete(*tree.get_children())
            self.detail={};self.detail_target=None
        self._populating=False
        self.load_detail()

    def load_detail(self):
        if self._populating:return
        ids=self.tree.selection()
        r=self.rows.get(ids[0]) if ids else None
        target=r['id'] if r else None
        if self.busy and target and getattr(self, '_detail_request', None)==target:return
        if target!=self.detail_target:
            self.marketing_status.set('Pulsa Actualizar integraciones para consultar el gimnasio seleccionado.')
            for tree in self.detail_trees.values():tree.delete(*tree.get_children())
            self.detail={}
        self.detail_target=None
        if not r:return
        self.selection_label.configure(text=f"{r['name']}  ·  ID: {r['id']}  ·  {r['plan']}")
        target=r['id']
        if self.busy:
            self.pending_detail=target
            return
        def done(data):
            if not self.tree.selection() or self.tree.selection()[0]!=target:return
            self._detail_request=None
            self.detail=data;self.detail_target=target
            zone=data.get('gym',{}).get('timezone') or r.get('timezone') or DEFAULT_ZONE
            for key,tree in self.detail_trees.items():
                clear_tree(tree)
                for index,item in enumerate(data.get(key,[])):
                    if key=='devices':values=(item['name'],'Bloqueado' if item['blocked'] else ('Autorizado' if item['approved'] else 'Pendiente'),date_text(item['last_seen'],zone),item['id'])
                    elif key=='users':values=(item['email'],{'admin':'Administración','receptionist':'Recepción'}.get(item['role'],item['role']),'Habilitado' if item['enabled'] else 'Deshabilitado',item['user_id'])
                    elif key=='payments':values=(date_text(item['created_at'],zone),money(item['amount'])+' '+item['currency'],item['months'],item['reference'],date_text(item['period_until'],zone))
                    else:values=(date_text(item['created_at'],zone),OWNER_ACTIONS.get(item['action'],item['action'].replace('_',' ').capitalize()),readable(item['detail']))
                    tree.insert('','end',iid=str(index),values=values)
        self._detail_request=target
        self.run(lambda:self.rpc('owner_gym_detail',{'p_gym_id':target}),done)

    def load_marketing(self):
        if self.busy:
            self.marketing_status.set('Espera a que termine la consulta y pulsa Actualizar integraciones.');return
        row=self.selected()
        if not row:return
        target=row['id'];self.marketing_status.set('Consultando integraciones de '+row['name']+'…')
        def load():
            try:return self.rpc('owner_marketing_status',{'p_gym_id':target})
            except Exception:return {'unavailable':True}
        def done(data):
            if not self.tree.selection() or self.tree.selection()[0]!=target:return
            if not isinstance(data,dict) or data.get('unavailable'):
                self.marketing_status.set('No se pudo consultar Marketing. Verifica la conexión y que la actualización esté instalada en el servidor.');return
            names={'CONNECTED':'Conectado','DISCONNECTED':'No conectado','CONNECTING':'Conexión pendiente','ATTENTION':'Requiere atención'}
            connections={c['provider']:c for c in data.get('connections',[])};lines=[row['name']]
            for key,label in [('META','WhatsApp'),('WOMPI','Wompi')]:
                c=connections.get(key,{})
                lines.append(label+': '+names.get(c.get('status'),'No conectado')+(' · Sandbox' if key=='WOMPI' and c.get('mode')=='test' else ''))
            lines.extend(['Asistente: '+('Activo' if data.get('chatbot_enabled') else 'Inactivo'),'Automatizaciones activas: '+str(data.get('automations_active',0)),'Última ejecución: '+date_text(data.get('last_execution'),row.get('timezone') or DEFAULT_ZONE),'Errores en los últimos 7 días: '+str(data.get('errors',0))])
            self.marketing_status.set('\n\n'.join(lines))
        self.run(load,done)

    def mutate(self,name,params,done=None):
        def success(result):
            if done:done(result)
            else:
                self.message.configure(text='Cambio guardado. Actualizando…')
                self.refresh()
        self.run(lambda:self.rpc(name,params),success)

    def new_gym(self):
        if self.busy:return
        p=Form(self,'Nuevo gimnasio',[('name','Nombre',''),('email','Correo del administrador',''),('price','Precio mensual del software',''),('currency','Moneda (COP / USD…)','COP'),('devices','Máximo de equipos',2),('days','Días de prueba',7),('timezone','Zona horaria','America/Bogota')],validate=new_gym_params).result
        if not p:return
        def done(result):
            self.show_code(result['activation_code'],f"Gimnasio: {result['gym_id']}\nCorreo autorizado: {result['email']}")
            self.refresh()
        self.mutate('owner_create_gym',p,done)

    def show_code(self,code,detail=''):
        try:
            self.clipboard_clear();self.clipboard_append(code)
            copied='copiado al portapapeles'
        except tk.TclError:
            copied='no se pudo copiar; anótalo antes de cerrar'
        messagebox.showinfo('Invitación creada',f'{detail}\n\nCódigo ({copied}):\n{code}\n\nVence en 7 días y solo se usa una vez.',parent=self)

    def renew(self):
        r=self.selected()
        if not r:return
        pending=self.pending_renewals.get(r['id'],{})
        reference=pending.get('reference') or 'GS-'+datetime.now(timezone.utc).strftime('%Y%m%d')+'-'+uuid.uuid4().hex[:8].upper()
        form=Form(self,'Registrar mensualidad',[('months','Meses que se renuevan',pending.get('months',1)),('amount','Valor recibido',pending.get('amount',r['monthly_price'])),('reference','Referencia única del pago',reference)],
                  validate=lambda f:renewal_params(r,f),hint='Puedes usar la referencia generada o el número del comprobante. Para reintentar el mismo pago conserva su referencia.')
        p=form.result
        if not p:return
        if not messagebox.askyesno('Registrar pago',f"{r['name']}\n{p['p_amount']} {r['currency']} por {p['p_months']} mes(es).\nReferencia: {p['p_reference']}\n\nEsto registra dinero que ya recibiste y activa la suscripción; no cobra al cliente. ¿Continuar?",parent=self):return
        self.pending_renewals[r['id']]=form.raw
        def done(payment):
            self.pending_renewals.pop(r['id'],None)
            messagebox.showinfo('Mensualidad registrada',f"{r['name']}\nReferencia: {payment['reference']}\nVigente hasta: {date_text(payment['period_until'],r.get('timezone') or DEFAULT_ZONE)}\n\nSi ya existía esta referencia, se recuperó el mismo registro sin renovar dos veces.",parent=self)
            self.refresh()
        self.mutate('owner_renew',p,done)

    def status(self,state):
        r=self.selected()
        if not r:return
        note='\nReactivar no extiende el vencimiento; registra una mensualidad o concede gracia si ya venció.' if state=='active' else ''
        reason=simpledialog.askstring('Cambiar estado',f"{r['name']} → {STATUS[state]}{note}\nEscribe el motivo (mínimo 3 caracteres):",parent=self,validate=lambda v:required(v,'Motivo',3))
        if reason:self.mutate('owner_set_status',{'p_gym_id':r['id'],'p_status':state,'p_reason':reason})

    def contract(self):
        r=self.selected()
        if not r:return
        p=Form(self,'Contrato',[('price','Precio mensual',r['monthly_price']),('currency','Moneda',r['currency']),('devices','Límite de equipos',r['max_devices']),('users','Límite de usuarios',r['max_users']),('notes','Notas internas',r['notes'])],validate=lambda f:contract_params(r,f)).result
        if not p:return
        self.mutate('owner_update_contract',p)

    def invite(self):
        r=self.selected()
        if not r:return
        p=Form(self,'Invitar usuario',[('email','Correo autorizado',''),('role','Rol','Recepción')],choices={'role':['Administración','Recepción']},validate=lambda f:invite_params(r,f)).result
        if p:self.mutate('owner_invite_user',p,lambda code:self.show_code(code,p['p_email']))

    def grace(self):
        r=self.selected()
        if not r:return
        p=Form(self,'Días de gracia',[('days','Días adicionales',3),('reason','Motivo','')],validate=lambda f:grace_params(r,f),hint='De 1 a 30 días. La gracia no levanta una suspensión o cancelación: usa Reactivar cuando corresponda.').result
        if p:self.mutate('owner_grant_grace',p)

    def toggle(self,key,enabled):
        r=self.selected()
        if not r:return
        if self.detail_target!=r['id']:
            messagebox.showinfo('Actualizar accesos','Espera a que carguen los accesos del gimnasio seleccionado.',parent=self)
            self.load_detail();return
        selected=self.detail_trees[key].selection()
        if not selected:
            messagebox.showinfo('Selecciona un acceso','Selecciona primero el equipo o usuario en su tabla.',parent=self);return
        item=self.detail[key][int(selected[0])]
        reason=simpledialog.askstring('Control de acceso',f"Gimnasio: {r['name']}\nAcceso: {item.get('name') or item.get('email')}\nMotivo (mínimo 3 caracteres):",parent=self,validate=lambda v:required(v,'Motivo',3))
        if not reason:return
        if key=='devices':self.mutate('owner_set_device',{'p_device_id':item['id'],'p_blocked':not enabled,'p_reason':reason})
        else:self.mutate('owner_set_user',{'p_user_id':item['user_id'],'p_enabled':enabled,'p_reason':reason})

    def backup(self):
        r=self.selected()
        if not r:return
        path=filedialog.asksaveasfilename(title='Guardar respaldo del gimnasio',defaultextension='.json',initialfile='GymSoft-'+r['id']+'-'+datetime.now().strftime('%Y%m%d')+'.json',parent=self)
        if not path:return
        def done(data):
            try:write_backup(path,data)
            except OSError as error:messagebox.showerror('No se pudo guardar',str(error),parent=self);return
            messagebox.showinfo('Respaldo','Respaldo guardado de '+r['name'],parent=self)
        self.mutate('owner_editor_backup',{'p_gym_id':r['id']},done)

    def open_editor(self):
        r=self.selected()
        if not r:return
        def checked(info):
            if info.get('owner_editor_version')!='3.1.0':
                messagebox.showinfo('Actualizar base comercial',
                    'Primero instala ACTUALIZAR_EDITOR_PROPIETARIO_3.1.0.sql en el proyecto comercial. No ejecutes INSTALAR_BASE_NUEVA.sql sobre tus gimnasios existentes.',parent=self)
                return
            from owner_editor import OwnerEditor
            OwnerEditor(self,r,Form)
            if not self._closing:self.refresh()
        self.run(lambda:self.rpc('commercial_system_info'),checked)

    def export_list(self):
        path=filedialog.asksaveasfilename(defaultextension='.csv',initialfile='GymSoft-gimnasios.csv',parent=self)
        if not path:return
        fields=['id','name','contact_email','effective_status','expires_at','monthly_price','currency','active_devices','max_devices']
        try:
            with open(path,'w',newline='',encoding='utf-8-sig') as file:
                writer=csv.writer(file);writer.writerow(fields)
                for r in self.rows.values():
                    values=[str(r.get(k,'')) for k in fields]
                    writer.writerow(["'"+v if v.startswith(('=','+','-','@')) else v for v in values])
        except OSError as error:messagebox.showerror('No se pudo guardar',str(error),parent=self)

def main():
    if '--diagnostico' in sys.argv:
        from diagnostico import main as diagnostic_main
        raise SystemExit(diagnostic_main())
    app=OwnerPanel()
    try:app.mainloop()
    except tk.TclError:pass


if __name__=='__main__':
    main()
