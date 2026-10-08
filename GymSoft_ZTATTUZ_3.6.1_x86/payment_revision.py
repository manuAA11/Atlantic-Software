"""Corrección de registros de pagos, compartida por Admin y Recepción.

No realiza devoluciones bancarias. Supabase autoriza y audita cada cambio.
"""
from __future__ import annotations
from gym_time import local_datetime, timezone_for

from responsive_ui import AutoScrollbar

import json
import re
from datetime import datetime, timedelta, timezone
import tkinter as tk
from tkinter import ttk
from responsive_ui import UI_FONT
from desktop_ui import messagebox
from typing import Any, Callable
from money_input import parse_amount

PAYMENT_UPDATE = "GymSoft-PAGOS-2.0.1"
PAYMENT_EXCEL_COLUMNS = {
    "Estado del pago": "payment_status",
    "Revisión del pago": "payment_revision",
    "Fecha de corrección": "payment_changed_at",
    "Corregido por": "payment_changed_by",
    "Motivo del cambio": "payment_change_reason",
}


def payment_amount(row: dict[str, Any]) -> int:
    value = row.get("amount")
    return int(row.get("amount_paid") or 0) if value is None else int(value)


def posted_income(rows: list[dict[str, Any]]) -> int:
    return sum(payment_amount(row) for row in rows
               if row.get("payment_status", "posted") == "posted")


def validate_import_payment(row: dict[str, Any]) -> None:
    """No permite que un estado desconocido se convierta en un pago vigente."""
    status = str(row.get("payment_status") or "posted").strip().lower()
    if status not in ("posted", "void"):
        raise ValueError("Estado del pago no válido: conserva posted o void en el Excel.")
    revision = row.get("payment_revision")
    if revision in (None, ""):
        revision = 0
    if not re.fullmatch(r"[0-9]+", str(revision)):
        raise ValueError("La revisión del pago debe ser un entero no negativo.")
    row["payment_status"] = status
    row["payment_revision"] = int(revision)


def _rpc(db: Any, name: str, data: dict[str, Any]) -> Any:
    try:
        response = db._execute(db.client.rpc(name, {"p_gym_id": db.gym_id, **data}))
    except Exception as error:
        code = str(getattr(error, "code", ""))
        if code in ("PGRST202", "42883"):
            raise ValueError("La función de pagos no está disponible en el proyecto comercial. Contacta al proveedor; no vuelvas a instalar la base completa.") from error
        raise
    result = response.data
    return json.loads(result) if isinstance(result, str) else result


def _when(value: Any, zone: str = 'America/Bogota') -> str:
    if not value: return '—'
    try: return local_datetime(value, zone).strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError): return str(value)


def open_payment_manager(
    parent: tk.Misc, db: Any, client_id: int, client_name: str,
    dialog_class: type, money: Callable[[Any], str],
    date_display: Callable[[Any], str], on_changed: Callable[[], None],
    money_hidden: Callable[[], bool] = lambda: False,
) -> None:
    """Un historial por cliente; cada pago conserva su identificador."""
    controller = _PaymentManager(
        parent, db, client_id, client_name, dialog_class,
        money, date_display, on_changed, money_hidden,
    )
    controller.window._payment_manager = controller


