from __future__ import annotations
from gym_time import display_timestamp, timezone_for, ticket_access_note, checkin_label


from responsive_ui import AutoScrollbar

import ctypes
import base64
import io
import queue
import sqlite3
import sys
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import ttk
from ui_performance import AsyncPageMixin, DataTreeview, clear_tree, background_reads, show_page, refresh_pages, process_realtime
from responsive_ui import UI_FONT
from ui_tasks import UiDatabase
from responsive_ui import ScrollArea, fit_window, enable_dpi_awareness, scale, adapt_tree, bind_layout_mode, layout_modes, page_header as responsive_header
from desktop_ui import configure_dark_styles, messagebox, simpledialog, set_app_id
from typing import Any, Callable

from PIL import Image, ImageOps, ImageTk

from cloud import CloudService, connect_cloud
import branding
from realtime_listener import RealtimeListener
from reception_database import ReceptionDatabase
from reception_expense_revision import open_reception_expense_manager  # GymSoft-RECEPTION-EXPENSES-2.0.4
from date_input import attach_date_mask
from plan_forms import membership_form_values
from plan_forms import plan_label
from ticket_forms import CarryoverFields
from biometric import BiometricAccessController, BiometricAccessControl
from biometric import AutomaticHidScanner, normalize_biometric_identifier
from payment_revision import open_payment_manager  # GymSoft-PAGOS-2.0.1



from product_config import RECEPTION_NAME as APP_NAME
from product_config import VERSION as APP_VERSION

from atlantic_ui import COLORS, COPYRIGHT

FONT_FAMILY = UI_FONT
ICON_FONT = "Segoe Fluent Icons"


def resource_path(filename: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / filename

    return Path(__file__).resolve().parent / filename


def set_window_icon(window: tk.Misc) -> None:
    icon_path = resource_path("icono_recepcion.ico")
    window._atlantic_icon_name = "icono_recepcion.ico"

    if not icon_path.is_file():
        return

    try:
        window.iconbitmap(str(icon_path))
        return
    except tk.TclError:
        pass
    try:
        image = Image.open(icon_path).convert("RGBA")
        photo = ImageTk.PhotoImage(image)
        window.iconphoto(True, photo)
        window._gymsoft_icon_photo = photo
    except (OSError, tk.TclError):
        pass


def enable_dark_title_bar(window: tk.Misc) -> None:
    if sys.platform != "win32":
        return

    def apply_style(_event: tk.Event[Any] | None = None) -> None:
        if _event is not None and _event.widget is not window:
            return
        try:
            child_handle = int(window.winfo_id())
            get_ancestor = ctypes.windll.user32.GetAncestor
            get_ancestor.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint,
            ]
            get_ancestor.restype = ctypes.c_void_p
            window_handle = get_ancestor(
                ctypes.c_void_p(child_handle),
                2,
            ) or child_handle
            set_attribute = (
                ctypes.windll.dwmapi.DwmSetWindowAttribute
            )
            set_attribute.argtypes = [
                ctypes.c_void_p,
                ctypes.c_uint,
                ctypes.c_void_p,
                ctypes.c_uint,
            ]
            set_attribute.restype = ctypes.c_long
            enabled = ctypes.c_int(1)
            result = set_attribute(
                window_handle,
                20,
                ctypes.byref(enabled),
                ctypes.sizeof(enabled),
            )

            if result != 0:
                set_attribute(
                    window_handle,
                    19,
                    ctypes.byref(enabled),
                    ctypes.sizeof(enabled),
                )

            def colorref(hex_color: str) -> int:
                red = int(hex_color[1:3], 16)
                green = int(hex_color[3:5], 16)
                blue = int(hex_color[5:7], 16)
                return red | (green << 8) | (blue << 16)

            for attribute, color in (
                (35, COLORS["background"]),
                (34, COLORS["line"]),
                (36, COLORS["text"]),
            ):
                value = ctypes.c_int(colorref(color))
                set_attribute(
                    window_handle,
                    attribute,
                    ctypes.byref(value),
                    ctypes.sizeof(value),
                )
        except Exception:
            pass

    window.bind("<Map>", apply_style, add="+")
    window.after_idle(apply_style)


def center_window(window: tk.Misc, parent: tk.Misc | None = None) -> None:
    fit_window(window, parent=parent, minimum=(760,480) if isinstance(window,tk.Tk) else (380,260))


def format_money(value: Any) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0

    return "$ " + f"{number:,}".replace(",", ".")


