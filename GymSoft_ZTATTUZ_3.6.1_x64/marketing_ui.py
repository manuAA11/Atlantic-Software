"""Shared Marketing UI for both brands. I/O uses the existing background coordinator."""
import json
import re
import tkinter as tk
from tkinter import ttk
import uuid
import webbrowser
from desktop_ui import Modal, messagebox, simpledialog
from dark_files import filedialog
from responsive_ui import AutoScrollbar, UI_FONT
from ui_performance import DataTreeview, background_reads
from gym_time import display_timestamp, timezone_for
from marketing_client import MarketingClient

BG, SURFACE, TEXT, MUTED = '#0b1220', '#172235', '#f8fafc', '#94a3b8'
TRIGGERS = {
    'MEMBERSHIP_BEFORE': 'Membresía: días antes de vencer', 'MEMBERSHIP_TODAY': 'Membresía: vence hoy',
    'MEMBERSHIP_AFTER': 'Membresía: días después de vencer', 'MEMBERSHIP_OVERDUE_REPEAT': 'Membresía: cada X días vencida',
    'MEMBERSHIP_RENEWED': 'Después de renovar', 'TICKET_REMAINING': 'Tiquetera: quedan X entradas',
    'TICKET_EXPIRING': 'Tiquetera: días antes de vencer', 'TICKET_CONSUMED': 'Tiquetera: después de consumir una entrada',
    'CHECK_IN_SUCCESS': 'Después de una entrada aprobada', 'FIRST_CHECK_IN_DAY': 'Primera entrada del día',
    'EVERY_N_CHECKINS': 'Cada X entradas', 'FIRST_CHECK_IN_RENEWAL': 'Primera entrada después de renovar',
    'INACTIVITY': 'Días o semanas sin asistir', 'BIRTHDAY': 'El día del cumpleaños', 'BIRTHDAY_BEFORE': 'Días antes del cumpleaños',
    'MANUAL_PAYMENT': 'Después de un pago manual', 'ONLINE_APPROVED': 'Pago online aprobado',
    'ONLINE_DECLINED': 'Pago online rechazado', 'PAYMENT_PENDING': 'Pago pendiente durante X horas',
    'UNUSED_PAYMENT_LINK': 'Enlace sin abrir durante X horas', 'CUSTOM_DATE': 'Fecha específica',
    'DAILY': 'Todos los días', 'WEEKLY': 'Cada semana', 'MONTHLY': 'Cada mes',
}
VARIABLES = dict(zip(('nombre','apellido','gimnasio','plan','precio','fecha_vencimiento','dias_restantes',
                     'entradas_restantes','fecha_ultima_entrada','telefono','link_pago'),
                    ('Nombre','Apellido','Gimnasio','Plan','Precio','Fecha de vencimiento','Días restantes',
                     'Entradas restantes','Última entrada','Teléfono','Enlace de renovación')))
STATES = {'CONNECTED':'Conectado','DISCONNECTED':'No conectado','CONNECTING':'Verificación pendiente',
          'ATTENTION':'Requiere atención','DRAFT':'Borrador','PENDING':'Pendiente','APPROVED':'Aprobado',
          'DECLINED':'Rechazado','REJECTED':'Rechazado','EXPIRED':'Vencido','VOIDED':'Anulado','ERROR':'Error',
          'QUEUED':'En cola','PROCESSING':'Enviando','SENT':'Enviado','DELIVERED':'Entregado','READ':'Leído',
          'FAILED':'Falló','SKIPPED':'Omitido','NO_CONSENT':'Sin autorización','UNCERTAIN':'Resultado por confirmar',
          'RECEIVED':'Recibido','BOT':'Asistente activo','HUMAN':'Atiende recepción','PAUSED':'En pausa',
          'VERIFIED':'Identidad verificada','DOB':'Verificación pendiente','LINK_REQUEST':'Vinculación pendiente'}
FILTERS = {'plan_id':'Plan','plan_type':'Tipo de plan','active':'Cliente activo','status':'Estado de membresía',
           'entries_remaining':'Entradas restantes','days_remaining':'Días restantes','days_absent':'Días sin asistir',
           'whatsapp_opt_in':'WhatsApp autorizado','payment_method':'Método de pago','payment_pending':'Pago pendiente',
           'client_type':'Tipo de cliente'}
OPS = {'eq':'Es igual a','ne':'Es diferente de','lt':'Es menor que','lte':'Es como máximo','gt':'Es mayor que','gte':'Es como mínimo'}


def raw_for(mapping, label):
    return next((key for key, value in mapping.items() if value == label), label)


def hint(parent, text):
    w = ttk.Label(parent, text=text, wraplength=600, justify='left')
    w.pack(anchor='w', fill='x', pady=(5, 10))
    return w


def field(parent, label, value='', choices=None, secret=False):
    row = ttk.Frame(parent); row.pack(fill='x', pady=5)
    ttk.Label(row, text=label).pack(anchor='w', pady=(0, 3))
    var = tk.StringVar(row, str(value or ''))
    widget = (ttk.Combobox(row, textvariable=var, values=choices, state='readonly') if choices is not None
              else ttk.Entry(row, textvariable=var, show='•' if secret else ''))
    widget.pack(fill='x')
    return var, widget


