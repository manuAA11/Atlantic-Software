"""Optional receptionist inbox using existing background reads; no provider credentials."""
import tkinter as tk
from tkinter import ttk
import uuid
from desktop_ui import Modal, messagebox, simpledialog
from marketing_client import MarketingClient
from marketing_ui import actions, table, fill, hint, STATES
from gym_time import display_timestamp, timezone_for

class ReceptionInbox(ttk.Frame):
    def __init__(self,parent,page):
        super().__init__(parent,padding=12)
        self.page,self.db,self.app=page,page.db,page.app
        self.data,self.busy={},False
        self.feedback=tk.StringVar(self,'Consulta conversaciones y vinculaciones cuando lo necesites.')
        ttk.Label(self,textvariable=self.feedback,wraplength=650).pack(fill='x',pady=8)
        actions(self,[('Actualizar',self.refresh)])
        hint(self,'Continúa desde WhatsApp Business. La atención humana pausa al asistente.')
        self.conversations=table(self,[('phone','WhatsApp',155),('mode','Atención',170),('last','Último mensaje',155)],5)
        actions(self,[('Atender en recepción',lambda:self.mode('HUMAN')),('Devolver al asistente',lambda:self.mode('BOT')),('Pausar',lambda:self.mode('PAUSED'))])
        ttk.Label(self,text='Vinculaciones pendientes').pack(anchor='w',pady=8)
        self.links=table(self,[('name','Nombre indicado',210),('phone','WhatsApp',155),('date','Solicitud',155)],4)
        actions(self,[('Verificar y vincular',self.approve),('Rechazar solicitud',self.reject)])
    @property
    def api(self):return MarketingClient(self.db)
    def run(self,work,done=None,refresh=True):
        if self.busy:return
        self.busy=True;self.feedback.set('Consultando…')
        def load():
            try:return {'result':work()}
            except Exception as error:return {'error':str(error) if isinstance(error,ValueError) else 'No se pudo consultar WhatsApp. La atención normal del gimnasio sigue disponible.'}
        def finish(result):
            self.busy=False
            if not self.winfo_exists():return
            if result.get('error'):self.feedback.set(result['error']);return
            self.feedback.set('Información actualizada.')
            if done:done(result['result'])
            if refresh:self.refresh()
        self.page.load_view('whatsapp_reception',load,finish,(str(uuid.uuid4()),))
    def refresh(self):self.run(lambda:self.api.rpc('marketing_reception_workspace'),self.render,False)
    def render(self,data):
        self.data=data or {};stamp=lambda value:display_timestamp(value,timezone_for(self.db))
        fill(self.conversations,[(r['id'],(r['sender_number'],STATES.get(r['mode'],r['mode']),stamp(r.get('last_inbound_at')))) for r in self.data.get('conversations',[])])
        fill(self.links,[(r['id'],(r['supplied_name'],r['sender_number'],stamp(r['created_at']))) for r in self.data.get('links',[])])
        if not self.data.get('connected'):self.feedback.set('WhatsApp todavía no está conectado. Administración puede activarlo desde Marketing.')
    def selected(self,kind):
        selected=getattr(self,kind).selection()
        if not selected:self.feedback.set('Selecciona un registro de la lista.');return None
        return next((r for r in self.data.get(kind,[]) if str(r['id'])==selected[0]),None)
    def mode(self,value):
        row=self.selected('conversations')
        if row:self.run(lambda:self.api.rpc('marketing_conversation_mode',p_id=row['id'],p_mode=value))
    def reject(self):
        row=self.selected('links')
        if row and messagebox.askyesno('Rechazar vinculación','¿Rechazar esta solicitud?',parent=self):self.run(lambda:self.api.rpc('marketing_review_link',p_id=row['id'],p_client_id=0,p_approved=False))
    def approve(self):
        row=self.selected('links')
        if not row:return
        query=simpledialog.askstring('Buscar cliente','Busca por nombre, documento o teléfono:',parent=self)
        if query is None:return
        def choose(rows):
            d=Modal(self,'Verificar identidad del cliente');hint(d.body,'Comprueba personalmente la identidad y el número. El nombre y cumpleaños enviados por chat no son suficientes.')
            tree=table(d.body,[('name','Cliente',210),('document','Documento',140),('phone','Teléfono registrado',155)],7)
            fill(tree,[(r['id'],((r['first_name']+' '+r.get('last_name','')).strip(),r.get('document',''),r.get('phone',''))) for r in rows])
            def accept():
                selected=tree.selection()
                if not selected:return
                c=next(r for r in rows if str(r['id'])==selected[0])
                if messagebox.askyesno('Confirmar vinculación',f"¿Verificaste que {row['sender_number']} pertenece a {c['first_name']} {c.get('last_name','')}?",parent=d):d.close(c['id'])
            actions(d.body,[('Cancelar',d.close),('Identidad verificada',accept)])
            cid=d.show()
            if cid:self.run(lambda:self.api.rpc('marketing_review_link',p_id=row['id'],p_client_id=cid,p_approved=True))
        self.run(lambda:self.api.lookup(query),choose,False)