def product_photo_from_data(
    image_data: Any,
    size: tuple[int, int],
) -> ImageTk.PhotoImage | None:
    text = str(image_data or "").strip()

    if not text:
        return None

    try:
        encoded = text.split(",", 1)[1] if "," in text else text
        raw = base64.b64decode(encoded, validate=True)

        with Image.open(io.BytesIO(raw)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image = ImageOps.contain(
                image,
                size,
                Image.Resampling.LANCZOS,
            )
            return ImageTk.PhotoImage(image)
    except Exception:
        return None


def date_to_display(value: Any) -> str:
    text = str(value or "").strip()

    if not text:
        return "—"

    try:
        return date.fromisoformat(text[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return text


def date_to_iso(value: str) -> str:
    return datetime.strptime(
        value.strip(),
        "%d/%m/%Y",
    ).date().isoformat()


def birthday_list_info(
    value: Any,
    today: date,
) -> dict[str, Any] | None:
    text = str(value or "").strip()

    try:
        born = date.fromisoformat(text[:10])
    except ValueError:
        return None

    def occurrence(year: int) -> date:
        try:
            return date(year, born.month, born.day)
        except ValueError:
            return date(year, 2, 28)

    month_offset = (born.month - today.month) % 12
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    in_current_week = any(
        week_start <= occurrence(year) <= week_end
        for year in {week_start.year, week_end.year}
    )

    if born.month == today.month and born.day == today.day:
        label = "HOY 🎂"
    elif in_current_week:
        label = "ESTA SEMANA"
    elif month_offset == 0:
        label = "ESTE MES"
    elif month_offset == 1:
        label = "PRÓXIMO MES"
    else:
        label = f"EN {month_offset} MESES"

    return {
        "born": born,
        "month_offset": month_offset,
        "label": label,
    }


def selected_id(tree: ttk.Treeview) -> int | None:
    selection = tree.selection()

    if not selection:
        return None

    return int(selection[0])


def bind_live_search(
    owner: tk.Misc,
    variable: tk.StringVar,
    callback: Callable[[], None],
    delay_ms: int = 260,
) -> None:
    """Ejecuta una búsqueda con pausa corta mientras se escribe."""
    state: dict[str, str | None] = {"job": None}

    def run() -> None:
        state["job"] = None
        try:
            callback()
        except Exception as error:
            print("No se pudo completar la búsqueda:", error)

    def schedule(*_args: Any) -> None:
        job = state["job"]
        if job is not None:
            try:
                owner.after_cancel(job)
            except tk.TclError:
                pass
        state["job"] = owner.after(delay_ms, run)

    variable.trace_add("write", schedule)


class CenteredTreeview(DataTreeview):
    def heading(
        self,
        column: str,
        option: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if kwargs:
            kwargs["anchor"] = "center"

        return super().heading(column, option, **kwargs)


class LoginDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        creating_account: bool,
    ) -> None:
        super().__init__(parent)
        self.result: tuple[str, str, str] | None = None
        self.email = tk.StringVar()
        self.password = tk.StringVar()
        self.invite = tk.StringVar()
        self.creating_account = creating_account
        action = (
            "Crear cuenta de recepción"
            if creating_account
            else "Iniciar sesión"
        )

        self.title(f"{action} · {APP_NAME}")
        self.geometry("520x430" if creating_account else "520x350")
        self.resizable(False, False)
        self.configure(bg=COLORS["background"])
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        set_window_icon(self)
        enable_dark_title_bar(self)

        body = tk.Frame(
            self,
            bg=COLORS["surface"],
            padx=34,
            pady=30,
            highlightbackground=COLORS["line"],
            highlightthickness=1,
        )
        body.pack(fill="both", expand=True, padx=16, pady=16)
        body.columnconfigure(0, weight=1)

        tk.Label(
            body,
            text=action,
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 19, "bold"),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            body,
            text="Acceso seguro para el personal autorizado.",
            bg=COLORS["surface"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 9),
        ).grid(row=1, column=0, sticky="w", pady=(3, 20))

        email_entry = self._field(
            body,
            "Correo",
            self.email,
            2,
        )
        self._field(
            body,
            "Contraseña",
            self.password,
            4,
            show="*",
        )

        button_row = 6

        if creating_account:
            self._field(
                body,
                "Código de invitación",
                self.invite,
                6,
            )
            button_row = 8

        buttons = tk.Frame(body, bg=COLORS["surface"])
        buttons.grid(
            row=button_row,
            column=0,
            sticky="e",
            pady=(22, 0),
        )

        ttk.Button(
            buttons,
            text="Cancelar",
            command=self.cancel,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(
            buttons,
            text=action,
            command=self.accept,
            style="Primary.TButton",
        ).pack(side="left")

        self.bind("<Return>", lambda _event: self.accept())
        self.bind("<Escape>", lambda _event: self.cancel())
        self.update_idletasks()
        center_window(self)
        self.deiconify()
        self.lift()
        self.wait_visibility()
        self.grab_set()
        email_entry.focus_force()

    def _field(
        self,
        parent: tk.Misc,
        label: str,
        variable: tk.StringVar,
        row: int,
        show: str = "",
    ) -> ttk.Entry:
        tk.Label(
            parent,
            text=label,
            bg=COLORS["surface"],
            fg="#CBD5E1",
            font=(FONT_FAMILY, 9, "bold"),
        ).grid(row=row, column=0, sticky="w", pady=(0, 5))

        entry = ttk.Entry(
            parent,
            textvariable=variable,
            show=show,
            font=(FONT_FAMILY, 11),
        )
        entry.grid(
            row=row + 1,
            column=0,
            sticky="ew",
            pady=(0, 14),
        )
        return entry

    def accept(self) -> None:
        email = self.email.get().strip()
        password = self.password.get()
        invite = self.invite.get().strip()

        if not email or not password:
            messagebox.showwarning(
                "Faltan datos",
                "Escribe el correo y la contraseña.",
                parent=self,
            )
            return

        if len(password) < 12:
            messagebox.showwarning(
                "Contraseña",
                "La contraseña debe tener al menos 12 caracteres.",
                parent=self,
            )
            return

        if self.creating_account and not invite:
            messagebox.showwarning(
                "Falta la invitación",
                "Escribe el código entregado por el administrador.",
                parent=self,
            )
            return

        self.result = (email, password, invite)
        self.destroy()

    def cancel(self) -> None:
        self.result = None
        self.destroy()


def _account_context(cloud: CloudService) -> dict[str, Any]:
    response = cloud.client.rpc(
        "reception_account_context"
    ).execute()
    data = response.data

    if isinstance(data, list):
        data = data[0] if data else None

    if not isinstance(data, dict):
        raise ValueError(
            "El servidor no devolvió la información de la cuenta."
        )

    return dict(data)


def connect_reception_cloud(parent: tk.Misc) -> CloudService | None:
    return connect_cloud(parent, reception=True)


class SidebarButton(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        icon: str,
        text: str,
        command: Callable[[], None],
    ) -> None:
        super().__init__(
            parent,
            bg=COLORS["sidebar"],
            cursor="hand2",
        )
        self.command = command
        self.active = False

        self.indicator = tk.Frame(
            self,
            bg=COLORS["sidebar"],
            width=3,
        )
        self.indicator.pack(side="left", fill="y")

        self.icon = tk.Label(
            self,
            text=icon,
            width=3,
            bg=COLORS["sidebar"],
            fg="#8EA0BA",
            font=(ICON_FONT, 13),
            cursor="hand2",
        )
        self.icon.pack(side="left", padx=(9, 3), pady=12)

        self.label = tk.Label(
            self,
            text=text,
            anchor="w",
            bg=COLORS["sidebar"],
            fg="#B7C3D4",
            font=(FONT_FAMILY, 9, "bold"),
            cursor="hand2",
        )
        self.label.pack(side="left", fill="x", expand=True)

        for widget in (self, self.icon, self.label):
            widget.bind("<Button-1>", lambda _event: self.command())
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

    def _paint(self, background: str) -> None:
        self.configure(bg=background)
        self.icon.configure(bg=background)
        self.label.configure(bg=background)

    def _enter(self, _event: tk.Event[Any]) -> None:
        if not self.active:
            self._paint(COLORS["sidebar_hover"])

    def _leave(self, _event: tk.Event[Any]) -> None:
        if not self.active:
            self._paint(COLORS["sidebar"])

    def set_active(self, active: bool) -> None:
        self.active = active
        background = (
            COLORS["sidebar_active"]
            if active
            else COLORS["sidebar"]
        )
        self._paint(background)
        self.indicator.configure(
            bg=COLORS["accent"] if active else COLORS["sidebar"]
        )
        self.icon.configure(
            fg="#FFFFFF" if active else "#8EA0BA"
        )
        self.label.configure(
            fg="#FFFFFF" if active else "#B7C3D4"
        )


class BaseDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        width: int,
        height: int,
    ) -> None:
        super().__init__(parent)
        self.title(title)
        fit_window(self, width, height, parent=parent)
        self.configure(bg=COLORS["background"])
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        set_window_icon(self)
        enable_dark_title_bar(self)

        self.viewport = ScrollArea(self, padding=24, style="Card.TFrame", width=width, height=height)
        self.viewport.pack(fill="both", expand=True, padx=10, pady=10)
        self.body = self.viewport.body
        self.body.columnconfigure(1, weight=1)
        self.after_idle(lambda: center_window(self, parent))
        self.after_idle(self._activate)

    def _activate(self) -> None:
        try:
            if not self.winfo_exists():
                return
            self.lift()
            if self.winfo_viewable():
                self.grab_set()
            else:
                self.after(30, self._activate)
        except tk.TclError:
            pass

    def add_entry(
        self,
        label: str,
        variable: tk.StringVar,
        row: int,
    ) -> ttk.Entry:
        ttk.Label(
            self.body,
            text=label,
            style="Field.TLabel",
        ).grid(
            row=row,
            column=0,
            sticky="w",
            padx=(0, 14),
            pady=7,
        )
        entry = ttk.Entry(
            self.body,
            textvariable=variable,
        )
        entry.grid(row=row, column=1, sticky="ew", pady=7)
        if "Fecha" in label:
            attach_date_mask(entry, variable)
        return entry


class ClientDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Misc,
        data: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            parent,
            "Editar cliente" if data else "Nuevo cliente",
            590,
            660,
        )
        data = data or {}
        self.result: dict[str, Any] | None = None
        self.variables = {
            "document": tk.StringVar(value=str(data.get("document", ""))),
            "first_name": tk.StringVar(value=str(data.get("first_name", ""))),
            "last_name": tk.StringVar(value=str(data.get("last_name", ""))),
            "phone": tk.StringVar(value=str(data.get("phone", ""))),
            "email": tk.StringVar(value=str(data.get("email", ""))),
            "birthdate": tk.StringVar(
                value=(
                    date_to_display(data.get("birthdate", ""))
                    if data.get("birthdate")
                    else ""
                )
            ),
            "biometric_identifier": tk.StringVar(
                value=str(data.get("biometric_identifier", ""))
            ),
        }
        fields = (
            ("Documento *", "document"),
            ("Nombres *", "first_name"),
            ("Apellidos", "last_name"),
            ("Teléfono", "phone"),
            ("Correo", "email"),
            ("Fecha de nacimiento (DD/MM/AAAA)", "birthdate"),
            ("Código de huella (opcional)", "biometric_identifier"),
        )
        first_entry: ttk.Entry | None = None

        for row, (label, key) in enumerate(fields):
            entry = self.add_entry(label, self.variables[key], row)
            first_entry = first_entry or entry

        from client_fingerprint import ClientFingerprintForm
        self.fingerprint_form = ClientFingerprintForm(self, parent, data, style="Card.TFrame")
        self.fingerprint_form.grid(row=len(fields), column=0, columnspan=2, sticky="ew")
        buttons = ttk.Frame(self.body, style="Card.TFrame")
        buttons.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(18, 0))
        self.cancel_button = ttk.Button(buttons, text="Cancelar", command=self.destroy)
        self.cancel_button.pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Guardar cliente", command=self.save, style="Primary.TButton").pack(side="left")
        self.bind("<Control-Return>", lambda _event: self.save())

        if first_entry:
            self.after_idle(first_entry.focus_force)

    def collect_data(self):
        result = {
            key: variable.get().strip()
            for key, variable in self.variables.items()
        }
        result["biometric_identifier"] = normalize_biometric_identifier(
            result.get("biometric_identifier", "")
        )

        if not result["document"] or not result["first_name"]:
            messagebox.showwarning(
                "Faltan datos",
                "El documento y el nombre son obligatorios.",
                parent=self,
            )
            return

        if result["birthdate"]:
            try:
                result["birthdate"] = date_to_iso(result["birthdate"])
            except ValueError:
                messagebox.showwarning(
                    "Fecha no válida",
                    "Usa el formato DD/MM/AAAA.",
                    parent=self,
                )
                return

        return result

    def save(self) -> None:
        result = self.collect_data()
        if result is None or self.fingerprint_form.finish(result):
            return
        self.result = result
        self.destroy()

    def destroy(self):
        form = getattr(self, 'fingerprint_form', None)
        if form is not None and not form.before_close():
            return
        super().destroy()


class PaymentDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Misc,
        client: dict[str, Any],
        plans: list[dict[str, Any]],
        today: date,
        *, on_submit=None,
    ) -> None:
        super().__init__(parent, "Registrar plan", 620, 690)
        self.on_submit = on_submit
        self.result: dict[str, Any] | None = None
        self.plans = plans
        self.plan_by_label = {
            plan_label(plan, format_money): plan
            for plan in plans
        }
        self.plan = tk.StringVar()
        self.start_date = tk.StringVar(value=today.strftime("%d/%m/%Y"))
        self.amount = tk.StringVar()
        self.method = tk.StringVar(value="EFECTIVO")
        self.reference = tk.StringVar()
        self.notes = tk.StringVar()

        ttk.Label(
            self.body,
            text=str(client.get("client_name", "Cliente")),
            style="Section.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Label(self.body, text="Plan *", style="Field.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 14), pady=7)
        combo = ttk.Combobox(
            self.body,
            textvariable=self.plan,
            values=list(self.plan_by_label),
            state="readonly",
        )
        combo.grid(row=1, column=1, sticky="ew", pady=7)
        combo.bind("<<ComboboxSelected>>", lambda _event: self.sync_price())

        self.add_entry("Fecha de inicio *", self.start_date, 2)
        self.amount_entry = self.add_entry("Valor pagado *", self.amount, 3)

        ttk.Label(self.body, text="Método *", style="Field.TLabel").grid(row=4, column=0, sticky="w", padx=(0, 14), pady=7)
        ttk.Combobox(
            self.body,
            textvariable=self.method,
            values=("EFECTIVO", "TRANSFERENCIA", "TARJETA", "OTRO"),
            state="readonly",
        ).grid(row=4, column=1, sticky="ew", pady=7)

        self.add_entry("Referencia", self.reference, 5)
        self.add_entry("Notas", self.notes, 6)

        self.ticket_fields = CarryoverFields(self.body, lambda: self.plan_by_label.get(self.plan.get()), self.start_date, today, self.sync_mode)
        self.ticket_fields.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        buttons = ttk.Frame(self.body, style="Card.TFrame")
        buttons.grid(row=8, column=0, columnspan=2, sticky="e", pady=(22, 0))
        ttk.Button(buttons, text="Cancelar", command=self.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Guardar plan", command=self.save, style="Primary.TButton").pack(side="left")

        if plans:
            self.plan.set(next(iter(self.plan_by_label)))
            self.sync_price()

    def sync_price(self) -> None:
        plan = self.plan_by_label.get(self.plan.get())

        if plan:
            self.amount.set(str(int(plan.get("price") or 0)))
        self.ticket_fields.refresh()
        self.sync_mode()

    def sync_mode(self):
        moved = self.ticket_fields.enabled.get()
        plan = self.plan_by_label.get(self.plan.get()) or {}
        self.amount.set('0' if moved else str(plan.get('price', 0)))
        self.amount_entry.configure(state='disabled' if moved else 'normal')

    def save(self) -> None:
        plan = self.plan_by_label.get(self.plan.get())

        if not plan:
            messagebox.showwarning("Falta el plan", "Selecciona un plan.", parent=self)
            return

        try:
            start_date, amount = membership_form_values(self.start_date.get(), self.amount.get())
            extra = self.ticket_fields.payload(start_date)
            if not start_date:
                raise ValueError("Escribe la fecha de inicio.")
        except ValueError as error:
            messagebox.showwarning(
                "Datos no válidos",
                str(error) or "Revisa la fecha y el valor pagado.",
                parent=self,
            )
            return

        if amount < 0:
            messagebox.showwarning("Valor no válido", "El pago no puede ser negativo.", parent=self)
            return

        payload = {
            "plan_id": int(plan["id"]),
            "start_date": start_date,
            "amount": amount,
            "payment_method": self.method.get(),
            "payment_reference": self.reference.get().strip(),
            "notes": self.notes.get().strip(),
            **extra,
        }
        from ui_tasks import submit_payment
        submit_payment(self, payload, self.on_submit)


class StoreSaleDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Misc,
        product: dict[str, Any],
    ) -> None:
        super().__init__(parent, "Registrar venta", 620, 520)
        self.result: dict[str, Any] | None = None
        self.product = product
        self.quantity = tk.StringVar(value="1")
        self.method = tk.StringVar(value="EFECTIVO")
        self.reference = tk.StringVar()
        self.customer = tk.StringVar()
        self.notes = tk.StringVar()
        self.total = tk.StringVar(
            value=format_money(product.get("sale_price", 0))
        )

        ttk.Label(
            self.body,
            text=str(product.get("name", "Producto")),
            style="Section.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            self.body,
            text=(
                f"Precio: {format_money(product.get('sale_price', 0))}  ·  "
                f"Disponibles: {int(product.get('stock_quantity') or 0)}"
            ),
            style="Field.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 14))

        quantity_entry = self.add_entry("Cantidad *", self.quantity, 2)
        ttk.Label(
            self.body,
            text="Método de pago *",
            style="Field.TLabel",
        ).grid(row=3, column=0, sticky="w", padx=(0, 14), pady=7)
        ttk.Combobox(
            self.body,
            textvariable=self.method,
            values=("EFECTIVO", "TRANSFERENCIA", "TARJETA", "OTRO"),
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", pady=7)
        self.add_entry("Cliente (opcional)", self.customer, 4)
        self.add_entry("Referencia", self.reference, 5)
        self.add_entry("Notas", self.notes, 6)

        ttk.Label(
            self.body,
            text="TOTAL",
            style="Field.TLabel",
        ).grid(row=7, column=0, sticky="w", pady=(14, 0))
        ttk.Label(
            self.body,
            textvariable=self.total,
            style="Section.TLabel",
        ).grid(row=7, column=1, sticky="e", pady=(14, 0))

        buttons = ttk.Frame(self.body, style="Card.TFrame")
        buttons.grid(row=8, column=0, columnspan=2, sticky="e", pady=(20, 0))
        ttk.Button(
            buttons,
            text="Cancelar",
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            buttons,
            text="Confirmar venta",
            command=self.save,
            style="Primary.TButton",
        ).pack(side="left")

        self.quantity.trace_add("write", self.update_total)
        self.after_idle(quantity_entry.focus_force)

    def update_total(self, *_args: Any) -> None:
        try:
            quantity = int(self.quantity.get())
        except ValueError:
            quantity = 0
        self.total.set(format_money(
            max(quantity, 0) * int(self.product.get("sale_price") or 0)
        ))

    def save(self) -> None:
        try:
            quantity = int(self.quantity.get())
        except ValueError:
            quantity = 0
        stock = int(self.product.get("stock_quantity") or 0)
        if quantity <= 0 or quantity > stock:
            messagebox.showwarning(
                "Cantidad no válida",
                f"Escribe una cantidad entre 1 y {stock}.",
                parent=self,
            )
            return

        self.result = {
            "quantity": quantity,
            "payment_method": self.method.get(),
            "payment_reference": self.reference.get().strip(),
            "customer_name": self.customer.get().strip(),
            "notes": self.notes.get().strip(),
        }
        self.destroy()


class PaymentHistoryDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Misc,
        client_name: str,
        rows: list[dict[str, Any]],
    ) -> None:
        super().__init__(parent, f"Pagos · {client_name}", 900, 500)
        self.body.rowconfigure(1, weight=1)

        ttk.Label(
            self.body,
            text=f"Historial de {client_name}",
            style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        tree = CenteredTreeview(
            self.body,
            columns=("paid", "plan", "period", "amount", "method"),
            show="headings",
        )
        columns = (
            ("paid", "Registrado", 160),
            ("plan", "Plan", 170),
            ("period", "Vigencia", 220),
            ("amount", "Valor", 130),
            ("method", "Método", 130),
        )

        for key, label, width in columns:
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor="center")

        tree.grid(row=1, column=0, sticky="nsew")

        for row in rows:
            tree.insert(
                "",
                "end",
                values=(
                    display_timestamp(row.get("paid_at", ""), timezone_for(self.db)),
                    row.get("plan_name", "Sin plan"),
                    f"{date_to_display(row.get('start_date'))} – {date_to_display(row.get('end_date'))}",
                    format_money(row.get("amount")),
                    row.get("payment_method", ""),
                ),
            )

        ttk.Button(
            self.body,
            text="Cerrar",
            command=self.destroy,
        ).grid(row=2, column=0, sticky="e", pady=(15, 0))


class BasePage(AsyncPageMixin, ttk.Frame):
    title = ""

    def __init__(
        self,
        parent: tk.Misc,
        app: "ReceptionApp",
    ) -> None:
        super().__init__(parent, padding=24, style="Page.TFrame")
        self.app = app
        self.db = app.db
        self.init_reads()

    def page_header(self, subtitle, actions=None):
        responsive_header(self, self.title, subtitle, actions or [])

    def refresh(self) -> None:
        return




class ClientsPage(BasePage):
    title = "Clientes y pagos"

    def __init__(self, parent: tk.Misc, app: "ReceptionApp") -> None:
        super().__init__(parent, app)
        self.clients: dict[int, dict[str, Any]] = {}
        self.search = tk.StringVar()
        self.page_header(
            "Consulta clientes, actualiza sus datos y registra pagos.",
            [
                ("Nuevo cliente", self.new_client, "Primary.TButton"),
                ("Registrar pago", self.register_payment, "Accent.TButton"),
                ("Crear gasto", self.new_expense, "Accent.TButton"),
            ],
        )

        search_bar = ttk.Frame(self, padding=14, style="Card.TFrame")
        search_bar.pack(fill="x", pady=(0, 14))
        ttk.Entry(search_bar, textvariable=self.search).pack(side="left", fill="x", expand=True)
        ttk.Button(search_bar, text="Buscar", command=self.refresh).pack(side="left", padx=(8, 0))
        ttk.Button(search_bar, text="Limpiar", command=self.clear_search).pack(side="left", padx=(8, 0))

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.clients_tab = ttk.Frame(
            self.notebook,
            padding=10,
            style="Page.TFrame",
        )
        self.birthdays_tab = ttk.Frame(
            self.notebook,
            padding=10,
            style="Page.TFrame",
        )
        self.notebook.add(self.clients_tab, text="Clientes")
        self.notebook.add(
            self.birthdays_tab,
            text="Cumpleaños",
        )

        card = ttk.Frame(
            self.clients_tab,
            padding=14,
            style="Card.TFrame",
        )
        card.pack(fill="both", expand=True)
        card.columnconfigure(0, weight=1)
        card.rowconfigure(0, weight=1)
        self.tree = CenteredTreeview(
            card,
            columns=("document", "name", "phone", "status", "plan", "end", "entries"),
            show="headings",
            selectmode="browse",
        )
        columns = (
            ("document", "Documento", 120),
            ("name", "Cliente", 220),
            ("phone", "Teléfono", 130),
            ("status", "Estado", 110),
            ("plan", "Plan", 130),
            ("end", "Vencimiento", 120),
            ("entries", "Entradas", 100),
        )

        for key, label, width in columns:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-1>", lambda _event: self.edit_client())
        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        ttk.Button(actions, text="Editar cliente", command=self.edit_client).pack(side="left")
        ttk.Button(actions, text="Registrar pago", command=self.register_payment, style="Primary.TButton").pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Ver historial", command=self.show_history).pack(side="left", padx=(8, 0))

        birthday_card = ttk.Frame(
            self.birthdays_tab,
            padding=14,
            style="Card.TFrame",
        )
        birthday_card.pack(fill="both", expand=True)
        birthday_card.columnconfigure(0, weight=1)
        birthday_card.rowconfigure(1, weight=1)

        ttk.Label(
            birthday_card,
            text=(
                "Lista anual para verificar cumpleaños, descuentos "
                "y premios de clientes."
            ),
            style="CardMuted.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        self.birthday_tree = CenteredTreeview(
            birthday_card,
            columns=(
                "document",
                "name",
                "phone",
                "birthday",
                "period",
                "status",
            ),
            show="headings",
            selectmode="browse",
        )

        for key, label, width in (
            ("document", "Documento", 120),
            ("name", "Cliente", 220),
            ("phone", "Teléfono", 130),
            ("birthday", "Cumpleaños", 120),
            ("period", "Periodo", 145),
            ("status", "Membresía", 115),
        ):
            self.birthday_tree.heading(key, text=label)
            self.birthday_tree.column(key, width=width)

        self.birthday_tree.grid(
            row=1,
            column=0,
            sticky="nsew",
        )
        self.birthday_tree.bind(
            "<Double-1>",
            lambda _event: self.open_birthday_client(),
        )
        self.birthday_tree.tag_configure(
            "today",
            foreground=COLORS["warning"],
        )
        self.birthday_tree.tag_configure(
            "inactive",
            foreground=COLORS["muted"],
        )

        birthday_actions = ttk.Frame(
            birthday_card,
            style="Card.TFrame",
        )
        birthday_actions.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(14, 0),
        )
        ttk.Button(
            birthday_actions,
            text="Abrir cliente",
            command=self.open_birthday_client,
        ).pack(side="left")
        ttk.Button(
            birthday_actions,
            text="Registrar pago",
            command=self.register_birthday_payment,
            style="Primary.TButton",
        ).pack(side="left", padx=(8, 0))
        bind_live_search(self, self.search, self.refresh)
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


    def clear_search(self) -> None:
        self.search.set("")
        self.refresh()

    def refresh(self) -> None:
        term = self.search.get()
        def load():
            rows = self.db.list_clients(term)
            birthdays = self.db.list_clients() if term.strip() else rows
            return rows, birthdays, self.db.today()
        self.load_view('clients', load, self._render_refresh, (term,))

    def _render_refresh(self, data):
        rows, birthday_rows, today = data
        self.clients = {int(row["id"]): row for row in rows}
        clear_tree(self.tree)

        for row in rows:
            remaining = row.get("entries_remaining")
            entries = "Ilimitadas" if remaining is None else str(remaining)
            status = str(row.get("status", "VENCIDO"))
            tag = "ok" if status == "AL DÍA" else "bad"
            self.tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("document", ""),
                    row.get("client_name", ""),
                    row.get("phone", ""),
                    status,
                    row.get("plan_name", "Sin plan"),
                    date_to_display(row.get("membership_end")),
                    entries,
                ),
                tags=(tag,),
            )

        self.tree.tag_configure("ok", foreground=COLORS["success"])
        self.tree.tag_configure("bad", foreground=COLORS["danger"])

        self.refresh_birthdays(birthday_rows, today)

    def refresh_birthdays(
        self,
        rows: list[dict[str, Any]],
        today: date | None = None,
    ) -> None:
        clear_tree(self.birthday_tree)
        today = today or self.db.today()
        birthday_rows: list[
            tuple[dict[str, Any], dict[str, Any]]
        ] = []

        for row in rows:
            info = birthday_list_info(
                row.get("birthdate"),
                today,
            )

            if info is not None:
                birthday_rows.append((row, info))

        birthday_rows.sort(
            key=lambda item: (
                item[1]["month_offset"],
                item[1]["born"].day,
                str(item[0].get("client_name", "")).casefold(),
            )
        )

        for row, info in birthday_rows:
            status = str(row.get("status", "VENCIDO"))
            tag = (
                "today"
                if info["label"] == "HOY 🎂"
                else "inactive"
                if status == "INACTIVO"
                else ""
            )
            self.birthday_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("document", ""),
                    row.get("client_name", ""),
                    row.get("phone", "") or "—",
                    date_to_display(row.get("birthdate")),
                    info["label"],
                    status,
                ),
                tags=(tag,) if tag else (),
            )

    def open_birthday_client(self) -> None:
        client_id = selected_id(self.birthday_tree)

        if client_id is None:
            messagebox.showinfo(
                "Selecciona un registro",
                "Selecciona primero una persona de la lista.",
                parent=self,
            )
            return

        item_id = str(client_id)

        if not self.tree.exists(item_id):
            self.search.set("")
            self.refresh()

        def select():
            if self.tree.exists(item_id):
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                self.tree.see(item_id)
                self.notebook.select(self.clients_tab)
        self.when_loaded(select)

    def register_birthday_payment(self) -> None:
        client_id = selected_id(self.birthday_tree)

        if client_id is None:
            messagebox.showinfo(
                "Selecciona un registro",
                "Selecciona primero una persona de la lista.",
                parent=self,
            )
            return

        item_id = str(client_id)

        if not self.tree.exists(item_id):
            self.search.set("")
            self.refresh()

        def select():
            if self.tree.exists(item_id):
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                self.register_payment()
        self.when_loaded(select)

    def selected_client(self) -> dict[str, Any] | None:
        client_id = selected_id(self.tree)

        if client_id is None:
            messagebox.showinfo("Selecciona un registro", "Selecciona primero un cliente.", parent=self)
            return None

        return self.clients.get(client_id)

    def new_client(self) -> None:
        dialog = ClientDialog(self)
        self.wait_window(dialog)

        if getattr(dialog, "client_saved", False):
            self.refresh()
            self.when_loaded(lambda: self.tree.selection_set(str(dialog.saved_client_id)) if self.tree.exists(str(dialog.saved_client_id)) else None)
            return
        if not dialog.result:
            return

        try:
            client_id = self.db.save_client(dialog.result)
        except sqlite3.IntegrityError:
            messagebox.showerror("Documento repetido", "Ya existe un cliente con ese documento.", parent=self)
            return
        except Exception as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self)
            return

        self.refresh()

        self.when_loaded(lambda: self.tree.selection_set(str(client_id)) if self.tree.exists(str(client_id)) else None)

    def edit_client(self) -> None:
        client = self.selected_client()

        if not client:
            return

        dialog = ClientDialog(self, client)
        self.wait_window(dialog)

        if getattr(dialog, "client_saved", False):
            self.refresh()
            self.when_loaded(lambda: self.tree.selection_set(str(dialog.saved_client_id)) if self.tree.exists(str(dialog.saved_client_id)) else None)
            return
        if not dialog.result:
            return

        try:
            self.db.save_client(dialog.result, int(client["id"]))
        except sqlite3.IntegrityError:
            messagebox.showerror("Documento repetido", "Ya existe otro cliente con ese documento.", parent=self)
            return
        except Exception as error:
            messagebox.showerror("No se pudo guardar", str(error), parent=self)
            return

        self.refresh()

    def register_payment(self) -> None:
        client = self.selected_client()

        if not client:
            return

        try:
            plans = self.db.list_plans()
            today = self.db.today()
        except Exception as error:
            messagebox.showerror("No se pudieron cargar los planes", str(error), parent=self)
            return

        if not plans:
            messagebox.showwarning("Sin planes", "El administrador debe crear al menos un plan activo.", parent=self)
            return

        dialog = PaymentDialog(
            self, client, plans, today,
            on_submit=lambda payload: self.db.add_membership(int(client['id']), **payload),
        )
        self.wait_window(dialog)

        if not dialog.result:
            return

        result = dialog.saved_result
        refresh_pages(self.app)
        messagebox.showinfo(
            "Pago registrado",
            "La membresía quedó registrada correctamente.\n\n"
            f"Inicio: {date_to_display(result.get('start_date'))}\n"
            f"Vencimiento: {date_to_display(result.get('end_date'))}",
            parent=self,
        )

    def new_expense(self) -> None:
        try:
            open_reception_expense_manager(
                self,
                self.db,
                BaseDialog,
            )
        except Exception as error:
            messagebox.showerror(
                "No se pudo abrir el registro de gastos",
                str(error),
                parent=self,
            )

    def show_history(self) -> None:
        client = self.selected_client()
        if not client:
            return
        try:
            open_payment_manager(
                self, self.db, int(client["id"]),
                str(client.get("client_name", "Cliente")),
                BaseDialog, format_money, date_to_display, self.refresh,
            )
        except Exception as error:
            messagebox.showerror("No se pudieron abrir los pagos", str(error), parent=self)


