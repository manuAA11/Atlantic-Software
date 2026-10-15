"""Shared server-authorized membership freezes; no local calendar arithmetic."""
import json
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
        return getattr(self, 'info', {}).get('permissions', {}).get('can_resume',
               getattr(self.db.cloud, 'role', '') in ('admin', 'owner'))

    def load(self):
        self.info = rpc(self.db, 'membership_freeze_info', p_client_id=self.client_id)
        self.membership = self.info['membership']
        m = self.membership
        internal = m.get('membership_type') == 'INTERNAL'
        policy = m.get('freeze_policy') or self.info['policy']
        self.days = int(policy['duration_days'])
        expiry = 'Sin vencimiento' if m.get('has_expiration', True) is False else date_label(m.get('membership_end'))
        text = f"Estado: {'CONGELADA' if m.get('frozen') else m.get('status', 'Sin plan')}\nPlan: {m.get('plan_name', 'Sin plan')}\nVencimiento: {expiry}"
        if internal:
            text += '\nPlan interno · sin pago · excluido de estadísticas financieras.'
            text += '\nAcceso ilimitado' if m.get('unlimited_access') else '\nEntradas restantes: '+str(m.get('entries_remaining', 0))
        if m.get('frozen'):
            f = m['freeze']; zone = f.get('timezone') or timezone_for(self.db)
            text += (f"\nInicio: {display_timestamp(f.get('freeze_started_at') or f.get('starts_at'), zone)}"
                     f"\nReanudación máxima: {display_timestamp(f.get('ends_at'), zone)}"
                     f"\nUtilizados: {f.get('freeze_used_days', 0)} de {f.get('freeze_max_days', self.days)} días"
                     f"\nRestantes del período: {f.get('freeze_remaining_days', self.days)} días")
        elif not m.get('can_freeze'):
            text += '\nEsta membresía no cumple la política para una nueva congelación.'
        self.status.set(text)
        for child in self.controls.winfo_children():
            child.destroy()
        if m.get('can_freeze'):
            ttk.Button(self.controls, text=f'CONGELAR {self.days} DÍAS', command=self.confirm).pack(side='left', padx=(0, 8))
        if self.admin and not internal:
            ttk.Button(self.controls, text='Política de congelación', command=self.policy).pack(side='left', padx=(0, 8))
            if m.get('frozen'):
                ttk.Button(self.controls, text='REANUDAR MEMBRESÍA', command=self.resume).pack(side='left')
            elif m.get('membership_id') and m.get('allowed') and not m.get('can_freeze'):
                ttk.Button(self.controls, text='Excepción administrativa', command=lambda:self.confirm(True)).pack(side='left')
        if internal and self.info.get('permissions', {}).get('can_manage_internal', self.admin):
            ttk.Button(self.controls, text='DESACTIVAR MEMBRESÍA' if m.get('membership_active') else 'ACTIVAR MEMBRESÍA',
                       command=self.toggle_internal).pack(side='left')
        self.table.delete(*self.table.get_children())
        for f in self.info['history']:
            self.table.insert('', 'end', iid=f['id'], values=(
                f"{display_timestamp(f.get('starts_at'), f.get('timezone') or timezone_for(self.db), seconds=False)} → {display_timestamp(f.get('resumed_at') or f.get('ends_at'), f.get('timezone') or timezone_for(self.db), seconds=False)}",
                f.get('freeze_used_days', int(f['days_added']) - int(f['days_reversed'])),
                {'ACTIVE':'Activa','COMPLETED':'Automática','RESUMED':'Reanudada','CANCELLED':'Cancelada','SCHEDULED':'Programada'}[f['status']],
                display_timestamp(f['created_at'], timezone_for(self.db))))

    def confirm(self, override=False):
        reason = ''
        if override:
            reason = simpledialog.askstring('Excepción administrativa', 'Motivo de la excepción (obligatorio):', parent=self.window)
            if not reason:
                return
        d = Modal(self.window, 'Confirmar congelación')
        d.preferred_width = 540
        ttk.Label(d.body, text=f'¿Deseas congelar esta membresía hasta un máximo de {self.days} días?\n\nDurante este período el cliente no podrá registrar entradas.\nPuedes reanudar antes. Al finalizar se agregarán solamente los días completos utilizados.', justify='left', wraplength=450).pack(fill='x', pady=12)
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

    def resume(self):
        try:
            preview = rpc(self.db, 'membership_resume_preview', p_freeze_id=self.membership['freeze']['id'])
            if not preview.get('can_resume'):
                self.load(); return
            days = int(preview['extension_days'])
            d = Modal(self.window, '¿Reanudar esta membresía?')
            d.preferred_width = 560
            ttk.Label(d.body, text=f'La membresía ha permanecido congelada durante {days} días completos.\nSe agregarán {days} días a su fecha de vencimiento.',
                      justify='left', wraplength=470).pack(fill='x', pady=12)
            actions = ttk.Frame(d.body); actions.pack(fill='x', pady=12)
            ttk.Button(actions, text='Cancelar', command=d.close).pack(side='left')
            ttk.Button(actions, text='Reanudar membresía', command=lambda:d.close(True)).pack(side='right')
            if not d.show(): return
            rpc(self.db, 'membership_resume_freeze', p_freeze_id=preview['id'], p_expected_days=days, p_reason='Reanudación solicitada desde Administración')
        except Exception as error:
            messagebox.showerror('No se pudo reanudar la membresía', str(error), parent=self.window)
            self.load()
            return
        self.changed()
        self.load()

    def cancel(self):
        """Compatibility for callers of the former controller method."""
        self.resume()

    def toggle_internal(self):
        active = not self.membership.get('membership_active', True)
        reason = simpledialog.askstring('Activar membresía interna' if active else 'Desactivar membresía interna',
                                       'Motivo del cambio (obligatorio):', parent=self.window)
        if not reason: return
        try:
            rpc(self.db, 'set_internal_membership_active', p_membership_id=self.membership['membership_id'], p_active=active, p_reason=reason)
        except Exception as error:
            messagebox.showerror('No se pudo cambiar la membresía', str(error), parent=self.window); return
        self.changed(); self.load()

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
        for label, variable in [('Máximo permitido (1 a 7 días)', days), ('Máximo por ciclo/membresía', maximum)]:
            ttk.Label(d.body, text=label).pack(anchor='w', pady=(10, 3))
            ttk.Entry(d.body, textvariable=variable, state='readonly' if variable is maximum else 'normal').pack(fill='x')
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