def actions(parent, specs):
    bar = ttk.Frame(parent); bar.pack(fill='x', pady=(5, 10))
    for index, (title, callback) in enumerate(specs):
        ttk.Button(bar, text=title, command=callback).grid(row=index//3, column=index%3, sticky='ew', padx=(0, 6), pady=3)
        bar.columnconfigure(index%3, weight=1)
    return bar


def table(parent, columns, height=7):
    box = ttk.Frame(parent); box.pack(fill='both', expand=True, pady=5)
    box.rowconfigure(0, weight=1); box.columnconfigure(0, weight=1)
    tree = DataTreeview(box, columns=[c[0] for c in columns], show='headings', height=height)
    for key, label, width in columns:
        tree.heading(key, text=label); tree.column(key, width=width, minwidth=70, stretch=True)
    tree.grid(row=0, column=0, sticky='nsew')
    ys = AutoScrollbar(box, orient='vertical', command=tree.yview); ys.grid(row=0,column=1,sticky='ns')
    xs = AutoScrollbar(box, orient='horizontal', command=tree.xview); xs.grid(row=1,column=0,sticky='ew')
    tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
    return tree


def fill(tree, rows):
    """Update only changed values, retaining selection and scroll position."""
    desired = set()
    old_order = list(tree.get_children())
    for index, (identifier, values) in enumerate(rows):
        identifier = str(identifier); desired.add(identifier)
        if tree.exists(identifier):
            if tuple(map(str, tree.item(identifier, 'values'))) != tuple(map(str, values)):
                tree.item(identifier, values=values)
            if index >= len(old_order) or old_order[index] != identifier:
                tree.move(identifier, '', index)
        else: tree.insert('', 'end', iid=identifier, values=values)
    for identifier in set(tree.get_children())-desired: tree.delete(identifier)


class MessageDialog(Modal):
    def __init__(self, parent, title, text):
        super().__init__(parent, title)
        view = tk.Text(self.body, bg=SURFACE, fg=TEXT, insertbackground=TEXT, wrap='word', height=16, width=60)
        view.insert('1.0', text); view.configure(state='disabled'); view.pack(fill='both', expand=True)
        ttk.Button(self.body, text='Cerrar', command=self.close).pack(anchor='e', pady=10)


class RuleDialog(Modal):
    def __init__(self, parent, data, templates, plans, wompi_ready):
        super().__init__(parent, 'Editar automatización' if data.get('id') else 'Nueva automatización')
        self.preferred_width = 790; self.original = data; self.conditions = list(data.get('conditions') or [])
        self.plans = {str(p['id']): p['name'] for p in plans}
        self.name, self.initial_focus = field(self.body, 'Nombre', data.get('name',''))
        self.trigger, trigger_control = field(self.body, '¿Cuándo debe ejecutarse?', TRIGGERS.get(data.get('trigger_type'), next(iter(TRIGGERS.values()))), list(TRIGGERS.values()))
        self.options_box = ttk.Frame(self.body); self.options_box.pack(fill='x')
        o = data.get('trigger_options') or {}
        self.value, self.value_entry = field(self.options_box, 'Cantidad de días, horas o entradas', o.get('value', 3))
        self.unit, _ = field(self.options_box, 'Unidad para inactividad', 'Semanas' if o.get('unit')=='weeks' else 'Días', ['Días','Semanas'])
        self.time, _ = field(self.options_box, 'Hora del gimnasio (HH:MM)', o.get('time','09:00'))
        self.date, _ = field(self.options_box, 'Fecha específica (DD/MM/AAAA)', '/'.join(reversed(o.get('date','').split('-'))))
        self.weekday, _ = field(self.options_box, 'Día de la semana', ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'][int(o.get('weekday',1))], ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'])
        self.monthday, _ = field(self.options_box, 'Día del mes', o.get('monthday',1))
        self.option_rows = list(self.options_box.winfo_children())
        trigger_control.bind('<<ComboboxSelected>>', lambda _: self.show_options())
        self.template_map = {'Sin plantilla aprobada': None, **{t['name']+' · '+STATES.get(t['status'],t['status']):t for t in templates}}
        selected = next((label for label,t in self.template_map.items() if t and t['id']==data.get('template_id')), 'Sin plantilla aprobada')
        self.template, template_control = field(self.body, 'Plantilla de WhatsApp', selected, list(self.template_map))
        ttk.Label(self.body,text='Mensaje').pack(anchor='w',pady=(12,4))
        self.message = tk.Text(self.body,bg=SURFACE,fg=TEXT,insertbackground=TEXT,height=7,wrap='word',font=(UI_FONT,10),undo=True)
        self.message.insert('1.0',data.get('body','Hola {{nombre}}, te escribimos de {{gimnasio}}.')); self.message.pack(fill='x')
        template_control.bind('<<ComboboxSelected>>',lambda _: self.use_template())
        variable, control = field(self.body,'Insertar variable', 'Nombre', list(VARIABLES.values()))
        control.bind('<<ComboboxSelected>>',lambda _: self.message.insert('insert','{{'+raw_for(VARIABLES,variable.get())+'}}'))
        ttk.Button(self.body,text='Ver vista previa',command=self.preview).pack(anchor='w',pady=6)
        self.link = tk.BooleanVar(self,bool(data.get('include_payment_link')))
        ttk.Checkbutton(self.body,text='Incluir enlace de renovación',variable=self.link).pack(anchor='w',pady=6)
        if not wompi_ready: hint(self.body,'Para enviar enlaces de renovación, conecta primero Wompi en Pagos online. Puedes guardar el mensaje como borrador.')
        ttk.Label(self.body,text='Condiciones adicionales · deben cumplirse todas').pack(anchor='w',pady=(12,4))
        self.condition_list = tk.Listbox(self.body,height=4,bg=SURFACE,fg=TEXT,selectbackground='#244475',exportselection=False)
        self.condition_list.pack(fill='x')
        actions(self.body,[('Añadir condición',self.add_condition),('Quitar condición',self.remove_condition)])
        self.count,_ = field(self.body,'Máximo de mensajes por cliente (0 = sin límite)',(data.get('frequency') or {}).get('count',1))
        self.hours,_ = field(self.body,'Durante cuántas horas (24 = un día; 168 = una semana)',(data.get('frequency') or {}).get('hours',24))
        self.enabled = tk.BooleanVar(self,bool(data.get('enabled')))
        ttk.Checkbutton(self.body,text='Activar al guardar',variable=self.enabled).pack(anchor='w',pady=8)
        hint(self.body,'La activación requiere una plantilla aprobada cuyo texto coincida con el mensaje. Puedes guardar y solicitar aprobación desde Plantillas.')
        self.feedback = tk.StringVar(self)
        ttk.Label(self.body,textvariable=self.feedback,foreground='#fbbf24',wraplength=650).pack(fill='x')
        actions(self.body,[('Cancelar',self.close),('Guardar',self.accept)])
        self.draw_conditions(); self.show_options()

    def show_options(self):
        trigger = raw_for(TRIGGERS,self.trigger.get())
        numeric = trigger in {'MEMBERSHIP_BEFORE','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','TICKET_REMAINING','TICKET_EXPIRING','EVERY_N_CHECKINS','INACTIVITY','BIRTHDAY_BEFORE','PAYMENT_PENDING','UNUSED_PAYMENT_LINK'}
        visible = [numeric,trigger=='INACTIVITY',trigger not in {'MEMBERSHIP_RENEWED','TICKET_CONSUMED','CHECK_IN_SUCCESS','FIRST_CHECK_IN_DAY','EVERY_N_CHECKINS','FIRST_CHECK_IN_RENEWAL','MANUAL_PAYMENT','ONLINE_APPROVED','ONLINE_DECLINED'},trigger=='CUSTOM_DATE',trigger=='WEEKLY',trigger=='MONTHLY']
        for row in self.option_rows: row.pack_forget()
        for row, show in zip(self.option_rows, visible):
            if show: row.pack(fill='x',pady=5)

    def use_template(self):
        template = self.template_map[self.template.get()]
        if template:
            self.message.delete('1.0','end');self.message.insert('1.0',template['body'])

    def preview(self):
        values={'nombre':'Juan','apellido':'Pérez','gimnasio':'Tu gimnasio','plan':'Mensual','precio':'$70.000','fecha_vencimiento':'18/10/2026','dias_restantes':'3','entradas_restantes':'2','fecha_ultima_entrada':'15/10/2026','telefono':'Número del cliente','link_pago':'[Enlace de renovación de ejemplo]'}
        body=self.message.get('1.0','end-1c')
        for key,value in values.items(): body=body.replace('{{'+key+'}}',value)
        MessageDialog(self,'Vista previa · datos de ejemplo',body).show()

    def draw_conditions(self):
        self.condition_list.delete(0,'end')
        for c in self.conditions:
            value=c['value']; value=self.plans.get(str(value),value) if c['field']=='plan_id' else value
            if isinstance(value,bool):value='Sí' if value else 'No'
            self.condition_list.insert('end',f"{FILTERS.get(c['field'],c['field'])} · {OPS.get(c['op'],c['op'])} · {value}")

    def add_condition(self):
        dialog=Modal(self,'Añadir condición')
        name,control=field(dialog.body,'Campo','Cliente activo',list(FILTERS.values()))
        op,_=field(dialog.body,'Condición','Es igual a',list(OPS.values()))
        value,entry=field(dialog.body,'Valor','Sí')
        choices={'active':['Sí','No'],'whatsapp_opt_in':['Sí','No'],'payment_pending':['Sí','No'],
                 'plan_type':['Mensualidad','Tiquetera'],'client_type':['Mensualidad','Tiquetera','Sesión'],
                 'status':['AL DÍA','VENCIDO','SIN PLAN','SIN ENTRADAS','INACTIVO'],'plan_id':list(self.plans.values())}
        def changed(_=None):
            values=choices.get(raw_for(FILTERS,name.get()),[])
            value.set(values[0] if values else '')
            label.configure(text='Opciones: '+', '.join(values) if values else 'Escribe un número o un método de pago.')
        label=hint(dialog.body,'Opciones: Sí, No');control.bind('<<ComboboxSelected>>',changed)
        def accept():
            key=raw_for(FILTERS,name.get());v=value.get().strip()
            if key in choices and v not in choices[key]:
                label.configure(text='Selecciona un valor de: '+', '.join(choices[key]));return
            if key in ('active','whatsapp_opt_in','payment_pending'):v=v=='Sí'
            elif key=='plan_id':v=int(next(k for k,n in self.plans.items() if n==v))
            elif key in ('plan_type','client_type'):v={'Mensualidad':'monthly','Tiquetera':'ticket','Sesión':'session'}[v]
            elif key in ('entries_remaining','days_remaining','days_absent'):
                try:v=int(v)
                except ValueError:label.configure(text='Escribe un número entero.');return
            dialog.close({'field':key,'op':raw_for(OPS,op.get()),'value':v})
        actions(dialog.body,[('Cancelar',dialog.close),('Añadir',accept)])
        result=dialog.show()
        if result:self.conditions.append(result);self.draw_conditions()

    def remove_condition(self):
        selected=self.condition_list.curselection()
        if selected:self.conditions.pop(selected[0]);self.draw_conditions()

    def accept(self):
        from datetime import datetime
        try:
            trigger=raw_for(TRIGGERS,self.trigger.get());options={'value':int(self.value.get()),'time':self.time.get(),'unit':'weeks' if self.unit.get()=='Semanas' else 'days'}
            if trigger=='CUSTOM_DATE':options['date']=datetime.strptime(self.date.get(),'%d/%m/%Y').date().isoformat()
            if trigger=='WEEKLY':options['weekday']=['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'].index(self.weekday.get())
            if trigger=='MONTHLY':options['monthday']=int(self.monthday.get());assert 1<=options['monthday']<=31
            body=self.message.get('1.0','end-1c').strip();template=self.template_map[self.template.get()]
            data={'name':self.name.get().strip(),'body':body,'trigger_type':trigger,'trigger_options':options,'conditions':self.conditions,'frequency':{'count':int(self.count.get()),'hours':int(self.hours.get())},'include_payment_link':self.link.get(),'enabled':self.enabled.get(),'template_id':template['id'] if template else None}
            if not data['name'] or not body:raise ValueError('Completa el nombre y el mensaje.')
            if self.link.get() and '{{link_pago}}' not in body:raise ValueError('Inserta la variable Enlace de renovación en el mensaje.')
            if self.enabled.get() and (not template or template['status']!='APPROVED' or template['body']!=body):raise ValueError('Guarda como borrador hasta que WhatsApp apruebe este mensaje.')
            self.close(data)
        except (ValueError,AssertionError) as error:self.feedback.set(str(error) or 'Revisa los números y la fecha.')


