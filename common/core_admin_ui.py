"""Atlantic Core console within the existing private owner application."""
from datetime import datetime, timezone, date
from decimal import Decimal
import json
import tkinter as tk
from tkinter import ttk
import uuid

from desktop_ui import decorate_window, messagebox
from responsive_ui import ScrollArea, fit_window, UI_FONT


class CoreAdmin(tk.Toplevel):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.rows = {}
        self.detail = {}
        self.pending_payments = {}
        self.payment_drafts = {}
        self.title('Atlantic Core · Gimnasios y plataforma')
        decorate_window(self)
        fit_window(self, 1180, 790, parent=owner)
        self.viewport = ScrollArea(self, padding=20)
        self.viewport.pack(fill='both', expand=True)
        body = self.viewport.body
        ttk.Label(body, text='Atlantic Core', font=(UI_FONT, 24, 'bold')).pack(anchor='w')
        ttk.Label(body, text='Suscripciones, dispositivos y actualizaciones. Los datos del gimnasio permanecen en su servidor.').pack(anchor='w', pady=(4, 12))
        actions = ttk.Frame(body); actions.pack(fill='x', pady=6)
        for index, (label, command) in enumerate([('Actualizar', self.refresh), ('Registrar pago', self.payment), ('Crear aviso', self.notify),
            ('Recordatorios', self.reminders), ('Publicar versión', self.release)]):
            ttk.Button(actions, text=label, command=command).grid(row=index//3,column=index%3,sticky='ew',padx=(0,6),pady=3)
            actions.columnconfigure(index%3,weight=1)
        second = ttk.Frame(body); second.pack(fill='x', pady=6)
        for index, (label, command) in enumerate([('Configuración', self.configure_gym), ('Estado de licencia', self.license),
            ('Autorizar/revocar equipo', self.device), ('Registrar gimnasio', self.register_gym), ('Registrar servidor', self.register_source)]):
            ttk.Button(second, text=label, command=command).grid(row=index//3,column=index%3,sticky='ew',padx=(0,6),pady=3)
            second.columnconfigure(index%3,weight=1)
        self.tree = owner.table(body, [('name','Gimnasio',160),('status','Estado',120),('price','Mensualidad',150),
            ('renewal','Próxima renovación',160),('last','Último pago',170),('devices','Equipos',80)], 5)
        self.tree.bind('<<TreeviewSelect>>', lambda _: self.load_detail())
        self.summary = ttk.Label(body, text='Selecciona un gimnasio.', wraplength=950)
        self.summary.pack(anchor='w', pady=10)
        tabs = ttk.Notebook(body); tabs.pack(fill='both', expand=True)
        self.tables = {}
        definitions = {
            'payments': ('Pagos', [('paid_at','Fecha real',170),('amount','Monto',130),('period','Período',210),('method','Método',140),('reference','Referencia',220)]),
            'devices': ('Dispositivos', [('device_name','Equipo',180),('architecture','Arquitectura',140),('app_version','Versión',100),('status','Estado',120),('last_seen','Última conexión',180)]),
            'notifications': ('Avisos', [('title','Título',200),('type','Tipo',120),('message','Mensaje',400),('expires_at','Vencimiento',180)]),
        }
        for key, (label, columns) in definitions.items():
            panel = ttk.Frame(tabs, padding=10); tabs.add(panel, text=label)
            self.tables[key] = owner.table(panel, columns, 6)
        self.refresh()

    def call(self, action, data=None):
        return self.owner.cloud.client.rpc('core_owner', {'p_action': action, 'p_data': data or {}}).execute().data

    def run(self, operation, done):
        return self.owner.run(operation, lambda value: done(value) if self.winfo_exists() else None)

    def selected(self):
        selected = self.tree.selection()
        if selected:
            return self.rows.get(selected[0])
        messagebox.showinfo('Atlantic Core', 'Selecciona un gimnasio.', parent=self)
        return None

    def refresh(self):
        def render(rows):
            self.rows = {str(row['gym_id']): row for row in rows}
            self.tree.delete(*self.tree.get_children())
            for key, row in self.rows.items():
                self.tree.insert('', 'end', iid=key, values=(row['name'], row['license_status'],
                    f"{Decimal(str(row['price'])):,.0f} {row['currency']}", row['next_renewal_date'], row.get('last_payment') or 'Sin registro', row['devices']))
        self.run(lambda: self.call('list'), render)

    def load_detail(self):
        row = self.selected()
        if not row: return
        target = row['gym_id']
        self.detail={}
        self.summary.configure(text='Consultando el gimnasio seleccionado…')
        for tree in self.tables.values():tree.delete(*tree.get_children())
        if self.owner.busy:
            self.after(250,lambda:self.load_detail() if self.winfo_exists() and self.tree.selection()==(str(target),) else None)
            return
        def render(detail):
            # A delayed response may not replace a newly selected gym.
            if self.tree.selection() != (str(target),): return
            self.detail = detail
            sub = detail['subscription']
            self.summary.configure(text=f"{row['name']} · ID: {row['gym_id']} · {row['license_status']} · Renovación: día {sub['renewal_day']} · {sub['price']} {sub['currency']}\nSin suspensión automática por pagos pendientes. Estado y licencia se administran explícitamente.")
            for key, tree in self.tables.items():
                tree.delete(*tree.get_children())
                for item in detail[key]:
                    if key == 'payments':
                        values=(item['paid_at'], item['amount'], item['period_start']+' → '+item['period_until']+' (fin exclusivo)', item['payment_method'], item['reference'])
                    elif key == 'devices': values=tuple(item.get(k, '') for k in ('device_name','architecture','app_version','status','last_seen'))
                    else: values=tuple(item.get(k, '') for k in ('title','type','message','expires_at'))
                    tree.insert('', 'end', iid=str(item.get('id') or item['device_id']), values=values)
        self.run(lambda: self.call('detail', {'gym_id': target}), render)

    def form(self, title, fields):
        from owner_panel import Form
        return Form(self, title, fields).result

    def mutate(self, action, data):
        prompt='¿Confirmas esta operación administrativa?'
        if action=='publish_release':
            prompt=('¿Publicar esta versión para el gimnasio seleccionado?' if data.get('gym_id') else
                '¿Publicar esta versión para TODOS los gimnasios con este perfil de instalación, arquitectura y canal?')
        if not messagebox.askyesno('Atlantic Core', prompt, parent=self): return
        def done(_):
            messagebox.showinfo('Atlantic Core', 'Operación confirmada por el servidor.', parent=self)
            self.refresh()
        self.run(lambda: self.call(action, data), done)

    def payment(self):
        row = self.selected()
        if not row: return
        draft=self.payment_drafts.get(row['gym_id'],{})
        data = self.form('Registrar pago recibido', [('amount','Monto recibido',draft.get('amount',row['price'])),('period_start','Inicio del período (AAAA-MM-DD)',draft.get('period_start',row['next_renewal_date'])),
            ('paid_at','Fecha real del pago (ISO, con zona)',draft.get('paid_at',datetime.now(timezone.utc).isoformat())),('payment_method','Método',draft.get('payment_method','Transferencia')),('reference','Referencia',draft.get('reference','')),('notes','Notas',draft.get('notes',''))])
        if not data: return
        try:
            data['amount'] = str(Decimal(data['amount']))
            date.fromisoformat(data['period_start'])
            if datetime.fromisoformat(data['paid_at'].replace('Z','+00:00')).tzinfo is None: raise ValueError('Incluye la zona horaria en la fecha del pago.')
        except Exception as error:
            messagebox.showerror('Revisa el pago', str(error), parent=self); return
        # Retain the request identity after an uncertain response, across retries.
        self.payment_drafts[row['gym_id']]=dict(data)
        fingerprint = json.dumps(data, sort_keys=True)
        key = (row['gym_id'], fingerprint)
        data.update(gym_id=row['gym_id'], currency=row['currency'], idempotency_key=self.pending_payments.setdefault(key,str(uuid.uuid4())))
        self.mutate('record_payment', data)

    def notify(self):
        row = self.selected()
        if not row: return
        data=self.form('Crear aviso para '+row['name'], [('title','Título',''),('message','Mensaje',''),('type','Tipo (INFO/WARNING/UPDATE/BILLING/MAINTENANCE)','INFO'),('expires_at','Vencimiento ISO opcional','')])
        if data: self.mutate('notify', dict(data, gym_id=row['gym_id']))

    def reminders(self):
        row=self.selected()
        if not row: return
        data=self.form('Recordatorios de renovación', [('enabled','Activar (sí/no)','no'),('offsets','Días respecto al vencimiento','-5,-2,0,1')])
        if not data:return
        try: offsets=[int(value.strip()) for value in data['offsets'].split(',')]
        except ValueError: messagebox.showerror('Recordatorios','Escribe días separados por comas.',parent=self);return
        self.mutate('reminders',dict(gym_id=row['gym_id'],enabled=data['enabled'].strip().lower()=='sí',offsets_days=offsets))

    def configure_gym(self):
        row=self.selected()
        if not row:return
        current=row['configuration']
        flags=[('notifications_enabled','Avisos habilitados'),('store_enabled','Tienda habilitada'),
               ('whatsapp_enabled','WhatsApp habilitado'),('automatic_door_enabled','Puerta habilitada')]
        fields=[('update_channel','Canal stable/beta',current.get('update_channel','stable'))]
        fields += [(key,label+' (sí/no)','sí' if current.get(key,True) else 'no') for key,label in flags]
        data=self.form('Configuración de plataforma',fields)
        if not data:return
        def boolean(value):
            normalized=value.strip().casefold()
            if normalized not in {'sí','si','no'}:raise ValueError('Escribe sí o no en las opciones de habilitación.')
            return normalized!='no'
        try:
            configuration={key:boolean(data[key]) for key,_ in flags}
        except ValueError as error:
            messagebox.showerror('Configuración',str(error),parent=self);return
        configuration['update_channel']=data['update_channel'].strip().lower()
        self.mutate('configure',dict(gym_id=row['gym_id'],configuration=configuration))

    def license(self):
        row=self.selected()
        if not row:return
        data=self.form('Estado explícito de licencia', [('status','Estado (ACTIVE/SUSPENDED/CANCELLED)',row['status']),('license_status','Licencia (ACTIVE/SUSPENDED/CANCELLED)',row['license_status']),('reason','Motivo','')])
        if data:self.mutate('set_status',dict(data,gym_id=row['gym_id']))

    def device(self):
        row=self.selected(); selection=self.tables['devices'].selection()
        if not row or not selection:return
        data=self.form('Estado del dispositivo', [('status','AUTHORIZED / REVOKED','AUTHORIZED')])
        if data:self.mutate('device_status',dict(data,gym_id=row['gym_id'],device_id=selection[0]))

    def release(self):
        row=self.selected()
        if not row:return
        data=self.form('Publicar actualización para '+row['name'], [('scope','Destino: gimnasio / todos','gimnasio'),('version','Versión',''),('architecture','windows-x86 / windows-x64','windows-x86'),('channel','Canal stable/beta','beta'),
            ('policy','OPTIONAL / RECOMMENDED / REQUIRED','OPTIONAL'),('installer_url','URL del instalador aprobado',''),('sha256','SHA256',''),('bytes','Tamaño exacto en bytes',''),('minimum_schema','Schema mínimo','core-1'),('notes','Notas de la versión','')])
        if not data:return
        scope=data.pop('scope').strip().lower()
        if scope not in {'gimnasio','todos'}:
            messagebox.showerror('Versión','Elige gimnasio o todos.',parent=self);return
        try:data['bytes']=int(data['bytes'])
        except ValueError:messagebox.showerror('Versión','Revisa el tamaño en bytes.',parent=self);return
        self.mutate('publish_release',dict(data,gym_id=row['gym_id'] if scope=='gimnasio' else None,variant=row['product_variant'],published=True))

    def register_gym(self):
        data=self.form('Registrar gimnasio existente', [('gym_id','UUID real del gimnasio',''),('source_project_ref','Referencia del servidor original',''),('name','Nombre',''),('price','Mensualidad COP',''),('renewal_day','Día de renovación','19'),('next_renewal_date','Primer vencimiento sin pago registrado (AAAA-MM-DD)','')])
        if data:self.mutate('register_gym',dict(data,source_gym_id=data['gym_id']))

    def register_source(self):
        data=self.form('Registrar servidor de origen', [('project_ref','Referencia Supabase',''),('publishable_key','Clave publicable (nunca secreta)',''),('context_rpc','commercial_context / reception_account_context','reception_account_context')])
        if data:self.mutate('register_source',data)


def open_panel(owner):
    panel=getattr(owner,'_core_panel',None)
    if panel is not None and panel.winfo_exists():panel.lift();return panel
    owner._core_panel=CoreAdmin(owner)
    return owner._core_panel