class ReceptionShopPage(BasePage):
    title = "Tienda"

    def __init__(self, parent: tk.Misc, app: "ReceptionApp") -> None:
        super().__init__(parent, app)
        self.products: dict[int, dict[str, Any]] = {}
        self.product_cards: list[tk.Frame] = []
        self.product_images: dict[int, ImageTk.PhotoImage] = {}
        self.search = tk.StringVar()
        self.search_job: str | None = None
        self.catalog_columns = 0
        self._catalog_profile = None
        self._catalog_profiles = {}
        self._catalog_width = None
        self._catalog_bounds = None

        self.page_header(
            "Escanea el código de barras o elige un producto para registrar la venta."
        )

        search_bar = ttk.Frame(
            self,
            padding=14,
            style="Card.TFrame",
        )
        search_bar.pack(fill="x", pady=(0, 14))

        ttk.Label(
            search_bar,
            text="Código o nombre",
            style="Field.TLabel",
        ).pack(side="left", padx=(0, 10))

        self.search_entry = ttk.Entry(
            search_bar,
            textvariable=self.search,
        )
        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
        )
        self.search_entry.bind("<Return>", lambda _event: "break")
        self.search.trace_add("write", self.schedule_search)
        self.barcode_scanner = AutomaticHidScanner(
            self,
            self.search_entry,
            self.search,
            self.process_barcode,
            minimum_length=4,
        )

        ttk.Button(
            search_bar,
            text="Buscar",
            command=self.refresh_products,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            search_bar,
            text="Limpiar",
            command=self.clear_search,
        ).pack(side="left", padx=(8, 0))

        ttk.Label(
            search_bar,
            text="Un lector compatible permite seleccionar el producto automáticamente.",
            style="CardMuted.TLabel",
        ).pack(side="right", padx=(14, 0))

        catalog = ttk.Frame(
            self,
            padding=10,
            style="Card.TFrame",
        )
        catalog.pack(fill="both", expand=True)
        catalog.columnconfigure(0, weight=1)
        catalog.rowconfigure(0, weight=1)

        self.catalog_canvas = tk.Canvas(
            catalog,
            bg=COLORS["surface"],
            highlightthickness=0,
            bd=0,
        )
        scrollbar = AutoScrollbar(
            catalog,
            orient="vertical",
            command=self.catalog_canvas.yview,
        )
        self.catalog_canvas.configure(
            yscrollcommand=scrollbar.set,
        )
        self.catalog_canvas.grid(
            row=0,
            column=0,
            sticky="nsew",
        )
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.catalog_frame = tk.Frame(
            self.catalog_canvas,
            bg=COLORS["surface"],
        )
        self.catalog_frame._responsive_skip = True
        self.catalog_window = self.catalog_canvas.create_window(
            (0, 0),
            window=self.catalog_frame,
            anchor="nw",
        )
        self.catalog_frame.bind(
            "<Configure>",
            self.sync_catalog_scroll,
        )
        self.catalog_canvas.bind(
            "<Configure>",
            self.resize_catalog,
        )
        bind_layout_mode(self.catalog_frame, self.choose_catalog_columns)
        self.after_idle(self.search_entry.focus_set)

    def refresh(self) -> None:
        self.refresh_products()

    def schedule_search(self, *_args: Any) -> None:
        if self.search_job is not None:
            try:
                self.after_cancel(self.search_job)
            except tk.TclError:
                pass

        self.search_job = self.after(
            280,
            self.run_scheduled_search,
        )

    def run_scheduled_search(self) -> None:
        self.search_job = None

        try:
            self.refresh_products()
        except Exception as error:
            print(
                "No se pudo completar la búsqueda de productos:",
                error,
            )

    def clear_search(self) -> None:
        self.search.set("")
        self.refresh_products()
        self.search_entry.focus_set()

    def process_barcode(self, code: str) -> None:
        if self.search_job is not None:
            self.after_cancel(self.search_job)
            self.search_job = None
        if not code:
            return
        term = self.search.get()
        self._barcode_sequence = getattr(self, '_barcode_sequence', 0) + 1
        def complete(rows):
            if self.search.get() != term:
                return
            exact = next((row for row in rows if str(row.get('sku', '')).casefold() == code.casefold()), None)
            if exact is not None:
                self.products[int(exact['id'])] = exact
                self.search.set('')
                self.sell_product_by_id(int(exact['id']))
        self.load_view('barcode', lambda: self.db.list_store_products(code), complete, (code, self._barcode_sequence))

    def sync_catalog_scroll(
        self,
        _event: tk.Event[Any] | None = None,
    ) -> None:
        bounds = self.catalog_canvas.bbox("all")
        if bounds != self._catalog_bounds:
            self._catalog_bounds = bounds
            self.catalog_canvas.configure(scrollregion=bounds)

    def resize_catalog(self, event: tk.Event[Any]) -> None:
        width = max(int(event.width), 210)
        if width != self._catalog_width:
            self._catalog_width = width
            self.catalog_canvas.itemconfigure(self.catalog_window, width=width)
        self.choose_catalog_columns()

    def choose_catalog_columns(self):
        profile = layout_modes(self).profile
        if profile == self._catalog_profile or self.catalog_canvas.winfo_width() < 30:
            return
        width = self.catalog_canvas.winfo_width()
        if profile not in self._catalog_profiles:
            if profile[0] == 'normal':
                root = self.winfo_toplevel()
                width = int(width * min(1, root.minsize()[0] / max(1, root.winfo_width())))
            self._catalog_profiles[profile] = max(1, int(width // (240 * scale(self))))
        columns = self._catalog_profiles[profile]
        self._catalog_profile = profile

        if columns != self.catalog_columns:
            self.catalog_columns = columns
            self.layout_product_cards()

    def layout_product_cards(self) -> None:
        columns = max(self.catalog_columns, 1)
        for column in range(max(columns, self.catalog_frame.grid_size()[0])):
            self.catalog_frame.columnconfigure(column, weight=1 if column < columns else 0,
                                               minsize=0, uniform='catalog' if column < columns else '')

        for index, card in enumerate(self.product_cards):
            card.grid(
                row=index // columns,
                column=index % columns,
                sticky="nsew",
                padx=7,
                pady=7,
            )

    def refresh_products(self) -> None:
        term = self.search.get()
        self.load_view("refresh_products", lambda: self.db.list_store_products(term), self._render_refresh_products, (term,))

    def _render_refresh_products(self, rows):
        self.products = {int(row['id']): row for row in rows}
        previous = getattr(self, '_catalog_records', {})
        cards = getattr(self, '_catalog_cards', {})
        for product_id in list(cards):
            if product_id not in self.products or previous.get(product_id) != self.products[product_id]:
                cards.pop(product_id).destroy()
            if product_id not in self.products:
                self.product_images.pop(product_id, None)
        empty = getattr(self, '_catalog_empty', None)
        if empty is not None:
            empty.destroy()
            self._catalog_empty = None
        for product_id, product in self.products.items():
            if product_id not in cards:
                cards[product_id] = self.create_product_card(product)
        self._catalog_cards = cards
        self._catalog_records = dict(self.products)
        self.product_cards = [cards[int(row['id'])] for row in rows]
        if not rows:
            empty = tk.Frame(self.catalog_frame, bg=COLORS['surface_alt'])
            tk.Label(empty, text='No se encontraron productos.', bg=COLORS['surface_alt'],
                     fg=COLORS['muted'], font=(FONT_FAMILY, 11)).pack(padx=25, pady=35)
            self._catalog_empty = empty
            self.product_cards = [empty]
        self.layout_product_cards()
        self.sync_catalog_scroll()

    def create_product_card(
        self,
        product: dict[str, Any],
    ) -> tk.Frame:
        product_id = int(product["id"])
        stock = int(product.get("stock_quantity") or 0)
        threshold = int(product.get("low_stock_threshold") or 0)

        if stock <= 0:
            status = "AGOTADO"
            status_color = COLORS["danger"]
        elif stock <= threshold:
            status = "POCAS UNIDADES"
            status_color = COLORS["warning"]
        else:
            status = "DISPONIBLE"
            status_color = COLORS["success"]

        card = tk.Frame(
            self.catalog_frame,
            bg=COLORS["surface_alt"],
            width=205,
            height=285,
            highlightbackground=COLORS["line"],
            highlightthickness=1,
        )
        # El alto sigue el texto y la escala del sistema; un límite fijo
        # recortaba el botón Vender y nombres largos al 125 %.
        card._responsive_skip = True
        card.columnconfigure(0, weight=1)

        image_data = product.get('image_data')
        cached = getattr(self, '_image_data', {})
        photo = self.product_images.get(product_id) if cached.get(product_id) == image_data else None
        if photo is None and image_data:
            photo = product_photo_from_data(image_data, (175, 112))
        cached[product_id] = image_data
        self._image_data = cached

        if photo is not None:
            self.product_images[product_id] = photo
            image_label = tk.Label(
                card,
                image=photo,
                bg=COLORS["input"],
                width=180,
                height=118,
            )
        else:
            image_label = tk.Label(
                card,
                text="▣\nSin foto",
                bg=COLORS["input"],
                fg=COLORS["muted"],
                font=(FONT_FAMILY, 11, "bold"),
                width=18,
                height=5,
            )

        image_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=(10, 7),
        )

        tk.Label(
            card,
            text=str(product.get("name", "")),
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 10, "bold"),
            wraplength=180,
            justify="center",
        ).grid(row=1, column=0, sticky="ew", padx=10)

        tk.Label(
            card,
            text=format_money(product.get("sale_price", 0)),
            bg=COLORS["surface_alt"],
            fg=COLORS["primary"],
            font=(FONT_FAMILY, 15, "bold"),
        ).grid(row=2, column=0, pady=(5, 1))

        code = str(product.get("sku") or "Sin código")
        tk.Label(
            card,
            text=f"{code}  ·  Existencias: {stock}",
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 8),
        ).grid(row=3, column=0)

        tk.Label(
            card,
            text=status,
            bg=COLORS["surface_alt"],
            fg=status_color,
            font=(FONT_FAMILY, 8, "bold"),
        ).grid(row=4, column=0, pady=(3, 7))

        ttk.Button(
            card,
            text="Vender",
            command=lambda: self.sell_product_by_id(product_id),
            style="Primary.TButton",
            state="disabled" if stock <= 0 else "normal",
        ).grid(
            row=5,
            column=0,
            sticky="ew",
            padx=10,
            pady=(0, 10),
        )

        return card

    def sell_product_by_id(self, product_id: int) -> None:
        product = self.products.get(product_id)

        if not product:
            return

        if int(product.get("stock_quantity") or 0) <= 0:
            messagebox.showwarning(
                "Producto agotado",
                "No quedan unidades disponibles de este producto.",
                parent=self,
            )
            return

        dialog = StoreSaleDialog(self, product)
        self.wait_window(dialog)

        if not dialog.result:
            self.search_entry.focus_set()
            return

        try:
            result = self.db.register_store_sale(
                product_id,
                **dialog.result,
            )
        except Exception as error:
            messagebox.showerror(
                "No se pudo registrar la venta",
                str(error),
                parent=self,
            )
            self.refresh_products()
            return

        self.refresh_products()
        self.search_entry.focus_set()
        messagebox.showinfo(
            "Venta registrada",
            f"Producto: {result.get('product_name', product.get('name', ''))}\n"
            f"Cantidad: {result.get('quantity', dialog.result['quantity'])}\n"
            f"Total: {format_money(result.get('total_amount'))}\n"
            f"Existencias restantes: {result.get('stock_remaining', '—')}",
            parent=self,
        )