class _PaymentManager:
    def __init__(self, parent, db, client_id, client_name, dialog_class,
                 money, date_display, on_changed, money_hidden):
        self.db, self.client_id = db, int(client_id)
        self.dialog_class, self.money, self.date_display = dialog_class, money, date_display
        self.on_changed, self.money_hidden = on_changed, money_hidden
        self.window = self._window(parent, f"Pagos · {client_name}", 980, 560)
        body = self.window.body
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)
        ttk.Label(body, text=f"Pagos de {client_name}", font=(UI_FONT, 16, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8))
        controls = ttk.Frame(body)
        controls.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.include_void = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(controls, text="Mostrar también los anulados", variable=self.include_void,
                        command=lambda: self.load(0)).pack(side="left")
        self._button(controls, "Actualizar", lambda: self.load(self.offset)).pack(side="right")
        from membership_freeze_ui import open_freeze_manager
        self._button(controls, 'Membresía y congelación', lambda: open_freeze_manager(
            self.window, self.db, self.client_id, client_name, self.on_changed)).pack(side='right', padx=8)
        table = ttk.Frame(body)
        table.grid(row=2, column=0, sticky="nsew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        columns = (("paid", "Registrado", 130), ("plan", "Plan", 125),
                   ("period", "Vigencia", 180), ("amount", "Valor", 115),
                   ("method", "Método", 105), ("status", "Estado", 110))
        self.tree = ttk.Treeview(table, columns=[c[0] for c in columns], show="headings", selectmode="browse")
        for key, title, width in columns:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=85, anchor="center")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = AutoScrollbar(table, command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)
        horizontal = AutoScrollbar(table, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=horizontal.set)
        self.tree.tag_configure("void", foreground="#FDA4AF")
        self.tree.bind("<<TreeviewSelect>>", self.selection_changed)
        self.info = tk.StringVar(master=self.window)
        ttk.Label(body, textvariable=self.info, wraplength=760).grid(row=3, column=0, sticky="w", pady=10)
        actions = ttk.Frame(body)
        actions.grid(row=4, column=0, sticky="ew")
        self.edit_button = self._button(actions, "Corregir pago", lambda: self.edit(False), "#15803D")
        self.edit_button.pack(side="left", padx=(0, 8))
        self.void_button = self._button(actions, "Anular registro", lambda: self.edit(True), "#B91C1C")
        self.void_button.pack(side="left", padx=(0, 8))
        self.history_button = self._button(actions, "Ver cambios", self.history)
        self.history_button.pack(side="left")
        self._button(actions, "Cerrar", self.window.destroy).pack(side="right")
        paging = ttk.Frame(body)
        paging.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        self.prev_button = self._button(paging, "Anterior", lambda: self.load(max(self.offset - 50, 0)))
        self.prev_button.pack(side="left")
        self.page_text = tk.StringVar(master=self.window)
        ttk.Label(paging, textvariable=self.page_text).pack(side="left", padx=12)
        self.next_button = self._button(paging, "Siguiente", lambda: self.load(self.offset + 50))
        self.next_button.pack(side="left")
        self.offset, self.rows, self.busy = 0, {}, False
        self.load(0)

    @staticmethod
    def _button(parent, text, command, color="#263C5E"):
        return tk.Button(parent, text=text, command=command, bg=color, fg="white",
                         activebackground=color, activeforeground="white", relief="flat",
                         disabledforeground="#9CA3AF", font=(UI_FONT, 10, "bold"),
                         padx=12, pady=9, cursor="hand2", takefocus=True)

    def _window(self, parent, title, width, height):
        window = self.dialog_class(parent, title, width, height)
        window.body.columnconfigure(1, weight=0)
        width = min(width, window.winfo_screenwidth() - 40)
        height = min(height, window.winfo_screenheight() - 80)
        window.minsize(min(width, 730), min(height, 470))
        window.geometry(f"{width}x{height}+{max((window.winfo_screenwidth()-width)//2,0)}"
                        f"+{max((window.winfo_screenheight()-height)//2,0)}")
        return window

    def load(self, offset):
        selected = self.tree.selection()
        try:
            data = _rpc(self.db, "ztattuz_client_payments", {
                "p_client_id": self.client_id, "p_include_void": self.include_void.get(),
                "p_offset": offset, "p_limit": 50,
            })
            if not isinstance(data, dict) or not isinstance(data.get("rows"), list):
                raise ValueError("No se recibió un historial de pagos válido.")
        except Exception as error:
            self.rows = {}
            self.tree.delete(*self.tree.get_children())
            self.selection_changed()
            self.prev_button.configure(state="disabled")
            self.next_button.configure(state="disabled")
            self.info.set("No se pudo actualizar. Pulsa Actualizar para consultar el estado actual.")
            messagebox.showerror("No se pudieron consultar los pagos", str(error), parent=self.window)
            return
        self.offset = offset
        self.rows = {str(row["id"]): row for row in data["rows"]}
        self.tree.delete(*self.tree.get_children())
        for key, row in self.rows.items():
            void = row["payment_status"] == "void"
            state = "ANULADO" if void else ("CORREGIDO" if row["payment_revision"] else "REGISTRADO")
            self.tree.insert("", "end", iid=key, tags=("void",) if void else (), values=(
                _when(row["paid_at"], timezone_for(self.db)), row["plan_name"],
                f"{self.date_display(row['start_date'])} → {self.date_display(row['end_date'])}",
                self.money(row["amount"]), row["payment_method"], state,
            ))
        if selected and selected[0] in self.rows:
            self.tree.selection_set(selected[0])
        self.prev_button.configure(state="normal" if offset else "disabled")
        self.next_button.configure(state="normal" if data.get("has_more") else "disabled")
        self.page_text.set(f"Página {offset // 50 + 1}")
        self.selection_changed()

    def selected(self):
        keys = self.tree.selection()
        return self.rows.get(keys[0]) if keys else None

    def selection_changed(self, _event=None):
        row = self.selected()
        can_change = row is not None and row["payment_status"] == "posted" and not self.busy
        self.edit_button.configure(state="normal" if can_change else "disabled")
        self.void_button.configure(state="normal" if can_change else "disabled")
        self.history_button.configure(state="normal" if row and not self.busy else "disabled")
        self.info.set("Selecciona un pago para corregirlo o anularlo." if not row else
                      ("Anulado: excluido de ingresos y de vigencia. Su historial se conserva."
                       if row["payment_status"] == "void" else
                       "Corregir mantiene el mismo registro. Anular quita el pago de los ingresos."))

    def edit(self, void):
        row = self.selected()
        if row is None or row["payment_status"] != "posted" or self.busy:
            return
        if not void and self.money_hidden():
            messagebox.showinfo("Valores ocultos", "Selecciona «Mostrar valores» antes de corregir un importe.", parent=self.window)
            return
        form = self._window(self.window, "Anular registro" if void else "Corregir pago", 600, 535)
        form.body.columnconfigure(0, weight=1)
        ttk.Label(form.body, text=f"{row['plan_name']} · {self.money(row['amount'])}",
                  font=(UI_FONT, 14, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 10))
        if void:
            description = ("El pago dejará de contar en Finanzas y este plan no habilitará entradas. "
                           "Los otros planes conservarán sus fechas. Las entradas anteriores seguirán "
                           "en el historial. Esta acción no realiza una devolución bancaria.")
        else:
            description = "Corrige el valor, el método o la referencia. El plan y sus fechas se conservan."
        ttk.Label(form.body, text=description, wraplength=470).grid(row=1, column=0, sticky="w", pady=(0, 12))
        fields = ttk.Frame(form.body)
        fields.grid(row=2, column=0, sticky="ew")
        fields.columnconfigure(1, weight=1)
        variables = {}
        if not void:
            for index, (key, label, value) in enumerate((
                ("amount", "Valor en pesos", str(row["amount"])),
                ("method", "Método de pago", row["payment_method"] or "Efectivo"),
                ("reference", "Referencia", row.get("payment_reference") or ""),
            )):
                variable = tk.StringVar(master=form, value=value)
                variables[key] = variable
                ttk.Label(fields, text=label).grid(row=index, column=0, sticky="w", padx=(0, 12), pady=6)
                widget = (ttk.Combobox(fields, textvariable=variable, values=("Efectivo", "Transferencia", "Tarjeta", "Otro"))
                          if key == "method" else ttk.Entry(fields, textvariable=variable))
                widget.grid(row=index, column=1, sticky="ew", pady=6)
        ttk.Label(form.body, text="Motivo obligatorio (3 a 500 caracteres)").grid(row=3, column=0, sticky="w", pady=(12, 6))
        reason = tk.Text(form.body, height=4, wrap="word", bg="#172235", fg="white", insertbackground="white",
                         font=(UI_FONT, 10), relief="flat", padx=8, pady=8)
        reason.grid(row=4, column=0, sticky="nsew")
        form.body.rowconfigure(4, weight=1)
        buttons = ttk.Frame(form.body)
        buttons.grid(row=5, column=0, sticky="e", pady=(14, 0))

        def close():
            if not self.busy:
                form.destroy()
                self.window.grab_set()

        def save():
            if self.busy:
                return
            try:
                why = reason.get("1.0", "end-1c").strip()
                if not 3 <= len(why) <= 500:
                    raise ValueError("Escribe un motivo de 3 a 500 caracteres.")
                args = {"p_membership_id": int(row["id"]),
                        "p_expected_revision": int(row["payment_revision"]),
                        "p_action": "void" if void else "correct", "p_reason": why}
                if not void:
                    args.update(p_amount=parse_amount(variables["amount"].get()),
                                p_payment_method=variables["method"].get().strip(),
                                p_payment_reference=variables["reference"].get().strip())
                self.busy = True
                save_button.configure(state="disabled")
                _rpc(self.db, "ztattuz_change_payment", args)
            except Exception as error:
                messagebox.showerror("No se confirmó el cambio",
                                     f"{error}\n\nSi se perdió la conexión, actualiza el historial antes de reintentar.", parent=form)
                return
            finally:
                self.busy = False
                save_button.configure(state="normal")
            close()
            self.load(self.offset)
            try:
                self.on_changed()
            except Exception:
                messagebox.showinfo("Cambio guardado", "El pago se actualizó. Abre de nuevo la sección para consultar los cambios.", parent=self.window)

        self._button(buttons, "Cancelar", close).pack(side="left", padx=(0, 8))
        save_button = self._button(buttons, "Confirmar anulación" if void else "Guardar corrección", save,
                                   "#B91C1C" if void else "#15803D")
        save_button.pack(side="left")
        form.protocol("WM_DELETE_WINDOW", close)
        form.bind("<Escape>", lambda _event: close())
        reason.focus_set()

    def history(self):
        row = self.selected()
        if row is None:
            return
        try:
            entries = _rpc(self.db, "ztattuz_payment_history", {"p_membership_id": int(row["id"])})
        except Exception as error:
            messagebox.showerror("No se pudo consultar la auditoría", str(error), parent=self.window)
            return
        window = self._window(self.window, f"Cambios del pago #{row['id']}", 760, 520)

        def close():
            window.destroy()
            self.window.grab_set()

        footer = ttk.Frame(window.body)
        footer.pack(side="bottom", fill="x", pady=(10, 0))
        self._button(footer, "Cerrar", close).pack(side="right")
        content = ttk.Frame(window.body)
        content.pack(fill="both", expand=True)
        text = tk.Text(content, wrap="word", bg="#172235", fg="white", font=(UI_FONT, 11), padx=14, pady=14)
        scroll = AutoScrollbar(content, command=text.yview)
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill="both", expand=True)
        if not entries:
            text.insert("end", "No hay cambios registrados para este pago.")
        for entry in entries:
            details = entry.get("details") or {}
            before, after = details.get("before"), details.get("after")
            label = {"PAGO_EDITADO": "CORRECCIÓN", "PAGO_ANULADO": "ANULACIÓN", "PAGO_REGISTRADO": "REGISTRO"}.get(entry["action"], entry["action"])
            text.insert("end", f"{label} · {_when(entry.get('created_at'), timezone_for(self.db))}\n"
                               f"{entry.get('actor_email', 'Sistema')} · {entry.get('actor_role', '')}\n")
            if isinstance(before, dict) and isinstance(after, dict):
                text.insert("end", f"Valor: {self.money(payment_amount(before))} → {self.money(payment_amount(after))}\n"
                                   f"Método: {before.get('payment_method', '')} → {after.get('payment_method', '')}\n")
                if not self.money_hidden():
                    text.insert("end", f"Referencia: {before.get('payment_reference') or '—'} → {after.get('payment_reference') or '—'}\n"
                                       f"Motivo: {details.get('reason') or '—'}\n")
            elif not self.money_hidden():
                text.insert("end", f"{entry.get('summary', '')}\n")
            text.insert("end", "\n")
        text.configure(state="disabled")

        window.protocol("WM_DELETE_WINDOW", close)
