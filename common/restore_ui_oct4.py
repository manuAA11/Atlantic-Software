from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=R/'common/marketing_ui.py';s=p.read_text().replace("text='Contactos y ajustes anteriores'","text='Contactos'").replace("ttk.Label(card,textvariable=self.values[key],font=(UI_FONT,18,'bold'))","ttk.Label(card,textvariable=self.values[key],font=(UI_FONT,18,'bold'),style='Card.TLabel')").replace("ttk.Label(card,text=label)","ttk.Label(card,text=label,style='CardMuted.TLabel')")
s=s.replace("lambda:self.edit_rule(self.chosen('automations'))", "lambda:self.edit_selected('automations',self.edit_rule)").replace("lambda:self.new_template(self.chosen('templates'))", "lambda:self.edit_selected('templates',self.new_template)")
s=s.replace('        def edit_rule(self,row=None):', "        def edit_selected(self,kind,editor):\n            row=self.chosen(kind)\n            if row:editor(row)\n\n        def edit_rule(self,row=None):")
s=s.replace("            self.data=data;summary=", "            self.offsets={'messages':0,'payments':0}\n            self.data=data;summary=")
s=s.replace("confirmed=True,request_key=str(uuid.uuid4())))", "confirmed=True,request_key=str(uuid.uuid4())),self.test_result)")
s=s.replace('        def build_payments(self):', "        def test_result(self,result):\n            status=result.get('status','UNCERTAIN') if isinstance(result,dict) else 'UNCERTAIN'\n            self.feedback.set('Prueba de WhatsApp: '+STATES.get(status,'Resultado por confirmar')+'. Consulta el detalle en Historial.')\n\n        def build_payments(self):")
p.write_text(s)
p=R/'common/marketing_client.py';s=p.read_text();start=s.index("            if hasattr(context, 'json'):");end=s.index("            raise ValueError('No se pudo confirmar",start)
s=s[:start]+'''            if hasattr(context, 'json'):
                try:response = context.json()
                except Exception:response = None
                if isinstance(response, dict) and response.get('message'):
                    raise ValueError(str(response['message'])[:500]) from None
''' +s[end:];p.write_text(s)
for d in R.glob('GymSoft_*'):
 for name in ['marketing_reception.py','marketing_ui.py','marketing_client.py']:(d/name).write_text((R/'common'/name).read_text())
 p=d/'reception_app.py';s=p.read_text();anchor='        bind_live_search(self, self.search, self.refresh)';pos=s.index(anchor,s.index('class ClientsPage'))+len(anchor)
 s=s[:pos]+'''
        self.whatsapp_tab=ttk.Frame(self.notebook)
        self.notebook.add(self.whatsapp_tab,text='Atención WhatsApp')
        def show_whatsapp(_event=None):
            if self.notebook.select()!=str(self.whatsapp_tab):return
            if not hasattr(self,'whatsapp_inbox'):
                from marketing_reception import ReceptionInbox
                self.whatsapp_inbox=ReceptionInbox(self.whatsapp_tab,self)
                self.whatsapp_inbox.pack(fill='both',expand=True)
            self.whatsapp_inbox.refresh()
        self.notebook.bind('<<NotebookTabChanged>>',show_whatsapp,add='+')
''' +s[pos:];p.write_text(s)
p=R/'GymSoft_Comercial_3.6.0/owner_panel.py';s=p.read_text();pos=s.index("        self.message=ttk.Label(outer,text='Conectado como '+self.cloud.email")
s=s[:pos]+'''        self.marketing_tab=ttk.Frame(tabs,padding=16)
        tabs.add(self.marketing_tab,text='Marketing')
        self.marketing_status=tk.StringVar(self,'Selecciona un gimnasio para consultar sus integraciones.')
        ttk.Label(self.marketing_tab,textvariable=self.marketing_status,justify='left',wraplength=760).pack(anchor='w',fill='x',pady=8)
        ttk.Button(self.marketing_tab,text='Actualizar integraciones',command=self.load_marketing).pack(anchor='w',pady=8)
        tabs.bind('<<NotebookTabChanged>>',lambda _:self.load_marketing() if tabs.select()==str(self.marketing_tab) else None,add='+')
''' +s[pos:];pos=s.index('    def mutate(')
s=s[:pos]+'''    def load_marketing(self):
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
            self.marketing_status.set('\\n\\n'.join(lines))
        self.run(load,done)

''' +s[pos:];s=s.replace("        if target!=self.detail_target:\n", "        if target!=self.detail_target:\n            self.marketing_status.set('Pulsa Actualizar integraciones para consultar el gimnasio seleccionado.')\n");p.write_text(s)
p=R/'GymSoft_Comercial_3.6.0/tests/test_panel_resilience.py';s=p.read_text().replace('selection_label=Mock())','selection_label=Mock(),marketing_status=Mock())');p.write_text(s)
