"""Shared server-authorized membership freezes; no local calendar arithmetic."""
import json
from datetime import date, timedelta
import tkinter as tk
from tkinter import ttk
from uuid import uuid4
from desktop_ui import Modal, messagebox, simpledialog
from gym_time import display_timestamp, timezone_for
from responsive_ui import AutoScrollbar, UI_FONT


def rpc(db, name, **params):
    result = db._execute(db.client.rpc(name, {'p_gym_id': db.gym_id, **params})).data
    return json.loads(result) if isinstance(result, str) else result


def date_label(value):
    if not value:
        return '—'
    year, month, day = str(value)[:10].split('-')
    return f'{day}/{month}/{year}'


class FreezeManager:
    def __init__(self, parent, db, client_id, client_name, changed):
        self.db, self.client_id, self.changed = db, int(client_id), changed
        self.window = Modal(parent, f'Membresía · {client_name}')
        self.window.preferred_width = 820
        self.window.minimum_height = 580
        self.window._freeze_manager = self
        body = self.window.body
        self.status = tk.StringVar(self.window, 'Consultando membresía…')
        ttk.Label(body, textvariable=self.status, justify='left', wraplength=680).pack(fill='x', pady=(0, 14))
        self.controls = ttk.Frame(body)
        self.controls.pack(fill='x', pady=8)
        style = ttk.Style(self.window)
        style.configure('Freeze.Treeview', background='#172235', fieldbackground='#172235',
                        foreground='#f8fafc', rowheight=28, font=(UI_FONT, 10))
        style.map('Freeze.Treeview', background=[('selected','#244475')], foreground=[('selected','#ffffff')])
        style.configure('Freeze.Treeview.Heading', background='#263c5e', foreground='#f8fafc', font=(UI_FONT,10,'bold'))
        self.table = ttk.Treeview(body, style='Freeze.Treeview', columns=('dates', 'days', 'status', 'created'), show='headings', height=7)
        for key, label, width in [('dates','Congelación',230),('days','Días',70),('status','Estado',110),('created','Registrada',170)]:
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=65)
        self.table.pack(fill='both', expand=True)
        scroll = AutoScrollbar(body, orient='horizontal', command=self.table.xview)
        scroll.pack(fill='x')
        self.table.configure(xscrollcommand=scroll.set)
        ttk.Button(body, text='Cerrar', command=self.window.close).pack(anchor='e', pady=(14, 0))
        try:
            self.load()
        except Exception:
            self.window.close()
            raise

    @property
    def admin(self):
        return getattr(self.db.cloud, 'role', '') == 'admin'

    def load(self):
        self.info = rpc(self.db, 'membership_freeze_info', p_client_id=self.client_id)
        self.membership = self.info['membership']
        m = self.membership
        policy = m.get('freeze_policy') or self.info['policy']
        self.days = int(policy['duration_days'])
        text = f"Estado: {'CONGELADA' if m.get('frozen') else m.get('status', 'Sin plan')}\nPlan: {m.get('plan_name', 'Sin plan')}\nVencimiento: {date_label(m.get('membership_end'))}"
        if m.get('frozen'):
            text += f"\nCongelada hasta: {date_label(m.get('freeze_last_date'))}\nSe reactiva: {date_label(m.get('resume_date'))}"
        elif not m.get('can_freeze'):
            text += '\nEsta membresía no cumple la política para una nueva congelación.'
        self.status.set(text)
        for child in self.controls.winfo_children():
            child.destroy()
        if m.get('can_freeze'):
            ttk.Button(self.controls, text=f'CONGELAR {self.days} DÍAS', command=self.confirm).pack(side='left', padx=(0, 8))
        if self.admin:
            ttk.Button(self.controls, text='Política de congelación', command=self.policy).pack(side='left', padx=(0, 8))
            if m.get('frozen'):
                ttk.Button(self.controls, text='Cancelar congelación', command=self.cancel).pack(side='left')
            elif m.get('membership_id') and m.get('allowed') and not m.get('can_freeze'):
                ttk.Button(self.controls, text='Excepción administrativa', command=lambda:self.confirm(True)).pack(side='left')
        self.table.delete(*self.table.get_children())
        for f in self.info['history']:
            self.table.insert('', 'end', iid=f['id'], values=(
                f"{date_label(f['start_date'])} → {date_label((date.fromisoformat(f['resume_date'])-timedelta(days=1)).isoformat())}",
                int(f['days_added']) - int(f['days_reversed']),
                {'ACTIVE':'Activa','COMPLETED':'Completada','CANCELLED':'Cancelada','SCHEDULED':'Programada'}[f['status']],
                display_timestamp(f['created_at'], timezone_for(self.db))))

    def confirm(self, override=False):
        reason = ''
        if override:
            reason = simpledialog.askstring('Excepción administrativa', 'Motivo de la excepción (obligatorio):', parent=self.window)
            if not reason:
                return
        d = Modal(self.window, 'Confirmar congelación')
        d.preferred_width = 540
        ttk.Label(d.body, text=f'¿Deseas congelar esta membresía durante {self.days} días?\n\nDurante este período el cliente no podrá registrar entradas.\nLa fecha de vencimiento se extenderá {self.days} días.', justify='left', wraplength=450).pack(fill='x', pady=12)
        actions = ttk.Frame(d.body)
        actions.pack(fill='x', pady=12)
        ttk.Button(actions, text='Cancelar', command=d.close).pack(side='right')
        ttk.Button(actions, text='Congelar', command=lambda:d.close(True)).pack(side='right', padx=8)
        if not d.show():
            return
        # One stable key survives any UI retry; the DB also locks the client.
        key = getattr(self, '_request_id', None) or str(uuid4())
        self._request_id = key
        try:
            rpc(self.db, 'membership_freeze', p_membership_id=int(self.membership['membership_id']),
                p_request_id=key, p_reason=reason, p_override=override)
        except Exception as error:
            messagebox.showerror('No se pudo congelar', str(error), parent=self.window)
            try:
                self.load()
            except Exception:
                self.status.set('No se pudo confirmar el estado. Reabre esta ventana cuando vuelva la conexión.')
            return
        self._request_id = None
        self.changed()
        self.load()

    def cancel(self):
        reason = simpledialog.askstring('Cancelar congelación', 'Motivo de cancelación (obligatorio):', parent=self.window)
        if not reason:
            return
        if not messagebox.askyesno('Cancelar congelación', 'Se conservarán solamente los días completos ya congelados. El cliente podrá volver a entrar. ¿Continuar?', parent=self.window):
            return
        try:
            rpc(self.db, 'membership_cancel_freeze', p_freeze_id=self.membership['freeze']['id'], p_reason=reason)
        except Exception as error:
            messagebox.showerror('No se pudo cancelar la congelación', str(error), parent=self.window)
            return
        self.changed()
        self.load()

    def policy(self):
        plan_id = self.membership.get('plan_id')
        d = Modal(self.window, 'Política de congelación')
        d.preferred_width = 540
        policy = self.membership.get('freeze_policy') or self.info['policy']
        enabled = tk.BooleanVar(d, bool(policy['enabled']))
        days = tk.StringVar(d, str(policy['duration_days']))
        maximum = tk.StringVar(d, str(policy['max_per_membership']))
        scope = tk.StringVar(d, 'Este plan' if plan_id else 'Todo el gimnasio')
        ttk.Checkbutton(d.body, text='Permitir congelación', variable=enabled).pack(anchor='w', pady=8)
        ttk.Label(d.body, text='Aplicar a').pack(anchor='w')
        ttk.Combobox(d.body, textvariable=scope, state='readonly', values=['Todo el gimnasio'] + (['Este plan'] if plan_id else [])).pack(fill='x')
        for label, variable in [('Duración (días)', days), ('Máximo por ciclo/membresía', maximum)]:
            ttk.Label(d.body, text=label).pack(anchor='w', pady=(10, 3))
            ttk.Entry(d.body, textvariable=variable).pack(fill='x')
        def save():
            try:
                rpc(self.db, 'membership_save_freeze_policy', p_enabled=enabled.get(),
                    p_duration_days=int(days.get()), p_max_per_membership=int(maximum.get()),
                    p_plan_id=plan_id if scope.get() == 'Este plan' else None)
            except Exception as error:
                messagebox.showerror('Revisa la política', str(error), parent=d)
                return
            d.close(True)
        ttk.Button(d.body, text='Guardar', command=save).pack(anchor='e', pady=14)
        if d.show():
            self.load()


def open_freeze_manager(parent, db, client_id, client_name, changed=lambda:None):
    try:
        manager = FreezeManager(parent, db, client_id, client_name, changed)
        manager.window.show()
    except Exception as error:
        messagebox.showerror('No se pudo consultar la membresía', str(error), parent=parent)