class AccessPage(BasePage):
    title = "Registro de entrada"

    def __init__(self, parent: tk.Misc, app: "ReceptionApp") -> None:
        super().__init__(parent, app)
        self.clients: dict[int, dict[str, Any]] = {}
        self.search = tk.StringVar()
        self.search_job: str | None = None
        self.status_name = tk.StringVar(value="Selecciona un cliente")
        self.status_detail = tk.StringVar(
            value="Consulta por documento, nombre o identificador biométrico."
        )
        self.page_header(
            "Busca clientes, valida su plan y registra cada ingreso al gimnasio.",
        )

        self.access_tabs = ttk.Notebook(self)
        self.access_tabs.pack(fill='both', expand=True)
        self.entry_tab = ttk.Frame(self.access_tabs, style='Page.TFrame', padding=(0, 10))
        self.history_tab = ttk.Frame(self.access_tabs, style='Page.TFrame', padding=(0, 10))
        self.access_tabs.add(self.entry_tab, text='Registrar entrada')
        self.access_tabs.add(self.history_tab, text='Historial de entradas')
        upper = ttk.Frame(self.entry_tab, style="Page.TFrame")
        upper.pack(fill="both", expand=True)
        upper.columnconfigure(0, weight=1, uniform="access")
        upper.columnconfigure(1, weight=1, uniform="access")
        upper.rowconfigure(1, weight=1)

        search_bar = ttk.Frame(upper, padding=14, style="Card.TFrame")
        search_bar._responsive_skip = True
        search_bar.columnconfigure(0, weight=1)
        search_bar.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=(0, 12))
        self.search_entry = ttk.Entry(search_bar, textvariable=self.search)
        self.search_entry.grid(row=0, column=0, sticky="ew")
        self.search_entry.bind("<Return>", lambda _event: "break")
        self.search.trace_add("write", self.schedule_search)
        self.app.biometric_access.attach_search(self.search_entry, self.search)
        BiometricAccessControl(self, self.app.biometric_access).pack(fill="x", before=self.access_tabs, pady=(0, 12))
        ttk.Button(search_bar, text="Buscar", command=self.refresh_clients).grid(row=0, column=1, padx=(8, 0))
        ttk.Label(
            search_bar,
            text="El identificador del lector se consulta automáticamente.",
            style="CardMuted.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        results_card = ttk.Frame(upper, padding=12, style="Card.TFrame")
        results_card.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        results_card.columnconfigure(0, weight=1)
        results_card.rowconfigure(0, weight=1)
        self.clients_tree = CenteredTreeview(
            results_card,
            columns=("document", "name", "status", "remaining"),
            show="headings",
            selectmode="browse", height=4,
        )

        for key, label, width in (
            ("document", "Documento", 120),
            ("name", "Cliente", 210),
            ("status", "Estado", 110),
            ("remaining", "Entradas", 90),
        ):
            self.clients_tree.heading(key, text=label)
            self.clients_tree.column(key, width=width, anchor="center")

        self.clients_tree.grid(row=0, column=0, sticky="nsew")
        self.clients_tree.bind("<<TreeviewSelect>>", self.show_selected)
        self.clients_tree.bind("<Double-1>", lambda _event: self.register_entry())

        status_card = tk.Frame(
            upper,
            bg=COLORS["surface"],
            padx=24,
            pady=24,
            highlightbackground=COLORS["line"],
            highlightthickness=1,
        )
        status_card.grid(row=0, column=1, rowspan=2, sticky="nsew")
        tk.Label(status_card, text="ESTADO DE MEMBRESÍA", bg=COLORS["surface"], fg=COLORS["muted"], font=(FONT_FAMILY, 8, "bold"), width=1, anchor="w").pack(fill="x")
        tk.Label(status_card, textvariable=self.status_name, bg=COLORS["surface"], fg=COLORS["text"], font=(FONT_FAMILY, 18, "bold"), wraplength=340, justify="left", width=1, anchor="w").pack(fill="x", pady=(14, 5))
        self.status_label = tk.Label(status_card, text="—", bg=COLORS["surface_alt"], fg=COLORS["muted"], font=(FONT_FAMILY, 13, "bold"), padx=16, pady=9, width=1)
        self.status_label.pack(fill="x", pady=(8, 16))
        tk.Label(status_card, textvariable=self.status_detail, bg=COLORS["surface"], fg=COLORS["muted"], font=(FONT_FAMILY, 10), wraplength=340, justify="left", width=1, anchor="w").pack(fill="x")
        ttk.Button(status_card, text="Registrar entrada", command=self.register_entry, style="Primary.TButton").pack(anchor="w", pady=(24, 0))

        history_card = ttk.Frame(self.history_tab, padding=14, style="Card.TFrame")
        history_card.pack(fill="both", expand=True)
        ttk.Label(history_card, text="Entradas recientes", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        self.history = CenteredTreeview(
            history_card,
            columns=("time", "document", "name", "result", "method"),
            show="headings",
            height=5,
        )

        for key, label, width in (
            ("time", "Fecha y hora", 170),
            ("document", "Documento", 120),
            ("name", "Cliente", 220),
            ("result", "Resultado", 110),
            ("method", "Registro", 130),
        ):
            self.history.heading(key, text=label)
            self.history.column(key, width=width, anchor="center")

        self.history.pack(fill="both", expand=True)

    def refresh(self) -> None:
        self.refresh_clients()
        self.refresh_history()

    def schedule_search(self, *_args: Any) -> None:
        if self.search_job is not None:
            try:
                self.after_cancel(self.search_job)
            except tk.TclError:
                pass

        self.search_job = self.after(
            280,
            self.run_scheduled_search,
        )

    def run_scheduled_search(self) -> None:
        self.search_job = None

        try:
            self.refresh_clients()
        except Exception as error:
            print("No se pudo completar la búsqueda:", error)

    def refresh_clients(self) -> None:
        term = self.search.get()
        self.load_view("refresh_clients", lambda: self.db.list_clients(term), self._render_refresh_clients, (term,))

    def _render_refresh_clients(self, rows):
        self.clients = {int(row["id"]): row for row in rows}
        clear_tree(self.clients_tree)
        term = self.search.get()
        changed_search = getattr(self, '_rendered_search', None) != term
        self._rendered_search = term
        if changed_search and term.strip() and term != getattr(self, '_result_search', None):
            self._access_result_visible = False
        if not getattr(self, '_access_result_visible', False) and (changed_search or not self.clients_tree.selection()):
            self.status_name.set(
                "Selecciona un cliente" if rows else "Sin resultados"
            )
            self.status_label.configure(
                text="—",
                fg=COLORS["muted"],
            )
            self.status_detail.set(
                "Selecciona una persona de la lista."
                if rows
                else "Busca por documento, nombre o identificador."
            )

        for row in rows:
            remaining = row.get("entries_remaining")
            remaining_text = "∞" if remaining is None else str(remaining)
            status = str(row.get("status", "VENCIDO"))
            self.clients_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("document", ""),
                    row.get("client_name", ""),
                    status,
                    remaining_text,
                ),
                tags=("ok" if status == "AL DÍA" else "bad",),
            )

        self.clients_tree.tag_configure("ok", foreground=COLORS["success"])
        self.clients_tree.tag_configure("bad", foreground=COLORS["danger"])

        self.clients_tree.finish_update()
        if len(rows) == 1 and changed_search and not getattr(self, '_access_result_visible', False):
            self.clients_tree.selection_set(str(rows[0]["id"]))
            self.show_selected()

    def show_selected(self, _event: tk.Event[Any] | None = None) -> None:
        client_id = selected_id(self.clients_tree)

        if client_id is None:
            return

        client = self.clients.get(client_id)

        if not client:
            return

        status = str(client.get("status", "VENCIDO"))
        remaining = client.get("entries_remaining")
        remaining_text = "Ilimitadas" if remaining is None else str(remaining)
        self.status_name.set(str(client.get("client_name", "Cliente")))
        self.status_label.configure(
            text=status,
            fg=COLORS["success"] if status == "AL DÍA" else COLORS["danger"],
        )
        self.status_detail.set(
            f"Plan: {client.get('plan_name', 'Sin plan')}\n"
            f"Vencimiento: {date_to_display(client.get('membership_end'))}\n"
            f"Entradas disponibles: {remaining_text}"
        )

    def register_entry(self) -> None:
        client_id = selected_id(self.clients_tree)

        if client_id is None:
            messagebox.showinfo("Selecciona un registro", "Selecciona primero un cliente.", parent=self)
            return

        self.register_client_entry(
            client_id,
            "RECEPCIÓN",
            show_confirmation=True,
        )

    def register_client_entry(
        self,
        client_id: int,
        method: str,
        *,
        show_confirmation: bool,
    ) -> None:
        try:
            result = self.db.register_checkin(client_id, method)
        except Exception as error:
            messagebox.showerror("No se pudo registrar la entrada", str(error), parent=self)
            return

        allowed = str(result.get("result")) == "PERMITIDA"
        self._access_result_visible = True
        self._result_search = self.search.get()
        self.refresh_clients()
        self.refresh_history()
        self.status_name.set(
            str(result.get("client_name", "Cliente"))
        )
        self.status_label.configure(
            text="INGRESO REGISTRADO" if allowed else "INGRESO NO AUTORIZADO",
            fg=COLORS["success"] if allowed else COLORS["danger"],
        )

        self.status_detail.set(ticket_access_note(result) or str(result.get("status", "")))

        if allowed and show_confirmation:
            messagebox.showinfo(
                "Ingreso registrado",
                (
                    f"{result.get('client_name', 'El cliente')} "
                    "ingresó correctamente al gimnasio."
                ),
                parent=self,
            )
        elif not allowed and show_confirmation:
            messagebox.showwarning(
                "Ingreso no autorizado",
                result.get("denial_message") or f"No se registró el ingreso.\n\nEstado: {result.get('status', 'VENCIDO')}",
                parent=self,
            )

    def process_biometric_scan(self, code: str) -> None:
        try:
            client = self.db.find_client_by_biometric_identifier(code)
        except Exception as error:
            messagebox.showerror(
                "No se pudo leer la huella",
                str(error),
                parent=self,
            )
            return

        if not client:
            self.refresh_clients()
            self.status_name.set("Huella no identificada")
            self.status_label.configure(
                text="SIN COINCIDENCIA",
                fg=COLORS["danger"],
            )
            self.status_detail.set(
                "Asocia el identificador del lector a la ficha del cliente."
            )
            self.bell()
            return

        self.register_client_entry(
            int(client["id"]),
            "HUELLA BIOMÉTRICA",
            show_confirmation=False,
        )
        self.search.set("")
        if self.search_job is not None:
            try:
                self.after_cancel(self.search_job)
            except tk.TclError:
                pass
            self.search_job = None
        self.search_entry.focus_set()

    def refresh_history(self) -> None:
        self.load_view("refresh_history", lambda: self.db.list_checkins(40), self._render_refresh_history, ())

    def _render_refresh_history(self, rows):
        clear_tree(self.history)

        for row in rows:
            result = str(row.get("result", ""))
            self.history.insert(
                "",
                "end",
                values=(
                    display_timestamp(row.get("checkin_at", ""), timezone_for(self.db)),
                    row.get("document", ""),
                    row.get("client_name", ""),
                    result,
                    row.get("method", ""),
                ),
                tags=("ok" if result == "PERMITIDA" else "bad",),
            )

        self.history.tag_configure("ok", foreground=COLORS["success"])
        self.history.tag_configure("bad", foreground=COLORS["danger"])