def marketing_page_class(BasePage, LegacyPage):
    class MarketingCenter(BasePage):
        title='Marketing'
        TABS=('Resumen','Automatizaciones','WhatsApp','Pagos online','Chatbot','Plantillas','Historial','Estado de integraciones')
        def __init__(self,parent,app):
            super().__init__(parent,app)
            self.data={};self.busy=False;self.offsets={'messages':0,'payments':0};self.section='Resumen'
            self.page_header('Conecta tu gimnasio con sus clientes y automatiza renovaciones y seguimiento.', [('Activar automatizaciones',self.setup,'Primary.TButton'),('Actualizar',self.refresh,'TButton')])
            self.feedback=tk.StringVar(self)
            ttk.Label(self,textvariable=self.feedback,wraplength=720).pack(fill='x',pady=(0,8))
            self.shell=ttk.Frame(self);self.shell.pack(fill='both',expand=True)
            nav=ttk.Frame(self.shell);nav.pack(side='left',fill='y',padx=(0,14))
            self.content=ttk.Frame(self.shell);self.content.pack(side='left',fill='both',expand=True)
            self.sections={};self.trees={};self.values={};self.connections={}
            for name in self.TABS:
                ttk.Button(nav,text=name,width=21,command=lambda n=name:self.select(n)).pack(fill='x',pady=3)
                self.sections[name]=ttk.Frame(self.content)
            ttk.Button(nav,text='Contactos',width=21,command=self.legacy).pack(fill='x',pady=(25,3))
            self.build_summary();self.build_rules();self.build_whatsapp();self.build_payments();self.build_chatbot();self.build_templates();self.build_history();self.build_health()
            self.select('Resumen')

        @property
        def api(self):return MarketingClient(self.db)

        def select(self,name):
            for frame in self.content.winfo_children():frame.pack_forget()
            self.sections[name].pack(fill='both',expand=True);self.section=name
            if hasattr(self.app,'content_area'):self.app.content_area.canvas.yview_moveto(0)

        def legacy(self):
            if not hasattr(self,'legacy_page'):self.legacy_page=LegacyPage(self.content,self.app)
            for frame in self.content.winfo_children():frame.pack_forget()
            self.legacy_page.pack(fill='both',expand=True);self.legacy_page.refresh()
            background_reads(self.winfo_toplevel()).show(self.legacy_page)

        def run(self,work,done=None,refresh=True):
            if self.busy:return
            self.busy=True;self.feedback.set('Procesando…')
            def load():
                try:return {'result':work()}
                except Exception as error:return {'error':str(error) if isinstance(error,ValueError) else 'No se pudo confirmar la operación. Revisa tu conexión y actualiza antes de repetirla.'}
            def finish(result):
                self.busy=False
                if result.get('error'):self.feedback.set(result['error']);return
                self.feedback.set('Operación completada.')
                if done:done(result.get('result'))
                if refresh:self.refresh()
            self.load_view('action',load,finish,(str(uuid.uuid4()),))

        def refresh(self):
            self.load_view('marketing',self.db.marketing_workspace,self.render)

        def render(self,data):
            if not isinstance(data,dict):data={}
            self.offsets={'messages':0,'payments':0}
            self.data=data;summary=data.get('summary') or {};settings=summary.get('settings') or {}
            for key,var in self.values.items():
                value=summary.get(key,0)
                var.set(f"${int(value or 0)/100:,.0f}" if key=='recovered_cents' else str(value or 0))
            connections={c['provider']:c for c in summary.get('connections',[])}
            for provider,var in self.connections.items():
                c=connections.get(provider) or {};status=STATES.get(c.get('status'),'No conectado')
                if provider=='WOMPI' and c.get('status')=='CONNECTED' and not (c.get('metadata') or {}).get('webhook_confirmed'):status='Cuenta configurada · falta completar la prueba'
                var.set(status+'\n'+(c.get('display_number','') if provider=='META' else ('Pruebas Sandbox' if c.get('mode')=='test' else 'Producción' if c.get('mode')=='prod' else '')))
            self.chat_state.set('Asistente activo' if settings.get('chatbot_enabled') else 'Asistente desactivado')
            self.pause_minutes.set(str(settings.get('human_pause_minutes',120)))
            fill(self.trees['automations'],[(r['id'],(r['name'],'Activa' if r['enabled'] else 'Pausada',TRIGGERS.get(r['trigger_type'],r['trigger_type']))) for r in data.get('automations',[])])
            fill(self.trees['templates'],[(r['id'],(r['name'],STATES.get(r['status'],r['status']),r.get('rejection_reason') or '')) for r in data.get('templates',[])])
            fill(self.trees['conversations'],[(r['id'],(r['sender_number'],STATES.get(r['mode'],r['mode']),self.stamp(r.get('last_inbound_at')))) for r in data.get('conversations',[])])
            fill(self.trees['links'],[(r['id'],(r['supplied_name'],r.get('sender_number',''),self.stamp(r['created_at']))) for r in data.get('links',[])])
            self.render_history('messages',data.get('messages',[]));self.render_history('payments',data.get('payments',[]))
            health=data.get('health') or {};self.health.set('Última ejecución: '+(self.stamp(health.get('last_worker_at')) or 'Todavía no se ha ejecutado')+'\nErrores recientes: '+str(health.get('recent_errors',0))+'\n'+('El servicio requiere revisión.' if health.get('worker_error') else 'Las funciones se habilitan después de conectar los servicios y aprobar las plantillas.'))
            self.feedback.set('Información actualizada · hora del gimnasio: '+timezone_for(self.db))

        def stamp(self,value):return display_timestamp(value,timezone_for(self.db))

        def chosen(self,kind):
            selection=self.trees[kind].selection()
            if not selection:self.feedback.set('Selecciona un registro de la lista.');return None
            return next((r for r in self.data.get(kind,[]) if str(r['id'])==selection[0]),None)

        def build_summary(self):
            frame=self.sections['Resumen'];hint(frame,'Este mes · cifras calculadas con los registros del gimnasio.')
            cards=ttk.Frame(frame);cards.pack(fill='x')
            metrics=[('automations_active','Automatizaciones activas'),('sent','Mensajes enviados'),('delivered','Entregados'),('read','Leídos'),('links','Enlaces generados'),('payments_started','Pagos iniciados'),('payments_approved','Pagos aprobados'),('recovered_cents','Ingresos recuperados')]
            for i,(key,label) in enumerate(metrics):
                card=ttk.Frame(cards,padding=12,style='Card.TFrame');card.grid(row=i//2,column=i%2,sticky='ew',padx=4,pady=4);cards.columnconfigure(i%2,weight=1)
                self.values[key]=tk.StringVar(self,'0');ttk.Label(card,textvariable=self.values[key],font=(UI_FONT,18,'bold'),style='Card.TLabel').pack(anchor='w');ttk.Label(card,text=label,style='CardMuted.TLabel').pack(anchor='w')
            hint(frame,'Los ingresos recuperados incluyen únicamente pagos reales aprobados vinculados a automatizaciones. Los pagos Sandbox no aumentan Finanzas.')
            actions(frame,[('Configurar por mí',lambda:self.run(lambda:self.api.edge('recommended'))),('Crear automatización',self.edit_rule)])

        def build_rules(self):
            frame=self.sections['Automatizaciones']
            actions(frame,[('Crear automatización',self.edit_rule),('Editar',lambda:self.edit_selected('automations',self.edit_rule)),('Duplicar',lambda:self.rule_action('duplicate')),('Activar / pausar',self.toggle_rule),('Probar sin enviar',self.preview_rule),('Eliminar',lambda:self.rule_action('delete'))])
            self.trees['automations']=table(frame,[('name','Nombre',210),('state','Estado',90),('trigger','Cuándo',230)])
            actions(frame,[('Preparar plantilla del mensaje',self.rule_template),('Ver historial',lambda:self.select('Historial'))])

        def edit_selected(self,kind,editor):
            row=self.chosen(kind)
            if row:editor(row)

        def edit_rule(self,row=None):
            row=row or {};templates=self.data.get('templates',[])
            ready=any(c['provider']=='WOMPI' and c['status']=='CONNECTED' for c in (self.data.get('summary') or {}).get('connections',[]))
            result=RuleDialog(self,row,templates,self.data.get('plans',[]),ready).show()
            if result:self.run(lambda:self.api.rpc('marketing_save_automation',p_data=result,p_id=row.get('id'),p_revision=row.get('revision')))

        def rule_action(self,action):
            row=self.chosen('automations')
            if not row:return
            if action=='delete' and not messagebox.askyesno('Eliminar automatización','Se conservará el historial de ejecuciones. ¿Eliminar esta automatización?',parent=self):return
            self.run(lambda:self.api.rpc('marketing_automation_action',p_id=row['id'],p_revision=row['revision'],p_action=action))

        def toggle_rule(self):
            row=self.chosen('automations')
            if row:self.rule_action('pause' if row['enabled'] else 'enable')

        def pick_client(self,done):
            query=simpledialog.askstring('Buscar cliente','Nombre, documento o teléfono del cliente:',parent=self)
            if query is None:return
            def choose(rows):
                dialog=Modal(self,'Selecciona el cliente');hint(dialog.body,'Resultados por nombre, documento y teléfono. No se muestran datos de otros gimnasios.')
                tree=table(dialog.body,[('name','Cliente',250),('document','Documento',140),('phone','Teléfono',140)],8)
                fill(tree,[(r['id'],((r['first_name']+' '+r.get('last_name','')).strip(),r.get('document',''),r.get('phone',''))) for r in rows])
                def accept():
                    selected=tree.selection()
                    if selected:dialog.close(next(r for r in rows if str(r['id'])==selected[0]))
                actions(dialog.body,[('Cancelar',dialog.close),('Seleccionar',accept)])
                result=dialog.show()
                if result:done(result)
            self.run(lambda:self.api.lookup(query),choose,refresh=False)

        def preview_rule(self):
            rule=self.chosen('automations')
            if not rule:return
            self.pick_client(lambda client:self.run(lambda:self.api.edge('preview',automation_id=rule['id'],client_id=client['id']),lambda r:MessageDialog(self,'Vista previa · no se envió ningún mensaje',r['message']).show(),refresh=False))

        def build_whatsapp(self):
            frame=self.sections['WhatsApp'];self.connections['META']=tk.StringVar(self,'No conectado')
            ttk.Label(frame,text='WhatsApp Business',font=(UI_FONT,17,'bold')).pack(anchor='w');ttk.Label(frame,textvariable=self.connections['META']).pack(anchor='w',pady=15)
            hint(frame,'Conecta el número del gimnasio mediante la autorización oficial de Meta. Cuando la cuenta sea compatible, podrás seguir atendiendo desde WhatsApp Business.')
            hint(frame,'Meta comprobará la compatibilidad. La conexión puede requerir volver a vincular dispositivos. No migraremos ni desconectaremos tu número automáticamente.')
            actions(frame,[('Conectar / reconectar',lambda:self.run(lambda:self.api.edge('connect_whatsapp'),lambda r:webbrowser.open(r['url']),refresh=False)),('Probar mensaje',self.test_message),('Revisar conexión',lambda:self.repair('META')),('Desconectar',lambda:self.disconnect('META'))])

        def repair(self,provider):self.run(lambda:self.api.edge('repair',provider=provider))

        def disconnect(self,provider):
            if messagebox.askyesno('Desconectar servicio','Se pausarán las funciones relacionadas. Se conservará el historial. ¿Continuar?',parent=self):self.run(lambda:self.api.rpc('marketing_disconnect',p_provider=provider))

        def test_message(self):
            template=self.chosen('templates') if self.section=='Plantillas' else next((t for t in self.data.get('templates',[]) if t['status']=='APPROVED'),None)
            if not template or template['status']!='APPROVED':self.feedback.set('Primero crea y aprueba una plantilla en Plantillas.');return
            def selected(client):
                body=template['body']
                if '{{link_pago}}' in body:self.feedback.set('Para esta prueba utiliza una plantilla sin enlace de pago.');return
                if messagebox.askyesno('Enviar prueba por WhatsApp',f"Se enviará un mensaje real a {client['first_name']} · {client.get('phone','')}.\n\n{body}\n\n¿Confirmas el envío de esta prueba?",parent=self):self.run(lambda:self.api.edge('test_message',client_id=client['id'],template_id=template['id'],confirmed=True,request_key=str(uuid.uuid4())),self.test_result)
            self.pick_client(selected)

        def test_result(self,result):
            status=result.get('status','UNCERTAIN') if isinstance(result,dict) else 'UNCERTAIN'
            self.feedback.set('Prueba de WhatsApp: '+STATES.get(status,'Resultado por confirmar')+'. Consulta el detalle en Historial.')

        def build_payments(self):
            frame=self.sections['Pagos online'];self.connections['WOMPI']=tk.StringVar(self,'No conectado')
            ttk.Label(frame,text='Wompi',font=(UI_FONT,17,'bold')).pack(anchor='w');ttk.Label(frame,textvariable=self.connections['WOMPI']).pack(anchor='w',pady=12)
            hint(frame,'Los clientes pagan directamente a la cuenta Wompi del gimnasio. Atlantic Tech no recibe ni custodia ese dinero.')
            actions(frame,[('Configurar Wompi',self.connect_wompi),('Probar pago Sandbox',self.payment_test),('Probar conexión',lambda:self.repair('WOMPI')),('Desconectar',lambda:self.disconnect('WOMPI'))])
            self.trees['payments']=table(frame,[('client','Cliente',165),('plan','Plan',115),('amount','Valor',100),('state','Estado',100),('date','Generado',155)],6)
            self.history_buttons(frame,'payments')

        def connect_wompi(self):
            d=Modal(self,'Conectar Wompi');hint(d.body,'En el comercio Wompi abre Desarrolladores. Copia las cuatro credenciales de Sandbox para las pruebas. No se guardan en este computador.')
            actions(d.body,[('Crear / abrir cuenta Wompi',lambda:webbrowser.open('https://comercios.wompi.co'))])
            fields={key:field(d.body,label,secret=True)[0] for key,label in [('public_key','Llave pública'),('private_key','Llave privada'),('events_secret','Secreto de eventos'),('integrity_secret','Secreto de integridad')]}
            def accept():
                data={k:v.get().strip() for k,v in fields.items()}
                if not all(data.values()):return
                for v in fields.values():v.set('')
                d.close(data)
            actions(d.body,[('Cancelar',d.close),('Conectar',accept)])
            result=d.show()
            if result:
                def connected(r):
                    dialog=Modal(self,'Completar la conexión Wompi');hint(dialog.body,'En Wompi → Desarrolladores → URL de eventos, guarda esta dirección. Wompi requiere configurar este dato desde su cuenta. Después ejecuta Probar pago Sandbox para confirmar la conexión completa.')
                    field(dialog.body,'Dirección para copiar',r['webhook_url']);ttk.Button(dialog.body,text='Entendido',command=dialog.close).pack(pady=12);dialog.show()
                self.run(lambda:self.api.edge('connect_wompi',credentials=result),connected)

        def payment_test(self):
            plans={p['name']:p for p in self.data.get('plans',[]) if p.get('active') and p.get('price',0)>0}
            if not plans:self.feedback.set('Crea primero un plan con precio en Configuración.');return
            d=Modal(self,'Pago de prueba · Sandbox');hint(d.body,'Se utilizará un cliente de prueba separado. No se cobrará dinero real ni se aumentarán los ingresos de Finanzas.')
            plan,_=field(d.body,'Plan',next(iter(plans)),list(plans));actions(d.body,[('Cancelar',d.close),('Abrir prueba',lambda:d.close(plans[plan.get()]['id']))]);result=d.show()
            if result:self.run(lambda:self.api.edge('payment_test',plan_id=result,request_key=str(uuid.uuid4())),lambda r:webbrowser.open(r['url']))

        def build_chatbot(self):
            frame=self.sections['Chatbot'];self.chat_state=tk.StringVar(self,'Asistente desactivado')
            ttk.Label(frame,textvariable=self.chat_state,font=(UI_FONT,14,'bold')).pack(anchor='w',pady=8)
            actions(frame,[('Activar / desactivar',self.toggle_chatbot)])
            self.pause_minutes,_=field(frame,'Reactivar tras estos minutos sin actividad de recepción',120)
            ttk.Button(frame,text='Guardar tiempo de pausa',command=self.save_pause).pack(anchor='w',pady=5)
            hint(frame,'El asistente verifica teléfono y fecha de nacimiento antes de mostrar información. Los números nuevos requieren aprobación del personal.')
            self.trees['conversations']=table(frame,[('phone','Número',180),('mode','Atención',190),('last','Último mensaje',160)],5)
            actions(frame,[('Atender en recepción',lambda:self.conversation_mode('HUMAN')),('Devolver al asistente',lambda:self.conversation_mode('BOT')),('Pausar',lambda:self.conversation_mode('PAUSED'))])
            ttk.Label(frame,text='Vinculaciones pendientes').pack(anchor='w',pady=(12,4))
            self.trees['links']=table(frame,[('name','Nombre indicado',180),('phone','Teléfono',145),('date','Solicitado',150)],4)
            actions(frame,[('Vincular a un cliente',self.approve_link),('Rechazar solicitud',self.reject_link)])

        def toggle_chatbot(self):
            settings=(self.data.get('summary') or {}).get('settings') or {};active=not settings.get('chatbot_enabled')
            self.run(lambda:self.api.rpc('marketing_features',p_flags={'chatbot_enabled':active,**({'whatsapp_enabled':True} if active else {})}))

        def save_pause(self):
            try:minutes=int(self.pause_minutes.get());assert 5<=minutes<=10080
            except (ValueError,AssertionError):self.feedback.set('Indica entre 5 y 10080 minutos.');return
            self.run(lambda:self.api.rpc('marketing_features',p_flags={'human_pause_minutes':minutes}))

        def conversation_mode(self,mode):
            row=self.chosen('conversations')
            if row:self.run(lambda:self.api.rpc('marketing_conversation_mode',p_id=row['id'],p_mode=mode))

        def approve_link(self):
            row=self.chosen('links')
            if not row:return
            def chosen(client):
                if messagebox.askyesno('Confirmar identidad',f"¿Verificaste personalmente que {row['sender_number']} pertenece a {client['first_name']} {client.get('last_name','')}?\n\nNo apruebes la vinculación basándote únicamente en el nombre y el cumpleaños enviados por el chat.",parent=self):self.run(lambda:self.api.rpc('marketing_review_link',p_id=row['id'],p_client_id=client['id'],p_approved=True))
            self.pick_client(chosen)

        def reject_link(self):
            row=self.chosen('links')
            if row:self.run(lambda:self.api.rpc('marketing_review_link',p_id=row['id'],p_client_id=0,p_approved=False))

        def build_templates(self):
            frame=self.sections['Plantillas'];hint(frame,'WhatsApp revisa las plantillas antes de permitir mensajes automáticos. Una plantilla pendiente o rechazada no puede activar una automatización.')
            actions(frame,[('Nueva plantilla',self.new_template),('Editar borrador',lambda:self.edit_selected('templates',self.new_template)),('Solicitar aprobación',self.submit_template),('Sincronizar estados',lambda:self.repair('META')),('Ver mensaje',self.show_template)])
            self.trees['templates']=table(frame,[('name','Nombre',180),('state','Estado',110),('reason','Detalle',230)])

        def new_template(self,row=None):
            row=row or {}
            if row and row['status'] not in ('DRAFT','REJECTED'):self.feedback.set('Crea otra plantilla para modificar un mensaje ya enviado a revisión.');return
            d=Modal(self,'Plantilla de WhatsApp');name,_=field(d.body,'Nombre corto (letras minúsculas, números y guion bajo)',row.get('name',''))
            category,_=field(d.body,'Tipo de mensaje','Seguimiento y promociones' if row.get('category')=='MARKETING' else 'Avisos de servicio',['Avisos de servicio','Seguimiento y promociones'])
            editor=tk.Text(d.body,height=8,bg=SURFACE,fg=TEXT,insertbackground=TEXT,wrap='word');editor.insert('1.0',row.get('body',''));editor.pack(fill='x',pady=8)
            variable,control=field(d.body,'Insertar variable','Nombre',list(VARIABLES.values()));control.bind('<<ComboboxSelected>>',lambda _:editor.insert('insert','{{'+raw_for(VARIABLES,variable.get())+'}}'))
            error=hint(d.body,'El texto debe coincidir con el mensaje de la automatización.')
            def accept():
                body=editor.get('1.0','end-1c').strip()
                if not re.fullmatch('[a-z][a-z0-9_]{0,79}',name.get()) or not body:error.configure(text='Completa el nombre válido y el mensaje.');return
                d.close({'name':name.get(),'body':body,'category':'UTILITY' if category.get()=='Avisos de servicio' else 'MARKETING','variables':list(dict.fromkeys(re.findall(r'\{\{([a-z_]+)\}\}',body)))})
            actions(d.body,[('Cancelar',d.close),('Guardar borrador',accept)]);result=d.show()
            if result:self.run(lambda:self.api.rpc('marketing_save_template',p_data=result,p_id=row.get('id')))

        def show_template(self):
            row=self.chosen('templates')
            if row:MessageDialog(self,row['name'],row['body']).show()

        def submit_template(self):
            row=self.chosen('templates')
            if row:self.run(lambda:self.api.edge('submit_template',template_id=row['id']))

        def rule_template(self):
            row=self.chosen('automations')
            if row:self.run(lambda:self.api.edge('prepare_rule_template',automation_id=row['id']),lambda _:self.select('Plantillas'))

        def build_history(self):
            frame=self.sections['Historial'];hint(frame,'Mensajes y resultados de entrega · las horas corresponden al gimnasio.')
            self.trees['messages']=table(frame,[('date','Fecha y hora',150),('client','Cliente / teléfono',190),('message','Mensaje',240),('state','Estado',125)])
            self.history_buttons(frame,'messages')

        def history_buttons(self,parent,kind):
            actions(parent,[('Anterior',lambda:self.page_history(kind,-1)),('Siguiente',lambda:self.page_history(kind,1)),('Ver detalle',lambda:self.history_detail(kind))])

        def render_history(self,kind,rows):
            if kind=='messages':values=[(r['id'],(self.stamp(r['created_at']),r.get('client_name') or r.get('phone',''),r.get('body') or r.get('template_name',''),STATES.get(r['status'],r['status']))) for r in rows]
            else:values=[(r['id'],(r.get('client_name',''),(r.get('plan_snapshot') or {}).get('name',''),f"${int(r['amount_in_cents'])/100:,.0f}",STATES.get(r['status'],r['status']),self.stamp(r['created_at']))) for r in rows]
            fill(self.trees[kind],values)

        def page_history(self,kind,direction):
            offset=max(0,self.offsets[kind]+100*direction)
            def show(rows):
                if not rows and direction>0:self.feedback.set('No hay más registros.');return
                self.offsets[kind]=offset;self.data[kind]=rows;self.render_history(kind,rows)
            self.run(lambda:self.api.history(kind,offset),show,refresh=False)

        def history_detail(self,kind):
            row=self.chosen(kind)
            if not row:return
            if kind=='messages':text='\n'.join([self.stamp(row.get('created_at')),row.get('client_name') or row.get('phone',''),row.get('body',''),STATES.get(row.get('status'),row.get('status','')),row.get('error_message',''),'Comprobante de envío: '+str(row.get('whatsapp_message_id') or 'Pendiente'),'Referencia del pago: '+str(row.get('payment_reference') or 'No aplica'),'Pago: '+STATES.get(row.get('payment_status'),'No aplica')])
            else:text='\n'.join([row.get('client_name',''),(row.get('plan_snapshot') or {}).get('name',''),'Generado: '+self.stamp(row.get('created_at')),'Pagado: '+self.stamp(row.get('paid_at')),'Fecha de la transacción Wompi: '+(self.stamp(row.get('provider_created_at')) or 'Pendiente'),'Referencia: '+row.get('reference',''),'Transacción Wompi: '+str(row.get('transaction_id') or 'Pendiente'),'Estado: '+STATES.get(row['status'],row['status'])])
            MessageDialog(self,'Detalle del registro',text).show()

        def build_health(self):
            frame=self.sections['Estado de integraciones'];self.health=tk.StringVar(self)
            ttk.Label(frame,textvariable=self.health,wraplength=600,justify='left').pack(fill='x',pady=10)
            actions(frame,[('Revisar WhatsApp',lambda:self.repair('META')),('Revisar Wompi',lambda:self.repair('WOMPI')),('Exportar diagnóstico',self.export_diagnostic)])
            hint(frame,'El diagnóstico incluye estados y errores de servicio. No contiene contraseñas, mensajes, teléfonos ni datos de clientes.')

        def export_diagnostic(self):
            path=filedialog.asksaveasfilename(parent=self,title='Guardar diagnóstico',defaultextension='.json',initialfile='Estado_Marketing.json')
            if path:
                from pathlib import Path
                Path(path).write_text(json.dumps(MarketingClient.diagnostic(self.data),ensure_ascii=False,indent=2),encoding='utf-8');self.feedback.set('Diagnóstico guardado.')

        def setup(self):
            d=Modal(self,'Activar automatizaciones');summary=self.data.get('summary') or {};connections={c['provider']:c for c in summary.get('connections',[])}
            hint(d.body,'1. Conecta WhatsApp. 2. Conecta Wompi si usarás enlaces de pago. 3. Elige las automatizaciones con plantilla aprobada.')
            for provider,label in [('META','WhatsApp'),('WOMPI','Pagos online')]:hint(d.body,label+': '+STATES.get((connections.get(provider) or {}).get('status'),'No conectado'))
            selected={};templates={t['id']:t for t in self.data.get('templates',[])}
            for r in self.data.get('automations',[]):
                t=templates.get(r.get('template_id'));ready=bool(t and t['status']=='APPROVED' and t['body']==r['body'])
                var=tk.BooleanVar(d,ready);selected[r['id']]=var
                ttk.Checkbutton(d.body,text=r['name']+('' if ready else ' · requiere aprobación'),variable=var,state='normal' if ready else 'disabled').pack(anchor='w',pady=4)
            chatbot=tk.BooleanVar(d,True);ttk.Checkbutton(d.body,text='Activar el asistente de WhatsApp',variable=chatbot).pack(anchor='w',pady=12)
            if not selected:hint(d.body,'Usa Configurar por mí en Resumen para crear las recomendaciones, que podrás editar.')
            actions(d.body,[('Cancelar',d.close),('Activar selección',lambda:d.close({'ids':[key for key,v in selected.items() if v.get()],'chatbot':chatbot.get()}))]);result=d.show()
            if result:self.run(lambda:self.api.rpc('marketing_activate_setup',p_rule_ids=result['ids'],p_chatbot=result['chatbot']))
    return MarketingCenter
