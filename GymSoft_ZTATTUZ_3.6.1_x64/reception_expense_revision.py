from __future__ import annotations

"""Formulario seguro para que Recepción registre gastos.

El módulo no consulta ni lista la contabilidad. Solo abre un formulario y
envía los datos al RPC validado por Supabase; el usuario que inició sesión se
guarda automáticamente como responsable del movimiento.
"""

import re
import tkinter as tk
from datetime import date
from tkinter import ttk
from desktop_ui import messagebox
from typing import Any, Callable


MARKER = "GymSoft-RECEPTION-EXPENSES-2.0.4"

_CATEGORIES = (
    "Arriendo",
    "Servicios públicos",
    "Nómina",
    "Insumos",
    "Mantenimiento",
    "Transporte",
    "Impuestos",
    "Otro",
)
_PAYMENT_METHODS = (
    "Efectivo",
    "Transferencia",
    "Tarjeta",
    "Otro",
)


def _parse_date(value: str) -> str:
    text = value.strip()
    if not re.fullmatch(r'[0-9]{2}/[0-9]{2}/[0-9]{4}',text):
        raise ValueError('Usa la fecha en formato DD/MM/AAAA.')
    try:
        parsed = date(
            int(text[6:10]),
            int(text[3:5]),
            int(text[0:2]),
        )
    except (TypeError, ValueError, IndexError):
        raise ValueError("Usa la fecha en formato DD/MM/AAAA.")
    return parsed.isoformat()


def _parse_amount(value: str) -> int:
    from payment_revision import parse_amount
    amount = parse_amount(value or '')
    if amount <= 0:
        raise ValueError("El valor debe ser mayor que cero.")
    return amount


def open_reception_expense_manager(
    parent: tk.Misc,
    db: Any,
    dialog_base: type[tk.Toplevel],
) -> bool:
    """Abre el formulario y registra un único gasto mediante el RPC."""

    try:
        today = db.today()
    except Exception:
        messagebox.showerror("No se pudo consultar la fecha",
            "Reintenta cuando vuelva la conexión al servidor del gimnasio.", parent=parent)
        return False

    class ExpenseDialog(dialog_base):
        def __init__(self, owner: tk.Misc, current_day: date) -> None:
            super().__init__(owner, "Crear gasto", 700, 650)
            self.result: dict[str, Any] | None = None
            self.category = tk.StringVar(value=_CATEGORIES[0])
            self.expense_date = tk.StringVar(
                value=current_day.strftime("%d/%m/%Y")
            )
            self.description = tk.StringVar()
            self.vendor = tk.StringVar()
            self.amount = tk.StringVar()
            self.payment_method = tk.StringVar(value=_PAYMENT_METHODS[0])
            self.payment_reference = tk.StringVar()
            self.receipt_reference = tk.StringVar()
            self.notes = tk.StringVar()

            ttk.Label(
                self.body,
                text="Registrar un gasto del gimnasio",
                style="Section.TLabel",
            ).grid(
                row=0,
                column=0,
                columnspan=2,
                sticky="w",
                pady=(0, 10),
            )

            ttk.Label(
                self.body,
                text=(
                    "El administrador lo verá en Finanzas. "
                    "Tu cuenta quedará registrada como responsable."
                ),
                style="CardMuted.TLabel",
                wraplength=560,
            ).grid(
                row=1,
                column=0,
                columnspan=2,
                sticky="w",
                pady=(0, 16),
            )

            self.add_entry("Fecha * (DD/MM/AAAA)", self.expense_date, 2)

            ttk.Label(
                self.body,
                text="Categoría *",
                style="Field.TLabel",
            ).grid(
                row=3,
                column=0,
                sticky="w",
                padx=(0, 14),
                pady=7,
            )
            ttk.Combobox(
                self.body,
                textvariable=self.category,
                values=_CATEGORIES,
                state="readonly",
            ).grid(row=3, column=1, sticky="ew", pady=7)

            self.add_entry("Concepto *", self.description, 4)
            self.add_entry("Proveedor / beneficiario", self.vendor, 5)
            self.add_entry("Valor *", self.amount, 6)

            ttk.Label(
                self.body,
                text="Método de pago *",
                style="Field.TLabel",
            ).grid(
                row=7,
                column=0,
                sticky="w",
                padx=(0, 14),
                pady=7,
            )
            ttk.Combobox(
                self.body,
                textvariable=self.payment_method,
                values=_PAYMENT_METHODS,
                state="readonly",
            ).grid(row=7, column=1, sticky="ew", pady=7)

            self.add_entry(
                "Referencia de pago",
                self.payment_reference,
                8,
            )
            self.add_entry(
                "Comprobante / factura",
                self.receipt_reference,
                9,
            )
            self.add_entry("Notas", self.notes, 10)

            buttons = ttk.Frame(self.body, style="Card.TFrame")
            buttons.grid(
                row=11,
                column=0,
                columnspan=2,
                sticky="e",
                pady=(20, 0),
            )
            ttk.Button(
                buttons,
                text="Cancelar",
                command=self.destroy,
            ).pack(side="left", padx=(0, 8))
            ttk.Button(
                buttons,
                text="Crear gasto",
                command=self.save,
                style="Primary.TButton",
            ).pack(side="left")
            self.bind("<Return>", lambda _event: self.save())
            self.bind("<Escape>", lambda _event: self.destroy())

        def save(self) -> None:
            description = self.description.get().strip()
            if not description:
                messagebox.showwarning(
                    "Falta el concepto",
                    "Escribe el concepto del gasto.",
                    parent=self,
                )
                return

            try:
                expense_date = _parse_date(self.expense_date.get())
                amount = _parse_amount(self.amount.get())
            except ValueError as error:
                messagebox.showwarning(
                    "Datos no válidos",
                    str(error),
                    parent=self,
                )
                return

            self.result = {
                "expense_date": expense_date,
                "category": self.category.get().strip() or "Otro",
                "description": description,
                "vendor": self.vendor.get().strip(),
                "amount": amount,
                "payment_method": self.payment_method.get().strip()
                or "Efectivo",
                "payment_reference": self.payment_reference.get().strip(),
                "receipt_reference": self.receipt_reference.get().strip(),
                "notes": self.notes.get().strip(),
            }
            self.destroy()

    dialog = ExpenseDialog(parent, today)
    parent.wait_window(dialog)
    result = getattr(dialog, "result", None)
    if not result:
        return False

    try:
        expense_id = db.create_expense(result)
    except Exception as error:
        message = str(error)
        lowered = message.casefold()
        if (
            "reception_create_expense" in lowered
            or "pgrst202" in lowered
            or "42883" in lowered
        ):
            message = (
                "La función de gastos no está disponible en el proyecto comercial. "
                "Contacta al proveedor; no reinstales la base completa."
            )
        elif "permiso" in lowered or "42501" in lowered:
            message = (
                "Esta cuenta no tiene permiso para registrar gastos. "
                "Verifica que el usuario sea Recepcionista o Administrador."
            )
        messagebox.showerror(
            "No se pudo crear el gasto",
            message,
            parent=parent,
        )
        return False

    messagebox.showinfo(
        "Gasto creado",
        (
            "El gasto quedó registrado correctamente.\n\n"
            f"Número: {expense_id}\n"
            "El administrador lo verá en Finanzas y Auditoría."
        ),
        parent=parent,
    )
    return True