class ReceptionApp(tk.Tk):
    def __init__(self) -> None:
        enable_dpi_awareness()
        set_app_id('Recepcion')
        super().__init__()
        from desktop_ui import install_error_handler
        install_error_handler(self)
        self.ready = False
        self.title(f'{APP_NAME} · {APP_VERSION}')
        fit_window(self, 1240, 790, minimum=(760, 480))
        self.configure(bg=COLORS["background"])
        set_window_icon(self)
        enable_dark_title_bar(self)
        self.configure_styles()
        ttk.Style(self).configure("Sidebar.TFrame", background=COLORS["sidebar"])
        # Mantener visible el root durante el acceso evita que el diálogo de
        # autenticación quede detrás de otra aplicación en Windows.
        self._startup_message = tk.Label(
            self,
            text=f"Conectando con {APP_NAME}…\n\nEn unos momentos podrás iniciar sesión.",
            bg=COLORS["background"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 12),
            justify="center",
        )
        self._startup_message.pack(fill="both", expand=True)
        self.update_idletasks()
        center_window(self)
        self.cloud = connect_reception_cloud(self)

        if self.cloud is None:
            self.destroy()
            return

        from door_ui import install as install_door
        self.db = UiDatabase(install_door(self, ReceptionDatabase(self.cloud), admin=False), self)
        self.pages: dict[str, BasePage] = {}
        self.page_types: dict[str, type[BasePage]] = {}
        self.nav_buttons: dict[str, SidebarButton] = {}
        self.current_page = ""
        self.realtime_events: queue.Queue[dict[str, Any]] = queue.Queue()
        self.realtime_refresh_pending = False
        self.realtime_listener: RealtimeListener | None = None
        self._startup_message.destroy()
        self.build_shell()
        self.biometric_access = BiometricAccessController(
            self, self.db.find_client_by_biometric_identifier, self.on_biometric_match,
            self.on_biometric_unknown,
            lambda error: messagebox.showerror("No se pudo consultar la huella", str(error), parent=self),
        )
        self.show_page("access")
        self.deiconify()
        self.ready = True
        center_window(self)
        self.protocol("WM_DELETE_WINDOW", self.close_app)
        self.realtime_listener = RealtimeListener(
            self.cloud,
            self.on_realtime_change,
        )
        self.realtime_listener.start()
        self.after(80, self.process_realtime_events)

    def configure_styles(self) -> None:
        configure_dark_styles(self)
        style = ttk.Style(self)

        if "clam" in style.theme_names():
            style.theme_use("clam")

        self.option_add("*Font", (FONT_FAMILY, 10))
        self.option_add("*TCombobox*Listbox.background", COLORS["input"])
        self.option_add("*TCombobox*Listbox.foreground", COLORS["text"])
        self.option_add("*TCombobox*Listbox.selectBackground", COLORS["sidebar_active"])
        style.configure("TFrame", background=COLORS["background"])
        style.configure("Page.TFrame", background=COLORS["background"])
        style.configure("Card.TFrame", background=COLORS["surface"], bordercolor=COLORS["line"], relief="flat", borderwidth=1)
        style.configure("Surface.TFrame", background=COLORS["surface"])
        style.configure("TLabel", background=COLORS["background"], foreground=COLORS["text"], font=(FONT_FAMILY, 10))
        style.configure("Title.TLabel", background=COLORS["background"], foreground=COLORS["text"], font=(FONT_FAMILY, 23, "bold"))
        style.configure("Subtitle.TLabel", background=COLORS["background"], foreground=COLORS["muted"], font=(FONT_FAMILY, 10))
        style.configure("Section.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=(FONT_FAMILY, 12, "bold"))
        style.configure("Field.TLabel", background=COLORS["surface"], foreground="#CBD5E1", font=(FONT_FAMILY, 9, "bold"))
        style.configure("TButton", background=COLORS["surface_hover"], foreground=COLORS["text"], font=(FONT_FAMILY, 9, "bold"), padding=(14, 9), borderwidth=0)
        style.map("TButton", background=[("active", "#2B3D5B"), ("pressed", COLORS["sidebar_active"])])
        style.configure("Primary.TButton", background=COLORS["primary"], foreground="#04130D", font=(FONT_FAMILY, 9, "bold"), padding=(16, 10), borderwidth=0)
        style.map("Primary.TButton", background=[("active", COLORS["primary_dark"]), ("pressed", "#0B8F5C")])
        style.configure("Accent.TButton", background=COLORS["accent"], foreground="white", font=(FONT_FAMILY, 9, "bold"), padding=(16, 10), borderwidth=0)
        style.map("Accent.TButton", background=[("active", COLORS["accent_hover"])])
        style.configure("TEntry", fieldbackground=COLORS["input"], foreground=COLORS["text"], insertcolor=COLORS["text"], bordercolor=COLORS["line"], lightcolor=COLORS["line"], darkcolor=COLORS["line"], padding=9)
        style.configure("TCombobox", fieldbackground=COLORS["input"], background=COLORS["surface_hover"], foreground=COLORS["text"], arrowcolor=COLORS["muted"], bordercolor=COLORS["line"], lightcolor=COLORS["line"], darkcolor=COLORS["line"], padding=8)
        style.map("TCombobox", fieldbackground=[("readonly", COLORS["input"])], foreground=[("readonly", COLORS["text"])])
        style.configure("Treeview", rowheight=34, background=COLORS["surface"], fieldbackground=COLORS["surface"], foreground="#DDE7F5", font=(FONT_FAMILY, 9), borderwidth=0)
        style.configure("Treeview.Heading", background=COLORS["surface_alt"], foreground="#B9C7DA", font=(FONT_FAMILY, 9, "bold"), padding=(9, 10), relief="flat")
        style.map("Treeview", background=[("selected", COLORS["sidebar_active"])], foreground=[("selected", "#FFFFFF")])
        style.configure("TNotebook", background=COLORS["background"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["surface_alt"], foreground=COLORS["muted"], padding=(18, 10), font=(FONT_FAMILY, 9, "bold"), borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", COLORS["surface"]), ("active", COLORS["surface_hover"])], foreground=[("selected", COLORS["text"])])

    def on_biometric_match(self, client):
        self.show_page("access")
        page = self.pages["access"]
        page.access_tabs.select(page.entry_tab)
        page.register_client_entry(int(client["id"]), "HUELLA BIOMÉTRICA", show_confirmation=False)
        page.search.set("")
        if page.search_job is not None:
            page.after_cancel(page.search_job); page.search_job = None
        page.search_entry.focus_set()

    def on_biometric_unknown(self, code):
        self.show_page("access")
        page = self.pages["access"]
        page.access_tabs.select(page.entry_tab)
        page._access_result_visible = True
        page._result_search = page.search.get()
        page.status_label.configure(text="HUELLA NO IDENTIFICADA", fg=COLORS["danger"])
        page.status_name.set("No se encontró un cliente")
        page.status_detail.set("Asocia el código del lector a la ficha del cliente.")
        self.bell()

    def build_shell(self) -> None:
        shell = tk.Frame(self, bg=COLORS["background"])
        shell.pack(fill="both", expand=True)
        sidebar_area = ScrollArea(shell, style="Sidebar.TFrame", background=COLORS["sidebar"],
                                  minimum_width=int(220*scale(self)), width=int(245*scale(self)), adaptive=False)
        sidebar_area.pack(side="left", fill="y")
        sidebar = sidebar_area.body
        def resize_sidebar():
            wanted = int((245 if layout_modes(self).profile[0] == 'maximized' else 220)*scale(self))
            if int(sidebar_area.canvas.cget('width')) != wanted:
                sidebar_area.canvas.configure(width=wanted)
        bind_layout_mode(shell, resize_sidebar)

        brand = tk.Frame(sidebar, bg=COLORS["sidebar"])
        brand.pack(fill="x", padx=22, pady=(24, 18))
        branding.show_reception_logo(self, brand)
        tk.Label(brand, text=self.cloud.gym_name, bg=COLORS["sidebar"], fg=COLORS["text"], font=(FONT_FAMILY, 16, "bold"), justify="left", anchor="w").pack(anchor="w")
        tk.Label(brand, text="RECEPCIÓN", bg=COLORS["sidebar"], fg=COLORS["accent"], font=(FONT_FAMILY, 8, "bold")).pack(anchor="w", pady=(3, 0))
        tk.Frame(sidebar, bg=COLORS["line"], height=1).pack(fill="x", padx=18, pady=(0, 16))
        nav_frame = tk.Frame(sidebar, bg=COLORS["sidebar"])
        nav_frame.pack(fill="x", padx=10)
        nav = (
            ("access", "\uE8FB", "Registro de entrada", AccessPage),
            ("clients", "\uE716", "Clientes y pagos", ClientsPage),
            ("shop", "\uE719", "Tienda", ReceptionShopPage),
        )
        self.page_types = {key: page_type for key, _icon, _label, page_type in nav}

        for key, icon, label, _page_type in nav:
            button = SidebarButton(nav_frame, icon, label, lambda page_key=key: self.show_page(page_key))
            button.pack(fill="x", pady=2)
            self.nav_buttons[key] = button

        footer = tk.Frame(sidebar, bg=COLORS["sidebar"])
        footer.pack(side="bottom", fill="x", padx=22, pady=20)
        tk.Label(footer, text="●  DATOS EN LA NUBE", bg=COLORS["sidebar"], fg=COLORS["success"], font=(FONT_FAMILY, 7, "bold")).pack(anchor="w")
        tk.Label(footer, text=f"Versión {APP_VERSION}", bg=COLORS["sidebar"], fg="#71819A", font=(FONT_FAMILY, 8)).pack(anchor="w", pady=(5, 0))
        main = tk.Frame(shell, bg=COLORS["background"])
        main.pack(side="left", fill="both", expand=True)
        topbar = tk.Frame(main, bg=COLORS["topbar"], height=62, highlightbackground=COLORS["line"], highlightthickness=1)
        topbar.pack(fill="x")
        topbar.pack_propagate(True)
        topbar.after_idle(lambda: adapt_tree(topbar))
        tk.Label(topbar, text="Recepción", bg=COLORS["topbar"], fg=COLORS["muted"], font=(FONT_FAMILY, 9)).pack(side="left", padx=24)
        profile = tk.Frame(topbar, bg=COLORS["topbar"])
        profile.pack(side="right", padx=22)
        tk.Label(profile, text="RC", width=3, bg=COLORS["sidebar_active"], fg="#BFDBFE", font=(FONT_FAMILY, 10, "bold")).pack(side="left", padx=(0, 9), ipady=5)
        role_label = "Administrador" if self.cloud.role == "admin" else "Recepción"
        tk.Label(profile, text=role_label, bg=COLORS["topbar"], fg=COLORS["text"], font=(FONT_FAMILY, 9, "bold")).pack(side="left")
        self.content_area = ScrollArea(main, style="Page.TFrame", minimum_width=420)
        self.content_area.pack(fill="both", expand=True)
        self.content = self.content_area.body

    def show_page(self, key: str) -> None:
        show_page(self, key)

    def on_realtime_change(self, payload: dict[str, Any]) -> None:
        self.realtime_events.put(payload)

    def process_realtime_events(self) -> None:
        process_realtime(self)

    def close_app(self) -> None:
        if getattr(self, '_foreground_io', False):
            self.bell()
            return
        if self.realtime_listener is not None:
            self.realtime_listener.stop()

        self.destroy()


def main() -> None:
    if "--diagnostico" in sys.argv:
        from diagnostico import main as diagnostic_main
        raise SystemExit(diagnostic_main())
    app = ReceptionApp()

    if app.ready:
        app.mainloop()


if __name__ == "__main__":
    main()
