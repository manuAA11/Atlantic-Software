"""Shared plan editor using the existing Atlantic dialog, fields and controls."""
import tkinter as tk
from tkinter import ttk
from desktop_ui import messagebox, Modal
from plan_forms import validate_plan_options, validate_months


class PlanEditorMixin:
    def __init__(self, parent, data=None):
        data = data or {}
        super().__init__(parent, 'Editar plan' if data else 'Nuevo plan', 630, 780)
        self.name = tk.StringVar(self, data.get('name', ''))
        self.days = tk.StringVar(self, str(data.get('duration_days') or 30))
        self.months = tk.StringVar(self, str(data.get('duration_months') or 1))
        self.price = tk.StringVar(self, str(data.get('price', 55000)))
        self.kind = tk.StringVar(self, 'Tiquetera / por entradas' if data.get('entry_limit') is not None else 'Mensualidad / por días')
        self.plan_type = tk.StringVar(self, 'Interno / No comercial' if data.get('plan_type') == 'INTERNAL' else 'Comercial')
        self.unlimited = tk.BooleanVar(self, data.get('unlimited_access', True))
        self.indefinite = tk.BooleanVar(self, not data.get('has_expiration', True))
        self.financial = tk.BooleanVar(self, data.get('include_in_financial_stats', True))
        self.entries = tk.StringVar(self, str(data.get('entry_limit') or 15))
        self.unit = tk.StringVar(self, 'Días' if data.get('entry_limit') is not None and data.get('duration_months') is None else 'Meses calendario')
        self.add_entry('Nombre del plan', self.name, 0)
        ttk.Label(self.body, text='Tipo de plan', style='Field.TLabel').grid(row=2, column=0, sticky='w', pady=(10, 3))
        self.type_control = ttk.Combobox(self.body, textvariable=self.plan_type, state='readonly', values=('Comercial', 'Interno / No comercial'))
        self.type_control.grid(row=3, column=0, sticky='ew')
        self.kind_control = ttk.Combobox(self.body, textvariable=self.kind, state='readonly', values=('Mensualidad / por días', 'Tiquetera / por entradas'))
        self.kind_control.grid(row=4, column=0, sticky='ew', pady=(10, 0))
        self.internal_frame = ttk.Frame(self.body, style='Surface.TFrame')
        self.internal_frame.grid(row=5, column=0, sticky='ew', pady=(10, 0))
        ttk.Checkbutton(self.internal_frame, text='Acceso ilimitado', variable=self.unlimited, command=self.update_kind).pack(anchor='w')
        ttk.Checkbutton(self.internal_frame, text='Vigencia indefinida', variable=self.indefinite, command=self.update_kind).pack(anchor='w', pady=(5, 0))
        ttk.Label(self.internal_frame, text='Sin venta, ingreso, deuda ni pago. Excluido de estadísticas financieras.', style='CardMuted.TLabel', wraplength=490).pack(anchor='w', pady=(8, 0))
        self.unit_frame = ttk.Frame(self.body, style='Surface.TFrame')
        self.unit_frame.grid(row=6, column=0, sticky='ew', pady=(10, 0))
        self.unit_frame.columnconfigure(0, weight=1)
        ttk.Label(self.unit_frame, text='Unidad de vigencia', style='Field.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Combobox(self.unit_frame, textvariable=self.unit, state='readonly', values=('Meses calendario', 'Días')).grid(row=1, column=0, sticky='ew', pady=(3, 0))
        self.duration_label = ttk.Label(self.body, style='Field.TLabel')
        self.duration_label.grid(row=7, column=0, sticky='w', pady=(10, 3))
        self.duration_entry = ttk.Entry(self.body)
        self.duration_entry.grid(row=8, column=0, sticky='ew')
        self.entries_label = ttk.Label(self.body, text='Cantidad total de entradas', style='Field.TLabel')
        self.entries_label.grid(row=9, column=0, sticky='w', pady=(10, 3))
        self.entries_entry = ttk.Entry(self.body, textvariable=self.entries)
        self.entries_entry.grid(row=10, column=0, sticky='ew')
        ttk.Label(self.body, text='Precio', style='Field.TLabel').grid(row=11, column=0, sticky='w', pady=(10, 3))
        self.price_entry = ttk.Entry(self.body, textvariable=self.price)
        self.price_entry.grid(row=12, column=0, sticky='ew')
        self.hint = ttk.Label(self.body, style='CardMuted.TLabel', wraplength=490)
        self.hint.grid(row=13, column=0, sticky='ew', pady=(12, 0))
        self.add_buttons(self.save, 14)
        self._previous_type = self.plan_type.get()
        self.plan_type.trace_add('write', self.type_changed)
        self.kind.trace_add('write', lambda *_: self.update_kind())
        self.unit.trace_add('write', lambda *_: self.update_kind())
        self.update_kind()

    def type_changed(self, *_):
        internal = self.plan_type.get() == 'Interno / No comercial'
        if self.plan_type.get() != self._previous_type:
            if internal:
                self._commercial_price = self.price.get()
                self.price.set('0'); self.unlimited.set(True); self.indefinite.set(True); self.financial.set(False)
            else:
                self.price.set(getattr(self, '_commercial_price', '55000')); self.indefinite.set(False); self.financial.set(True)
            self._previous_type = self.plan_type.get()
        self.update_kind()

    def update_kind(self):
        internal = self.plan_type.get() == 'Interno / No comercial'
        ticket = not self.unlimited.get() if internal else self.kind.get() == 'Tiquetera / por entradas'
        indefinite = internal and self.indefinite.get()
        months = not internal and ticket and self.unit.get() == 'Meses calendario'
        self.kind_control.grid_remove() if internal else self.kind_control.grid()
        self.internal_frame.grid() if internal else self.internal_frame.grid_remove()
        self.unit_frame.grid() if not internal and ticket else self.unit_frame.grid_remove()
        for widget in (self.entries_label, self.entries_entry):
            widget.grid() if ticket else widget.grid_remove()
        for widget in (self.duration_label, self.duration_entry):
            widget.grid_remove() if indefinite else widget.grid()
        self.duration_label.configure(text='Cantidad de meses de vigencia' if months else 'Vigencia en días')
        self.duration_entry.configure(textvariable=self.months if months else self.days)
        self.price_entry.configure(state='disabled' if internal else 'normal')
        self.hint.configure(text=('Puedes usar cualquier nombre. Los valores recomendados son $0, acceso ilimitado y vigencia indefinida; no se crea ningún plan automáticamente.' if internal else
            'La tiquetera termina al agotar las entradas o vencer su vigencia. Las compras existentes conservan su cupo y fechas.' if ticket else
            'Acceso por días, sin límite de entradas durante la vigencia. Las membresías vendidas conservan sus fechas.'))

    def save(self):
        try:
            internal = self.plan_type.get() == 'Interno / No comercial'
            ticket = self.kind.get() == 'Tiquetera / por entradas'
            months = validate_months(self.months.get(), self.entries.get()) if not internal and ticket and self.unit.get() == 'Meses calendario' else None
            self.result = validate_plan_options(self.name.get(), months * 30 if months else self.days.get(), self.price.get(),
                self.entries.get() if (not self.unlimited.get() if internal else ticket) else None, months,
                'INTERNAL' if internal else 'COMMERCIAL', self.unlimited.get(), not self.indefinite.get() if internal else True,
                self.financial.get())
        except ValueError as error:
            messagebox.showwarning('Revisa el plan', str(error), parent=self)
            return
        if hasattr(self, 'close'):
            self.close(self.result)
        else:
            self.destroy()


class _PlanModalAdapter(Modal):
    def __init__(self, parent, title, width, height):
        super().__init__(parent, title)
        self.preferred_width = width
        self.minimum_height = 550
        self.body.columnconfigure(0, weight=1)

    def add_entry(self, label, variable, row):
        ttk.Label(self.body, text=label, style='Field.TLabel').grid(row=row * 2, column=0, sticky='w', pady=(7, 3))
        entry = ttk.Entry(self.body, textvariable=variable)
        entry.grid(row=row * 2 + 1, column=0, sticky='ew')
        return entry

    def add_buttons(self, save, row):
        bar = ttk.Frame(self.body)
        bar.grid(row=row, column=0, sticky='ew', pady=(14, 0))
        ttk.Button(bar, text='Cancelar', command=self.close).pack(side='left')
        ttk.Button(bar, text='Guardar', command=save).pack(side='right')


class OwnerPlanDialog(PlanEditorMixin, _PlanModalAdapter):
    pass
