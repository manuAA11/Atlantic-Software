"""Campos compartidos para trasladar una tiquetera que ya estaba en uso."""
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from uuid import uuid4
from plan_forms import carryover_values, plan_end_date


class CarryoverFields(ttk.Frame):
    def __init__(self, parent, plan, start, today, on_change):
        super().__init__(parent, style='Card.TFrame', padding=10)
        self.plan = plan
        self.start = start
        self.today = today
        self.on_change = on_change
        self.request_id = str(uuid4())
        self.enabled = tk.BooleanVar(self, value=False)
        self.used = tk.StringVar(self, value='0')
        self.columnconfigure(0, weight=1)
        ttk.Checkbutton(self, text='Tiquetera ya iniciada (sin nuevo cobro)',
                        variable=self.enabled).grid(row=0, column=0, sticky='w')
        self.fields = ttk.Frame(self, style='Card.TFrame')
        self.fields.grid(row=1, column=0, sticky='ew', pady=(8, 0))
        self.fields.columnconfigure(0, weight=1)
        ttk.Label(self.fields, text='Entradas ya utilizadas', style='Field.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Entry(self.fields, textvariable=self.used).grid(row=1, column=0, sticky='ew', pady=(3, 4))
        self.preview = ttk.Label(self, style='CardMuted.TLabel', wraplength=450)
        self.preview.grid(row=2, column=0, sticky='ew', pady=(8, 0))
        self.enabled.trace_add('write', self.changed)
        self.used.trace_add('write', lambda *_: self.update_preview())
        self.start.trace_add('write', lambda *_: self.update_preview())

    def changed(self, *_):
        self.update_preview()
        self.on_change()

    def refresh(self):
        plan = self.plan() or {}
        if plan.get('entry_limit') is not None:
            self.grid()
        else:
            self.enabled.set(False)
            self.grid_remove()
        self.update_preview()

    def update_preview(self):
        if self.enabled.get():
            self.fields.grid()
        else:
            self.fields.grid_remove()
        plan = self.plan() or {}
        try:
            start = datetime.strptime(self.start.get(), '%d/%m/%Y').date()
            end = plan_end_date(plan, start)
            text = f'Vencimiento: {end:%d/%m/%Y}.'
            if self.enabled.get():
                used, end = carryover_values(plan, start.isoformat(), self.used.get(), self.today)
                remaining = int(plan['entry_limit']) - used
                text += f' Quedan {remaining} de {plan["entry_limit"]} entradas.'
                text += f' El próximo ingreso será el número {used + 1}.' if remaining else ' El cupo está agotado.'
                text += ' Este traslado no registra un nuevo cobro ni crea visitas anteriores.'
            else:
                text += ' Si hay otro plan pendiente, las fechas se desplazan al terminar ese plan.'
        except (ValueError, KeyError, TypeError):
            text = 'Completa la fecha de inicio y las entradas utilizadas para ver el saldo.'
        self.preview.configure(text=text)

    def payload(self, start):
        if not self.enabled.get():
            return {}
        used, _end = carryover_values(self.plan(), start, self.used.get(), self.today)
        return {'carryover': True, 'initial_entries_used': used, 'request_id': self.request_id}
