from __future__ import annotations
from gym_time import display_timestamp, timezone_for, ticket_access_note, checkin_label, business_today


import ctypes
import base64
import io
import os
import shutil
import sqlite3
import sys
import queue
import tkinter as tk
from datetime import (
    date,
    datetime,
    timedelta,
)
from pathlib import Path
from tkinter import ttk
from ui_performance import AsyncPageMixin, DataTreeview, clear_tree, background_reads, show_page, refresh_pages, process_realtime
from ui_tasks import UiDatabase, run_io
from money_input import parse_amount
from responsive_ui import UI_FONT
from responsive_ui import ScrollArea, fit_window, enable_dpi_awareness, scale, adapt_tree, bind_layout_mode, layout_modes, page_header as responsive_header
from dark_files import filedialog
from desktop_ui import configure_dark_styles, messagebox, set_app_id, install_error_handler, friendly_error
from ui_text import service_status, MARKETING_ACTIVITY_LABELS
from date_input import attach_date_mask
from plan_forms import membership_form_values
from plan_forms import validate_plan, validate_months, plan_label, plan_duration
from ticket_forms import CarryoverFields
from followup_ui import TicketDashboard, ContactList, open_client as open_followup_client
from typing import Any, Callable

from PIL import Image, ImageOps, ImageTk

from biometric import BiometricAccessController, BiometricAccessControl
from biometric import (
    AutomaticHidScanner,
    ManualAccessProvider,
    normalize_biometric_identifier,
)
from cloud import connect_cloud
import branding
from realtime_listener import RealtimeListener
from cloud_database import CloudDatabase
from database import Database
from payment_revision import open_payment_manager  # GymSoft-PAGOS-2.0.1



from product_config import ADMIN_NAME as APP_NAME
from product_config import VERSION as APP_VERSION
DATA_FOLDER_NAME= "GymControl"
MONEY_VALUES_HIDDEN = False

from atlantic_ui import COLORS, COPYRIGHT

FONT_FAMILY = UI_FONT
ICON_FONT = "Segoe Fluent Icons"


def enable_dark_title_bar(window: tk.Misc) -> None:
    """Usa una barra de título oscura en Windows 10 y 11."""
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

            # GA_ROOT obtiene la ventana real de Windows sin confundirla
            # con la ventana propietaria de un cuadro emergente.
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

            # Windows 11 usa el atributo 20; algunas versiones de
            # Windows 10 todavía usan el atributo 19.
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

            caption_color = ctypes.c_int(
                colorref(COLORS["background"])
            )
            border_color = ctypes.c_int(
                colorref(COLORS["line"])
            )
            text_color = ctypes.c_int(
                colorref(COLORS["text"])
            )

            # Colores compatibles con Windows 11. En Windows 10 se
            # ignoran sin afectar el funcionamiento de la aplicación.
            for attribute, value in (
                (34, border_color),
                (35, caption_color),
                (36, text_color),
            ):
                set_attribute(
                    window_handle,
                    attribute,
                    ctypes.byref(value),
                    ctypes.sizeof(value),
                )
        except (AttributeError, OSError, tk.TclError, ValueError):
            pass

    window.after_idle(apply_style)
    window.after(80, apply_style)
    window.bind("<Map>", apply_style, add="+")


def app_data_directory() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        return base / DATA_FOLDER_NAME
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / DATA_FOLDER_NAME

def resource_path(filename: str) -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / filename

    return Path(__file__).resolve().parent / filename


def set_window_icon(window: tk.Misc) -> None:
    icon_path = resource_path("icono.ico")
    window._atlantic_icon_name = "icono.ico"
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



def format_money(value: int | str) -> str:
    if MONEY_VALUES_HIDDEN:
        return "*****"

    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 0
    return "$ " + f"{number:,}".replace(",", ".")


def encode_product_image(path: str | Path) -> str:
    """Convierte una foto a JPEG compacto para sincronizarla en Supabase."""
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail((640, 640), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.save(
            output,
            format="JPEG",
            quality=82,
            optimize=True,
        )

    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


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


def format_duration(seconds: Any) -> str:
    try:
        total_minutes = max(int(seconds) // 60, 0)
    except (TypeError, ValueError):
        total_minutes = 0

    hours, minutes = divmod(total_minutes, 60)
    return f"{hours} h {minutes:02d} min"


def next_birthday_days(value: Any, today: date) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None

    try:
        born = date.fromisoformat(text[:10])
    except ValueError:
        return None

    try:
        upcoming = date(today.year, born.month, born.day)
    except ValueError:
        upcoming = date(today.year, 2, 28)

    if upcoming < today:
        try:
            upcoming = date(today.year + 1, born.month, born.day)
        except ValueError:
            upcoming = date(today.year + 1, 2, 28)

    return (upcoming - today).days


def birthday_calendar_info(
    value: Any,
    today: date,
) -> dict[str, Any] | None:
    """Normaliza un cumpleaños y lo ubica en el calendario actual."""
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
    occurrence_year = today.year + int(born.month < today.month)
    upcoming = occurrence(occurrence_year)

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    week_candidates = {
        occurrence(week_start.year),
        occurrence(week_end.year),
    }
    in_current_week = any(
        week_start <= candidate <= week_end
        for candidate in week_candidates
    )

    if born.month == today.month:
        upcoming = occurrence(today.year)

    if upcoming == today:
        period_label = "HOY 🎂"
    elif in_current_week:
        period_label = "ESTA SEMANA"
    elif month_offset == 0:
        period_label = "ESTE MES"
    elif month_offset == 1:
        period_label = "PRÓXIMO MES"
    else:
        period_label = f"EN {month_offset} MESES"

    return {
        "born": born,
        "upcoming": upcoming,
        "month_offset": month_offset,
        "in_current_week": in_current_week,
        "period_label": period_label,
    }


def birthday_dashboard_groups(
    clients: list[dict[str, Any]],
    today: date,
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {
        "this_week": [],
        "this_month": [],
        "next_months": [],
    }

    for client in clients:
        info = birthday_calendar_info(
            client.get("birthdate"),
            today,
        )

        if info is None:
            continue

        person = dict(client)
        person["birthday_info"] = info

        if info["in_current_week"]:
            groups["this_week"].append(person)
        elif info["month_offset"] == 0:
            groups["this_month"].append(person)
        else:
            groups["next_months"].append(person)

    for people in groups.values():
        people.sort(
            key=lambda person: (
                person["birthday_info"]["month_offset"],
                person["birthday_info"]["born"].day,
                str(person.get("first_name", "")).casefold(),
                str(person.get("last_name", "")).casefold(),
            )
        )

    return groups

def date_to_display(value: Any) -> str:
    text = str(value or "").strip()

    if not text:
        return ""

    try:
        return date.fromisoformat(text[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return text


def date_to_iso(value: str) -> str:
    text = value.strip()

    if not text:
        return ""

    return datetime.strptime(
        text,
        "%d/%m/%Y",
    ).date().isoformat()


def center_window(window: tk.Misc, parent: tk.Misc | None = None) -> None:
    fit_window(window, parent=parent, minimum=(760,480) if isinstance(window,tk.Tk) else (380,260))


class CenteredTreeview(DataTreeview):
    def heading(
        self,
        column: str,
        option: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if kwargs:
            kwargs["anchor"] = "center"

        return super().heading(
            column,
            option,
            **kwargs,
        )

    def column(
        self,
        column: str,
        option: str | None = None,
        **kwargs: Any,
    ) -> Any:
        if kwargs:
            kwargs["anchor"] = "center"

        return super().column(
            column,
            option,
            **kwargs,
        )


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
            height=42,
            cursor="hand2",
        )
        self.pack_propagate(False)
        self.command = command
        self.active = False

        self.indicator = tk.Frame(
            self,
            bg=COLORS["sidebar"],
            width=3,
        )
        self.indicator.pack(side="left", fill="y")

        self.icon_label = tk.Label(
            self,
            text=icon,
            width=3,
            anchor="center",
            bg=COLORS["sidebar"],
            fg=COLORS["muted"],
            font=(ICON_FONT, 14),
            cursor="hand2",
        )
        self.icon_label.pack(side="left", padx=(12, 4))

        self.text_label = tk.Label(
            self,
            text=text,
            anchor="w",
            bg=COLORS["sidebar"],
            fg="#DCE6F5",
            font=(FONT_FAMILY, 10),
            cursor="hand2",
        )
        self.text_label.pack(
            side="left",
            fill="both",
            expand=True,
        )

        for widget in (
            self,
            self.indicator,
            self.icon_label,
            self.text_label,
        ):
            widget.bind(
                "<Button-1>",
                lambda _event: self.command(),
            )
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

    def _paint(self, background: str) -> None:
        self.configure(bg=background)
        self.icon_label.configure(bg=background)
        self.text_label.configure(bg=background)

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
            bg=(
                COLORS["blue"]
                if active
                else background
            )
        )
        self.icon_label.configure(
            fg=(
                "#93C5FD"
                if active
                else COLORS["muted"]
            )
        )
        self.text_label.configure(
            fg=(
                COLORS["text"]
                if active
                else "#DCE6F5"
            ),
            font=(
                FONT_FAMILY,
                10,
                "bold" if active else "normal",
            ),
        )


class QuickActionButton(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        icon: str,
        text: str,
        command: Callable[[], None],
        accent: str = COLORS["blue"],
    ) -> None:
        super().__init__(
            parent,
            bg=COLORS["surface_alt"],
            cursor="hand2",
            highlightbackground=COLORS["line"],
            highlightthickness=1,
        )
        self.command = command

        self.icon_label = tk.Label(
            self,
            text=icon,
            width=3,
            bg=COLORS["surface_alt"],
            fg=accent,
            font=(ICON_FONT, 15),
            cursor="hand2",
        )
        self.icon_label.pack(
            side="left",
            padx=(14, 7),
            pady=13,
        )

        self.text_label = tk.Label(
            self,
            text=text,
            anchor="w",
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 9, "bold"),
            cursor="hand2",
        )
        self.text_label.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 12),
        )

        for widget in (
            self,
            self.icon_label,
            self.text_label,
        ):
            widget.bind(
                "<Button-1>",
                lambda _event: self.command(),
            )
            widget.bind(
                "<Enter>",
                lambda _event: self._paint(
                    COLORS["surface_hover"]
                ),
            )
            widget.bind(
                "<Leave>",
                lambda _event: self._paint(
                    COLORS["surface_alt"]
                ),
            )

    def _paint(self, background: str) -> None:
        self.configure(bg=background)
        self.icon_label.configure(bg=background)
        self.text_label.configure(bg=background)


class MembershipStatusCard(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        icon: str,
        color: str,
        background: str,
        command: Callable[[], None],
        help_text: str = "Ver personas  →",
    ) -> None:
        super().__init__(
            parent,
            bg=background,
            cursor="hand2",
            highlightbackground=color,
            highlightthickness=1,
        )
        self.normal_background = background
        self.command = command

        header = tk.Frame(
            self,
            bg=background,
            cursor="hand2",
        )
        header.pack(fill="x", padx=13, pady=(12, 0))

        self.title_label = tk.Label(
            header,
            text=title,
            bg=background,
            fg=color,
            font=(FONT_FAMILY, 8, "bold"),
            cursor="hand2",
        )
        self.title_label.pack(side="left")

        self.icon_label = tk.Label(
            header,
            text=icon,
            bg=background,
            fg=color,
            font=(ICON_FONT, 13),
            cursor="hand2",
        )
        self.icon_label.pack(side="right")

        self.value_label = tk.Label(
            self,
            text="0",
            bg=background,
            fg=COLORS["text"],
            font=(FONT_FAMILY, 22, "bold"),
            cursor="hand2",
        )
        self.value_label.pack(
            anchor="w",
            padx=13,
            pady=(4, 0),
        )

        self.help_label = tk.Label(
            self,
            text=help_text,
            bg=background,
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 8),
            cursor="hand2",
        )
        self.help_label.pack(
            anchor="w",
            padx=13,
            pady=(0, 11),
        )

        self.widgets = (
            self,
            header,
            self.title_label,
            self.icon_label,
            self.value_label,
            self.help_label,
        )

        for widget in self.widgets:
            widget.bind(
                "<Button-1>",
                lambda _event: self.command(),
            )
            widget.bind("<Enter>", self._enter)
            widget.bind("<Leave>", self._leave)

    def _paint(self, background: str) -> None:
        for widget in self.widgets:
            widget.configure(bg=background)

    def _enter(self, _event: tk.Event[Any]) -> None:
        self._paint(COLORS["surface_hover"])

    def _leave(self, _event: tk.Event[Any]) -> None:
        self._paint(self.normal_background)

    def set_count(self, count: int) -> None:
        self.value_label.configure(text=str(count))

def selected_id(tree: ttk.Treeview) -> int | None:
    selection = tree.selection()
    return int(selection[0]) if selection else None


def bind_live_search(
    owner: tk.Misc,
    variable: tk.StringVar,
    callback: Callable[[], None],
    delay_ms: int = 260,
) -> None:
    """Ejecuta una búsqueda con pausa corta mientras el usuario escribe."""
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


class BaseDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, title: str, width: int = 520, height: int = 520):
        super().__init__(parent)
        self.title(title)
        fit_window(self, width, height, parent=parent)
        self.configure(bg=COLORS["background"])
        self.transient(parent)

        set_window_icon(self)

        enable_dark_title_bar(self)
        self.grab_set()
        self.result: Any = None
        self.viewport = ScrollArea(self, padding=22, style="Surface.TFrame", width=width, height=height)
        self.viewport.pack(fill="both", expand=True, padx=10, pady=10)
        self.body = self.viewport.body
        self.columnconfigure(0, weight=1)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def add_entry(
        self,
        label: str,
        variable: tk.StringVar,
        row: int,
        *,
        show: str | None = None,
    ) -> ttk.Entry:
        ttk.Label(self.body, text=label, style="Field.TLabel").grid(
            row=row * 2, column=0, sticky="w", pady=(7, 3)
        )
        entry = ttk.Entry(self.body, textvariable=variable, show=show or "")
        entry.grid(row=row * 2 + 1, column=0, sticky="ew")
        self.body.columnconfigure(0, weight=1)
        if "DD/MM/AAAA" in label:
            attach_date_mask(entry, variable)
        return entry

    def add_buttons(self, save: Callable[[], None], row: int) -> None:
        frame = ttk.Frame(self.body, style="Surface.TFrame")
        frame.grid(row=row, column=0, sticky="e", pady=(18, 0))
        ttk.Button(frame, text="Cancelar", command=self.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(frame, text="Guardar", command=save, style="Primary.TButton").pack(
            side="left"
        )


class ClientDialog(BaseDialog):
    def __init__(self, parent: tk.Misc, data: dict[str, Any] | None = None):
        self.is_editing = data is not None
        self.delete_requested = False

        super().__init__(
            parent,
            "Editar cliente" if self.is_editing else "Nuevo cliente",
            720,
            700,
        )

        data = data or {}
        self.vars = {
            "document": tk.StringVar(value=data.get("document", "")),
            "first_name": tk.StringVar(value=data.get("first_name", "")),
            "last_name": tk.StringVar(value=data.get("last_name", "")),
            "phone": tk.StringVar(value=data.get("phone", "")),
            "email": tk.StringVar(value=data.get("email", "")),
            "birthdate": tk.StringVar(value=date_to_display(data.get("birthdate", ""))),
            "emergency_contact": tk.StringVar(value=data.get("emergency_contact", "")),
            "biometric_identifier": tk.StringVar(
                value=data.get("biometric_identifier", "")
            ),
            "photo_path": tk.StringVar(value=data.get("photo_path", "")),
        }
        self.active = tk.BooleanVar(value=bool(data.get("active", 1)))

        fields = [
            ("Documento *", "document", 0, 0),
            ("Fecha de nacimiento (DD/MM/AAAA)", "birthdate", 0, 1),            ("Nombres *", "first_name", 1, 0),
            ("Apellidos *", "last_name", 1, 1),
            ("Teléfono", "phone", 2, 0),
            ("Correo", "email", 2, 1),
            ("Contacto de emergencia", "emergency_contact", 3, 0),
            ("Código de huella (opcional)", "biometric_identifier", 3, 1),
        ]
        self.body.columnconfigure(0, weight=1)
        self.body.columnconfigure(1, weight=1)
        first_entry = None
        for label, key, row, column in fields:
            field = ttk.Frame(self.body, style="Surface.TFrame")
            field.grid(
                row=row,
                column=column,
                sticky="ew",
                padx=(0, 8) if column == 0 else (8, 0),
                pady=(4, 8),
            )
            field.columnconfigure(0, weight=1)
            ttk.Label(field, text=label, style="Field.TLabel").grid(
                row=0, column=0, sticky="w", pady=(0, 3)
            )
            entry = ttk.Entry(field, textvariable=self.vars[key])
            entry.grid(row=1, column=0, sticky="ew")
            if key == "birthdate": attach_date_mask(entry, self.vars[key])
            if key == "biometric_identifier":
                entry.bind(
                    "<FocusOut>",
                    lambda _event: self.vars["biometric_identifier"].set(
                        normalize_biometric_identifier(
                            self.vars["biometric_identifier"].get()
                        )
                    ),
                )
                ttk.Label(
                    field,
                    text="Solo para lectores que escriben códigos. Para U.are.U, usa Registrar huella.",
                    wraplength=270,
                    style="CardMuted.TLabel",
                ).grid(row=2, column=0, sticky="w", pady=(3, 0))
            first_entry = first_entry or entry

        photo_row = 4
        ttk.Label(self.body, text="Fotografía", style="Field.TLabel").grid(
            row=photo_row, column=0, columnspan=2, sticky="w", pady=(8, 3)
        )
        photo_frame = ttk.Frame(self.body, style="Surface.TFrame")
        photo_frame.grid(row=photo_row + 1, column=0, columnspan=2, sticky="ew")
        photo_frame.columnconfigure(0, weight=1)
        ttk.Entry(photo_frame, textvariable=self.vars["photo_path"], state="readonly").grid(
            row=0, column=0, sticky="ew"
        )
        ttk.Button(photo_frame, text="Elegir…", command=self.pick_photo).grid(
            row=0, column=1, padx=(8, 0)
        )
        ttk.Checkbutton(self.body, text="Cliente activo", variable=self.active).grid(
            row=photo_row + 2, column=0, columnspan=2, sticky="w", pady=(12, 0)
        )
        from client_fingerprint import ClientFingerprintForm
        self.fingerprint_form = ClientFingerprintForm(self, parent, data)
        self.fingerprint_form.grid(row=photo_row + 3, column=0, columnspan=2, sticky="ew")
        buttons = ttk.Frame(self.body, style="Surface.TFrame")
        buttons.grid(row=photo_row + 4, column=0, columnspan=2, sticky="e", pady=(18, 0))
        if self.is_editing:
            ttk.Button(
                buttons,
                text="✕  Eliminar cliente",
                command=self.request_delete,
                style="Danger.TButton",
            ).pack(side="left", padx=(0, 8))
        self.cancel_button = ttk.Button(buttons, text="Cancelar", command=self.destroy)
        self.cancel_button.pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="✓  Guardar cliente", command=self.save, style="Primary.TButton").pack(
            side="left"
        )
        self.bind("<Control-Return>", lambda _event: self.save())
        if first_entry:
            first_entry.focus_set()
        center_window(self, parent)
    def request_delete(self) -> None:
        if self.fingerprint_form.busy or self.fingerprint_form.operation:
            self.fingerprint_form.status.set("Finaliza o cancela la lectura antes de eliminar al cliente.")
            return
        name = (
            f"{self.vars['first_name'].get()} "
            f"{self.vars['last_name'].get()}"
        ).strip()

        confirmed = messagebox.askyesno(
            "Eliminar cliente",
            (
                f"¿Deseas eliminar permanentemente a {name}?\n\n"
                "También se eliminarán sus pagos, entradas, "
                "rutinas y reservas.\n\n"
                "Esta acción no se puede deshacer."
            ),
            parent=self,
        )

        if confirmed:
            self.delete_requested = True
            self.destroy()
    def pick_photo(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Elegir fotografía",
            filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp"), ("Todos", "*.*")],
        )
        if path:
            self.vars["photo_path"].set(path)

    def collect_data(self):
        if not all(self.vars[key].get().strip() for key in ("document", "first_name", "last_name")):
            messagebox.showwarning("Faltan datos", "Documento, nombres y apellidos son obligatorios.", parent=self)
            return
        birthdate = self.vars["birthdate"].get().strip()

        if birthdate:
            try:
                birthdate = date_to_iso(birthdate)
            except ValueError:
                messagebox.showwarning(
                    "Fecha inválida",
                    "Usa el formato DD/MM/AAAA.",
                    parent=self,
                )
                return

        result = {
            key: var.get().strip()
            for key, var in self.vars.items()
        }

        result["birthdate"] = birthdate
        result["biometric_identifier"] = normalize_biometric_identifier(
            result.get("biometric_identifier", "")
        )
        result["active"] = int(self.active.get())
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


class MembershipDialog(BaseDialog):
    def __init__(self, parent: tk.Misc, db: Database, client_name: str, *, on_submit=None):
        # Consultar antes de crear el modal evita ventanas a medio construir
        # cuando falla la carga de planes o de la fecha.
        plans, today = db.list_plans(), db._today()
        super().__init__(parent, f"Registrar plan · {client_name}", 580, 690)
        self.on_submit = on_submit
        self.plans = plans
        self.plan_by_label: dict[str, dict[str, Any]] = {
            plan_label(plan, format_money): plan for plan in self.plans
        }
        self.plan = tk.StringVar(value=next(iter(self.plan_by_label), ""))
        self.start_date = tk.StringVar(
            value=today.strftime("%d/%m/%Y")
        )
        self.amount = tk.StringVar()
        self.method = tk.StringVar(value="Efectivo")
        self.reference = tk.StringVar()
        self.notes = tk.StringVar()

        ttk.Label(self.body, text="Plan", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(7, 3))
        plan_combo = ttk.Combobox(
            self.body,
            textvariable=self.plan,
            values=list(self.plan_by_label),
            state="readonly",
        )
        plan_combo.grid(row=1, column=0, sticky="ew")
        plan_combo.bind("<<ComboboxSelected>>", lambda _event: self.sync_amount())
        self.add_entry(
            "Fecha de inicio (DD/MM/AAAA)",
            self.start_date,
            1,
        )
        self.amount_entry = self.add_entry("Valor pagado", self.amount, 2)
        ttk.Label(self.body, text="Método de pago", style="Field.TLabel").grid(row=6, column=0, sticky="w", pady=(7, 3))
        ttk.Combobox(
            self.body,
            textvariable=self.method,
            values=["Efectivo", "Transferencia"],
            state="readonly",
        ).grid(row=7, column=0, sticky="ew")
        self.add_entry("Referencia o comprobante", self.reference, 4)
        self.add_entry("Notas", self.notes, 5)
        self.ticket_fields = CarryoverFields(self.body, lambda: self.plan_by_label.get(self.plan.get()), self.start_date, today, self.sync_mode)
        self.ticket_fields.grid(row=12, column=0, sticky="ew", pady=(12, 0))
        self.add_buttons(self.save, 13)
        self.sync_amount()
        center_window(self, parent)

    def sync_amount(self) -> None:
        plan = self.plan_by_label.get(self.plan.get())
        if plan:
            self.amount.set(str(plan["price"]))
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
            messagebox.showwarning("Plan", "Selecciona un plan.", parent=self)
            return
        try:
            start_date, amount = membership_form_values(self.start_date.get(), self.amount.get())
            extra = self.ticket_fields.payload(start_date)
            if not start_date:
                raise ValueError("Escribe la fecha de inicio.")
            if amount < 0:
                raise ValueError
        except ValueError as error:
            messagebox.showwarning("Datos inválidos", str(error) or "Revisa la fecha y el valor pagado.", parent=self)
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


class PlanDialog(BaseDialog):
    def __init__(self, parent, data=None):
        data = data or {}
        super().__init__(parent, 'Editar plan' if data else 'Nuevo plan', 590, 680)
        self.name = tk.StringVar(value=data.get('name', ''))
        self.days = tk.StringVar(value=str(data.get('duration_days', 30)))
        self.months = tk.StringVar(value=str(data.get('duration_months') or 1))
        self.price = tk.StringVar(value=str(data.get('price', 55000)))
        self.kind = tk.StringVar(value='Tiquetera / por entradas' if data.get('entry_limit') is not None else 'Mensualidad / por días')
        old_days_ticket = data.get('entry_limit') is not None and data.get('duration_months') is None
        self.unit = tk.StringVar(value='Días' if old_days_ticket else 'Meses calendario')
        self.entries = tk.StringVar(value=str(data.get('entry_limit') or 15))
        self.add_entry('Nombre del plan', self.name, 0)
        ttk.Label(self.body, text='Tipo de plan', style='Field.TLabel').grid(row=2, column=0, sticky='w', pady=(10, 3))
        ttk.Combobox(self.body, textvariable=self.kind, state='readonly', values=('Mensualidad / por días', 'Tiquetera / por entradas')).grid(row=3, column=0, sticky='ew')
        self.unit_frame = ttk.Frame(self.body, style='Surface.TFrame')
        self.unit_frame.grid(row=4, column=0, sticky='ew', pady=(10, 0))
        self.unit_frame.columnconfigure(0, weight=1)
        ttk.Label(self.unit_frame, text='Unidad de vigencia', style='Field.TLabel').grid(row=0, column=0, sticky='w')
        ttk.Combobox(self.unit_frame, textvariable=self.unit, state='readonly', values=('Meses calendario', 'Días')).grid(row=1, column=0, sticky='ew', pady=(3, 0))
        self.duration_label = ttk.Label(self.body, style='Field.TLabel')
        self.duration_label.grid(row=5, column=0, sticky='w', pady=(10, 3))
        self.duration_entry = ttk.Entry(self.body)
        self.duration_entry.grid(row=6, column=0, sticky='ew')
        self.entries_label = ttk.Label(self.body, text='Cantidad total de entradas', style='Field.TLabel')
        self.entries_label.grid(row=7, column=0, sticky='w', pady=(10, 3))
        self.entries_entry = ttk.Entry(self.body, textvariable=self.entries)
        self.entries_entry.grid(row=8, column=0, sticky='ew')
        ttk.Label(self.body, text='Precio', style='Field.TLabel').grid(row=9, column=0, sticky='w', pady=(10, 3))
        ttk.Entry(self.body, textvariable=self.price).grid(row=10, column=0, sticky='ew')
        self.hint = ttk.Label(self.body, style='CardMuted.TLabel', wraplength=490)
        self.hint.grid(row=11, column=0, sticky='ew', pady=(12, 0))
        self.add_buttons(self.save, 12)
        self.kind.trace_add('write', lambda *_: self.update_kind())
        self.unit.trace_add('write', lambda *_: self.update_kind())
        self.update_kind()
        center_window(self, parent)

    def update_kind(self):
        ticket = self.kind.get() == 'Tiquetera / por entradas'
        months = ticket and self.unit.get() == 'Meses calendario'
        for widget in (self.unit_frame, self.entries_label, self.entries_entry):
            widget.grid() if ticket else widget.grid_remove()
        self.duration_label.configure(text='Cantidad de meses de vigencia' if months else 'Vigencia en días')
        self.duration_entry.configure(textvariable=self.months if months else self.days)
        self.hint.configure(text=(
            'La tiquetera termina al agotar las entradas o vencer su vigencia. Los cambios se aplican a las próximas compras; las tiqueteras vendidas conservan su cupo y vencimiento. '
            'Para trasladar una tiquetera anterior, abre el cliente y selecciona «Tiquetera ya iniciada» al registrar el plan.' if ticket else
            'Acceso por días, sin límite de entradas durante la vigencia. Las membresías ya vendidas conservan sus fechas.'))

    def save(self):
        try:
            ticket = self.kind.get() == 'Tiquetera / por entradas'
            months = validate_months(self.months.get(), self.entries.get()) if ticket and self.unit.get() == 'Meses calendario' else None
            values = validate_plan(self.name.get(), months * 30 if months else self.days.get(), self.price.get(), self.entries.get() if ticket else None)
            self.result = (*values, months)
        except ValueError as error:
            messagebox.showwarning('Revisa el plan', str(error), parent=self)
            return
        self.destroy()


class ExpenseDialog(BaseDialog):
    CATEGORIES = (
        "Arriendo",
        "Servicios públicos",
        "Nómina",
        "Mantenimiento",
        "Equipos",
        "Aseo",
        "Publicidad",
        "Impuestos",
        "Compras de tienda",
        "Otros",
    )
    PAYMENT_METHODS = (
        "Efectivo",
        "Transferencia",
        "Tarjeta",
        "Nequi",
        "Daviplata",
        "Otro",
    )

    def __init__(
        self,
        parent: tk.Misc,
        data: dict[str, Any] | None = None,
    ) -> None:
        data = data or {}
        super().__init__(
            parent,
            "Editar gasto" if data else "Crear gasto",
            540,
            720,
        )
        self.expense_date = tk.StringVar(
            value=(
                date_to_display(data.get("expense_date"))
                or business_today(parent).strftime("%d/%m/%Y")
            )
        )
        self.category = tk.StringVar(
            value=str(data.get("category") or self.CATEGORIES[0])
        )
        self.description = tk.StringVar(
            value=str(data.get("description", ""))
        )
        self.vendor = tk.StringVar(value=str(data.get("vendor", "")))
        self.amount = tk.StringVar(value=str(data.get("amount", "")))
        self.payment_method = tk.StringVar(
            value=str(data.get("payment_method") or "Efectivo")
        )
        self.payment_reference = tk.StringVar(
            value=str(data.get("payment_reference", ""))
        )
        self.receipt_reference = tk.StringVar(
            value=str(data.get("receipt_reference", ""))
        )
        self.notes = tk.StringVar(value=str(data.get("notes", "")))

        date_entry = self.add_entry(
            "Fecha del gasto (DD/MM/AAAA) *",
            self.expense_date,
            0,
        )
        ttk.Label(
            self.body,
            text="Categoría *",
            style="Field.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(7, 3))
        ttk.Combobox(
            self.body,
            textvariable=self.category,
            values=self.CATEGORIES,
            state="readonly",
        ).grid(row=3, column=0, sticky="ew")
        self.add_entry("Descripción *", self.description, 2)
        self.add_entry("Proveedor o beneficiario", self.vendor, 3)
        self.add_entry("Valor pagado *", self.amount, 4)
        ttk.Label(
            self.body,
            text="Método de pago",
            style="Field.TLabel",
        ).grid(row=10, column=0, sticky="w", pady=(7, 3))
        ttk.Combobox(
            self.body,
            textvariable=self.payment_method,
            values=self.PAYMENT_METHODS,
            state="readonly",
        ).grid(row=11, column=0, sticky="ew")
        self.add_entry("Referencia del pago", self.payment_reference, 6)
        self.add_entry("Número o ruta del comprobante", self.receipt_reference, 7)
        self.add_entry("Notas", self.notes, 8)
        self.add_buttons(self.save, 19)
        center_window(self, parent)
        self.after_idle(date_entry.focus_force)

    def save(self) -> None:
        try:
            expense_date = date_to_iso(self.expense_date.get())
            amount = parse_amount(self.amount.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Datos inválidos",
                "Revisa la fecha y escribe un valor mayor que cero.",
                parent=self,
            )
            return

        if not self.description.get().strip():
            messagebox.showwarning(
                "Falta la descripción",
                "Escribe el concepto del gasto.",
                parent=self,
            )
            return

        self.result = {
            "expense_date": expense_date,
            "category": self.category.get().strip(),
            "description": self.description.get().strip(),
            "vendor": self.vendor.get().strip(),
            "amount": amount,
            "payment_method": self.payment_method.get().strip(),
            "payment_reference": self.payment_reference.get().strip(),
            "receipt_reference": self.receipt_reference.get().strip(),
            "notes": self.notes.get().strip(),
        }
        self.destroy()


class ProductDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Misc,
        data: dict[str, Any] | None = None,
    ) -> None:
        data = data or {}
        super().__init__(
            parent,
            "Editar producto" if data else "Nuevo producto",
            560,
            710,
        )
        self.image_data = str(data.get("image_data", ""))
        self.preview_image: ImageTk.PhotoImage | None = None
        self.name = tk.StringVar(value=str(data.get("name", "")))
        self.sku = tk.StringVar(value=str(data.get("sku", "")))
        self.price = tk.StringVar(
            value=str(data.get("sale_price", 0))
        )
        self.stock = tk.StringVar(
            value=str(data.get("stock_quantity", 0))
        )
        self.low_stock = tk.StringVar(
            value=str(data.get("low_stock_threshold", 5))
        )
        self.active = tk.BooleanVar(
            value=bool(data.get("active", True))
        )

        name_entry = self.add_entry("Nombre del producto *", self.name, 0)
        self.add_entry("Código de barras o SKU", self.sku, 1)
        self.add_entry("Precio de venta *", self.price, 2)
        self.add_entry("Cantidad disponible *", self.stock, 3)
        self.add_entry("Avisar cuando queden", self.low_stock, 4)
        ttk.Checkbutton(
            self.body,
            text="Producto disponible para la venta",
            variable=self.active,
        ).grid(row=10, column=0, sticky="w", pady=(12, 0))

        ttk.Label(
            self.body,
            text="Foto del producto",
            style="Field.TLabel",
        ).grid(row=11, column=0, sticky="w", pady=(12, 4))

        photo_area = ttk.Frame(
            self.body,
            padding=10,
            style="Card.TFrame",
        )
        photo_area.grid(row=12, column=0, sticky="ew")

        self.photo_preview = tk.Label(
            photo_area,
            text="Sin foto",
            width=22,
            height=7,
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 9),
        )
        self.photo_preview.pack(side="left")

        photo_actions = ttk.Frame(
            photo_area,
            style="Card.TFrame",
        )
        photo_actions.pack(side="left", padx=(12, 0))
        ttk.Button(
            photo_actions,
            text="Seleccionar foto…",
            command=self.pick_image,
        ).pack(anchor="w")
        ttk.Button(
            photo_actions,
            text="Quitar foto",
            command=self.remove_image,
        ).pack(anchor="w", pady=(8, 0))

        self.add_buttons(self.save, 13)
        center_window(self, parent)
        self.update_image_preview()
        self.after_idle(name_entry.focus_force)

    def pick_image(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar foto del producto",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.webp *.bmp"),
            ],
        )

        if not path:
            return

        try:
            self.image_data = encode_product_image(path)
        except Exception as error:
            messagebox.showerror(
                "No se pudo cargar la foto",
                f"Selecciona una imagen válida.\n\n{error}",
                parent=self,
            )
            return

        self.update_image_preview()

    def remove_image(self) -> None:
        self.image_data = ""
        self.update_image_preview()

    def update_image_preview(self) -> None:
        self.preview_image = product_photo_from_data(
            self.image_data,
            (170, 105),
        )

        if self.preview_image is None:
            self.photo_preview.configure(
                image="",
                text="Sin foto",
            )
        else:
            self.photo_preview.configure(
                image=self.preview_image,
                text="",
            )

    def save(self) -> None:
        try:
            price = parse_amount(self.price.get())
            stock = int(self.stock.get())
            low_stock = int(self.low_stock.get())
            if not self.name.get().strip():
                raise ValueError
            if price < 0 or stock < 0 or low_stock < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Datos inválidos",
                "Completa correctamente el nombre, precio y cantidades.",
                parent=self,
            )
            return

        self.result = {
            "name": self.name.get().strip(),
            "sku": self.sku.get().strip().upper(),
            "sale_price": price,
            "stock_quantity": stock,
            "low_stock_threshold": low_stock,
            "active": bool(self.active.get()),
            "image_data": self.image_data,
        }
        self.destroy()


class TrainerDialog(BaseDialog):
    def __init__(self, parent: tk.Misc, data: dict[str, Any] | None = None):
        super().__init__(parent, "Editar entrenador" if data else "Nuevo entrenador", 520, 650)
        data = data or {}
        self.vars = {
            "name": tk.StringVar(value=data.get("name", "")),
            "phone": tk.StringVar(value=data.get("phone", "")),
            "email": tk.StringVar(value=data.get("email", "")),
            "specialty": tk.StringVar(value=data.get("specialty", "")),
            "hourly_rate": tk.StringVar(value=str(data.get("hourly_rate", 0))),
            "hire_date": tk.StringVar(
                value=date_to_display(data.get("hire_date", ""))
            ),
            "notes": tk.StringVar(value=data.get("notes", "")),
        }
        self.active = tk.BooleanVar(value=bool(data.get("active", 1)))
        for index, (label, key) in enumerate(
            [
                ("Nombre *", "name"),
                ("Teléfono", "phone"),
                ("Correo", "email"),
                ("Especialidad", "specialty"),
                ("Pago por hora", "hourly_rate"),
                ("Fecha de contratación (DD/MM/AAAA)", "hire_date"),
                ("Notas", "notes"),
            ]
        ):
            self.add_entry(label, self.vars[key], index)
        ttk.Checkbutton(self.body, text="Entrenador activo", variable=self.active).grid(
            row=14, column=0, sticky="w", pady=(12, 0)
        )
        self.add_buttons(self.save, 15)
        center_window(self, parent)

    def save(self) -> None:
        if not self.vars["name"].get().strip():
            messagebox.showwarning("Nombre", "Escribe el nombre del entrenador.", parent=self)
            return

        try:
            hourly_rate = parse_amount(self.vars["hourly_rate"].get())
            if hourly_rate < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Pago por hora",
                "Escribe un valor por hora válido.",
                parent=self,
            )
            return

        hire_date = self.vars["hire_date"].get().strip()
        if hire_date:
            try:
                hire_date = date_to_iso(hire_date)
            except ValueError:
                messagebox.showwarning(
                    "Fecha inválida",
                    "Usa el formato DD/MM/AAAA.",
                    parent=self,
                )
                return

        self.result = {key: value.get().strip() for key, value in self.vars.items()}
        self.result["hourly_rate"] = hourly_rate
        self.result["hire_date"] = hire_date
        self.result["active"] = int(self.active.get())
        self.destroy()


class RoutineDialog(BaseDialog):
    def __init__(self, parent: tk.Misc, db: Database):
        super().__init__(parent, "Nueva rutina", 540, 540)
        self.clients = [client for client in db.list_clients() if client["active"]]
        self.trainers = db.list_trainers(active_only=True)
        self.client_map = {
            f"{item['first_name']} {item['last_name']} · {item['document']}": item["id"]
            for item in self.clients
        }
        self.trainer_map = {item["name"]: item["id"] for item in self.trainers}
        self.client = tk.StringVar(value=next(iter(self.client_map), ""))
        self.trainer = tk.StringVar(value=next(iter(self.trainer_map), "Sin asignar"))
        self.name = tk.StringVar(value="Rutina inicial")
        self.goal = tk.StringVar()
        self.start_date = tk.StringVar(
            value=db._today().strftime("%d/%m/%Y")
        )
        self.notes = tk.StringVar()

        self._combo("Cliente", self.client, list(self.client_map), 0)
        self._combo("Entrenador", self.trainer, ["Sin asignar", *self.trainer_map], 1)
        self.add_entry("Nombre de la rutina", self.name, 2)
        self.add_entry("Objetivo", self.goal, 3)
        self.add_entry(
            "Fecha de inicio (DD/MM/AAAA)",
            self.start_date,
            4,
        )
        self.add_entry("Notas", self.notes, 5)
        self.add_buttons(self.save, 12)
        center_window(self, parent)

    def _combo(self, label: str, variable: tk.StringVar, values: list[str], row: int) -> None:
        ttk.Label(self.body, text=label, style="Field.TLabel").grid(row=row * 2, column=0, sticky="w", pady=(7, 3))
        ttk.Combobox(self.body, textvariable=variable, values=values, state="readonly").grid(
            row=row * 2 + 1, column=0, sticky="ew"
        )

    def save(self) -> None:
        client_id = self.client_map.get(self.client.get())
        if not client_id or not self.name.get().strip():
            messagebox.showwarning("Faltan datos", "Selecciona un cliente y escribe un nombre.", parent=self)
            return
        try:
            start_date = date_to_iso(
                self.start_date.get()
            )
        except ValueError:
            messagebox.showwarning(
                "Fecha inválida",
                "Usa el formato DD/MM/AAAA.",
                parent=self,
            )
            return
        self.result = {
            "client_id": int(client_id),
            "trainer_id": self.trainer_map.get(self.trainer.get()),
            "name": self.name.get().strip(),
            "goal": self.goal.get().strip(),
            "start_date": start_date,
            "notes": self.notes.get().strip(),
        }
        self.destroy()


class ExerciseDialog(BaseDialog):
    def __init__(self, parent: tk.Misc):
        super().__init__(parent, "Agregar ejercicio", 500, 560)
        self.vars = {
            "day_name": tk.StringVar(value="Día 1"),
            "name": tk.StringVar(),
            "sets": tk.StringVar(value="3"),
            "reps": tk.StringVar(value="10"),
            "weight": tk.StringVar(),
            "notes": tk.StringVar(),
        }
        for index, (label, key) in enumerate(
            [
                ("Día o grupo", "day_name"),
                ("Ejercicio", "name"),
                ("Series", "sets"),
                ("Repeticiones", "reps"),
                ("Peso sugerido", "weight"),
                ("Notas", "notes"),
            ]
        ):
            self.add_entry(label, self.vars[key], index)
        self.add_buttons(self.save, 12)
        center_window(self, parent)

    def save(self) -> None:
        if not self.vars["day_name"].get().strip() or not self.vars["name"].get().strip():
            messagebox.showwarning("Faltan datos", "Escribe el día y el ejercicio.", parent=self)
            return
        self.result = {key: value.get().strip() for key, value in self.vars.items()}
        self.destroy()


class ClassDialog(BaseDialog):
    def __init__(self, parent: tk.Misc, db: Database):
        super().__init__(parent, "Programar clase", 500, 500)
        trainers = db.list_trainers(active_only=True)
        self.trainer_map = {item["name"]: item["id"] for item in trainers}
        self.name = tk.StringVar()
        self.trainer = tk.StringVar(value=next(iter(self.trainer_map), "Sin asignar"))
        self.starts_at = tk.StringVar(value=db._today().strftime("%Y-%m-%d 18:00"))
        self.capacity = tk.StringVar(value="15")
        self.notes = tk.StringVar()
        self.add_entry("Nombre de la clase", self.name, 0)
        ttk.Label(self.body, text="Entrenador", style="Field.TLabel").grid(row=2, column=0, sticky="w", pady=(7, 3))
        ttk.Combobox(
            self.body,
            textvariable=self.trainer,
            values=["Sin asignar", *self.trainer_map],
            state="readonly",
        ).grid(row=3, column=0, sticky="ew")
        self.add_entry("Fecha y hora (AAAA-MM-DD HH:MM)", self.starts_at, 2)
        self.add_entry("Cupos", self.capacity, 3)
        self.add_entry("Notas", self.notes, 4)
        self.add_buttons(self.save, 10)
        center_window(self, parent)

    def save(self) -> None:
        try:
            datetime.strptime(self.starts_at.get().strip(), "%Y-%m-%d %H:%M")
            capacity = int(self.capacity.get())
            if not self.name.get().strip() or capacity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "Datos inválidos",
                "Revisa el nombre, la fecha (AAAA-MM-DD HH:MM) y los cupos.",
                parent=self,
            )
            return
        self.result = {
            "name": self.name.get().strip(),
            "trainer_id": self.trainer_map.get(self.trainer.get()),
            "starts_at": self.starts_at.get().strip(),
            "capacity": capacity,
            "notes": self.notes.get().strip(),
        }
        self.destroy()


class ChoiceDialog(BaseDialog):
    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        label: str,
        choices: dict[str, int],
    ):
        super().__init__(parent, title, 500, 280)
        self.choices = choices
        self.choice = tk.StringVar(value=next(iter(choices), ""))
        ttk.Label(self.body, text=label, style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=(7, 3))
        ttk.Combobox(
            self.body,
            textvariable=self.choice,
            values=list(choices),
            state="readonly",
        ).grid(row=1, column=0, sticky="ew")
        self.add_buttons(self.save, 2)
        center_window(self, parent)

    def save(self) -> None:
        self.result = self.choices.get(self.choice.get())
        if self.result is None:
            messagebox.showwarning("Selección", "Elige una opción.", parent=self)
            return
        self.destroy()


class BasePage(AsyncPageMixin, ttk.Frame):
    title = ""

    def __init__(self, parent: tk.Misc, app: "GymSoftApp"):
        super().__init__(parent, padding=24, style="Page.TFrame")
        self.app = app
        self.db = app.db
        self.init_reads()

    def page_header(self, subtitle, actions=None):
        responsive_header(self, self.title, subtitle, actions or [])

    def refresh(self) -> None:
        pass


class DashboardPage(BasePage):
    title = "Dashboard"

    BIRTHDAY_BUCKETS = [
        (
            "this_week",
            "Esta semana",
            "\uE787",
            COLORS["danger"],
            COLORS["danger_bg"],
        ),
        (
            "this_month",
            "Este mes",
            "\uE916",
            COLORS["purple"],
            COLORS["purple_bg"],
        ),
        (
            "next_months",
            "Próximos meses",
            "\uE8D4",
            COLORS["blue"],
            COLORS["blue_bg"],
        ),
    ]

    EXPIRATION_BUCKETS = [
        (
            "expired",
            "Vencidas",
            "\uE783",
            COLORS["danger"],
            COLORS["danger_bg"],
        ),
        (
            "days_0_7",
            "0–7 días",
            "\uE7BA",
            COLORS["warning"],
            COLORS["warning_bg"],
        ),
        (
            "days_8_15",
            "8–15 días",
            "\uE916",
            COLORS["warning"],
            COLORS["warning_bg"],
        ),
        (
            "days_16_30",
            "16–30 días",
            "\uE787",
            COLORS["blue"],
            COLORS["blue_bg"],
        ),
    ]

    def __init__(self, parent: tk.Misc, app: "GymSoftApp"):
        super().__init__(parent, app)
        self.configure(padding=(16, 24))
        self.page_header(
            "Vista general y acciones principales del gimnasio.",
            [
                ("↻  Actualizar", self.refresh, "Primary.TButton"),
            ],
        )
        self.cards = ttk.Frame(self, style="Page.TFrame")
        self.cards.pack(fill="x")
        for column in range(4):
            self.cards.columnconfigure(column, weight=1)
        self.metric_labels: dict[str, tk.Label] = {}
        card_data = [
            (
                "active_clients",
                "Clientes activos",
                "\uE716",
                COLORS["blue"],
                COLORS["blue_bg"],
            ),
            (
                "valid_memberships",
                "Membresías al día",
                "\uE73E",
                COLORS["success"],
                COLORS["success_bg"],
            ),
            (
                "expired_memberships",
                "Membresías vencidas",
                "\uE783",
                COLORS["danger"],
                COLORS["danger_bg"],
            ),
            (
                "checkins_today",
                "Entradas hoy",
                "\uE787",
                COLORS["warning"],
                COLORS["warning_bg"],
            ),
        ]

        for column, data in enumerate(card_data):
            key, label, icon, color, icon_background = data
            card = tk.Frame(
                self.cards,
                bg=COLORS["surface"],
                bd=0,
                highlightbackground=COLORS["line"],
                highlightthickness=1,
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(
                    0 if column == 0 else 6,
                    0 if column == 3 else 6,
                ),
            )

            header = tk.Frame(
                card,
                bg=COLORS["surface"],
            )
            header.pack(fill="x", padx=16, pady=(15, 3))

            tk.Label(
                header,
                text=label,
                font=(FONT_FAMILY, 9),
                fg=COLORS["muted"],
                bg=COLORS["surface"],
            ).pack(side="left")

            tk.Label(
                header,
                text=icon,
                width=2,
                bg=icon_background,
                fg=color,
                font=(ICON_FONT, 13),
            ).pack(side="right", ipady=5)

            value = tk.Label(
                card,
                text="0",
                font=(FONT_FAMILY, 23, "bold"),
                fg=COLORS["text"],
                bg=COLORS["surface"],
            )
            value.pack(
                anchor="w",
                padx=16,
                pady=(0, 15),
            )
            self.metric_labels[key] = value

        quick_section = ttk.Frame(
            self,
            padding=16,
            style="Card.TFrame",
        )
        quick_section.pack(fill="x", pady=(16, 0))
        ttk.Label(
            quick_section,
            text="Acciones rápidas",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 10))

        quick_actions = ttk.Frame(
            quick_section,
            style="Card.TFrame",
        )
        quick_actions.pack(fill="x")

        action_data = [
            (
                "\uE710",
                "Nuevo cliente",
                self.quick_new_client,
                COLORS["blue"],
            ),
            (
                "\uE8C7",
                "Registrar pago",
                self.quick_register_payment,
                COLORS["success"],
            ),
            (
                "\uE8FB",
                "Registrar entrada",
                lambda: self.app.show_page("checkin"),
                COLORS["warning"],
            ),
            (
                "\uE9D2",
                "Ver estadísticas",
                lambda: self.app.show_page("statistics"),
                COLORS["purple"],
            ),
        ]

        for column in range(len(action_data)):
            quick_actions.columnconfigure(column, weight=1)

        for column, data in enumerate(action_data):
            icon, text, command, accent = data
            button = QuickActionButton(
                quick_actions,
                icon,
                text,
                command,
                accent,
            )
            button.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(
                    0 if column == 0 else 5,
                    0 if column == len(action_data) - 1 else 5,
                ),
            )

        membership_section = ttk.Frame(
            self,
            padding=16,
            style="Card.TFrame",
        )
        membership_section.pack(
            fill="both",
            expand=True,
            pady=(16, 0),
        )

        ttk.Label(
            membership_section,
            text="Estado de membresías",
            style="Section.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            membership_section,
            text=(
                "Haz clic en una tarjeta para ver las personas "
                "incluidas en ese rango."
            ),
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(3, 11))

        status_cards = ttk.Frame(
            membership_section,
            style="Card.TFrame",
        )
        status_cards.pack(fill="x")

        self.expiration_groups: dict[
            str,
            list[dict[str, Any]],
        ] = {}
        self.expiration_cards: dict[
            str,
            MembershipStatusCard,
        ] = {}

        for column in range(len(self.EXPIRATION_BUCKETS)):
            status_cards.columnconfigure(column, weight=1)

        for column, data in enumerate(
            self.EXPIRATION_BUCKETS
        ):
            key, title, icon, color, background = data
            card = MembershipStatusCard(
                status_cards,
                title,
                icon,
                color,
                background,
                lambda bucket=key, label=title: (
                    self.show_expiration_list(bucket, label)
                ),
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(
                    0 if column == 0 else 5,
                    0
                    if column == len(self.EXPIRATION_BUCKETS) - 1
                    else 5,
                ),
            )
            self.expiration_cards[key] = card

        self.ticket_dashboard = TicketDashboard(membership_section, app, BaseDialog)
        self.ticket_dashboard.pack(fill='x', pady=(18, 0))

        ttk.Separator(
            membership_section,
            orient="horizontal",
        ).pack(fill="x", pady=(18, 14))

        ttk.Label(
            membership_section,
            text="Cumpleaños de clientes",
            style="Section.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            membership_section,
            text=(
                "Organiza a todos los clientes con fecha de nacimiento; "
                "cada persona aparece una sola vez."
            ),
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(3, 11))

        birthday_cards_frame = ttk.Frame(
            membership_section,
            style="Card.TFrame",
        )
        birthday_cards_frame.pack(fill="x")

        self.birthday_groups: dict[
            str,
            list[dict[str, Any]],
        ] = {}
        self.birthday_cards: dict[
            str,
            MembershipStatusCard,
        ] = {}

        for column in range(len(self.BIRTHDAY_BUCKETS)):
            birthday_cards_frame.columnconfigure(column, weight=1)

        for column, data in enumerate(self.BIRTHDAY_BUCKETS):
            key, title, icon, color, background = data
            card = MembershipStatusCard(
                birthday_cards_frame,
                title,
                icon,
                color,
                background,
                lambda bucket=key, label=title: (
                    self.show_birthday_list(bucket, label)
                ),
                help_text="Ver cumpleaños  →",
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(
                    0 if column == 0 else 5,
                    0
                    if column == len(self.BIRTHDAY_BUCKETS) - 1
                    else 5,
                ),
            )
            self.birthday_cards[key] = card

    def refresh(self) -> None:
        self.load_view('dashboard', lambda: (self.db.dashboard_metrics(),
            self.db.membership_expiration_groups(), self.db.ticket_followup(),
            self.db.list_clients(), self.db._today()), self._render_refresh)

    def _render_refresh(self, data):
        metrics, self.expiration_groups, tickets, clients, today = data
        for key, label in self.metric_labels.items():
            label.configure(text=format_money(metrics[key]) if key == "income_month" else str(metrics[key]))


        for key, card in self.expiration_cards.items():
            card.set_count(
                len(self.expiration_groups.get(key, []))
            )

        self.ticket_dashboard.set_rows(tickets)

        self.birthday_groups = birthday_dashboard_groups(
            clients,
            today,
        )

        for key, card in self.birthday_cards.items():
            card.set_count(
                len(self.birthday_groups.get(key, []))
            )

    def quick_new_client(self) -> None:
        self.app.show_page("clients")
        page = self.app.pages.get("clients")

        if isinstance(page, ClientsPage):
            page.new_client()

    def quick_register_payment(self) -> None:
        clients = [
            client
            for client in self.db.list_clients()
            if bool(client.get("active", True))
        ]

        choices = {
            (
                f"{client['first_name']} "
                f"{client['last_name']} · "
                f"{client['document']}"
            ): int(client["id"])
            for client in clients
        }

        if not choices:
            messagebox.showinfo(
                "Sin clientes",
                "Primero registra un cliente activo.",
                parent=self,
            )
            return

        dialog = ChoiceDialog(
            self,
            "Registrar pago",
            "Selecciona el cliente",
            choices,
        )
        self.wait_window(dialog)

        if dialog.result is not None:
            self.register_payment_for_client(
                self,
                int(dialog.result),
            )

    def register_payment_for_client(
        self,
        parent: tk.Misc,
        client_id: int,
    ) -> bool:
        try:
            client = self.db.get_client(client_id)
        except Exception as error:
            messagebox.showerror('No se pudo consultar el cliente', str(error), parent=parent)
            return False

        if not client:
            messagebox.showerror(
                "Cliente no encontrado",
                "El cliente ya no está disponible. Actualiza la lista.",
                parent=parent,
            )
            return False

        client_name = (
            f"{client['first_name']} {client['last_name']}"
        ).strip()
        try:
            dialog = MembershipDialog(
                parent, self.db, client_name,
                on_submit=lambda payload: self.db.add_membership(client_id=client_id, **payload),
            )
        except Exception as error:
            messagebox.showerror(
                "No se pudo registrar el pago",
                str(error),
                parent=parent,
            )
            return False
        parent.wait_window(dialog)
        if not dialog.result:
            return False
        self.app.refresh_all(except_page=self)
        messagebox.showinfo(
            "Plan registrado",
            "El plan quedó registrado correctamente.",
            parent=parent,
        )
        return True

    def show_expiration_list(
        self,
        bucket: str,
        title: str,
    ) -> None:
        people = self.expiration_groups.get(bucket, [])
        window = BaseDialog(
            self,
            f"{title} · Estado de membresías",
            920,
            540,
        )

        ttk.Label(
            window.body,
            text=f"{title} · {len(people)} personas",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 4))

        ttk.Label(
            window.body,
            text=(
                "Selecciona una persona para abrir su ficha "
                "o registrar un pago."
            ),
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        tree = CenteredTreeview(
            window.body,
            columns=(
                "document",
                "client",
                "phone",
                "expiry",
                "remaining",
            ),
            show="headings",
            selectmode="browse",
        )

        columns = [
            ("document", "Documento", 135),
            ("client", "Cliente", 250),
            ("phone", "Teléfono", 135),
            ("expiry", "Vencimiento", 135),
            ("remaining", "Estado", 160),
        ]

        for key, label, width in columns:
            tree.heading(key, text=label)
            tree.column(key, width=width)

        tree.pack(fill="both", expand=True)
        tree.tag_configure(
            "expired",
            foreground=COLORS["danger"],
        )

        for person in people:
            days = person.get("days_remaining")

            if days is None:
                remaining = "Sin membresía"
            elif int(days) < 0:
                overdue = abs(int(days))
                remaining = (
                    f"Vencida hace {overdue} "
                    f"{'día' if overdue == 1 else 'días'}"
                )
            elif int(days) == 0:
                remaining = "Vence hoy"
            else:
                remaining = (
                    f"{int(days)} "
                    f"{'día' if int(days) == 1 else 'días'}"
                )

            tree.insert(
                "",
                "end",
                iid=str(person["id"]),
                values=(
                    person["document"],
                    person["client_name"],
                    person.get("phone") or "—",
                    date_to_display(person.get("end_date"))
                    or "—",
                    remaining,
                ),
                tags=("expired",)
                if bucket == "expired"
                else (),
            )

        def open_client() -> None:
            client_id = selected_id(tree)

            if client_id is None:
                messagebox.showinfo(
                    "Selecciona un registro",
                    "Selecciona una persona de la lista.",
                    parent=window,
                )
                return

            window.destroy()
            open_followup_client(self.app, client_id)

        def register_payment() -> None:
            client_id = selected_id(tree)

            if client_id is None:
                messagebox.showinfo(
                    "Selecciona un registro",
                    "Selecciona la persona que realizó el pago.",
                    parent=window,
                )
                return

            if self.register_payment_for_client(
                window,
                client_id,
            ):
                window.destroy()

        tree.bind(
            "<Double-1>",
            lambda _event: open_client(),
        )

        actions = ttk.Frame(
            window.body,
            style="Surface.TFrame",
        )
        actions.pack(fill="x", pady=(14, 0))

        tk.Button(
            actions,
            text="Cerrar",
            command=window.destroy,
            bg=COLORS["surface_hover"],
            fg=COLORS["text"],
            activebackground=COLORS["sidebar_active"],
            activeforeground=COLORS["text"],
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
        ).pack(side="right")

        tk.Button(
            actions,
            text="Registrar pago",
            command=register_payment,
            bg=COLORS["primary"],
            fg="#04130D",
            activebackground=COLORS["primary_dark"],
            activeforeground="#04130D",
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        tk.Button(
            actions,
            text="Abrir cliente",
            command=open_client,
            bg=COLORS["surface_hover"],
            fg=COLORS["text"],
            activebackground=COLORS["sidebar_active"],
            activeforeground=COLORS["text"],
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
            bd=0,
            padx=18,
            pady=9,
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        center_window(window, self)

    def show_birthday_list(
        self,
        bucket: str,
        title: str,
    ) -> None:
        people = self.birthday_groups.get(bucket, [])
        window = BaseDialog(
            self,
            f"{title} · Cumpleaños",
            980,
            590,
        )

        ttk.Label(
            window.body,
            text=f"{title} · {len(people)} cumpleaños",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 4))

        ttk.Label(
            window.body,
            text=(
                "La lista incluye clientes con y sin membresía vigente "
                "para validar descuentos o premios."
            ),
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        tree = CenteredTreeview(
            window.body,
            columns=(
                "document",
                "client",
                "phone",
                "birthday",
                "period",
                "membership",
            ),
            show="headings",
            selectmode="browse",
        )

        for key, label, width in (
            ("document", "Documento", 125),
            ("client", "Cliente", 225),
            ("phone", "Teléfono", 125),
            ("birthday", "Cumpleaños", 120),
            ("period", "Periodo", 145),
            ("membership", "Membresía", 115),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width)

        tree.pack(fill="both", expand=True)
        tree.tag_configure("today", foreground=COLORS["warning"])
        tree.tag_configure("inactive", foreground=COLORS["muted"])

        for person in people:
            info = person["birthday_info"]
            status = str(person.get("membership_status", ""))
            tag = (
                "today"
                if info["period_label"] == "HOY 🎂"
                else "inactive"
                if status == "INACTIVO"
                else ""
            )
            tree.insert(
                "",
                "end",
                iid=str(person["id"]),
                values=(
                    person.get("document", ""),
                    (
                        f"{person.get('first_name', '')} "
                        f"{person.get('last_name', '')}"
                    ).strip(),
                    person.get("phone", "") or "—",
                    date_to_display(person.get("birthdate")),
                    info["period_label"],
                    status or "—",
                ),
                tags=(tag,) if tag else (),
            )

        def open_client() -> None:
            client_id = selected_id(tree)

            if client_id is None:
                messagebox.showinfo(
                    "Selecciona un registro",
                    "Selecciona una persona de la lista.",
                    parent=window,
                )
                return

            window.destroy()
            open_followup_client(self.app, client_id)

        def register_payment() -> None:
            client_id = selected_id(tree)

            if client_id is None:
                messagebox.showinfo(
                    "Selecciona un registro",
                    "Selecciona la persona que realizó el pago.",
                    parent=window,
                )
                return

            if self.register_payment_for_client(window, client_id):
                window.destroy()

        tree.bind("<Double-1>", lambda _event: open_client())

        actions = ttk.Frame(
            window.body,
            style="Surface.TFrame",
        )
        actions.pack(fill="x", pady=(14, 0))
        tk.Button(
            actions,
            text="Cerrar",
            command=window.destroy,
            bg=COLORS["surface_hover"],
            fg=COLORS["text"],
            activebackground=COLORS["sidebar_active"],
            activeforeground=COLORS["text"],
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
        ).pack(side="right")
        tk.Button(
            actions,
            text="Abrir en Clientes y pagos",
            command=open_client,
            bg=COLORS["surface_hover"],
            fg=COLORS["text"],
            activebackground=COLORS["sidebar_active"],
            activeforeground=COLORS["text"],
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))
        tk.Button(
            actions,
            text="Registrar pago",
            command=register_payment,
            bg=COLORS["primary"],
            fg="#04130D",
            activebackground=COLORS["primary_dark"],
            activeforeground="#04130D",
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
            bd=0,
            padx=18,
            pady=10,
            cursor="hand2",
        ).pack(side="right", padx=(0, 8))

        center_window(window, self)


    def create_backup(self) -> None:
        default = f"GymSoft-respaldo-{datetime.now():%Y%m%d-%H%M}.db"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar respaldo",
            defaultextension=".db",
            initialfile=default,
            filetypes=[("Base de datos GymSoft", "*.db")],
        )
        if path:
            self.db.backup(path)
            messagebox.showinfo("Respaldo creado", f"Se guardó correctamente en:\n{path}", parent=self)


class StatisticsPage(BasePage):
    title = "Estadísticas"

    PERIODS = {
        "Últimos 7 días": 7,
        "Últimos 14 días": 14,
        "Últimos 30 días": 30,
        "Últimos 90 días": 90,
    }

    def __init__(
        self,
        parent: tk.Misc,
        app: "GymSoftApp",
    ):
        super().__init__(parent, app)
        self.chart_data: list[dict[str, Any]] = []
        self.page_header(
            "Analiza la asistencia y el comportamiento de los clientes."
        )

        toolbar = ttk.Frame(
            self,
            style="Page.TFrame",
        )
        toolbar.pack(fill="x", pady=(0, 12))

        ttk.Label(
            toolbar,
            text="Período:",
        ).pack(side="left")

        self.period = tk.StringVar(
            value="Últimos 30 días"
        )
        period_box = ttk.Combobox(
            toolbar,
            textvariable=self.period,
            values=list(self.PERIODS),
            state="readonly",
            width=19,
        )
        period_box.pack(side="left", padx=(8, 0))
        period_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.refresh(),
        )

        ttk.Button(
            toolbar,
            text="Actualizar",
            command=self.refresh,
            style="Primary.TButton",
        ).pack(side="right")

        self.updated_label = ttk.Label(
            toolbar,
            text="",
            style="Subtitle.TLabel",
        )
        self.updated_label.pack(
            side="right",
            padx=(0, 12),
        )

        cards = ttk.Frame(
            self,
            style="Page.TFrame",
        )
        cards.pack(fill="x")

        for column in range(4):
            cards.columnconfigure(column, weight=1)

        self.metric_labels: dict[
            str,
            tuple[tk.Label, tk.Label],
        ] = {}

        card_data = [
            (
                "today",
                "Entradas hoy",
                COLORS["blue"],
                COLORS["blue_bg"],
            ),
            (
                "week",
                "Entradas esta semana",
                COLORS["success"],
                COLORS["success_bg"],
            ),
            (
                "month",
                "Entradas este mes",
                COLORS["warning"],
                COLORS["warning_bg"],
            ),
            (
                "period",
                "Personas en el período",
                COLORS["purple"],
                COLORS["purple_bg"],
            ),
        ]

        for column, data in enumerate(card_data):
            key, title, color, background = data
            card = tk.Frame(
                cards,
                bg=background,
                bd=0,
                highlightthickness=0,
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(
                    0 if column == 0 else 6,
                    0 if column == 3 else 6,
                ),
            )

            value = tk.Label(
                card,
                text="0",
                font=(UI_FONT, 22, "bold"),
                fg=color,
                bg=background,
            )
            value.pack(
                anchor="w",
                padx=16,
                pady=(13, 0),
            )

            tk.Label(
                card,
                text=title,
                font=(UI_FONT, 9, "bold"),
                fg=COLORS["text"],
                bg=background,
            ).pack(anchor="w", padx=16, pady=(1, 0))

            detail = tk.Label(
                card,
                text="0 personas únicas",
                font=(UI_FONT, 8),
                fg=COLORS["muted"],
                bg=background,
            )
            detail.pack(
                anchor="w",
                padx=16,
                pady=(1, 12),
            )
            self.metric_labels[key] = (
                value,
                detail,
            )

        notebook = ttk.Notebook(self)
        notebook.pack(
            fill="both",
            expand=True,
            pady=(14, 0),
        )

        general_tab = ttk.Frame(
            notebook,
            padding=12,
            style="Page.TFrame",
        )
        clients_tab = ttk.Frame(
            notebook,
            padding=12,
            style="Page.TFrame",
        )
        notebook.add(general_tab, text="Asistencia general")
        notebook.add(clients_tab, text="Frecuencia de clientes")
        sessions_tab = ttk.Frame(notebook, padding=14, style='Card.TFrame')
        notebook.add(sessions_tab, text='Seguimiento de sesiones')
        ttk.Label(sessions_tab, text='Clientes que asistieron solo por sesión', style='Section.TLabel').pack(anchor='w')
        ttk.Label(sessions_tab, text='Incluye a quienes solo registraron entradas con plan de sesión durante el período seleccionado. '
                  'Revisa su plan actual antes de contactarlos. El listado no envía mensajes.',
                  style='CardMuted.TLabel', wraplength=800).pack(fill='x', pady=(4, 10))
        session_toolbar = ttk.Frame(sessions_tab, style='Card.TFrame')
        session_toolbar.pack(fill='x', pady=(0, 12))
        ttk.Label(session_toolbar, text='Visitas registradas en:').pack(side='left')
        self.session_days = tk.StringVar(value='Últimos 7 días')
        self.session_periods = {'Últimos 7 días': 7, 'Últimos 14 días': 14, 'Últimos 30 días': 30}
        picker = ttk.Combobox(session_toolbar, textvariable=self.session_days, state='readonly', values=list(self.session_periods), width=20)
        picker.pack(side='left', padx=8)
        picker.bind('<<ComboboxSelected>>', lambda _: self.refresh_sessions())
        ttk.Button(session_toolbar, text='Actualizar listado', command=self.refresh_sessions).pack(side='left')
        self.session_range = ttk.Label(sessions_tab, style='CardMuted.TLabel')
        self.session_range.pack(fill='x', pady=(0, 8))
        self.session_contacts = ContactList(sessions_tab, [
            ('document', 'Documento', 110), ('client_name', 'Cliente', 210), ('phone', 'Teléfono', 130),
            ('email', 'Correo', 210), ('entries', 'Sesiones', 85), ('last_visit', 'Última sesión', 120),
            ('current_plan', 'Plan actual', 150), ('current_status', 'Estado actual', 130),
        ], open_record=lambda cid: open_followup_client(self.app, cid))
        self.session_contacts.pack(fill='both', expand=True)


        general_top = ttk.Frame(
            general_tab,
            style="Page.TFrame",
        )
        general_top.pack(fill="both", expand=True)
        general_top.columnconfigure(0, weight=3)
        general_top.columnconfigure(1, weight=2)
        general_top.rowconfigure(0, weight=1)

        chart_card = ttk.Frame(
            general_top,
            padding=16,
            style="Card.TFrame",
        )
        chart_card.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 7),
        )

        self.chart_title = ttk.Label(
            chart_card,
            text="Asistencia diaria",
            style="Section.TLabel",
        )
        self.chart_title.pack(anchor="w")

        self.chart = tk.Canvas(
            chart_card,
            bg=COLORS["surface"],
            height=220,
            highlightthickness=0,
        )
        self.chart.pack(fill="both", expand=True, pady=(8, 0))
        self.chart.bind(
            "<Configure>",
            lambda _event: self.schedule_chart(),
        )

        plan_card = ttk.Frame(
            general_top,
            padding=16,
            style="Card.TFrame",
        )
        plan_card.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(7, 0),
        )

        ttk.Label(
            plan_card,
            text="Asistencia por tipo de plan",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        self.plan_tree = CenteredTreeview(
            plan_card,
            columns=("type", "people", "entries", "percent"),
            show="headings",
            height=7,
        )

        for key, title, width in [
            ("type", "Tipo", 125),
            ("people", "Personas", 75),
            ("entries", "Entradas", 75),
            ("percent", "%", 65),
        ]:
            self.plan_tree.heading(key, text=title)
            self.plan_tree.column(key, width=width)

        self.plan_tree.pack(fill="both", expand=True)

        insights = ttk.Frame(
            general_tab,
            style="Page.TFrame",
        )
        insights.pack(fill="x", pady=(12, 0))

        for column in range(5):
            insights.columnconfigure(column, weight=1)

        self.insight_labels: dict[str, tk.Label] = {}
        insight_data = [
            ("period_entries", "Actual / período anterior"),
            ("daily_average", "Promedio diario"),
            ("trend", "Cambio anterior"),
            ("busiest_weekday", "Día más concurrido"),
            ("peak_hour", "Hora más concurrida"),
        ]

        for column, (key, title) in enumerate(insight_data):
            box = tk.Frame(
                insights,
                bg=COLORS["surface"],
                highlightbackground=COLORS["line"],
                highlightthickness=1,
            )
            box.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(
                    0 if column == 0 else 5,
                    0 if column == 4 else 5,
                ),
            )

            value = tk.Label(
                box,
                text="—",
                bg=COLORS["surface"],
                fg=COLORS["text"],
                font=(UI_FONT, 14, "bold"),
            )
            value.pack(pady=(10, 1), padx=8)

            tk.Label(
                box,
                text=title,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=(UI_FONT, 8),
            ).pack(pady=(0, 10), padx=8)

            self.insight_labels[key] = value

        inactive_cards = ttk.Frame(
            clients_tab,
            style="Page.TFrame",
        )
        inactive_cards.pack(fill="x", pady=(0, 12))

        for column in range(3):
            inactive_cards.columnconfigure(column, weight=1)

        self.inactive_labels: dict[int, tk.Label] = {}

        for column, days in enumerate((7, 15, 30)):
            background = (
                COLORS["warning_bg"]
                if days < 30
                else COLORS["danger_bg"]
            )
            foreground = (
                COLORS["warning"]
                if days < 30
                else COLORS["danger"]
            )
            card = tk.Frame(
                inactive_cards,
                bg=background,
            )
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(
                    0 if column == 0 else 6,
                    0 if column == 2 else 6,
                ),
            )

            value = tk.Label(
                card,
                text="0",
                bg=background,
                fg=foreground,
                font=(UI_FONT, 22, "bold"),
            )
            value.pack(pady=(13, 0))

            tk.Label(
                card,
                text=f"Sin asistir durante {days} días",
                bg=background,
                fg=COLORS["text"],
                font=(UI_FONT, 9, "bold"),
            ).pack(pady=(0, 13))

            self.inactive_labels[days] = value

        top_card = ttk.Frame(
            clients_tab,
            padding=16,
            style="Card.TFrame",
        )
        top_card.pack(fill="both", expand=True)

        ttk.Label(
            top_card,
            text="Clientes con mayor asistencia en el período",
            style="Section.TLabel",
        ).pack(anchor="w", pady=(0, 8))

        self.top_clients = CenteredTreeview(
            top_card,
            columns=(
                "position",
                "document",
                "client",
                "plan",
                "entries",
                "last_visit",
            ),
            show="headings",
            height=10,
        )

        for key, title, width in [
            ("position", "#", 45),
            ("document", "Documento", 125),
            ("client", "Cliente", 260),
            ("plan", "Tipo de plan", 125),
            ("entries", "Entradas", 90),
            ("last_visit", "Última entrada", 120),
        ]:
            self.top_clients.heading(key, text=title)
            self.top_clients.column(key, width=width)

        self.top_clients.pack(fill="both", expand=True)

    @staticmethod
    def number(
        data: dict[str, Any],
        key: str,
    ) -> int:
        try:
            return int(data.get(key) or 0)
        except (TypeError, ValueError):
            return 0

    def refresh_sessions(self):
        days = self.session_periods[self.session_days.get()]
        self.load_view('sessions', lambda: (self.db.session_followup(days), self.db._today()),
                       lambda data: self._render_sessions(data, days), (days,))

    def _render_sessions(self, data, days):
        rows, today = data
        self.session_contacts.set_rows(rows)
        since = today - timedelta(days=days - 1)
        self.session_range.configure(text=f'Del {since:%d/%m/%Y} al {today:%d/%m/%Y}, ambos incluidos. {len(rows)} clientes.')

    def refresh(self) -> None:
        self.refresh_sessions()
        days = self.PERIODS.get(self.period.get(), 30)
        self.load_view('statistics', lambda: self.db.attendance_statistics(days),
                       lambda data: self._render_refresh(data, days), (days,))

    def _render_refresh(self, data, days):
        metrics = data.get("metrics") or {}

        card_values = {
            "today": (
                self.number(metrics, "today_entries"),
                self.number(metrics, "today_unique"),
            ),
            "week": (
                self.number(metrics, "week_entries"),
                self.number(metrics, "week_unique"),
            ),
            "month": (
                self.number(metrics, "month_entries"),
                self.number(metrics, "month_unique"),
            ),
            "period": (
                self.number(metrics, "period_unique"),
                self.number(metrics, "period_entries"),
            ),
        }

        for key, (value, detail) in card_values.items():
            value_label, detail_label = self.metric_labels[key]
            value_label.configure(text=str(value))

            if key == "period":
                detail_label.configure(
                    text=f"{detail} entradas en {days} días"
                )
            else:
                detail_label.configure(
                    text=f"{detail} personas únicas"
                )

        clear_tree(self.plan_tree)

        for item in data.get("plan_breakdown") or []:
            percentage = float(item.get("percentage") or 0)
            self.plan_tree.insert(
                "",
                "end",
                values=(
                    item.get("type", "Sin plan"),
                    self.number(item, "people"),
                    self.number(item, "entries"),
                    f"{percentage:.1f}%",
                ),
            )

        clear_tree(self.top_clients)

        for position, item in enumerate(
            data.get("top_clients") or [],
            start=1,
        ):
            self.top_clients.insert(
                "",
                "end",
                values=(
                    position,
                    item.get("document", ""),
                    item.get("client_name", ""),
                    item.get("plan_type", "Sin plan"),
                    self.number(item, "entries"),
                    date_to_display(
                        item.get("last_visit", "")
                    ) or "—",
                ),
            )

        period_entries = self.number(
            metrics,
            "period_entries",
        )
        previous_entries = self.number(
            metrics,
            "previous_entries",
        )
        average = float(
            metrics.get("daily_average") or 0
        )
        trend = float(
            metrics.get("trend_percentage") or 0
        )

        self.insight_labels["period_entries"].configure(
            text=str(period_entries)
        )
        self.insight_labels["daily_average"].configure(
            text=f"{average:.1f}"
        )
        self.insight_labels["trend"].configure(
            text=f"{trend:+.1f}%",
            fg=(
                COLORS["success"]
                if trend >= 0
                else COLORS["danger"]
            ),
        )
        self.insight_labels["busiest_weekday"].configure(
            text=str(
                metrics.get("busiest_weekday")
                or "Sin datos"
            )
        )
        self.insight_labels["peak_hour"].configure(
            text=str(
                metrics.get("peak_hour")
                or "Sin datos"
            )
        )

        self.insight_labels["period_entries"].configure(
            text=f"{period_entries} / {previous_entries}"
        )

        active_clients = self.number(
            metrics,
            "active_clients",
        )

        for inactivity_days in (7, 15, 30):
            value = self.number(
                metrics,
                f"inactive_{inactivity_days}",
            )
            self.inactive_labels[inactivity_days].configure(
                text=f"{value} de {active_clients}"
            )

        self.chart_data = list(
            data.get("daily_series") or []
        )
        self.chart_title.configure(
            text=(
                "Asistencia diaria · "
                f"últimos {len(self.chart_data)} días"
            )
        )
        self.schedule_chart()

        self.updated_label.configure(
            text=f"Actualizado {datetime.now():%H:%M:%S}"
        )

    def schedule_chart(self):
        pending = getattr(self, '_chart_job', None)
        if pending is not None:
            self.after_cancel(pending)
        self._chart_job = self.after(60, self.draw_chart)

    def draw_chart(self) -> None:
        self._chart_job = None
        canvas = self.chart
        canvas.delete("all")

        width = max(canvas.winfo_width(), 300)
        height = max(canvas.winfo_height(), 180)
        left = 42
        right = 14
        top = 18
        bottom = 34
        plot_width = max(width - left - right, 1)
        plot_height = max(height - top - bottom, 1)

        values = [
            self.number(item, "count")
            for item in self.chart_data
        ]

        if not values:
            canvas.create_text(
                width / 2,
                height / 2,
                text="Todavía no hay entradas en este período.",
                fill=COLORS["muted"],
                font=(UI_FONT, 10),
            )
            return

        maximum = max(max(values), 1)

        for line in range(5):
            value = round(maximum * line / 4)
            y = top + plot_height - plot_height * line / 4
            canvas.create_line(
                left,
                y,
                width - right,
                y,
                fill=COLORS["line"],
            )
            canvas.create_text(
                left - 8,
                y,
                text=str(value),
                anchor="e",
                fill=COLORS["muted"],
                font=(UI_FONT, 8),
            )

        slot_width = plot_width / len(values)
        bar_width = max(min(slot_width * 0.68, 30), 2)
        label_step = max((len(values) + 6) // 7, 1)

        for index, (item, value) in enumerate(
            zip(self.chart_data, values)
        ):
            center = left + slot_width * (index + 0.5)
            bar_height = plot_height * value / maximum
            x1 = center - bar_width / 2
            x2 = center + bar_width / 2
            y1 = top + plot_height - bar_height
            y2 = top + plot_height

            canvas.create_rectangle(
                x1,
                y1,
                x2,
                y2,
                fill=COLORS["primary"],
                outline="",
            )

            if value and len(values) <= 14:
                canvas.create_text(
                    center,
                    max(y1 - 8, 8),
                    text=str(value),
                    fill=COLORS["text"],
                    font=(UI_FONT, 8, "bold"),
                )

            if (
                index % label_step == 0
                or index == len(values) - 1
            ):
                label = date_to_display(
                    item.get("date", "")
                )[:5]
                canvas.create_text(
                    center,
                    height - 16,
                    text=label,
                    fill=COLORS["muted"],
                    font=(UI_FONT, 8),
                )


class LegacyMarketingPage(BasePage):
    title = "Marketing"

    TYPE_LABELS = {
        "BIRTHDAY": "Cumpleaños",
        "EXPIRING": "Vence pronto",
        "EXPIRED": "Membresía vencida",
    }
    STATUS_LABELS = {
        "PENDING": "PENDIENTE",
        "PROCESSING": "PROCESANDO",
        "SENT": "ENVIADO",
        "FAILED": "ERROR",
        "SKIPPED": "OMITIDO",
    }

    def __init__(
        self,
        parent: tk.Misc,
        app: "GymSoftApp",
    ) -> None:
        super().__init__(parent, app)
        self.contacts: dict[int, dict[str, Any]] = {}
        self.search = tk.StringVar()
        self.metric_authorized = tk.StringVar(value="0")
        self.metric_pending = tk.StringVar(value="0")
        self.metric_sent = tk.StringVar(value="0")
        self.metric_failed = tk.StringVar(value="0")
        self.settings_vars: dict[str, tk.Variable] = {
            "whatsapp_enabled": tk.BooleanVar(value=False),
            "birthday_enabled": tk.BooleanVar(value=True),
            "expiring_enabled": tk.BooleanVar(value=True),
            "expired_enabled": tk.BooleanVar(value=True),
            "send_hour": tk.StringVar(value="09:00"),
            "warning_days": tk.StringVar(value="5"),
            "timezone": tk.StringVar(value="America/Bogota"),
            "birthday_template": tk.StringVar(
                value="ztattuz_cumpleanos"
            ),
            "expiring_template": tk.StringVar(
                value="ztattuz_membresia_vence"
            ),
            "expired_template": tk.StringVar(
                value="ztattuz_membresia_vencida"
            ),
        }

        self.page_header(
            (
                "Automatiza mensajes útiles por WhatsApp y supervisa "
                "cada envío desde un solo lugar."
            ),
            [
                ("Guardar configuración", self.save_settings, "Primary.TButton"),
                ("Actualizar", self.refresh, None),
            ],
        )

        metrics = tk.Frame(self, bg=COLORS["background"])
        metrics.pack(fill="x", pady=(0, 14))

        for column in range(4):
            metrics.columnconfigure(column, weight=1)

        for column, (label, variable, color) in enumerate((
            ("CONTACTOS AUTORIZADOS", self.metric_authorized, COLORS["success"]),
            ("MENSAJES PENDIENTES", self.metric_pending, COLORS["warning"]),
            ("ENVIADOS ESTE MES", self.metric_sent, COLORS["blue"]),
            ("ENVÍOS CON ERROR", self.metric_failed, COLORS["danger"]),
        )):
            card = tk.Frame(
                metrics,
                bg=COLORS["surface"],
                padx=18,
                pady=14,
                highlightbackground=COLORS["line"],
                highlightthickness=1,
            )
            card.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 5, 0 if column == 3 else 5),
            )
            tk.Label(
                card,
                text=label,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=(FONT_FAMILY, 8, "bold"),
            ).pack(anchor="w")
            tk.Label(
                card,
                textvariable=variable,
                bg=COLORS["surface"],
                fg=color,
                font=(FONT_FAMILY, 20, "bold"),
            ).pack(anchor="w", pady=(5, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        automations_tab = ttk.Frame(
            notebook,
            padding=14,
            style="Card.TFrame",
        )
        contacts_tab = ttk.Frame(
            notebook,
            padding=14,
            style="Card.TFrame",
        )
        activity_tab = ttk.Frame(
            notebook,
            padding=14,
            style="Card.TFrame",
        )
        notebook.add(automations_tab, text="Automatizaciones")
        notebook.add(contacts_tab, text="Contactos autorizados")
        notebook.add(activity_tab, text="Registro de mensajes")

        self.build_automations_tab(automations_tab)
        self.build_contacts_tab(contacts_tab)
        self.build_activity_tab(activity_tab)
        bind_live_search(self, self.search, self.refresh_contacts)

    def build_automations_tab(self, parent: ttk.Frame) -> None:
        schedule = ttk.Frame(parent, padding=14, style="Surface.TFrame")
        schedule.pack(fill="x", pady=(0, 14))

        ttk.Checkbutton(
            schedule,
            text="Activar automatización de WhatsApp",
            variable=self.settings_vars["whatsapp_enabled"],
        ).pack(side="left")
        ttk.Label(
            schedule,
            text="Enviar a las",
            style="Field.TLabel",
        ).pack(side="left", padx=(28, 8))
        ttk.Combobox(
            schedule,
            textvariable=self.settings_vars["send_hour"],
            values=[f"{hour:02d}:00" for hour in range(6, 22)],
            state="readonly",
            width=8,
        ).pack(side="left")
        ttk.Label(
            schedule,
            text="Hora del gimnasio · requiere activar el servicio de envíos",
            style="CardMuted.TLabel",
        ).pack(side="left", padx=(14, 0))

        panels = tk.Frame(parent, bg=COLORS["surface"])
        panels.pack(fill="both", expand=True)

        for column in range(3):
            panels.columnconfigure(column, weight=1)
            panels.rowconfigure(0, weight=1)

        self.birthday_extra = self.automation_panel(
            panels,
            0,
            "Cumpleaños",
            "Se envía el día del cumpleaños.",
            "birthday_enabled",
            "birthday_template",
            COLORS["danger"],
        )
        self.expiring_extra = self.automation_panel(
            panels,
            1,
            "Membresía por vencer",
            "Se envía antes de la fecha de vencimiento.",
            "expiring_enabled",
            "expiring_template",
            COLORS["warning"],
            include_days=True,
        )
        self.expired_extra = self.automation_panel(
            panels,
            2,
            "Membresía vencida",
            "Se envía una vez cuando el plan ya venció.",
            "expired_enabled",
            "expired_template",
            COLORS["blue"],
        )

    def automation_panel(
        self,
        parent: tk.Misc,
        column: int,
        title: str,
        subtitle: str,
        enabled_key: str,
        template_key: str,
        color: str,
        include_days: bool = False,
    ) -> tk.Text:
        panel = tk.Frame(
            parent,
            bg=COLORS["surface_alt"],
            highlightbackground=color,
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        panel.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0 if column == 0 else 6, 0 if column == 2 else 6),
        )
        ttk.Checkbutton(
            panel,
            text=title,
            variable=self.settings_vars[enabled_key],
            style="TCheckbutton",
        ).pack(anchor="w")
        tk.Label(
            panel,
            text=subtitle,
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 8),
            wraplength=270,
            justify="left",
        ).pack(anchor="w", pady=(3, 12))

        if include_days:
            days = tk.Frame(panel, bg=COLORS["surface_alt"])
            days.pack(fill="x", pady=(0, 10))
            tk.Label(
                days,
                text="Avisar con",
                bg=COLORS["surface_alt"],
                fg=COLORS["text"],
                font=(FONT_FAMILY, 8, "bold"),
            ).pack(side="left")
            ttk.Combobox(
                days,
                textvariable=self.settings_vars["warning_days"],
                values=[str(day) for day in range(1, 16)],
                state="readonly",
                width=5,
            ).pack(side="left", padx=7)
            tk.Label(
                days,
                text="días",
                bg=COLORS["surface_alt"],
                fg=COLORS["text"],
                font=(FONT_FAMILY, 8),
            ).pack(side="left")

        tk.Label(
            panel,
            text="Plantilla aprobada en Meta",
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 8, "bold"),
        ).pack(anchor="w")
        ttk.Entry(
            panel,
            textvariable=self.settings_vars[template_key],
        ).pack(fill="x", pady=(4, 11))
        tk.Label(
            panel,
            text="Mensaje adicional personalizable",
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 8, "bold"),
        ).pack(anchor="w")
        editor = tk.Text(
            panel,
            height=5,
            wrap="word",
            bg=COLORS["input"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["sidebar_active"],
            relief="flat",
            bd=0,
            padx=9,
            pady=8,
            font=(FONT_FAMILY, 9),
        )
        editor.pack(fill="both", expand=True, pady=(4, 8))
        tk.Label(
            panel,
            text="Variables disponibles: {nombre}, {gimnasio}, {vencimiento}, {dias}",
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 7),
            wraplength=270,
            justify="left",
        ).pack(anchor="w")
        return editor

    def build_contacts_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        toolbar = ttk.Frame(parent, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Entry(
            toolbar,
            textvariable=self.search,
            width=34,
        ).pack(side="left")
        ttk.Button(
            toolbar,
            text="Buscar",
            command=self.refresh_contacts,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text="Limpiar",
            command=self.clear_search,
        ).pack(side="left", padx=(8, 0))
        ttk.Label(
            toolbar,
            text="Solo se enviarán mensajes a quienes autorizaron WhatsApp.",
            style="CardMuted.TLabel",
        ).pack(side="right")

        self.contacts_tree = CenteredTreeview(
            parent,
            columns=(
                "document",
                "client",
                "phone",
                "birthday",
                "membership",
                "authorization",
            ),
            show="headings",
            selectmode="browse",
        )
        for key, label, width, anchor in (
            ("document", "Documento", 120, "center"),
            ("client", "Cliente", 225, "w"),
            ("phone", "WhatsApp", 135, "center"),
            ("birthday", "Cumpleaños", 115, "center"),
            ("membership", "Vencimiento", 120, "center"),
            ("authorization", "Autorización", 145, "center"),
        ):
            self.contacts_tree.heading(key, text=label)
            self.contacts_tree.column(key, width=width, anchor=anchor)
        self.contacts_tree.grid(row=1, column=0, sticky="nsew")
        self.contacts_tree.tag_configure("authorized", foreground=COLORS["success"])
        self.contacts_tree.tag_configure("pending", foreground=COLORS["muted"])

        actions = ttk.Frame(parent, style="Card.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(
            actions,
            text="Autorizar mensajes",
            command=lambda: self.set_contact_authorization(True),
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Revocar autorización",
            command=lambda: self.set_contact_authorization(False),
        ).pack(side="left", padx=(8, 0))

    def build_activity_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        self.activity_tree = CenteredTreeview(
            parent,
            columns=("date", "type", "client", "phone", "status", "detail"),
            show="headings",
        )
        for key, label, width, anchor in (
            ("date", "Fecha y hora", 155, "center"),
            ("type", "Automatización", 145, "center"),
            ("client", "Cliente", 190, "w"),
            ("phone", "WhatsApp", 125, "center"),
            ("status", "Estado", 105, "center"),
            ("detail", "Detalle", 285, "w"),
        ):
            self.activity_tree.heading(key, text=label)
            self.activity_tree.column(key, width=width, anchor=anchor)
        self.activity_tree.grid(row=0, column=0, sticky="nsew")
        self.activity_tree.tag_configure("sent", foreground=COLORS["success"])
        self.activity_tree.tag_configure("failed", foreground=COLORS["danger"])
        self.activity_tree.tag_configure("pending", foreground=COLORS["warning"])

    @staticmethod
    def text_value(editor: tk.Text) -> str:
        return editor.get("1.0", "end-1c").strip()

    @staticmethod
    def set_text(editor: tk.Text, value: Any) -> None:
        editor.delete("1.0", "end")
        editor.insert("1.0", str(value or ""))

    def save_settings(self) -> None:
        try:
            send_hour = int(
                str(self.settings_vars["send_hour"].get()).split(":", 1)[0]
            )
            warning_days = int(self.settings_vars["warning_days"].get())
        except (TypeError, ValueError):
            messagebox.showwarning(
                "Configuración no válida",
                "Revisa la hora y los días del recordatorio.",
                parent=self,
            )
            return

        try:
            current_settings = self.db.marketing_settings()
        except Exception as error:
            messagebox.showerror(
                "No se pudo cargar Marketing",
                str(error),
                parent=self,
            )
            return

        enabled = bool(self.settings_vars["whatsapp_enabled"].get())
        phone_number_id = str(
            current_settings.get("phone_number_id") or ""
        ).strip()

        if enabled and not phone_number_id:
            messagebox.showwarning(
                "Falta conectar WhatsApp",
                "Escribe primero el ID del número de teléfono de Meta.",
                parent=self,
            )
            return

        data = dict(current_settings)
        data.update({
            key: variable.get()
            for key, variable in self.settings_vars.items()
        })
        data["send_hour"] = send_hour
        data["warning_days"] = warning_days
        data["birthday_extra"] = self.text_value(self.birthday_extra)
        data["expiring_extra"] = self.text_value(self.expiring_extra)
        data["expired_extra"] = self.text_value(self.expired_extra)

        try:
            self.db.save_marketing_settings(data)
        except Exception as error:
            messagebox.showerror(
                "No se pudo guardar Marketing",
                str(error),
                parent=self,
            )
            return

        self.refresh()
        messagebox.showinfo(
            "Marketing actualizado",
            "La configuración quedó guardada en la nube.",
            parent=self,
        )

    def clear_search(self) -> None:
        self.search.set("")
        self.refresh_contacts()

    def refresh_contacts(self) -> None:
        term = self.search.get()
        self.load_view("refresh_contacts", lambda: self.db.marketing_contacts(term), self._render_refresh_contacts, (term,))

    def _render_refresh_contacts(self, rows):
        self.contacts = {int(row["id"]): row for row in rows}
        clear_tree(self.contacts_tree)

        for row in rows:
            authorized = bool(row.get("whatsapp_opt_in"))
            self.contacts_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("document", ""),
                    row.get("client_name", ""),
                    row.get("phone", "") or "—",
                    date_to_display(row.get("birthdate")) or "—",
                    date_to_display(row.get("membership_end")) or "—",
                    "AUTORIZADO" if authorized else "SIN AUTORIZAR",
                ),
                tags=("authorized" if authorized else "pending",),
            )

    def selected_contact(self) -> dict[str, Any] | None:
        client_id = selected_id(self.contacts_tree)

        if client_id is None:
            messagebox.showinfo(
                "Selecciona un cliente",
                "Selecciona primero una persona de la lista.",
                parent=self,
            )
            return None

        return self.contacts.get(client_id)

    def set_contact_authorization(self, enabled: bool) -> None:
        contact = self.selected_contact()

        if not contact:
            return

        if enabled and not str(contact.get("phone") or "").strip():
            messagebox.showwarning(
                "Falta el teléfono",
                "Agrega primero el número de WhatsApp del cliente.",
                parent=self,
            )
            return

        if enabled:
            question = (
                f"¿{contact.get('client_name', 'El cliente')} autorizó recibir "
                "por WhatsApp mensajes de GymSoft sobre cumpleaños y "
                "estado de su membresía?"
            )
        else:
            question = (
                f"¿Deseas revocar los mensajes para "
                f"{contact.get('client_name', 'este cliente')}?"
            )

        if not messagebox.askyesno(
            "Autorización de WhatsApp",
            question,
            parent=self,
        ):
            return

        try:
            self.db.set_marketing_opt_in(int(contact["id"]), enabled)
        except Exception as error:
            messagebox.showerror(
                "No se pudo actualizar",
                str(error),
                parent=self,
            )
            return

        self.refresh()

    def refresh(self) -> None:
        term = self.search.get()
        self.load_view('marketing', lambda: (self.db.marketing_settings(),
            self.db.marketing_contacts(term), self.db.marketing_activity()), self._render_refresh, (term,))

    def _render_refresh(self, data):
        settings, contacts, activity = data
        previous = getattr(self, '_settings_snapshot', {})
        updated = {}
        for key, variable in self.settings_vars.items():
            value = f"{int(settings.get(key, 9)):02d}:00" if key == 'send_hour' else settings.get(key, variable.get())
            if key not in previous or str(variable.get()) == str(previous[key]):
                variable.set(value)
            updated[key] = value
        for key in ('birthday_extra', 'expiring_extra', 'expired_extra'):
            widget = getattr(self, key)
            if key not in previous or widget.get('1.0', 'end-1c') == str(previous[key] or ''):
                self.set_text(widget, settings.get(key))
            updated[key] = settings.get(key) or ''
        self._settings_snapshot = updated
        self.contacts = {int(row["id"]): row for row in contacts}
        self.refresh_contacts_from_rows(contacts)
        self.refresh_activity(activity)

        authorized = sum(
            1 for row in contacts if bool(row.get("whatsapp_opt_in"))
        )
        pending = sum(
            1
            for row in activity
            if str(row.get("status", "")) in {"PENDING", "PROCESSING"}
        )
        month_prefix = self.db._today().strftime("%Y-%m")
        sent = sum(
            1
            for row in activity
            if str(row.get("status", "")) == "SENT"
            and str(row.get("sent_at") or row.get("created_at") or "")
            .startswith(month_prefix)
        )
        failed = sum(
            1 for row in activity if str(row.get("status", "")) == "FAILED"
        )
        self.metric_authorized.set(str(authorized))
        self.metric_pending.set(str(pending))
        self.metric_sent.set(str(sent))
        self.metric_failed.set(str(failed))

    def refresh_contacts_from_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> None:
        clear_tree(self.contacts_tree)

        for row in rows:
            authorized = bool(row.get("whatsapp_opt_in"))
            self.contacts_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("document", ""),
                    row.get("client_name", ""),
                    row.get("phone", "") or "—",
                    date_to_display(row.get("birthdate")) or "—",
                    date_to_display(row.get("membership_end")) or "—",
                    "AUTORIZADO" if authorized else "SIN AUTORIZAR",
                ),
                tags=("authorized" if authorized else "pending",),
            )

    def refresh_activity(self, rows: list[dict[str, Any]]) -> None:
        clear_tree(self.activity_tree)

        for row in rows:
            status = str(row.get("status") or "PENDING")
            tag = (
                "sent"
                if status == "SENT"
                else "failed"
                if status == "FAILED"
                else "pending"
            )
            self.activity_tree.insert(
                "",
                "end",
                iid=str(row.get("id")),
                values=(
                    display_timestamp(row.get("created_at") or "", timezone_for(self.db)),
                    self.TYPE_LABELS.get(
                        str(row.get("automation_type") or ""),
                        str(row.get("automation_type") or ""),
                    ),
                    row.get("client_name", ""),
                    row.get("phone", ""),
                    self.STATUS_LABELS.get(status, status),
                    row.get("error_message", "")
                    or row.get("template_name", ""),
                ),
                tags=(tag,),
            )


from marketing_ui import marketing_page_class

class MarketingPage(marketing_page_class(BasePage, LegacyMarketingPage)):
    pass


class FinancePage(BasePage):
    title = "Finanzas y auditoría"

    ACTIONS = {
        "Todos los movimientos": "",
        "Pagos registrados": "PAGO_REGISTRADO",
        "Pagos editados": "PAGO_EDITADO",
        "Pagos anulados": "PAGO_ANULADO",
        "Pagos eliminados": "PAGO_ELIMINADO",
        "Entradas": "ENTRADA_REGISTRADA",
        "Membresías congeladas": "MEMBERSHIP_FROZEN",
        "Congelaciones completadas": "MEMBERSHIP_FREEZE_COMPLETED",
        "Congelaciones canceladas": "MEMBERSHIP_FREEZE_CANCELLED",
        "Ingresos denegados por congelación": "CHECK_IN_DENIED_MEMBERSHIP_FROZEN",
        "Clientes creados": "CLIENTE_CREADO",
        "Clientes editados": "CLIENTE_EDITADO",
        "Clientes eliminados": "CLIENTE_ELIMINADO",
        "Planes": "PLAN_EDITADO",
        "Usuarios agregados": "USUARIO_AGREGADO",
        "Ventas de tienda": "VENTA_TIENDA",
        "Productos creados": "PRODUCTO_CREADO",
        "Productos editados": "PRODUCTO_EDITADO",
        "Gastos": "EGRESO_REGISTRADO",
        "Jornadas iniciadas": "JORNADA_INICIADA",
        "Jornadas finalizadas": "JORNADA_FINALIZADA",
        "Entrenadores": "ENTRENADOR_EDITADO",
    }

    ACTION_LABELS = {
        "PAGO_REGISTRADO": "Pago registrado",
        "PAGO_EDITADO": "Pago editado",
        "PAGO_ANULADO": "Pago anulado",
        "PAGO_ELIMINADO": "Pago eliminado",
        "ENTRADA_REGISTRADA": "Entrada registrada",
        "MEMBERSHIP_FROZEN": "Membresía congelada",
        "MEMBERSHIP_FREEZE_COMPLETED": "Congelación completada",
        "MEMBERSHIP_FREEZE_CANCELLED": "Congelación cancelada",
        "CHECK_IN_DENIED_MEMBERSHIP_FROZEN": "Ingreso denegado · membresía congelada",
        "CLIENTE_CREADO": "Cliente creado",
        "CLIENTE_EDITADO": "Cliente editado",
        "CLIENTE_ELIMINADO": "Cliente eliminado",
        "PLAN_CREADO": "Plan creado",
        "PLAN_EDITADO": "Plan editado",
        "PLAN_ELIMINADO": "Plan eliminado",
        "USUARIO_AGREGADO": "Usuario agregado",
        "USUARIO_EDITADO": "Usuario editado",
        "USUARIO_ELIMINADO": "Usuario eliminado",
        "VENTA_TIENDA": "Venta de tienda",
        "PRODUCTO_CREADO": "Producto creado",
        "PRODUCTO_EDITADO": "Producto editado",
        "PRODUCTO_ELIMINADO": "Producto eliminado",
        "EGRESO_REGISTRADO": "Gasto creado",
        "EGRESO_EDITADO": "Gasto editado",
        "EGRESO_ELIMINADO": "Gasto eliminado",
        "JORNADA_INICIADA": "Jornada iniciada",
        "JORNADA_FINALIZADA": "Jornada finalizada",
        "JORNADA_EDITADA": "Jornada editada",
        "JORNADA_ELIMINADA": "Jornada eliminada",
        "ENTRENADOR_CREADO": "Entrenador creado",
        "ENTRENADOR_EDITADO": "Entrenador editado",
        "ENTRENADOR_ELIMINADO": "Entrenador eliminado",
    }
    ACTION_LABELS.update(MARKETING_ACTIVITY_LABELS)

    def __init__(
        self,
        parent: tk.Misc,
        app: "GymSoftApp",
    ) -> None:
        super().__init__(parent, app)
        self._dates_initialized = False

        self.date_from = tk.StringVar(
            value=""
        )
        self.date_to = tk.StringVar(
            value=""
        )
        self.total_income = tk.StringVar(value="$ 0")
        self.total_expenses = tk.StringVar(value="$ 0")
        self.net_profit = tk.StringVar(value="$ 0")
        self.membership_income = tk.StringVar(value="$ 0")
        self.store_income = tk.StringVar(value="$ 0")
        self.payment_count = tk.StringVar(value="0")
        self.average_payment = tk.StringVar(value="$ 0")
        self.action_filter = tk.StringVar(
            value="Todos los movimientos"
        )
        self.expenses: dict[int, dict[str, Any]] = {}
        self.payment_movements: dict[str, dict[str, Any]] = {}

        self.page_header(
            "Controla ingresos, gastos, utilidad real y acciones realizadas por cada cuenta."
        )

        filters = ttk.Frame(
            self,
            padding=14,
            style="Card.TFrame",
        )
        filters.pack(fill="x", pady=(0, 14))

        ttk.Label(
            filters,
            text="Desde",
            style="Field.TLabel",
        ).pack(side="left")
        ttk.Entry(
            filters,
            textvariable=self.date_from,
            width=14,
        ).pack(side="left", padx=(8, 16))

        ttk.Label(
            filters,
            text="Hasta",
            style="Field.TLabel",
        ).pack(side="left")
        ttk.Entry(
            filters,
            textvariable=self.date_to,
            width=14,
        ).pack(side="left", padx=(8, 16))

        ttk.Button(
            filters,
            text="Este mes",
            command=lambda: self.set_period(0),
        ).pack(side="left")
        ttk.Button(
            filters,
            text="Últimos 30 días",
            command=lambda: self.set_period(30),
        ).pack(side="left", padx=(7, 0))
        ttk.Button(
            filters,
            text="Últimos 90 días",
            command=lambda: self.set_period(90),
        ).pack(side="left", padx=(7, 0))
        ttk.Button(
            filters,
            text="Actualizar",
            command=self.refresh,
            style="Primary.TButton",
        ).pack(side="right")

        cards = tk.Frame(self, bg=COLORS["background"])
        cards.pack(fill="x", pady=(0, 14))

        for column in range(5):
            cards.columnconfigure(column, weight=1)

        for column, (label, variable, color) in enumerate((
            ("INGRESOS DEL PERÍODO", self.total_income, COLORS["success"]),
            ("GASTOS", self.total_expenses, COLORS["danger"]),
            ("UTILIDAD NETA", self.net_profit, COLORS["warning"]),
            ("MEMBRESÍAS", self.membership_income, COLORS["blue"]),
            ("TIENDA", self.store_income, COLORS["purple"]),
        )):
            card = tk.Frame(
                cards,
                bg=COLORS["surface"],
                padx=20,
                pady=17,
                highlightbackground=COLORS["line"],
                highlightthickness=1,
            )
            card.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 5, 0 if column == 4 else 5),
            )
            tk.Label(
                card,
                text=label,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=(FONT_FAMILY, 8, "bold"),
            ).pack(anchor="w")
            tk.Label(
                card,
                textvariable=variable,
                bg=COLORS["surface"],
                fg=color,
                font=(FONT_FAMILY, 21, "bold"),
            ).pack(anchor="w", pady=(7, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        payments_tab = ttk.Frame(
            notebook,
            padding=14,
            style="Card.TFrame",
        )
        notebook.add(payments_tab, text="Movimientos financieros")
        payments_tab.columnconfigure(0, weight=1)
        payments_tab.rowconfigure(0, weight=1)

        self.payments_tree = CenteredTreeview(
            payments_tab,
            columns=(
                "date",
                "source",
                "party",
                "concept",
                "method",
                "amount",
                "actor",
            ),
            show="headings",
        )
        for key, label, width, anchor in (
            ("date", "Fecha y hora", 155, "center"),
            ("source", "Origen", 105, "center"),
            ("party", "Cliente / producto", 195, "w"),
            ("concept", "Concepto", 145, "center"),
            ("method", "Método", 110, "center"),
            ("amount", "Valor", 110, "e"),
            ("actor", "Registrado por", 185, "w"),
        ):
            self.payments_tree.heading(key, text=label)
            self.payments_tree.column(
                key,
                width=width,
                anchor=anchor,
            )
        self.payments_tree.grid(row=0, column=0, sticky="nsew")
        self.payments_tree.bind(
            "<<TreeviewSelect>>",
            lambda _event: self.update_payment_action_state(),
        )
        payment_actions = ttk.Frame(
            payments_tab,
            style="Card.TFrame",
        )
        payment_actions.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(12, 0),
        )
        self.payment_action_button = ttk.Button(
            payment_actions,
            text="Corregir el pago seleccionado",
            command=self.open_selected_payment,
            state="disabled",
            style="Accent.TButton",
        )
        self.payment_action_button.pack(side="left")
        ttk.Label(
            payment_actions,
            text="Selecciona un movimiento de membresía para corregirlo o anularlo.",
            style="CardMuted.TLabel",
        ).pack(side="left", padx=(12, 0))

        expenses_tab = ttk.Frame(
            notebook,
            padding=14,
            style="Card.TFrame",
        )
        notebook.add(expenses_tab, text="Gastos")
        expenses_tab.columnconfigure(0, weight=1)
        expenses_tab.rowconfigure(0, weight=1)

        self.expenses_tree = CenteredTreeview(
            expenses_tab,
            columns=(
                "date",
                "category",
                "description",
                "vendor",
                "method",
                "amount",
                "actor",
            ),
            show="headings",
        )
        for key, label, width, anchor in (
            ("date", "Fecha", 105, "center"),
            ("category", "Categoría", 145, "w"),
            ("description", "Descripción", 220, "w"),
            ("vendor", "Proveedor", 160, "w"),
            ("method", "Método", 110, "center"),
            ("amount", "Valor", 115, "e"),
            ("actor", "Registrado por", 180, "w"),
        ):
            self.expenses_tree.heading(key, text=label)
            self.expenses_tree.column(
                key,
                width=width,
                anchor=anchor,
            )
        self.expenses_tree.grid(row=0, column=0, sticky="nsew")
        self.expenses_tree.bind(
            "<Double-1>",
            lambda _event: self.edit_expense(),
        )

        expense_actions = ttk.Frame(
            expenses_tab,
            style="Card.TFrame",
        )
        expense_actions.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(
            expense_actions,
            text="＋  Crear gasto",
            command=self.new_expense,
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Button(
            expense_actions,
            text="Editar",
            command=self.edit_expense,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            expense_actions,
            text="Eliminar",
            command=self.delete_expense,
            style="Danger.TButton",
        ).pack(side="left", padx=(8, 0))

        breakdown_tab = ttk.Frame(
            notebook,
            padding=14,
            style="Card.TFrame",
        )
        notebook.add(breakdown_tab, text="Distribución")
        breakdown_tab.columnconfigure(0, weight=1)
        breakdown_tab.columnconfigure(1, weight=1)
        breakdown_tab.rowconfigure(1, weight=1)
        breakdown_tab.rowconfigure(3, weight=1)
        breakdown_tab.rowconfigure(5, weight=1)

        ttk.Label(
            breakdown_tab,
            text="Ingresos por plan",
            style="Section.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))
        ttk.Label(
            breakdown_tab,
            text="Ingresos por método de pago",
            style="Section.TLabel",
        ).grid(row=0, column=1, sticky="w", padx=(14, 0), pady=(0, 10))

        self.plan_tree = self.breakdown_tree(breakdown_tab)
        self.plan_tree.grid(row=1, column=0, sticky="nsew")
        self.method_tree = self.breakdown_tree(breakdown_tab)
        self.method_tree.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=(14, 0),
        )

        ttk.Label(
            breakdown_tab,
            text="Ventas de tienda por producto",
            style="Section.TLabel",
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(16, 10),
        )
        self.product_income_tree = self.breakdown_tree(breakdown_tab)
        self.product_income_tree.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="nsew",
        )

        ttk.Label(
            breakdown_tab,
            text="Gastos por categoría",
            style="Section.TLabel",
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(16, 10),
        )
        self.expense_category_tree = self.breakdown_tree(breakdown_tab)
        self.expense_category_tree.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="nsew",
        )

        audit_tab = ttk.Frame(
            notebook,
            padding=14,
            style="Card.TFrame",
        )
        notebook.add(audit_tab, text="Registro de actividad")
        audit_tab.columnconfigure(0, weight=1)
        audit_tab.rowconfigure(1, weight=1)

        audit_filters = ttk.Frame(
            audit_tab,
            style="Card.TFrame",
        )
        audit_filters.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(
            audit_filters,
            text="Mostrar",
            style="Field.TLabel",
        ).pack(side="left")
        action_combo = ttk.Combobox(
            audit_filters,
            textvariable=self.action_filter,
            values=list(self.ACTIONS),
            state="readonly",
            width=25,
        )
        action_combo.pack(side="left", padx=(9, 0))
        action_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.refresh_audit(),
        )
        ttk.Button(
            audit_filters,
            text="Actualizar registro",
            command=self.refresh_audit,
        ).pack(side="right")

        self.audit_tree = CenteredTreeview(
            audit_tab,
            columns=("date", "actor", "role", "action", "summary"),
            show="headings",
        )
        for key, label, width, anchor in (
            ("date", "Fecha y hora", 160, "center"),
            ("actor", "Usuario", 210, "w"),
            ("role", "Rol", 105, "center"),
            ("action", "Movimiento", 160, "center"),
            ("summary", "Detalle", 360, "w"),
        ):
            self.audit_tree.heading(key, text=label)
            self.audit_tree.column(
                key,
                width=width,
                anchor=anchor,
            )
        self.audit_tree.grid(row=1, column=0, sticky="nsew")

    @staticmethod
    def breakdown_tree(parent: tk.Misc) -> CenteredTreeview:
        tree = CenteredTreeview(
            parent,
            columns=("label", "count", "total"),
            show="headings",
        )
        for key, label, width, anchor in (
            ("label", "Categoría", 190, "w"),
            ("count", "Cantidad", 90, "center"),
            ("total", "Total", 130, "e"),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, anchor=anchor)
        return tree

    def set_period(self, days: int) -> None:
        self.load_view('period', self.db._today, lambda today: self._set_period(today, days), (days,))

    def _set_period(self, today, days):
        self._dates_initialized = True
        start = (
            today.replace(day=1)
            if days == 0
            else today - timedelta(days=days - 1)
        )
        self.date_from.set(start.strftime("%d/%m/%Y"))
        self.date_to.set(today.strftime("%d/%m/%Y"))
        self.refresh()

    @staticmethod
    def rpc_dict(response: Any) -> dict[str, Any]:
        data = response.data
        if isinstance(data, list):
            data = data[0] if data else {}
        return dict(data) if isinstance(data, dict) else {}

    @staticmethod
    def rpc_list(response: Any) -> list[dict[str, Any]]:
        data = response.data
        if not isinstance(data, list):
            return []
        if len(data) == 1 and isinstance(data[0], list):
            data = data[0]
        return [dict(item) for item in data if isinstance(item, dict)]

    def refresh(self) -> None:
        if not self._dates_initialized:
            self.load_view('server_day', self.db._today, self._initialize_dates)
            return
        try:
            date_from = date_to_iso(self.date_from.get())
            date_to = date_to_iso(self.date_to.get())
        except ValueError:
            messagebox.showwarning(
                "Fechas no válidas",
                "Usa el formato DD/MM/AAAA.",
                parent=self,
            )
            return

        gym_id = self.app.cloud.gym_id
        def load():
            response = self.app.cloud.client.rpc('get_finance_dashboard', {
                'p_gym_id': gym_id, 'p_date_from': date_from, 'p_date_to': date_to}).execute()
            return (self.rpc_dict(response), self.db.store_finance(date_from, date_to),
                    self.db.accounting_expenses(date_from, date_to))
        self.load_view('finance', load, self._render_refresh, (date_from, date_to))
        self.refresh_audit(show_error=False)

    def _initialize_dates(self, today):
        self._dates_initialized = True
        if not self.date_from.get():
            self.date_from.set(today.replace(day=1).strftime('%d/%m/%Y'))
        if not self.date_to.get():
            self.date_to.set(today.strftime('%d/%m/%Y'))
        self.refresh()

    def _render_refresh(self, data):
        membership_data, store_data, expense_data = data
        membership_total = int(
            membership_data.get("total_income") or 0
        )
        store_total = int(store_data.get("store_income") or 0)
        membership_count = int(
            membership_data.get("payment_count") or 0
        )
        store_count = int(store_data.get("sale_count") or 0)
        expense_count = int(expense_data.get("expense_count") or 0)
        income_count = membership_count + store_count
        transaction_count = income_count + expense_count
        total_income = membership_total + store_total
        total_expenses = int(
            expense_data.get("total_expenses") or 0
        )
        net_profit = total_income - total_expenses

        self.total_income.set(format_money(total_income))
        self.total_expenses.set(format_money(total_expenses))
        self.net_profit.set(format_money(net_profit))
        self.membership_income.set(format_money(membership_total))
        self.store_income.set(format_money(store_total))
        self.payment_count.set(str(transaction_count))
        self.average_payment.set(format_money(
            total_income // income_count
            if income_count
            else 0
        ))
        clear_tree(self.payments_tree)
        clear_tree(self.expenses_tree)
        expense_rows = expense_data.get("expenses", [])
        self.expenses = {
            int(item["id"]): dict(item)
            for item in expense_rows
            if isinstance(item, dict) and item.get("id") is not None
        }

        movements: list[dict[str, Any]] = []
        self.payment_movements = {}
        for payment in membership_data.get("payments", []):
            if not isinstance(payment, dict):
                continue
            movement = {
                "key": f"membership-{payment.get('id')}",
                "date": str(payment.get("paid_at", "")),
                "source": "Membresía",
                "party": payment.get("client_name", ""),
                "concept": payment.get("plan_name", "Sin plan"),
                "method": payment.get("payment_method", ""),
                "amount": payment.get("amount", 0),
                "actor_email": payment.get("actor_email", "Sistema"),
                "actor_role": payment.get("actor_role", ""),
                "client_id": payment.get("client_id"),
            }
            movements.append(movement)
            self.payment_movements[str(movement["key"])] = movement

        for sale in store_data.get("sales", []):
            if not isinstance(sale, dict):
                continue
            quantity = int(sale.get("quantity") or 0)
            movements.append({
                "key": f"store-{sale.get('id')}",
                "date": str(sale.get("sold_at", "")),
                "source": "Tienda",
                "party": sale.get("product_name", ""),
                "concept": f"{quantity} unidad(es)",
                "method": sale.get("payment_method", ""),
                "amount": sale.get("total_amount", 0),
                "actor_email": sale.get("actor_email", "Sistema"),
                "actor_role": sale.get("actor_role", ""),
            })

        for expense in self.expenses.values():
            actor = str(expense.get("actor_email", "Sistema"))
            movements.append({
                "key": f"expense-{expense.get('id')}",
                "date": str(expense.get("created_at", "")),
                "source": "Gasto",
                "party": expense.get("vendor", "") or "—",
                "concept": expense.get("description", ""),
                "method": expense.get("payment_method", ""),
                "amount": -int(expense.get("amount") or 0),
                "actor_email": actor,
                "actor_role": expense.get("actor_role", "admin"),
            })

            self.expenses_tree.insert(
                "",
                "end",
                iid=str(expense["id"]),
                values=(
                    date_to_display(expense.get("expense_date")),
                    expense.get("category", ""),
                    expense.get("description", ""),
                    expense.get("vendor", "") or "—",
                    expense.get("payment_method", ""),
                    format_money(expense.get("amount", 0)),
                    actor,
                ),
            )

        movements.sort(
            key=lambda item: str(item.get("date", "")),
            reverse=True,
        )

        for movement in movements:
            role = str(movement.get("actor_role", ""))
            actor = str(movement.get("actor_email", "Sistema"))
            if role == "receptionist":
                actor += " · Recepción"
            elif role == "admin":
                actor += " · Admin"
            self.payments_tree.insert(
                "",
                "end",
                iid=str(movement.get("key")),
                values=(
                    display_timestamp(movement.get("date", ""), timezone_for(self.db)),
                    movement.get("source", ""),
                    movement.get("party", ""),
                    movement.get("concept", ""),
                    movement.get("method", ""),
                    format_money(movement.get("amount", 0)),
                    actor,
                ),
            )

        self.update_payment_action_state()

        self.fill_breakdown(
            self.plan_tree,
            membership_data.get("by_plan", []),
        )
        self.fill_breakdown(
            self.method_tree,
            self.merge_breakdowns(
                membership_data.get("by_method", []),
                store_data.get("by_method", []),
            ),
        )
        self.fill_breakdown(
            self.product_income_tree,
            store_data.get("by_product", []),
        )
        self.fill_breakdown(
            self.expense_category_tree,
            expense_data.get("by_category", []),
        )

    def update_payment_action_state(self) -> None:
        if not hasattr(self, "payment_action_button"):
            return
        selected = self.payments_tree.selection()
        key = selected[0] if selected else ""
        state = "normal" if key in self.payment_movements else "disabled"
        self.payment_action_button.configure(state=state)

    def open_selected_payment(self) -> None:
        selected = self.payments_tree.selection()
        if not selected:
            return
        movement = self.payment_movements.get(selected[0])
        if not movement or movement.get("client_id") is None:
            messagebox.showinfo(
                "Selecciona un pago",
                "Selecciona un movimiento de membresía, no una venta o un gasto.",
                parent=self,
            )
            return
        try:
            client_id = int(movement["client_id"])
            client_name = str(movement.get("party") or "Cliente")
            open_payment_manager(
                self,
                self.db,
                client_id,
                client_name,
                BaseDialog,
                format_money,
                date_to_display,
                self.refresh,
                money_hidden=lambda: bool(globals().get("MONEY_VALUES_HIDDEN", False)),
            )
        except Exception as error:
            messagebox.showerror(
                "No se pudo abrir la corrección de pagos",
                str(error),
                parent=self,
            )

    def new_expense(self) -> None:
        dialog = ExpenseDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return

        try:
            self.db.save_expense(dialog.result)
        except Exception as error:
            messagebox.showerror(
                "No se pudo crear el gasto",
                str(error),
                parent=self,
            )
            return

        self.app.refresh_all(except_page=self)

    def edit_expense(self) -> None:
        expense_id = selected_id(self.expenses_tree)
        if expense_id is None:
            messagebox.showinfo(
                "Selecciona un gasto",
                "Selecciona primero el movimiento que deseas editar.",
                parent=self,
            )
            return

        expense = self.expenses.get(expense_id)
        if not expense:
            return

        dialog = ExpenseDialog(self, expense)
        self.wait_window(dialog)
        if not dialog.result:
            return

        try:
            self.db.save_expense(dialog.result, expense_id)
        except Exception as error:
            messagebox.showerror(
                "No se pudo editar el gasto",
                str(error),
                parent=self,
            )
            return

        self.app.refresh_all(except_page=self)

    def delete_expense(self) -> None:
        expense_id = selected_id(self.expenses_tree)
        if expense_id is None:
            messagebox.showinfo(
                "Selecciona un gasto",
                "Selecciona primero el movimiento que deseas eliminar.",
                parent=self,
            )
            return

        expense = self.expenses.get(expense_id, {})
        if not messagebox.askyesno(
            "Eliminar gasto",
            (
                "¿Deseas eliminar este gasto?\n\n"
                f"{expense.get('description', '')} · "
                f"{format_money(expense.get('amount', 0))}"
            ),
            parent=self,
        ):
            return

        try:
            self.db.delete_expense(expense_id)
        except Exception as error:
            messagebox.showerror(
                "No se pudo eliminar el gasto",
                str(error),
                parent=self,
            )
            return

        self.app.refresh_all(except_page=self)

    @staticmethod
    def merge_breakdowns(*groups: Any) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for rows in groups:
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                label = str(row.get("label", "Sin definir"))
                target = merged.setdefault(
                    label,
                    {"label": label, "count": 0, "total": 0},
                )
                target["count"] += int(row.get("count") or 0)
                target["total"] += int(row.get("total") or 0)
        return sorted(
            merged.values(),
            key=lambda item: (-int(item["total"]), str(item["label"])),
        )

    @staticmethod
    def fill_breakdown(
        tree: CenteredTreeview,
        rows: Any,
    ) -> None:
        clear_tree(tree)
        if not isinstance(rows, list):
            return
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    row.get("label", "Sin definir"),
                    int(row.get("count") or 0),
                    format_money(row.get("total", 0)),
                ),
            )

    def refresh_audit(self, show_error: bool = True) -> None:
        action = self.ACTIONS.get(self.action_filter.get(), '')
        gym_id = self.app.cloud.gym_id
        def load():
            return self.rpc_list(self.app.cloud.client.rpc('get_audit_logs', {
                'p_gym_id': gym_id, 'p_limit': 300, 'p_action': action}).execute())
        self.load_view('audit', load, self._render_refresh_audit, (action,))

    def _render_refresh_audit(self, rows):
        clear_tree(self.audit_tree)
        for row in rows:
            action_code = str(row.get("action", ""))
            role = str(row.get("actor_role", ""))
            role_label = {
                "admin": "Admin",
                "receptionist": "Recepción",
                "system": "Sistema",
            }.get(role, role or "Usuario")
            self.audit_tree.insert(
                "",
                "end",
                iid=str(row.get("id")),
                values=(
                    row.get("created_at_local") or display_timestamp(row.get("occurred_at") or row.get("created_at", ""), row.get("timezone") or timezone_for(self.db)),
                    row.get("actor_email", "Sistema"),
                    role_label,
                    self.ACTION_LABELS.get(action_code, action_code),
                    "Detalle oculto" if MONEY_VALUES_HIDDEN else row.get("summary", ""),
                ),
            )


class ClientsPage(BasePage):
    title = "Clientes y Pagos"

    def __init__(self, parent: tk.Misc, app: "GymSoftApp"):
        super().__init__(parent, app)
        self.page_header(
            "Administra datos personales, planes, pagos y vencimientos.",
            [
                ("🎂  Avisos y cumpleaños", self.show_notifications, "TButton"),
                ("＋  Nuevo cliente", self.new_client, "Primary.TButton"),
            ],
        )
        toolbar = ttk.Frame(self, style="Page.TFrame")
        toolbar.pack(fill="x", pady=(0, 10))
        self.search = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.search, width=36)
        search_entry.pack(side="left")
        search_entry.bind("<Return>", lambda _event: self.refresh())
        ttk.Button(toolbar, text="Buscar", command=self.refresh).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Limpiar", command=self.clear_search).pack(side="left", padx=(8, 0))

        card = ttk.Frame(self, padding=14, style="Card.TFrame")
        card.pack(fill="both", expand=True)
        self.tree = CenteredTreeview(
            card,
            columns=("document", "name", "phone", "birthday", "status", "end"),
            show="headings",
            selectmode="browse",
        )
        headings = {
            "document": "Documento",
            "name": "Nombre",
            "phone": "Teléfono",
            "birthday": "Cumpleaños",
            "status": "Mensualidad",
            "end": "Vencimiento",
        }
        widths = {
            "document": 125,
            "name": 245,
            "phone": 135,
            "birthday": 115,
            "status": 115,
            "end": 110,
        }
        for column in headings:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("valid", foreground=COLORS["success"])
        self.tree.tag_configure("expired", foreground=COLORS["danger"])
        self.tree.tag_configure("inactive", foreground=COLORS["muted"])
        self.tree.bind("<Double-1>", lambda _event: self.edit_client())

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="✎  Editar cliente", command=self.edit_client).pack(side="left")
        ttk.Button(actions, text="$  Registrar pago", command=self.add_membership, style="Primary.TButton").pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="✎  Consultar y editar pagos", command=self.show_memberships).pack(side="left", padx=(8, 0))

        bind_live_search(self, self.search, self.refresh)


    def clear_search(self) -> None:
        self.search.set("")
        self.refresh()

    def refresh(self) -> None:
        term = self.search.get()
        self.load_view("refresh", lambda: self.db.list_clients(term), self._render_refresh, (term,))

    def _render_refresh(self, rows):
        clear_tree(self.tree)
        for client in rows:
            status = client["membership_status"]
            tag = "valid" if status == "AL DÍA" else "inactive" if status == "INACTIVO" else "expired"
            self.tree.insert(
                "",
                "end",
                iid=str(client["id"]),
                values=(
                    client["document"],
                    f"{client['first_name']} {client['last_name']}",
                    client["phone"],
                    date_to_display(client.get("birthdate")) or "—",
                    status,
                    date_to_display(
                        client["membership_end"]
                    ) or "—",
                ),
                tags=(tag,),
            )

    def new_client(self) -> None:
        dialog = ClientDialog(self)
        self.wait_window(dialog)
        if getattr(dialog, "client_saved", False):
            self.app.refresh_all()
            return
        if dialog.result:
            try:
                self.db.save_client(dialog.result)
            except sqlite3.IntegrityError:
                messagebox.showerror("Documento repetido", "Ya existe un cliente con ese documento.", parent=self)
                return
            except Exception as error:
                messagebox.showerror(
                    "No se pudo guardar el cliente",
                    str(error),
                    parent=self,
                )
                return
            self.app.refresh_all()

    def edit_client(self) -> None:
        client_id = selected_id(self.tree)
        if not client_id:
            messagebox.showinfo("Selecciona un registro", "Selecciona un cliente.", parent=self)
            return
        dialog = ClientDialog(self, self.db.get_client(client_id))
        self.wait_window(dialog)
        if dialog.delete_requested:
            self.db.delete_client(client_id)
            self.app.refresh_all()

            messagebox.showinfo(
                "Cliente eliminado",
                "El cliente fue eliminado correctamente.",
                parent=self,
            )
            return
        if getattr(dialog, "client_saved", False):
            self.app.refresh_all()
            return
        if dialog.result:
            try:
                self.db.save_client(dialog.result, client_id)
            except sqlite3.IntegrityError:
                messagebox.showerror("Documento repetido", "Ya existe un cliente con ese documento.", parent=self)
                return
            except Exception as error:
                messagebox.showerror(
                    "No se pudo guardar el cliente",
                    str(error),
                    parent=self,
                )
                return
            self.app.refresh_all()

    def add_membership(self) -> None:
        client_id = selected_id(self.tree)
        if not client_id:
            messagebox.showinfo("Selecciona un registro", "Selecciona el cliente que realizó el pago.", parent=self)
            return
        try:
            client = self.db.get_client(client_id)
            if not client:
                raise ValueError('El cliente ya no está disponible. Actualiza la lista.')
            dialog = MembershipDialog(
                self, self.db, f"{client['first_name']} {client['last_name']}",
                on_submit=lambda payload: self.db.add_membership(client_id=client_id, **payload),
            )
        except Exception as error:
            messagebox.showerror('No se pudo abrir el registro de pago', str(error), parent=self)
            return
        self.wait_window(dialog)
        if dialog.result:
            self.app.refresh_all()
            messagebox.showinfo("Pago registrado", "El pago quedó registrado correctamente.", parent=self)

    def show_memberships(self) -> None:
        client_id = selected_id(self.tree)
        if not client_id:
            messagebox.showinfo("Selecciona un registro", "Selecciona un cliente.", parent=self)
            return
        try:
            client = self.db.get_client(client_id)
            if not client:
                raise ValueError("Cliente no encontrado.")
            open_payment_manager(
                self, self.db, client_id,
                f"{client['first_name']} {client['last_name']}",
                BaseDialog, format_money, date_to_display, self.refresh,
                money_hidden=lambda: bool(globals().get("MONEY_VALUES_HIDDEN", False)),
            )
        except Exception as error:
            messagebox.showerror("No se pudieron abrir los pagos", str(error), parent=self)

    def show_notifications(self) -> None:
        try:
            today = self.db._today()
        except Exception:
            raise ValueError("No se pudo consultar la fecha del gimnasio. Reintenta con conexión al servidor.")

        clients = self.db.list_clients()
        client_by_id = {
            int(client["id"]): client
            for client in clients
        }
        birthdays: list[tuple[dict[str, Any], int]] = []
        expiring: list[tuple[dict[str, Any], int]] = []
        expired: list[tuple[dict[str, Any], int]] = []

        for client in clients:
            days = next_birthday_days(client.get("birthdate"), today)
            if days is not None and days <= 30:
                birthdays.append((client, days))

            end_text = str(client.get("membership_end") or "")[:10]
            if not end_text or not client.get("active", True):
                continue
            try:
                membership_end = date.fromisoformat(end_text)
            except ValueError:
                continue

            remaining = (membership_end - today).days
            if 0 <= remaining <= 5:
                expiring.append((client, remaining))
            elif remaining < 0:
                expired.append((client, remaining))

        birthdays.sort(key=lambda item: (item[1], item[0].get("first_name", "")))
        expiring.sort(key=lambda item: (item[1], item[0].get("first_name", "")))
        expired.sort(key=lambda item: (-item[1], item[0].get("first_name", "")))

        window = BaseDialog(self, "Avisos de clientes", 980, 620)
        notebook = ttk.Notebook(window.body)
        notebook.pack(fill="both", expand=True)
        trees: list[CenteredTreeview] = []

        def add_tab(
            title: str,
            rows: list[tuple[dict[str, Any], int]],
            mode: str,
        ) -> CenteredTreeview:
            tab = ttk.Frame(notebook, padding=12, style="Card.TFrame")
            notebook.add(tab, text=f"{title} ({len(rows)})")
            tree = CenteredTreeview(
                tab,
                columns=("name", "phone", "date", "detail", "status"),
                show="headings",
            )
            for key, label, width in (
                ("name", "Cliente", 245),
                ("phone", "Teléfono", 145),
                ("date", "Fecha", 120),
                ("detail", "Aviso", 180),
                ("status", "Membresía", 120),
            ):
                tree.heading(key, text=label)
                tree.column(key, width=width)
            tree.pack(fill="both", expand=True)

            for client, days in rows:
                name = (
                    f"{client.get('first_name', '')} "
                    f"{client.get('last_name', '')}"
                ).strip()
                if mode == "birthday":
                    date_text = date_to_display(client.get("birthdate"))
                    detail = "HOY 🎂" if days == 0 else f"En {days} días"
                else:
                    date_text = date_to_display(client.get("membership_end"))
                    if mode == "expiring":
                        detail = "Vence hoy" if days == 0 else f"Faltan {days} días"
                    else:
                        detail = f"Vencida hace {abs(days)} días"

                tree.insert(
                    "",
                    "end",
                    iid=str(client["id"]),
                    values=(
                        name,
                        client.get("phone", "") or "—",
                        date_text,
                        detail,
                        client.get("membership_status", ""),
                    ),
                )
            trees.append(tree)
            return tree

        add_tab("Cumpleaños próximos", birthdays, "birthday")
        add_tab("Vencen en 5 días", expiring, "expiring")
        add_tab("Membresías vencidas", expired, "expired")

        def copy_message() -> None:
            index = notebook.index(notebook.select())
            tree = trees[index]
            client_id = selected_id(tree)
            if client_id is None:
                messagebox.showinfo(
                    "Selecciona un cliente",
                    "Selecciona primero una persona de la lista.",
                    parent=window,
                )
                return

            client = client_by_id[client_id]
            first_name = str(client.get("first_name") or "").strip()
            if index == 0:
                message = (
                    f"¡Hola {first_name}! 🎉 Desde GymSoft te deseamos "
                    "un feliz cumpleaños. ¡Que tengas un excelente día!"
                )
            elif index == 1:
                message = (
                    f"Hola {first_name}, te recordamos que tu membresía "
                    f"de GymSoft vence el "
                    f"{date_to_display(client.get('membership_end'))}."
                )
            else:
                message = (
                    f"Hola {first_name}, tu membresía de GymSoft venció "
                    f"el {date_to_display(client.get('membership_end'))}. "
                    "Puedes renovarla en recepción."
                )

            window.clipboard_clear()
            window.clipboard_append(message)
            messagebox.showinfo(
                "Mensaje copiado",
                "El mensaje quedó listo para pegarlo en WhatsApp.",
                parent=window,
            )

        actions = ttk.Frame(window.body, style="Surface.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(
            actions,
            text="Copiar mensaje",
            command=copy_message,
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Cerrar",
            command=window.destroy,
        ).pack(side="right")
        center_window(window, self)

    def manage_plans(self) -> None:
        window = BaseDialog(self, "Planes de membresía", 620, 430)
        tree = CenteredTreeview(window.body, columns=("name", "days", "price"), show="headings")
        for key, label, width in [("name", "Plan", 220), ("days", "Días", 90), ("price", "Precio", 150)]:
            tree.heading(key, text=label)
            tree.column(key, width=width)
        tree.pack(fill="both", expand=True)

        def refresh_plans() -> None:
            clear_tree(tree)
            for plan in self.db.list_plans(active_only=False):
                tree.insert("", "end", iid=str(plan["id"]), values=(plan["name"], plan_duration(plan), format_money(plan["price"])))

        def add_plan() -> None:
            dialog = PlanDialog(window)
            window.wait_window(dialog)
            if dialog.result:
                try:
                    self.db.add_plan(*dialog.result)
                except sqlite3.IntegrityError:
                    messagebox.showerror("Plan repetido", "Ya existe un plan con ese nombre.", parent=window)
                    return
                refresh_plans()

        actions = ttk.Frame(window.body, style="Surface.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        ttk.Button(actions, text="Nuevo plan", command=add_plan, style="Primary.TButton").pack(side="left")
        ttk.Button(actions, text="Cerrar", command=window.destroy).pack(side="right")
        refresh_plans()
        center_window(window, self)


class StaffPage(BasePage):
    title = "Personal"

    def __init__(self, parent: tk.Misc, app: "GymSoftApp") -> None:
        super().__init__(parent, app)
        self._dates_initialized = False

        self.date_from = tk.StringVar(
            value=""
        )
        self.date_to = tk.StringVar(value="")
        self.active_staff = tk.StringVar(value="0")
        self.working_now = tk.StringVar(value="0")
        self.total_hours = tk.StringVar(value="0 h")
        self.estimated_payroll = tk.StringVar(value="$ 0")
        self.workers: dict[int, dict[str, Any]] = {}

        self.page_header(
            "Administra trabajadores, jornadas y pago estimado por horas.",
            [("＋  Nuevo entrenador", self.new_trainer, "Primary.TButton")],
        )

        filters = ttk.Frame(self, padding=14, style="Card.TFrame")
        filters.pack(fill="x", pady=(0, 14))
        ttk.Label(filters, text="Desde", style="Field.TLabel").pack(side="left")
        ttk.Entry(
            filters,
            textvariable=self.date_from,
            width=14,
        ).pack(side="left", padx=(8, 16))
        ttk.Label(filters, text="Hasta", style="Field.TLabel").pack(side="left")
        ttk.Entry(
            filters,
            textvariable=self.date_to,
            width=14,
        ).pack(side="left", padx=(8, 16))
        ttk.Button(
            filters,
            text="Este mes",
            command=self.set_current_month,
        ).pack(side="left")
        ttk.Button(
            filters,
            text="Actualizar",
            command=self.refresh,
            style="Primary.TButton",
        ).pack(side="right")

        cards = tk.Frame(self, bg=COLORS["background"])
        cards.pack(fill="x", pady=(0, 14))
        for column in range(4):
            cards.columnconfigure(column, weight=1)
        for column, (label, variable, color) in enumerate((
            ("PERSONAL ACTIVO", self.active_staff, COLORS["blue"]),
            ("TRABAJANDO AHORA", self.working_now, COLORS["success"]),
            ("HORAS DEL PERÍODO", self.total_hours, COLORS["purple"]),
            ("PAGO ESTIMADO", self.estimated_payroll, COLORS["warning"]),
        )):
            card = tk.Frame(
                cards,
                bg=COLORS["surface"],
                padx=18,
                pady=15,
                highlightbackground=COLORS["line"],
                highlightthickness=1,
            )
            card.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 5, 0 if column == 3 else 5),
            )
            tk.Label(
                card,
                text=label,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=(FONT_FAMILY, 8, "bold"),
            ).pack(anchor="w")
            tk.Label(
                card,
                textvariable=variable,
                bg=COLORS["surface"],
                fg=color,
                font=(FONT_FAMILY, 20, "bold"),
            ).pack(anchor="w", pady=(6, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        staff_tab = ttk.Frame(notebook, padding=14, style="Card.TFrame")
        notebook.add(staff_tab, text="Personal")
        staff_tab.columnconfigure(0, weight=1)
        staff_tab.rowconfigure(0, weight=1)
        self.staff_tree = CenteredTreeview(
            staff_tab,
            columns=(
                "name",
                "specialty",
                "rate",
                "status",
                "checkin",
                "hours",
                "pay",
            ),
            show="headings",
        )
        for key, label, width, anchor in (
            ("name", "Entrenador", 220, "w"),
            ("specialty", "Especialidad", 175, "w"),
            ("rate", "Valor/hora", 105, "e"),
            ("status", "Jornada", 95, "center"),
            ("checkin", "Entrada actual", 145, "center"),
            ("hours", "Horas", 105, "center"),
            ("pay", "Pago estimado", 125, "e"),
        ):
            self.staff_tree.heading(key, text=label)
            self.staff_tree.column(key, width=width, anchor=anchor)
        self.staff_tree.grid(row=0, column=0, sticky="nsew")
        self.staff_tree.bind("<Double-1>", lambda _event: self.edit_trainer())

        actions = ttk.Frame(staff_tab, style="Card.TFrame")
        actions.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(
            actions,
            text="Editar",
            command=self.edit_trainer,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Iniciar/finalizar jornada",
            command=self.toggle_shift,
            style="Primary.TButton",
        ).pack(side="left", padx=(8, 0))

        shifts_tab = ttk.Frame(notebook, padding=14, style="Card.TFrame")
        notebook.add(shifts_tab, text="Historial de jornadas")
        shifts_tab.columnconfigure(0, weight=1)
        shifts_tab.rowconfigure(0, weight=1)
        self.shifts_tree = CenteredTreeview(
            shifts_tab,
            columns=("name", "in", "out", "duration", "rate", "pay"),
            show="headings",
        )
        for key, label, width, anchor in (
            ("name", "Entrenador", 210, "w"),
            ("in", "Entrada", 165, "center"),
            ("out", "Salida", 165, "center"),
            ("duration", "Tiempo", 125, "center"),
            ("rate", "Valor/hora", 115, "e"),
            ("pay", "Pago estimado", 130, "e"),
        ):
            self.shifts_tree.heading(key, text=label)
            self.shifts_tree.column(key, width=width, anchor=anchor)
        self.shifts_tree.grid(row=0, column=0, sticky="nsew")

        self.after(30000, self.refresh_running_clock)

    def set_current_month(self) -> None:
        try:
            today = self.db._today()
        except Exception:
            raise ValueError("No se pudo consultar la fecha del gimnasio. Reintenta con conexión al servidor.")
        self.date_from.set(today.replace(day=1).strftime("%d/%m/%Y"))
        self.date_to.set(today.strftime("%d/%m/%Y"))
        self.refresh()

    def refresh_running_clock(self) -> None:
        try:
            if self.app.current_page == "staff":
                self.refresh(show_error=False)
            self.after(30000, self.refresh_running_clock)
        except tk.TclError:
            return

    def refresh(self, show_error: bool = True) -> None:
        if not self._dates_initialized:
            self.load_view('server_day', self.db._today, self._initialize_dates)
            return
        try:
            date_from = date_to_iso(self.date_from.get())
            date_to = date_to_iso(self.date_to.get())
        except Exception as error:
            if show_error:
                messagebox.showerror(
                    "No se pudo cargar el personal",
                    str(error),
                    parent=self,
                )
            return

        self.load_view('staff', lambda: self.db.staff_dashboard(date_from, date_to),
                       self._render_refresh, (date_from, date_to))

    def _initialize_dates(self, today):
        self._dates_initialized = True
        if not self.date_from.get():
            self.date_from.set(today.replace(day=1).strftime('%d/%m/%Y'))
        if not self.date_to.get():
            self.date_to.set(today.strftime('%d/%m/%Y'))
        self.refresh()

    def _render_refresh(self, data):
        workers = data.get("workers", [])
        self.workers = {
            int(worker["id"]): dict(worker)
            for worker in workers
            if isinstance(worker, dict) and worker.get("id") is not None
        }
        self.active_staff.set(str(int(data.get("active_staff") or 0)))
        self.working_now.set(str(int(data.get("working_now") or 0)))
        self.total_hours.set(format_duration(data.get("total_seconds", 0)))
        self.estimated_payroll.set(
            format_money(data.get("estimated_payroll", 0))
        )

        clear_tree(self.staff_tree)
        for worker in self.workers.values():
            working = bool(worker.get("current_check_in"))
            self.staff_tree.insert(
                "",
                "end",
                iid=str(worker["id"]),
                values=(
                    worker.get("name", ""),
                    worker.get("specialty", ""),
                    format_money(worker.get("hourly_rate", 0)),
                    "TRABAJANDO" if working else "FUERA",
                    display_timestamp(worker.get("current_check_in") or "—", timezone_for(self.db)),
                    format_duration(worker.get("period_seconds", 0)),
                    format_money(worker.get("estimated_pay", 0)),
                ),
                tags=("working" if working else "inactive",),
            )
        self.staff_tree.tag_configure("working", foreground=COLORS["success"])
        self.staff_tree.tag_configure("inactive", foreground=COLORS["muted"])

        clear_tree(self.shifts_tree)
        for shift in data.get("shifts", []):
            if not isinstance(shift, dict):
                continue
            self.shifts_tree.insert(
                "",
                "end",
                iid=str(shift.get("id")),
                values=(
                    shift.get("trainer_name", ""),
                    display_timestamp(shift.get("check_in_at", ""), timezone_for(self.db)),
                    display_timestamp(shift.get("check_out_at") or "EN CURSO", timezone_for(self.db)),
                    format_duration(shift.get("duration_seconds", 0)),
                    format_money(shift.get("hourly_rate", 0)),
                    format_money(shift.get("estimated_pay", 0)),
                ),
            )

    def selected_worker(self) -> dict[str, Any] | None:
        trainer_id = selected_id(self.staff_tree)
        if trainer_id is None:
            messagebox.showinfo(
                "Selecciona un trabajador",
                "Selecciona primero un entrenador.",
                parent=self,
            )
            return None
        return self.workers.get(trainer_id)

    def new_trainer(self) -> None:
        dialog = TrainerDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            try:
                self.db.save_trainer(dialog.result)
            except Exception as error:
                messagebox.showerror(
                    "No se pudo guardar",
                    str(error),
                    parent=self,
                )
                return
            self.app.refresh_all(except_page=self)

    def edit_trainer(self) -> None:
        worker = self.selected_worker()
        if not worker:
            return
        dialog = TrainerDialog(self, worker)
        self.wait_window(dialog)
        if dialog.result:
            try:
                self.db.save_trainer(dialog.result, int(worker["id"]))
            except Exception as error:
                messagebox.showerror(
                    "No se pudo actualizar",
                    str(error),
                    parent=self,
                )
                return
            self.app.refresh_all(except_page=self)

    def toggle_shift(self) -> None:
        worker = self.selected_worker()
        if not worker:
            return
        working = bool(worker.get("current_check_in"))
        action = "OUT" if working else "IN"
        action_label = "finalizar" if working else "iniciar"
        if not messagebox.askyesno(
            "Control de jornada",
            f"¿Deseas {action_label} la jornada de {worker.get('name', '')}?",
            parent=self,
        ):
            return
        try:
            self.db.staff_clock(int(worker["id"]), action)
        except Exception as error:
            messagebox.showerror(
                "No se pudo actualizar la jornada",
                str(error),
                parent=self,
            )
            return
        self.app.refresh_all(except_page=self)


class ShopPage(BasePage):
    title = "Tienda"

    def __init__(self, parent: tk.Misc, app: "GymSoftApp"):
        super().__init__(parent, app)
        self.products: dict[int, dict[str, Any]] = {}
        self.search = tk.StringVar()
        self.product_count = tk.StringVar(value="0")
        self.stock_units = tk.StringVar(value="0")
        self.low_stock_count = tk.StringVar(value="0")
        self.page_header(
            "Administra productos, precios, inventario y ventas registradas.",
            [("＋  Nuevo producto", self.new_product, "Primary.TButton")],
        )

        summary = tk.Frame(self, bg=COLORS["background"])
        summary.pack(fill="x", pady=(0, 14))
        for column in range(3):
            summary.columnconfigure(column, weight=1)
        for column, (label, variable, color) in enumerate((
            ("PRODUCTOS ACTIVOS", self.product_count, COLORS["blue"]),
            ("UNIDADES EN INVENTARIO", self.stock_units, COLORS["success"]),
            ("STOCK BAJO O AGOTADO", self.low_stock_count, COLORS["warning"]),
        )):
            card = tk.Frame(
                summary,
                bg=COLORS["surface"],
                padx=18,
                pady=14,
                highlightbackground=COLORS["line"],
                highlightthickness=1,
            )
            card.grid(
                row=0,
                column=column,
                sticky="ew",
                padx=(0 if column == 0 else 6, 0 if column == 2 else 6),
            )
            tk.Label(
                card,
                text=label,
                bg=COLORS["surface"],
                fg=COLORS["muted"],
                font=(FONT_FAMILY, 8, "bold"),
            ).pack(anchor="w")
            tk.Label(
                card,
                textvariable=variable,
                bg=COLORS["surface"],
                fg=color,
                font=(FONT_FAMILY, 20, "bold"),
            ).pack(anchor="w", pady=(5, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        products_tab = ttk.Frame(
            notebook,
            padding=14,
            style="Card.TFrame",
        )
        notebook.add(products_tab, text="Productos e inventario")
        products_tab.columnconfigure(0, weight=1)
        products_tab.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(products_tab, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Entry(
            toolbar,
            textvariable=self.search,
            width=34,
        ).pack(side="left")
        ttk.Button(
            toolbar,
            text="Buscar",
            command=self.refresh_products,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            toolbar,
            text="Limpiar",
            command=self.clear_search,
        ).pack(side="left", padx=(8, 0))

        self.products_tree = CenteredTreeview(
            products_tab,
            columns=("sku", "name", "price", "stock", "alert", "status"),
            show="headings",
            selectmode="browse",
        )
        for key, label, width, anchor in (
            ("sku", "Código", 110, "center"),
            ("name", "Producto", 260, "w"),
            ("price", "Precio", 130, "e"),
            ("stock", "Existencias", 100, "center"),
            ("alert", "Aviso", 90, "center"),
            ("status", "Estado", 135, "center"),
        ):
            self.products_tree.heading(key, text=label)
            self.products_tree.column(key, width=width, anchor=anchor)
        self.products_tree.grid(row=1, column=0, sticky="nsew")
        self.products_tree.bind("<Double-1>", lambda _event: self.edit_product())
        self.products_tree.tag_configure("ok", foreground=COLORS["success"])
        self.products_tree.tag_configure("low", foreground=COLORS["warning"])
        self.products_tree.tag_configure("off", foreground=COLORS["muted"])

        actions = ttk.Frame(products_tab, style="Card.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(
            actions,
            text="Editar producto",
            command=self.edit_product,
        ).pack(side="left")
        ttk.Button(
            actions,
            text="Activar/desactivar",
            command=self.toggle_product,
        ).pack(side="left", padx=(8, 0))

        sales_tab = ttk.Frame(
            notebook,
            padding=14,
            style="Card.TFrame",
        )
        notebook.add(sales_tab, text="Ventas recientes")
        sales_tab.columnconfigure(0, weight=1)
        sales_tab.rowconfigure(0, weight=1)
        self.sales_tree = CenteredTreeview(
            sales_tab,
            columns=(
                "date",
                "product",
                "quantity",
                "unit",
                "total",
                "method",
                "actor",
            ),
            show="headings",
        )
        for key, label, width, anchor in (
            ("date", "Fecha y hora", 150, "center"),
            ("product", "Producto", 210, "w"),
            ("quantity", "Cantidad", 80, "center"),
            ("unit", "Precio", 105, "e"),
            ("total", "Total", 115, "e"),
            ("method", "Método", 115, "center"),
            ("actor", "Registrada por", 200, "w"),
        ):
            self.sales_tree.heading(key, text=label)
            self.sales_tree.column(key, width=width, anchor=anchor)
        self.sales_tree.grid(row=0, column=0, sticky="nsew")
        bind_live_search(self, self.search, self.refresh_products)

    def clear_search(self) -> None:
        self.search.set("")
        self.refresh_products()

    def selected_product(self) -> dict[str, Any] | None:
        product_id = selected_id(self.products_tree)
        if product_id is None:
            messagebox.showinfo(
                "Selecciona un registro",
                "Selecciona primero un producto.",
                parent=self,
            )
            return None
        return self.products.get(product_id)

    def new_product(self) -> None:
        dialog = ProductDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            self.db.save_store_product(dialog.result)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Producto repetido",
                "Ya existe un producto con ese nombre o código.",
                parent=self,
            )
            return
        except Exception as error:
            messagebox.showerror(
                "No se pudo guardar",
                str(error),
                parent=self,
            )
            return
        self.refresh()

    def edit_product(self) -> None:
        product = self.selected_product()
        if not product:
            return
        dialog = ProductDialog(self, product)
        self.wait_window(dialog)
        if not dialog.result:
            return
        try:
            self.db.save_store_product(
                dialog.result,
                int(product["id"]),
            )
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Producto repetido",
                "Ya existe otro producto con ese nombre o código.",
                parent=self,
            )
            return
        except Exception as error:
            messagebox.showerror(
                "No se pudo guardar",
                str(error),
                parent=self,
            )
            return
        self.refresh()

    def toggle_product(self) -> None:
        product = self.selected_product()
        if not product:
            return
        data = dict(product)
        data["active"] = not bool(product.get("active", True))
        try:
            self.db.save_store_product(data, int(product["id"]))
        except Exception as error:
            messagebox.showerror(
                "No se pudo cambiar el estado",
                str(error),
                parent=self,
            )
            return
        self.refresh()

    def refresh_products(self) -> None:
        term = self.search.get()
        self.load_view("refresh_products", lambda: self.db.list_store_products(term, True), self._render_refresh_products, (term,))

    def _render_refresh_products(self, rows):
        self.products = {int(row["id"]): row for row in rows}
        clear_tree(self.products_tree)
        active_rows = [row for row in rows if bool(row.get("active", True))]
        self.product_count.set(str(len(active_rows)))
        self.stock_units.set(str(sum(
            int(row.get("stock_quantity") or 0)
            for row in active_rows
        )))
        self.low_stock_count.set(str(sum(
            1
            for row in active_rows
            if int(row.get("stock_quantity") or 0)
            <= int(row.get("low_stock_threshold") or 0)
        )))

        for row in rows:
            active = bool(row.get("active", True))
            stock = int(row.get("stock_quantity") or 0)
            threshold = int(row.get("low_stock_threshold") or 0)
            tag = "off" if not active else "low" if stock <= threshold else "ok"
            self.products_tree.insert(
                "",
                "end",
                iid=str(row["id"]),
                values=(
                    row.get("sku") or "—",
                    row.get("name", ""),
                    format_money(row.get("sale_price", 0)),
                    stock,
                    threshold,
                    row.get("stock_status", ""),
                ),
                tags=(tag,),
            )

    def refresh_sales(self) -> None:
        self.load_view("refresh_sales", lambda: self.db.list_store_sales(150), self._render_refresh_sales, ())

    def _render_refresh_sales(self, rows):
        clear_tree(self.sales_tree)
        for sale in rows:
            role = str(sale.get("actor_role", ""))
            actor = str(sale.get("actor_email", "Sistema"))
            if role == "receptionist":
                actor += " · Recepción"
            elif role == "admin":
                actor += " · Admin"
            self.sales_tree.insert(
                "",
                "end",
                iid=str(sale.get("id")),
                values=(
                    display_timestamp(sale.get("sold_at", ""), timezone_for(self.db)),
                    sale.get("product_name", ""),
                    int(sale.get("quantity") or 0),
                    format_money(sale.get("unit_price", 0)),
                    format_money(sale.get("total_amount", 0)),
                    sale.get("payment_method", ""),
                    actor,
                ),
            )

    def refresh(self) -> None:
        try:
            self.refresh_products()
            self.refresh_sales()
        except Exception as error:
            messagebox.showerror(
                "No se pudo cargar la tienda",
                str(error),
                parent=self,
            )


class CheckinPage(BasePage):
    title = "Registro de entrada"

    def __init__(self, parent: tk.Misc, app: "GymSoftApp"):
        super().__init__(parent, app)
        self.provider = ManualAccessProvider()
        self.last_denied_client: int | None = None
        self.page_header(
            "Busca al cliente, valida su plan activo y registra el ingreso."
        )
        self.access_tabs = ttk.Notebook(self)
        self.access_tabs.pack(fill='both', expand=True)
        self.entry_tab = ttk.Frame(self.access_tabs, style='Page.TFrame', padding=(0, 10))
        self.history_tab = ttk.Frame(self.access_tabs, style='Page.TFrame', padding=(0, 10))
        self.access_tabs.add(self.entry_tab, text='Registrar entrada')
        self.access_tabs.add(self.history_tab, text='Historial de entradas')
        top = ttk.Frame(self.entry_tab, style="Page.TFrame")
        top.pack(fill="both", expand=True)
        # El ancho depende del espacio disponible, no del mensaje o del nombre.
        # Evita realimentar grid -> wraplength -> tamaño solicitado -> grid.
        top.columnconfigure(0, weight=1, uniform="access")
        top.columnconfigure(1, weight=1, uniform="access")
        top.rowconfigure(0, weight=1)

        picker = ttk.Frame(top, padding=18, style="Card.TFrame")
        picker.grid(row=0, column=0, sticky="nsew", padx=(0, 9))
        ttk.Label(
            picker,
            text="1. Busca y selecciona un cliente",
            style="Section.TLabel", width=1, anchor="w",
        ).pack(fill="x")
        ttk.Label(
            picker,
            text=(
                "Escribe para buscar. Un lector compatible identifica la "
                "huella desde cualquier sección. También puedes escribir su código aquí."
            ),
            style="CardMuted.TLabel",
            wraplength=360, width=1, anchor="w", justify="left",
        ).pack(fill="x", pady=(3, 12))
        self.search = tk.StringVar()
        self.search_entry = ttk.Entry(picker, textvariable=self.search)
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<Return>", lambda _event: "break")
        self.app.biometric_access.attach_search(self.search_entry, self.search)
        BiometricAccessControl(self, self.app.biometric_access).pack(fill="x", before=self.access_tabs, pady=(0, 12))
        bind_live_search(self, self.search, self.refresh_clients)
        self.clients = CenteredTreeview(picker, columns=("document", "name", "status"), show="headings", height=4)
        for key, label, width in [("document", "Documento", 115), ("name", "Cliente", 210), ("status", "Estado", 90)]:
            self.clients.heading(key, text=label)
            self.clients.column(key, width=width)
        self.clients.pack(fill="both", expand=True, pady=(10, 12))
        ttk.Button(
            picker,
            text="✓  Registrar ingreso",
            command=self.register_entry,
            style="Primary.TButton",
        ).pack(fill="x")

        # Mantiene el botón de autorización completo en ventanas medianas y
        # con escalado de Windows al 125 %, sin obligar a reducir la fuente.
        result = ttk.Frame(top, padding=18, style="Card.TFrame")
        result.grid(row=0, column=1, sticky="nsew", padx=(9, 0))
        ttk.Label(
            result,
            text="2. Resultado del ingreso",
            style="Section.TLabel", width=1, anchor="w",
        ).pack(fill="x")
        self.badge = tk.Label(
            result,
            text="LISTO PARA REGISTRAR",
            width=1,
            font=(UI_FONT, 15, "bold"),
            bg=COLORS["blue_bg"],
            fg=COLORS["blue"],
            padx=20,
            pady=18,
        )
        self.badge.pack(fill="x", pady=(18, 16))
        self.result_name = ttk.Label(result, text="—", style="ResultName.TLabel", width=1, anchor="w", justify="left")
        self.result_name.pack(fill="x")
        self.result_details = ttk.Label(
            result,
            text="Selecciona un cliente para registrar su ingreso.",
            style="CardMuted.TLabel", width=1, anchor="w", justify="left",
        )
        self.result_details.pack(fill="x", pady=(6, 14))
        self.override_button = ttk.Button(
            result,
            text="Autorizar ingreso excepcional",
            command=self.override,
            state="disabled",
        )
        self.override_button.pack(anchor="w")

        recent = ttk.Frame(self.history_tab, padding=14, style="Card.TFrame")
        recent.pack(fill="both", expand=True)
        ttk.Label(recent, text="Entradas recientes", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self.history = CenteredTreeview(
            recent,
            columns=("time", "client", "document", "method", "result"),
            show="headings",
            height=7,
        )
        for key, label, width in [
            ("time", "Fecha y hora", 160),
            ("client", "Cliente", 250),
            ("document", "Documento", 135),
            ("method", "Registro", 130),
            ("result", "Resultado", 110),
        ]:
            self.history.heading(key, text=label)
            self.history.column(key, width=width)
        self.history.pack(fill="both", expand=True)
        self.history.tag_configure("allowed", foreground=COLORS["success"])
        self.history.tag_configure("denied", foreground=COLORS["danger"])

    def refresh_clients(self) -> None:
        term = self.search.get()
        self.load_view("refresh_clients", lambda: self.db.list_clients(term), self._render_refresh_clients, (term,))

    def _render_refresh_clients(self, rows):
        clear_tree(self.clients)
        for client in rows:
            if client["active"]:
                self.clients.insert(
                    "",
                    "end",
                    iid=str(client["id"]),
                    values=(client["document"], f"{client['first_name']} {client['last_name']}", client["membership_status"]),
                )

    def refresh_history(self) -> None:
        self.load_view("refresh_history", lambda: self.db.list_checkins(40), self._render_refresh_history, ())

    def _render_refresh_history(self, rows):
        clear_tree(self.history)
        for item in rows:
            tag = "allowed" if item["result"] == "PERMITIDA" else "denied"
            self.history.insert(
                "",
                "end",
                iid=str(item["id"]),
                values=(item["checkin_at"][:16], item["client_name"], item["document"], item["method"], checkin_label(item)),
                tags=(tag,),
            )

    def refresh(self) -> None:
        self.refresh_clients()
        self.refresh_history()

    def register_entry(self) -> None:
        match = self.provider.identify(selected_id(self.clients))
        if not match.matched or match.client_id is None:
            messagebox.showinfo(
                "Selecciona un cliente",
                match.message,
                parent=self,
            )
            return
        self.register_client_entry(
            match.client_id,
            match.method,
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
            messagebox.showerror(
                "No se pudo registrar el ingreso",
                str(error),
                parent=self,
            )
            return
        self.show_result(result)
        self.refresh_history()
        self.app.refresh_all(except_page=self)

        if show_confirmation and result["result"] == "PERMITIDA":
            messagebox.showinfo(
                "Ingreso registrado",
                f"{result['client_name']} ingresó correctamente.",
                parent=self,
            )

    def process_biometric_scan(self, code: str) -> None:
        try:
            client = self.db.get_client_by_biometric_identifier(code)
        except Exception as error:
            messagebox.showerror(
                "No se pudo leer la huella",
                str(error),
                parent=self,
            )
            return
        if client is None:
            self.badge.configure(
                text="HUELLA NO IDENTIFICADA",
                bg=COLORS["danger_bg"],
                fg=COLORS["danger"],
            )
            self.result_name.configure(text="No se encontró un cliente")
            self.result_details.configure(
                text="Asocia el identificador del lector a la ficha del cliente."
            )
            self.bell()
            self.refresh_clients()
            return

        self.register_client_entry(
            int(client["id"]),
            "HUELLA BIOMÉTRICA",
            show_confirmation=False,
        )
        self.search.set("")
        self.search_entry.focus_set()

    def show_result(self, result: dict[str, Any]) -> None:
        allowed = result["result"] == "PERMITIDA"
        if allowed:
            self.badge.configure(text="INGRESO REGISTRADO", bg=COLORS["success_bg"], fg=COLORS["success"])
            self.last_denied_client = None
            self.override_button.configure(state="disabled")
        else:
            self.badge.configure(text="INGRESO NO AUTORIZADO", bg=COLORS["danger_bg"], fg=COLORS["danger"])
            self.last_denied_client = int(result["id"])
            self.override_button.configure(state="normal")
        self.result_name.configure(text=result["client_name"])
        end = (
            date_to_display(
                result.get("membership_end")
            )
            or "sin plan vigente"
        )
        details = (
            f"Documento: {result['document']}"
            f"  ·  Estado: {result['status']}"
            f"  ·  Vencimiento: {end}"
        )

        if result.get("entries_remaining") is not None:
            details += (
                f"  ·  Entradas restantes: "
                f"{result['entries_remaining']}"
                f" de {result['entry_limit']}"
            )

        self.result_details.configure(text=details + ("\n" + ticket_access_note(result) if ticket_access_note(result) else ""))
    def override(self) -> None:
        if self.last_denied_client is None:
            return
        if not messagebox.askyesno(
            "Autorizar entrada",
            (
                "El cliente no tiene un plan vigente. "
                "¿Deseas registrar un ingreso excepcional?"
            ),
            parent=self,
        ):
            return
        result = self.db.register_checkin(self.last_denied_client, "AUTORIZACIÓN MANUAL", override=True)
        self.show_result(result)
        self.refresh_history()
        self.app.refresh_all(except_page=self)


class RoutinesPage(BasePage):
    title = "Rutinas y entrenadores"

    def __init__(self, parent: tk.Misc, app: "GymSoftApp"):
        super().__init__(parent, app)
        self.page_header("Asigna entrenadores y construye planes de entrenamiento por cliente.")
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        trainers_tab = ttk.Frame(notebook, padding=14, style="Card.TFrame")
        routines_tab = ttk.Frame(notebook, padding=14, style="Card.TFrame")
        notebook.add(routines_tab, text="Rutinas")
        notebook.add(trainers_tab, text="Entrenadores")

        self.routines = CenteredTreeview(
            routines_tab,
            columns=("name", "client", "trainer", "goal", "exercises"),
            show="headings",
            height=9,
        )
        for key, label, width in [
            ("name", "Rutina", 180),
            ("client", "Cliente", 220),
            ("trainer", "Entrenador", 190),
            ("goal", "Objetivo", 200),
            ("exercises", "Ejercicios", 80),
        ]:
            self.routines.heading(key, text=label)
            self.routines.column(key, width=width)
        self.routines.pack(fill="both", expand=True)
        self.routines.bind("<<TreeviewSelect>>", lambda _event: self.refresh_exercises())
        routine_actions = ttk.Frame(routines_tab, style="Card.TFrame")
        routine_actions.pack(fill="x", pady=(10, 10))
        ttk.Button(routine_actions, text="Nueva rutina", command=self.new_routine, style="Primary.TButton").pack(side="left")
        ttk.Button(routine_actions, text="Agregar ejercicio", command=self.new_exercise).pack(side="left", padx=(8, 0))

        ttk.Label(routines_tab, text="Ejercicios de la rutina seleccionada", style="Section.TLabel").pack(anchor="w", pady=(4, 7))
        self.exercises = CenteredTreeview(
            routines_tab,
            columns=("day", "name", "sets", "reps", "weight", "notes"),
            show="headings",
            height=8,
        )
        for key, label, width in [
            ("day", "Día", 100),
            ("name", "Ejercicio", 210),
            ("sets", "Series", 70),
            ("reps", "Reps", 70),
            ("weight", "Peso", 90),
            ("notes", "Notas", 240),
        ]:
            self.exercises.heading(key, text=label)
            self.exercises.column(key, width=width)
        self.exercises.pack(fill="both", expand=True)

        self.trainers = CenteredTreeview(
            trainers_tab,
            columns=("name", "phone", "email", "specialty", "status"),
            show="headings",
        )
        for key, label, width in [
            ("name", "Nombre", 220),
            ("phone", "Teléfono", 150),
            ("email", "Correo", 230),
            ("specialty", "Especialidad", 180),
            ("status", "Estado", 90),
        ]:
            self.trainers.heading(key, text=label)
            self.trainers.column(key, width=width)
        self.trainers.pack(fill="both", expand=True)
        trainer_actions = ttk.Frame(trainers_tab, style="Card.TFrame")
        trainer_actions.pack(fill="x", pady=(12, 0))
        ttk.Button(trainer_actions, text="Nuevo entrenador", command=self.new_trainer, style="Primary.TButton").pack(side="left")
        ttk.Button(trainer_actions, text="Editar", command=self.edit_trainer).pack(side="left", padx=(8, 0))
        self.trainers.bind("<Double-1>", lambda _event: self.edit_trainer())

    def refresh(self) -> None:
        self.load_view('routines', lambda: (self.db.list_routines(), self.db.list_trainers()), self._render_refresh)

    def _render_refresh(self, data):
        routines, trainers = data
        clear_tree(self.routines)
        for routine in routines:
            self.routines.insert(
                "",
                "end",
                iid=str(routine["id"]),
                values=(routine["name"], routine["client_name"], routine["trainer_name"], routine["goal"], routine["exercise_count"]),
            )
        clear_tree(self.trainers)
        for trainer in trainers:
            self.trainers.insert(
                "",
                "end",
                iid=str(trainer["id"]),
                values=(trainer["name"], trainer["phone"], trainer["email"], trainer["specialty"], "ACTIVO" if trainer["active"] else "INACTIVO"),
            )
        self.routines.finish_update()
        self.refresh_exercises()

    def refresh_exercises(self) -> None:
        selected = selected_id(self.routines)
        self.load_view("refresh_exercises", lambda: self.db.list_exercises(selected) if selected else [],
                       self._render_refresh_exercises, (selected,))

    def _render_refresh_exercises(self, rows):
        clear_tree(self.exercises)
        for exercise in rows:
            self.exercises.insert(
                "",
                "end",
                iid=str(exercise["id"]),
                values=(exercise["day_name"], exercise["name"], exercise["sets"], exercise["reps"], exercise["weight"], exercise["notes"]),
            )

    def new_trainer(self) -> None:
        dialog = TrainerDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.db.save_trainer(dialog.result)
            self.refresh()

    def edit_trainer(self) -> None:
        trainer_id = selected_id(self.trainers)
        if not trainer_id:
            messagebox.showinfo("Selecciona un registro", "Selecciona un entrenador.", parent=self)
            return
        data = next((item for item in self.db.list_trainers() if item["id"] == trainer_id), None)
        dialog = TrainerDialog(self, data)
        self.wait_window(dialog)
        if dialog.result:
            self.db.save_trainer(dialog.result, trainer_id)
            self.refresh()

    def new_routine(self) -> None:
        dialog = RoutineDialog(self, self.db)
        self.wait_window(dialog)
        if dialog.result:
            routine_id = self.db.create_routine(**dialog.result)
            self.refresh()
            self.when_loaded(lambda: self.routines.selection_set(str(routine_id)) if self.routines.exists(str(routine_id)) else None)

    def new_exercise(self) -> None:
        routine_id = selected_id(self.routines)
        if not routine_id:
            messagebox.showinfo("Selecciona un registro", "Selecciona primero una rutina.", parent=self)
            return
        dialog = ExerciseDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.db.add_exercise(routine_id=routine_id, **dialog.result)
            self.refresh()
            self.routines.selection_set(str(routine_id))
            self.refresh_exercises()


class ClassesPage(BasePage):
    title = "Clases y Reservas"

    def __init__(self, parent: tk.Misc, app: "GymSoftApp"):
        super().__init__(parent, app)
        self.page_header(
            "Programa clases, controla los cupos y registra reservas.",
            [("Programar clase", self.new_class, "Primary.TButton")],
        )
        classes_card = ttk.Frame(self, padding=14, style="Card.TFrame")
        classes_card.pack(fill="both", expand=True)
        self.classes = CenteredTreeview(
            classes_card,
            columns=("name", "date", "trainer", "capacity", "reserved", "status"),
            show="headings",
            height=10,
        )
        for key, label, width in [
            ("name", "Clase", 190),
            ("date", "Fecha y hora", 155),
            ("trainer", "Entrenador", 200),
            ("capacity", "Cupos", 75),
            ("reserved", "Reservados", 90),
            ("status", "Estado", 105),
        ]:
            self.classes.heading(key, text=label)
            self.classes.column(key, width=width)
        self.classes.pack(fill="both", expand=True)
        self.classes.bind("<<TreeviewSelect>>", lambda _event: self.refresh_reservations())
        ttk.Button(classes_card, text="Reservar cliente", command=self.reserve, style="Primary.TButton").pack(anchor="w", pady=(10, 0))

        reservations_card = ttk.Frame(self, padding=14, style="Card.TFrame")
        reservations_card.pack(fill="both", expand=True, pady=(16, 0))
        ttk.Label(reservations_card, text="Reservas de la clase seleccionada", style="Section.TLabel").pack(anchor="w", pady=(0, 8))
        self.reservations = CenteredTreeview(
            reservations_card,
            columns=("client", "document", "status", "created"),
            show="headings",
            height=7,
        )
        for key, label, width in [
            ("client", "Cliente", 300),
            ("document", "Documento", 150),
            ("status", "Estado", 120),
            ("created", "Registrada", 165),
        ]:
            self.reservations.heading(key, text=label)
            self.reservations.column(key, width=width)
        self.reservations.pack(fill="both", expand=True)
        ttk.Button(reservations_card, text="Cancelar reserva", command=self.cancel_reservation).pack(anchor="w", pady=(10, 0))

    def refresh(self) -> None:
        self.load_view("refresh", lambda: self.db.list_classes(), self._render_refresh, ())

    def _render_refresh(self, rows):
        clear_tree(self.classes)
        for gym_class in rows:
            self.classes.insert(
                "",
                "end",
                iid=str(gym_class["id"]),
                values=(gym_class["name"], gym_class["starts_at"], gym_class["trainer_name"], gym_class["capacity"], gym_class["reserved"], gym_class["status"]),
            )
        self.classes.finish_update()
        self.refresh_reservations()

    def refresh_reservations(self) -> None:
        selected = selected_id(self.classes)
        self.load_view("refresh_reservations", lambda: self.db.list_reservations(selected) if selected else [],
                       self._render_refresh_reservations, (selected,))

    def _render_refresh_reservations(self, rows):
        clear_tree(self.reservations)
        for reservation in rows:
            self.reservations.insert(
                "",
                "end",
                iid=str(reservation["id"]),
                values=(reservation["client_name"], reservation["document"], reservation["status"], display_timestamp(reservation["created_at"], timezone_for(self.db), seconds=False)),
            )

    def new_class(self) -> None:
        dialog = ClassDialog(self, self.db)
        self.wait_window(dialog)
        if dialog.result:
            self.db.create_class(**dialog.result)
            self.refresh()

    def reserve(self) -> None:
        class_id = selected_id(self.classes)
        if not class_id:
            messagebox.showinfo("Selecciona un registro", "Selecciona una clase.", parent=self)
            return
        clients = [client for client in self.db.list_clients() if client["active"]]
        choices = {
            f"{item['first_name']} {item['last_name']} · {item['document']}": item["id"]
            for item in clients
        }
        if not choices:
            messagebox.showinfo("Sin clientes", "Primero registra un cliente activo.", parent=self)
            return
        dialog = ChoiceDialog(self, "Reservar cliente", "Cliente", choices)
        self.wait_window(dialog)
        if dialog.result:
            try:
                self.db.reserve_class(class_id, int(dialog.result))
            except ValueError as exc:
                messagebox.showwarning("No se pudo reservar", str(exc), parent=self)
                return
            self.refresh()
            self.classes.selection_set(str(class_id))
            self.refresh_reservations()

    def cancel_reservation(self) -> None:
        reservation_id = selected_id(self.reservations)
        class_id = selected_id(self.classes)
        if not reservation_id:
            messagebox.showinfo("Selecciona un registro", "Selecciona una reserva.", parent=self)
            return
        if messagebox.askyesno("Cancelar reserva", "¿Deseas cancelar esta reserva?", parent=self):
            self.db.cancel_reservation(reservation_id)
            self.refresh()
            if class_id:
                self.classes.selection_set(str(class_id))
                self.refresh_reservations()

class SettingsPage(BasePage):
    title = "Configuración"

    def __init__(
        self,
        parent: tk.Misc,
        app: "GymSoftApp",
    ):
        super().__init__(parent, app)
        self.whatsapp_vars = {
            "waba_id": tk.StringVar(),
            "phone_number_id": tk.StringVar(),
            "default_country_code": tk.StringVar(value="57"),
            "graph_api_version": tk.StringVar(value="v23.0"),
            "language_code": tk.StringVar(value="es_CO"),
        }
        self.whatsapp_connection_status = tk.StringVar(value="PENDIENTE")
        self.whatsapp_last_worker = tk.StringVar(
            value="Última ejecución: Sin ejecutar"
        )
        self.whatsapp_last_error = tk.StringVar(
            value="Sin errores registrados"
        )

        self.page_header(
            "Administra planes, importaciones, respaldos y servicios del gimnasio."
        )

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        # Pestaña de planes
        plans_tab = ttk.Frame(
            notebook,
            padding=18,
            style="Card.TFrame",
        )
        notebook.add(plans_tab, text="Planes")

        plans_tab.columnconfigure(0, weight=1)
        plans_tab.rowconfigure(0, weight=1)

        self.plans_tree = CenteredTreeview(
            plans_tab,
            columns=("name", "days", "entries", "price", "status"),
            show="headings",
            selectmode="browse",
        )

        columns = [
            ("name", "Plan", 260, "w"),
            ("days", "Vigencia", 120, "center"),
            ("entries", "Entradas", 115, "center"),
            ("price", "Precio", 160, "e"),
            ("status", "Estado", 130, "center"),
        ]

        for key, label, width, anchor in columns:
            self.plans_tree.heading(key, text=label)
            self.plans_tree.column(
                key,
                width=width,
                anchor=anchor,
            )

        self.plans_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        self.plans_tree.bind(
            "<Double-1>",
            lambda _event: self.edit_plan(),
        )

        plan_actions = ttk.Frame(
            plans_tab,
            style="Card.TFrame",
        )
        plan_actions.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(15, 0),
        )

        ttk.Button(
            plan_actions,
            text="Nuevo plan",
            command=self.new_plan,
            style="Primary.TButton",
        ).pack(side="left")

        ttk.Button(
            plan_actions,
            text="Editar plan",
            command=self.edit_plan,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            plan_actions,
            text="Activar/desactivar",
            command=self.toggle_plan,
        ).pack(side="left", padx=(8, 0))

        # Pestaña de respaldos
        backup_tab = ttk.Frame(
            notebook,
            padding=22,
            style="Card.TFrame",
        )
        notebook.add(
            backup_tab,
            text="Importar y exportar",
        )

        ttk.Label(
            backup_tab,
            text="Exportar a Excel",
            style="Section.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            backup_tab,
            text=(
                "Crea un archivo organizado con clientes, pagos, "
                "entradas, tienda, gastos, personal y auditoría."
            ),
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(5, 12))

        ttk.Button(
            backup_tab,
            text="Exportar a Excel",
            command=self.export_excel,
            style="Primary.TButton",
        ).pack(anchor="w")

        ttk.Separator(
            backup_tab,
            orient="horizontal",
        ).pack(fill="x", pady=25)

        ttk.Label(
            backup_tab,
            text="Copia de seguridad",
            style="Section.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            backup_tab,
            text=(
                "Guarda un archivo JSON completo y restaurable de la "
                "información central del gimnasio."
            ),
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(5, 12))

        backup_actions = ttk.Frame(
            backup_tab,
            style="Card.TFrame",
        )
        backup_actions.pack(anchor="w")

        ttk.Button(
            backup_actions,
            text="Exportar respaldo",
            command=self.export_data,
        ).pack(side="left")

        ttk.Button(
            backup_actions,
            text="Restaurar copia de seguridad",
            command=self.restore_technical_backup,
        ).pack(side="left", padx=(8, 0))

        ttk.Separator(
            backup_tab,
            orient="horizontal",
        ).pack(fill="x", pady=25)

        ttk.Label(
            backup_tab,
            text="Reemplazar desde Excel",
            style="Section.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            backup_tab,
            text=(
                "Valida un Excel completo, crea dos respaldos automáticos "
                "y reemplaza los datos en una sola operación segura. "
                "Las cuentas, permisos y conexión de WhatsApp se conservan."
            ),
            style="CardMuted.TLabel",
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(5, 12))

        ttk.Button(
            backup_tab,
            text="Importar Excel y reemplazar información",
            command=self.import_data,
            style="Danger.TButton",
        ).pack(anchor="w")

        # Pestaña para invitar personal de recepción
        reception_tab = ttk.Frame(
            notebook,
            padding=22,
            style="Card.TFrame",
        )
        notebook.add(
            reception_tab,
            text="Personal de recepción",
        )

        ttk.Label(
            reception_tab,
            text="Invitar a un trabajador",
            style="Section.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            reception_tab,
            text=(
                "Genera un código temporal para crear una cuenta "
                "en GymSoft Recepción. El trabajador podrá atender "
                "clientes, registrar pagos y controlar accesos, pero "
                "no tendrá permisos administrativos."
            ),
            style="CardMuted.TLabel",
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(5, 18))

        code_card = ttk.Frame(
            reception_tab,
            padding=18,
            style="Surface.TFrame",
        )
        code_card.pack(fill="x")

        ttk.Label(
            code_card,
            text="Código de invitación",
            style="Field.TLabel",
        ).pack(anchor="w")

        self.reception_invite = tk.StringVar(
            value="Todavía no se ha generado un código."
        )

        invite_entry = ttk.Entry(
            code_card,
            textvariable=self.reception_invite,
            state="readonly",
            font=(FONT_FAMILY, 12, "bold"),
        )
        invite_entry.pack(fill="x", pady=(7, 14))

        invite_actions = ttk.Frame(
            code_card,
            style="Surface.TFrame",
        )
        invite_actions.pack(fill="x")

        ttk.Button(
            invite_actions,
            text="Generar invitación",
            command=self.generate_reception_invite,
            style="Primary.TButton",
        ).pack(side="left")

        ttk.Button(
            invite_actions,
            text="Copiar código",
            command=self.copy_reception_invite,
        ).pack(side="left", padx=(8, 0))

        ttk.Label(
            reception_tab,
            text=(
                "La invitación vence en 6 meses y puede utilizarse "
                "una sola vez. Generar una nueva invalida cualquier "
                "invitación anterior que todavía no se haya usado."
            ),
            style="CardMuted.TLabel",
            wraplength=720,
            justify="left",
        ).pack(anchor="w", pady=(16, 0))

        # Pestaña de conexión de WhatsApp
        whatsapp_tab = ttk.Frame(
            notebook,
            padding=22,
            style="Card.TFrame",
        )
        notebook.add(
            whatsapp_tab,
            text="WhatsApp",
        )

        whatsapp_content = ttk.Frame(
            whatsapp_tab,
            padding=18,
            style="Surface.TFrame",
        )
        whatsapp_content.pack(fill="both", expand=True)
        whatsapp_content.columnconfigure(1, weight=1)

        ttk.Label(
            whatsapp_content,
            text="Conexión oficial de WhatsApp Business",
            style="Section.TLabel",
        ).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            whatsapp_content,
            text=(
                "Configura aquí la conexión con WhatsApp Cloud API. "
                "Las reglas y los mensajes automáticos continúan en "
                "la sección Marketing. El token secreto permanece en "
                "Supabase y nunca se guarda dentro del ejecutable."
            ),
            style="CardMuted.TLabel",
            wraplength=760,
            justify="left",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(5, 18),
        )

        whatsapp_fields = (
            ("ID de la cuenta de WhatsApp (WABA)", "waba_id"),
            ("ID del número de teléfono", "phone_number_id"),
            ("Código de país predeterminado", "default_country_code"),
            ("Versión de Graph API", "graph_api_version"),
            ("Idioma de las plantillas", "language_code"),
        )

        for row, (label, key) in enumerate(whatsapp_fields, start=2):
            ttk.Label(
                whatsapp_content,
                text=label,
                style="Field.TLabel",
            ).grid(
                row=row,
                column=0,
                sticky="w",
                pady=7,
                padx=(0, 18),
            )
            ttk.Entry(
                whatsapp_content,
                textvariable=self.whatsapp_vars[key],
            ).grid(row=row, column=1, sticky="ew", pady=7)

        whatsapp_actions = ttk.Frame(
            whatsapp_content,
            style="Surface.TFrame",
        )
        whatsapp_actions.grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(14, 0),
        )
        ttk.Button(
            whatsapp_actions,
            text="Guardar conexión",
            command=self.save_whatsapp_connection,
            style="Primary.TButton",
        ).pack(side="left")
        ttk.Button(
            whatsapp_actions,
            text="Actualizar estado",
            command=self.load_whatsapp_settings,
        ).pack(side="left", padx=(8, 0))

        whatsapp_status_card = tk.Frame(
            whatsapp_content,
            bg=COLORS["surface_alt"],
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        whatsapp_status_card.grid(
            row=8,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(18, 0),
        )
        tk.Label(
            whatsapp_status_card,
            text="ESTADO DEL SERVICIO",
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 8, "bold"),
        ).grid(row=0, column=0, sticky="w")
        self.whatsapp_connection_status_label = tk.Label(
            whatsapp_status_card,
            textvariable=self.whatsapp_connection_status,
            bg=COLORS["surface_alt"],
            fg=COLORS["warning"],
            font=(FONT_FAMILY, 13, "bold"),
        )
        self.whatsapp_connection_status_label.grid(
            row=1,
            column=0,
            sticky="w",
            pady=(3, 0),
        )
        tk.Label(
            whatsapp_status_card,
            textvariable=self.whatsapp_last_worker,
            bg=COLORS["surface_alt"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 9),
        ).grid(row=0, column=1, sticky="w", padx=(45, 0))
        tk.Label(
            whatsapp_status_card,
            textvariable=self.whatsapp_last_error,
            bg=COLORS["surface_alt"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 8),
            wraplength=430,
            justify="left",
        ).grid(row=1, column=1, sticky="w", padx=(45, 0), pady=(3, 0))

        # Pestaña para personalizar el logo
        logo_tab = ttk.Frame(
            notebook,
            padding=22,
            style="Card.TFrame",
        )
        notebook.add(
            logo_tab,
            text="Logotipo",
        )

        ttk.Label(
            logo_tab,
            text="Logotipo del gimnasio",
            style="Section.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            logo_tab,
            text=(
                "Selecciona la imagen PNG que aparecerá "
                "en la barra lateral de la aplicación."
            ),
            style="CardMuted.TLabel",
        ).pack(anchor="w", pady=(5, 15))

        ttk.Button(
            logo_tab,
            text="Cambiar logotipo",
            command=self.app.choose_logo,
            style="Primary.TButton",
        ).pack(anchor="w")

        tk.Label(
            self,
            text=COPYRIGHT,
            bg=COLORS["background"],
            fg="#5F7089",
            font=(FONT_FAMILY, 7),
        ).pack(side="bottom", anchor="e", pady=(5, 0), padx=(0, 3))

        from door_ui import settings_tab
        settings_tab(notebook, app)

    def load_whatsapp_settings(self, show_error: bool = True) -> None:
        self.load_view('whatsapp', self.db.marketing_settings, self._render_load_whatsapp_settings)

    def _render_load_whatsapp_settings(self, settings):
        previous = getattr(self, '_whatsapp_snapshot', {})
        for key, variable in self.whatsapp_vars.items():
            if key not in previous or str(variable.get()) == str(previous[key]):
                variable.set(settings.get(key, variable.get()))
        self._whatsapp_snapshot = {key: settings.get(key, variable.get()) for key, variable in self.whatsapp_vars.items()}

        last_worker = str(settings.get("last_worker_at") or "")
        last_error = str(settings.get("last_error") or "")
        status, color_key = service_status(settings)
        color = COLORS[color_key]

        self.whatsapp_connection_status.set(status)
        self.whatsapp_connection_status_label.configure(fg=color)
        self.whatsapp_last_worker.set(
            "Última ejecución: "
            + (
                display_timestamp(last_worker, timezone_for(self.db))
                if last_worker
                else "Sin ejecutar"
            )
        )
        self.whatsapp_last_error.set(
            friendly_error(last_error) if last_error else "Sin errores registrados"
        )

    def save_whatsapp_connection(self) -> None:
        try:
            settings = self.db.marketing_settings()

            for key, variable in self.whatsapp_vars.items():
                settings[key] = str(variable.get()).strip()

            self.db.save_marketing_settings(settings)
        except Exception as error:
            messagebox.showerror(
                "No se pudo guardar WhatsApp",
                str(error),
                parent=self,
            )
            return

        self.load_whatsapp_settings(show_error=False)
        messagebox.showinfo(
            "Conexión guardada",
            "La configuración de WhatsApp quedó guardada en la nube.",
            parent=self,
        )

    def generate_reception_invite(self) -> None:
        confirmed = messagebox.askyesno(
            "Generar invitación",
            "¿Deseas generar un nuevo código para recepción?\n\n"
            "Cualquier código anterior que no se haya usado "
            "quedará invalidado.",
            parent=self,
        )

        if not confirmed:
            return

        try:
            response = run_io(self, lambda: self.app.cloud.client.rpc(
                "create_reception_invite"
            ).execute(), 'Generando invitación')
            code: Any = response.data

            if isinstance(code, list):
                code = code[0] if code else None

            if isinstance(code, dict):
                code = code.get("create_reception_invite")

            code = str(code or "").strip()

            if not code:
                raise ValueError(
                    "El servidor no devolvió un código de invitación. Inténtalo de nuevo."
                )
        except Exception as error:
            messagebox.showerror(
                "No se pudo crear la invitación",
                str(error),
                parent=self,
            )
            return

        self.reception_invite.set(code)
        self.clipboard_clear()
        self.clipboard_append(code)

        messagebox.showinfo(
            "Invitación creada",
            "El código se copió al portapapeles.\n\n"
            "Compártelo únicamente con el trabajador que instalará "
            "GymSoft Recepción.",
            parent=self,
        )

    def copy_reception_invite(self) -> None:
        code = self.reception_invite.get().strip()

        if not code or code.startswith("Todavía"):
            messagebox.showinfo(
                "Sin invitación",
                "Genera primero un código de invitación.",
                parent=self,
            )
            return

        self.clipboard_clear()
        self.clipboard_append(code)

        messagebox.showinfo(
            "Código copiado",
            "La invitación quedó copiada al portapapeles.",
            parent=self,
        )

    def refresh(self) -> None:
        self.load_whatsapp_settings(show_error=False)
        self.load_view("refresh", lambda: self.db.list_plans(active_only=False), self._render_refresh, ())

    def _render_refresh(self, rows):
        clear_tree(self.plans_tree)

        for plan in rows:
            status = "ACTIVO" if plan["active"] else "INACTIVO"

            self.plans_tree.insert(
                "",
                "end",
                iid=str(plan["id"]),
                values=(
                    plan["name"],
                    plan_duration(plan),
                    plan.get("entry_limit") if plan.get("entry_limit") is not None else "Sin límite",
                    format_money(plan["price"]),
                    status,
                ),
                tags=("active" if plan["active"] else "inactive",),
            )

        self.plans_tree.tag_configure(
            "active",
            foreground=COLORS["success"],
        )
        self.plans_tree.tag_configure(
            "inactive",
            foreground=COLORS["muted"],
        )


    def selected_plan(self) -> dict[str, Any] | None:
        plan_id = selected_id(self.plans_tree)

        if not plan_id:
            messagebox.showinfo(
                "Selecciona un plan",
                "Selecciona primero un plan.",
                parent=self,
            )
            return None

        return next(
            (
                plan
                for plan in self.db.list_plans(active_only=False)
                if plan["id"] == plan_id
            ),
            None,
        )

    def new_plan(self) -> None:
        dialog = PlanDialog(self)
        self.wait_window(dialog)

        if not dialog.result:
            return

        try:
            self.db.add_plan(*dialog.result)
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Plan repetido",
                "Ya existe un plan con ese nombre.",
                parent=self,
            )
            return

        self.app.refresh_all(except_page=self)

    def edit_plan(self) -> None:
        plan = self.selected_plan()

        if not plan:
            return

        dialog = PlanDialog(self, plan)
        self.wait_window(dialog)

        if not dialog.result:
            return

        try:
            self.db.update_plan(
                int(plan["id"]),
                *dialog.result,
            )
        except sqlite3.IntegrityError:
            messagebox.showerror(
                "Nombre repetido",
                "Ya existe otro plan con ese nombre.",
                parent=self,
            )
            return

        self.app.refresh_all(except_page=self)

    def toggle_plan(self) -> None:
        plan = self.selected_plan()

        if not plan:
            return

        is_active = bool(plan["active"])

        if is_active:
            active_plans = [
                item
                for item in self.db.list_plans()
                if item["active"]
            ]

            if len(active_plans) == 1:
                messagebox.showwarning(
                    "Plan necesario",
                    "Debe existir al menos un plan activo.",
                    parent=self,
                )
                return

        action = "desactivar" if is_active else "activar"

        confirmed = messagebox.askyesno(
            "Cambiar estado",
            f"¿Deseas {action} el plan {plan['name']}?",
            parent=self,
        )

        if not confirmed:
            return

        self.db.set_plan_active(
            int(plan["id"]),
            not is_active,
        )

        self.app.refresh_all(except_page=self)

    def export_excel(self) -> None:
        filename = (
            f"GymSoft-informacion-completa-"
            f"{datetime.now():%Y%m%d-%H%M}.xlsx"
        )
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar información actualizada a Excel",
            defaultextension=".xlsx",
            initialfile=filename,
            filetypes=[
                ("Libro de Excel", "*.xlsx"),
            ],
        )

        if not path:
            return

        try:
            exported = self.db.export_excel(path)
        except Exception as error:
            messagebox.showerror(
                "No se pudo crear el Excel",
                str(error),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Excel exportado",
            (
                "La información actualizada se exportó correctamente "
                f"en:\n\n{exported}"
            ),
            parent=self,
        )

    def export_data(self) -> None:
        filename = (
            f"{APP_NAME}-respaldo-"
            f"{datetime.now():%Y%m%d-%H%M}.json"
        )

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar respaldo técnico",
            defaultextension=".json",
            initialfile=filename,
            filetypes=[
                ("Respaldo técnico de GymSoft", "*.json"),
            ],
        )

        if not path:
            return

        try:
            self.db.backup(path)
        except Exception as error:
            messagebox.showerror(
                "No se pudo exportar",
                str(error),
                parent=self,
            )
            return

        messagebox.showinfo(
            "Información exportada",
            f"El respaldo se guardó en:\n\n{path}",
            parent=self,
        )

    def restore_technical_backup(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Restaurar respaldo técnico de GymSoft",
            filetypes=[
                ("Respaldo técnico de GymSoft", "*.json"),
            ],
        )

        if not path:
            return

        try:
            prepared = self.db.prepare_technical_backup_replacement(path)
        except Exception as error:
            messagebox.showerror(
                "Respaldo no válido",
                str(error),
                parent=self,
            )
            return

        if not messagebox.askyesno(
            "Restaurar respaldo técnico",
            (
                f"Archivo: {Path(path).name}\n"
                f"Registros: {prepared['total_rows']:,}\n\n"
                "La información operativa actual será reemplazada por el "
                "contenido de este respaldo. Antes de restaurarlo se creará "
                "otra copia de seguridad de la base actual.\n\n"
                "¿Deseas continuar?"
            ),
            parent=self,
        ):
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_directory = (
            Path.home() / "Documents" / "GymSoft Respaldos"
        )

        try:
            backup_directory.mkdir(parents=True, exist_ok=True)
            safety_json = backup_directory / (
                f"GymSoft-antes-restaurar-{timestamp}.json"
            )
            safety_excel = backup_directory / (
                f"GymSoft-antes-restaurar-{timestamp}.xlsx"
            )
            self.db.backup(safety_json)
            self.db.export_excel(safety_excel)
        except Exception as error:
            messagebox.showerror(
                "No se pudo crear el respaldo preventivo",
                (
                    f"{error}\n\n"
                    "La restauración fue cancelada y la nube no cambió."
                ),
                parent=self,
            )
            return

        try:
            result = self.db.replace_from_excel(prepared)
        except Exception as error:
            messagebox.showerror(
                "No se pudo restaurar",
                (
                    f"{error}\n\n"
                    "No se pudo confirmar el resultado. Actualiza los datos "
                    "y revisa el historial antes de repetir la restauración."
                ),
                parent=self,
            )
            return

        self.app.refresh_all(except_page=self)
        messagebox.showinfo(
            "Respaldo restaurado",
            (
                f"Se restauraron {int(result.get('total_rows', 0)):,} "
                "registros correctamente.\n\n"
                "La copia preventiva quedó en:\n"
                f"{backup_directory}"
            ),
            parent=self,
        )

    def _legacy_import_data(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Importar información",
            filetypes=[
                ("Respaldo del gimnasio", "*.db"),
            ],
        )

        if not path:
            return

        try:
            with Path(path).open("rb") as source:
                is_sqlite = source.read(16) == b"SQLite format 3\x00"
        except OSError as error:
            messagebox.showerror(
                "No se pudo abrir el archivo",
                str(error),
                parent=self,
            )
            return

        if is_sqlite:
            confirmed = messagebox.askyesno(
                "Importar clientes y pagos",
                (
                    "Los clientes del archivo se agregarán o actualizarán "
                    "en la base central. Los pagos que ya existan no se "
                    "duplicarán.\n\n"
                    "Antes de comenzar se intentará crear un respaldo "
                    "automático. Si Supabase no permite generarlo, la "
                    "importación acumulativa podrá continuar sin eliminar "
                    "información existente.\n\n"
                    "¿Deseas continuar?"
                ),
                parent=self,
            )

            if not confirmed:
                return

            backup_path = Path(path).with_name(
                "GymSoft-antes-importar-excel-"
                f"{datetime.now():%Y%m%d-%H%M%S}.db"
            )

            backup_error: str | None = None
            try:
                self.db.backup(backup_path)
            except Exception as error:
                backup_error = str(error)

            try:
                counts = self.db.import_sqlite(path)
            except Exception as error:
                if backup_error:
                    backup_status = (
                        "\n\nEl respaldo automático tampoco pudo crearse:\n"
                        f"{backup_error}"
                    )
                else:
                    backup_status = (
                        "\n\nRespaldo anterior creado en:\n"
                        f"{backup_path}"
                    )

                messagebox.showerror(
                    "No se pudo importar el Excel",
                    f"La importación falló:\n{error}{backup_status}\n\n"
                    "Puedes volver a intentarlo: los pagos ya importados "
                    "no se duplicarán.",
                    parent=self,
                )
                return

            self.app.refresh_all(except_page=self)

            if backup_error:
                backup_status = (
                    "\n\nAviso: Supabase no permitió crear el respaldo "
                    "automático, pero esto no bloqueó la importación. "
                    "No se eliminó información existente."
                )
            else:
                backup_status = (
                    "\n\nRespaldo anterior:\n"
                    f"{backup_path}"
                )

            messagebox.showinfo(
                "Información importada",
                (
                    "La base central quedó actualizada.\n\n"
                    f"Clientes procesados: {counts.get('clients', 0)}\n"
                    f"Pagos nuevos: {counts.get('memberships', 0)}"
                    f"{backup_status}"
                ),
                parent=self,
            )
            return

        confirmed = messagebox.askyesno(
            "Confirmar importación",
            (
                "La información actual será reemplazada.\n\n"
                "Se creará automáticamente una copia de seguridad.\n\n"
                "¿Deseas continuar?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        try:
            automatic_backup = self.db.restore(path)
        except (
            OSError,
            sqlite3.DatabaseError,
            ValueError,
        ) as error:
            messagebox.showerror(
                "No se pudo importar",
                str(error),
                parent=self,
            )
            return

        self.app.refresh_all(except_page=self)

        messagebox.showinfo(
            "Información importada",
            (
                "La información se importó correctamente.\n\n"
                "Respaldo anterior:\n"
                f"{automatic_backup}"
            ),
            parent=self,
        )

    def import_data(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Seleccionar Excel completo de GymSoft",
            filetypes=[
                ("Libro de Excel", "*.xlsx *.xlsm"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if not path:
            return

        try:
            prepared = self.db.prepare_excel_replacement(path)
        except Exception as error:
            messagebox.showerror(
                "El Excel no está listo para importar",
                (
                    f"{error}\n\n"
                    "No se realizó ningún cambio y no se eliminó información."
                ),
                parent=self,
            )
            return

        count_labels = {
            "clients": "Clientes",
            "plans": "Planes",
            "memberships": "Membresías y pagos",
            "checkins": "Entradas",
            "store_products": "Productos",
            "store_sales": "Ventas de tienda",
            "accounting_expenses": "Gastos",
            "trainers": "Personal",
            "staff_shifts": "Jornadas",
            "routines": "Rutinas",
            "exercises": "Ejercicios",
            "classes": "Clases",
            "reservations": "Reservas",
            "marketing_messages": "Mensajes de marketing",
        }
        counts = prepared["counts"]
        preview_lines = [
            f"{label}: {counts.get(table, 0):,}"
            for table, label in count_labels.items()
        ]

        confirmed = messagebox.askyesno(
            "Confirmar reemplazo completo",
            (
                f"Archivo: {Path(path).name}\n\n"
                "Información que quedará en la nube:\n"
                + "\n".join(preview_lines)
                + "\n\nANTES DE REEMPLAZAR:\n"
                "• Se validará nuevamente el archivo.\n"
                "• Se guardará un respaldo técnico JSON.\n"
                "• Se guardará un respaldo completo en Excel.\n"
                "• La operación será total: si algo falla, Supabase "
                "revertirá todos los cambios.\n\n"
                "Las cuentas, roles, auditoría y conexión de WhatsApp "
                "no se reemplazarán.\n\n"
                "¿Deseas continuar?"
            ),
            parent=self,
        )

        if not confirmed:
            return

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        documents = Path.home() / "Documents"
        backup_directory = documents / "GymSoft Respaldos"

        try:
            backup_directory.mkdir(parents=True, exist_ok=True)
            technical_backup = backup_directory / (
                f"GymSoft-antes-importacion-{timestamp}.json"
            )
            excel_backup = backup_directory / (
                f"GymSoft-antes-importacion-{timestamp}.xlsx"
            )
            self.db.backup(technical_backup)
            self.db.export_excel(excel_backup)
        except Exception as error:
            messagebox.showerror(
                "No se pudo crear el respaldo",
                (
                    "La importación fue cancelada para proteger la información.\n\n"
                    f"{error}\n\n"
                    "No se modificó la base de datos."
                ),
                parent=self,
            )
            return

        try:
            result = self.db.replace_from_excel(prepared)
        except Exception as error:
            message = str(error)

            if (
                "admin_replace_gym_from_excel" in message
                or "PGRST202" in message
                or "schema cache" in message.casefold()
            ):
                message = (
                    "El servicio de importación no está disponible. "
                    "Contacta al soporte de Gym soft para revisar la configuración."
                )

            messagebox.showerror(
                "No se pudo confirmar la importación",
                (
                    f"{message}\n\n"
                    "Actualiza los datos y revisa el historial antes de "
                    "repetir la importación.\n\n"
                    "Respaldos creados en:\n"
                    f"{backup_directory}"
                ),
                parent=self,
            )
            return

        self.app.refresh_all(except_page=self)

        messagebox.showinfo(
            "Importación completada",
            (
                "La información del Excel reemplazó correctamente los "
                "datos operativos de GymSoft.\n\n"
                f"Registros importados: "
                f"{int(result.get('total_rows', prepared['total_rows'])):,}\n\n"
                "Respaldos de la información anterior:\n"
                f"{technical_backup}\n"
                f"{excel_backup}"
            ),
            parent=self,
        )
class GymSoftApp(tk.Tk):
    def __init__(self, database_path: str | Path | None = None, seed_demo: bool = True):
        enable_dpi_awareness()
        set_app_id('Administracion')
        super().__init__()
        install_error_handler(self)
        self.ready = False
        self.realtime_events: queue.Queue[dict[str, Any]] = (
    queue.Queue()
        )
        self.realtime_refresh_pending = False
        self.realtime_listener: RealtimeListener | None = None
        set_window_icon(self)
        self.title(f"{APP_NAME} · {APP_VERSION}")
        fit_window(self, 1280, 800, minimum=(760, 480))
        self.configure(bg=COLORS["background"])
        enable_dark_title_bar(self)
        self.data_dir = app_data_directory()
        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.logo_path = (
            self.data_dir / "gym_logo.png"
        )
        self.logo_image: tk.PhotoImage | None = None

        self.pages: dict[str, BasePage] = {}
        self.nav_buttons: dict[str, SidebarButton] = {}
        self.current_page = ""

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
        self.cloud = connect_cloud(self)

        if self.cloud is None:
            self.destroy()
            return

        self.data_dir = app_data_directory()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logo_path = self.data_dir / "gym_logo.png"
        # Después conectar la base de datos en la nube
        local_database_path = Path(
            database_path
            or self.data_dir / "gymcontrol.db"
        )

        from door_ui import install as install_door
        self.db = UiDatabase(install_door(self, CloudDatabase(self.cloud), admin=True), self)

        self._startup_message.destroy()
        self.build_shell()
        self.biometric_access = BiometricAccessController(
            self, self.db.get_client_by_biometric_identifier, self.on_biometric_match,
            self.on_biometric_unknown,
            lambda error: messagebox.showerror("No se pudo consultar la huella", str(error), parent=self),
        )
        self.show_page("dashboard")
        self.deiconify()
        self.ready = True
        center_window(self)

        self.protocol(
    "WM_DELETE_WINDOW",
            self.close_app,
        )

        self.realtime_listener = RealtimeListener(
            self.cloud,
            self.on_realtime_change,
        )
        self.realtime_listener.start()

        self.after(
            50,
            self.process_realtime_events,
        )

        center_window(self)

    def on_realtime_change(
        self,
        payload: dict[str, Any],
    ) -> None:
        change = payload.get(
            "data",
            payload,
        )

        if (
            isinstance(change, dict)
            and change.get("table") == "app_clock"
        ):
            self.db.invalidate_today_cache()

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



    def configure_styles(self) -> None:
        configure_dark_styles(self)
        style = ttk.Style(self)

        if "clam" in style.theme_names():
            style.theme_use("clam")

        self.option_add(
            "*TCombobox*Listbox.background",
            COLORS["input"],
        )
        self.option_add(
            "*TCombobox*Listbox.foreground",
            COLORS["text"],
        )
        self.option_add(
            "*TCombobox*Listbox.selectBackground",
            COLORS["sidebar_active"],
        )
        self.option_add(
            "*TCombobox*Listbox.selectForeground",
            COLORS["text"],
        )
        self.option_add("*Font", (FONT_FAMILY, 10))

        style.configure(
            "TFrame",
            background=COLORS["background"],
        )
        style.configure(
            "Page.TFrame",
            background=COLORS["background"],
        )
        style.configure(
            "Card.TFrame",
            background=COLORS["surface"],
            bordercolor=COLORS["line"],
            relief="flat",
            borderwidth=1,
        )
        style.configure(
            "Surface.TFrame",
            background=COLORS["surface"],
        )

        style.configure(
            "TLabel",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "Title.TLabel",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=(FONT_FAMILY, 24, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=COLORS["background"],
            foreground=COLORS["muted"],
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "Section.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            font=(FONT_FAMILY, 12, "bold"),
        )
        style.configure(
            "CardMuted.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["muted"],
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "ResultName.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            font=(FONT_FAMILY, 20, "bold"),
        )
        style.configure(
            "Field.TLabel",
            background=COLORS["surface"],
            foreground="#CBD5E1",
            font=(FONT_FAMILY, 9, "bold"),
        )

        style.configure(
            "TButton",
            background=COLORS["surface_hover"],
            foreground=COLORS["text"],
            font=(FONT_FAMILY, 9, "bold"),
            padding=(14, 9),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "TButton",
            background=[
                ("active", "#2B3D5B"),
                ("pressed", COLORS["sidebar_active"]),
                ("disabled", COLORS["surface_alt"]),
            ],
            foreground=[
                ("disabled", "#64748B"),
            ],
        )
        style.configure(
            "Primary.TButton",
            background=COLORS["primary"],
            foreground="#04130D",
            font=(FONT_FAMILY, 9, "bold"),
            padding=(16, 10),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Primary.TButton",
            background=[
                ("active", COLORS["primary_dark"]),
                ("pressed", "#0B8F5C"),
                ("disabled", "#1D4A3C"),
            ],
            foreground=[
                ("disabled", "#78998D"),
            ],
        )
        style.configure(
            "Accent.TButton",
            background=COLORS["accent"],
            foreground="white",
            font=(FONT_FAMILY, 9, "bold"),
            padding=(16, 10),
            borderwidth=0,
        )
        style.map(
            "Accent.TButton",
            background=[
                ("active", COLORS["accent_hover"]),
                ("pressed", "#1D4ED8"),
            ],
        )
        style.configure(
            "Danger.TButton",
            background=COLORS["danger_bg"],
            foreground=COLORS["danger"],
            font=(FONT_FAMILY, 9, "bold"),
            padding=(14, 9),
            borderwidth=0,
        )

        style.configure(
            "TEntry",
            fieldbackground=COLORS["input"],
            foreground=COLORS["text"],
            insertcolor=COLORS["text"],
            bordercolor=COLORS["line"],
            lightcolor=COLORS["line"],
            darkcolor=COLORS["line"],
            padding=9,
        )
        style.map(
            "TEntry",
            bordercolor=[("focus", COLORS["accent"])],
            lightcolor=[("focus", COLORS["accent"])],
            darkcolor=[("focus", COLORS["accent"])],
            fieldbackground=[
                ("disabled", COLORS["surface_alt"]),
                ("readonly", COLORS["surface_alt"]),
            ],
        )
        style.configure(
            "TCombobox",
            fieldbackground=COLORS["input"],
            background=COLORS["surface_hover"],
            foreground=COLORS["text"],
            arrowcolor=COLORS["muted"],
            bordercolor=COLORS["line"],
            lightcolor=COLORS["line"],
            darkcolor=COLORS["line"],
            padding=8,
        )
        style.map(
            "TCombobox",
            fieldbackground=[
                ("readonly", COLORS["input"]),
            ],
            foreground=[
                ("readonly", COLORS["text"]),
            ],
            bordercolor=[("focus", COLORS["accent"])],
        )
        style.configure(
            "TCheckbutton",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            font=(FONT_FAMILY, 9),
        )
        style.map(
            "TCheckbutton",
            background=[("active", COLORS["surface"])],
            foreground=[("active", COLORS["text"])],
        )

        style.configure(
            "Treeview",
            rowheight=34,
            background=COLORS["surface"],
            fieldbackground=COLORS["surface"],
            foreground="#DDE7F5",
            font=(FONT_FAMILY, 9),
            bordercolor=COLORS["line"],
            lightcolor=COLORS["line"],
            darkcolor=COLORS["line"],
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background=COLORS["surface_alt"],
            foreground="#B9C7DA",
            font=(FONT_FAMILY, 9, "bold"),
            padding=(9, 10),
            bordercolor=COLORS["line"],
            lightcolor=COLORS["surface_alt"],
            darkcolor=COLORS["surface_alt"],
            relief="flat",
        )
        style.map(
            "Treeview",
            background=[("selected", COLORS["sidebar_active"])],
            foreground=[("selected", "#FFFFFF")],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", COLORS["surface_hover"])],
        )

        style.configure(
            "TNotebook",
            background=COLORS["background"],
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background=COLORS["surface_alt"],
            foreground=COLORS["muted"],
            padding=(18, 10),
            font=(FONT_FAMILY, 9, "bold"),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", COLORS["surface"]),
                ("active", COLORS["surface_hover"]),
            ],
            foreground=[
                ("selected", COLORS["text"]),
                ("active", COLORS["text"]),
            ],
        )
        style.configure(
            "TSeparator",
            background=COLORS["line"],
        )
        style.configure(
            "Vertical.TScrollbar",
            background=COLORS["surface_hover"],
            troughcolor=COLORS["background"],
            arrowcolor=COLORS["muted"],
            borderwidth=0,
        )

    def on_biometric_match(self, client):
        self.show_page("checkin")
        page = self.pages["checkin"]
        page.access_tabs.select(page.entry_tab)
        page.register_client_entry(int(client["id"]), "HUELLA BIOMÉTRICA", show_confirmation=False)
        page.search.set("")
        page.search_entry.focus_set()

    def on_biometric_unknown(self, code):
        self.show_page("checkin")
        page = self.pages["checkin"]
        page.access_tabs.select(page.entry_tab)
        page.badge.configure(text="HUELLA NO IDENTIFICADA", bg=COLORS["danger_bg"], fg=COLORS["danger"])
        page.result_name.configure(text="No se encontró un cliente")
        page.result_details.configure(text="Asocia el código del lector a la ficha del cliente.")
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
        brand.pack(fill="x", padx=22, pady=(22, 16))

        tk.Label(
            brand,
            text="ATLANTIC GYM",
            bg=COLORS["sidebar"],
            fg="#4F8CFF",
            font=(FONT_FAMILY, 10, "bold"),
        ).pack(anchor="w")

        self.logo_label = tk.Label(brand, bg=COLORS["sidebar"], bd=0)
        self.logo_label.pack(anchor="center", pady=(8, 8))

        tk.Label(
            brand,
            text=self.cloud.gym_name,
            bg=COLORS["sidebar"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 16, "bold"),
            justify="left", anchor="w",
        ).pack(anchor="w")

        tk.Label(
            brand,
            text="GESTIÓN DE GIMNASIO",
            bg=COLORS["sidebar"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 7, "bold"),
        ).pack(anchor="w", pady=(2, 0))

        self.load_logo()

        tk.Frame(
            sidebar,
            bg=COLORS["line"],
            height=1,
        ).pack(fill="x", padx=18, pady=(0, 14))

        tk.Label(
            sidebar,
            text="MENÚ PRINCIPAL",
            bg=COLORS["sidebar"],
            fg="#71819A",
            font=(FONT_FAMILY, 7, "bold"),
        ).pack(anchor="w", padx=22, pady=(0, 7))

        nav_frame = tk.Frame(
            sidebar,
            bg=COLORS["sidebar"],
        )
        nav_frame.pack(fill="x", padx=10)

        nav = [
            ("dashboard", "\uE80F", "Dashboard", DashboardPage),
            ("checkin", "\uE8FB", "Registro de entrada", CheckinPage),
            ("clients", "\uE716", "Clientes y pagos", ClientsPage),
            ("shop", "\uE719", "Tienda", ShopPage),
            ("finance", "\uE8C7", "Finanzas y auditoría", FinancePage),
            ("statistics", "\uE9D2", "Estadísticas", StatisticsPage),
            ("routines", "\uE945", "Rutinas", RoutinesPage),
            ("classes", "\uE787", "Clases y reservas", ClassesPage),
            ("staff", "\uE77B", "Personal", StaffPage),
            ("marketing", "\uE715", "Marketing", MarketingPage),
        ]

        self.page_types = {
            key: page_type
            for key, _icon, _label, page_type in nav
        }
        self.page_types["settings"] = SettingsPage

        for key, icon, label, _page_type in nav:
            button = SidebarButton(
                nav_frame,
                icon,
                label,
                lambda page_key=key: self.show_page(
                    page_key
                ),
            )
            button.pack(fill="x", pady=1)
            self.nav_buttons[key] = button

        footer = tk.Frame(
            sidebar,
            bg=COLORS["sidebar"],
        )
        footer.pack(
            side="bottom",
            fill="x",
            padx=22,
            pady=20,
        )

        tk.Label(
            footer,
            text="●  DATOS EN LA NUBE",
            bg=COLORS["sidebar"],
            fg=COLORS["success"],
            font=(FONT_FAMILY, 7, "bold"),
        ).pack(anchor="w")

        tk.Label(
            footer,
            text=f"Atlantic Gym {APP_VERSION}  ·  {self.cloud.gym_id[:8]}",
            bg=COLORS["sidebar"],
            fg="#71819A",
            font=(FONT_FAMILY, 8),
        ).pack(anchor="w", pady=(5, 0))

        settings_area = tk.Frame(
            sidebar,
            bg=COLORS["sidebar"],
        )
        settings_area.pack(
            side="bottom",
            fill="x",
            padx=10,
            pady=(0, 4),
        )

        settings_button = SidebarButton(
            settings_area,
            "\uE713",
            "Configuración",
            lambda: self.show_page("settings"),
        )
        settings_button.pack(fill="x")
        self.nav_buttons["settings"] = settings_button

        main = tk.Frame(
            shell,
            bg=COLORS["background"],
        )
        main.pack(side="left", fill="both", expand=True)

        topbar = tk.Frame(
            main,
            bg=COLORS["topbar"],
            height=62,
            highlightbackground=COLORS["line"],
            highlightthickness=1,
        )
        topbar.pack(fill="x")
        topbar.pack_propagate(True)
        topbar.after_idle(lambda: adapt_tree(topbar))

        tk.Label(
            topbar,
            text="Administración",
            bg=COLORS["topbar"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 9),
        ).pack(side="left", padx=24)

        profile = tk.Frame(
            topbar,
            bg=COLORS["topbar"],
        )
        profile.pack(side="right", padx=22)

        tk.Label(
            profile,
            text="AD",
            width=3,
            height=1,
            bg=COLORS["sidebar_active"],
            fg="#BFDBFE",
            font=(FONT_FAMILY, 10, "bold"),
        ).pack(side="left", padx=(0, 9), ipady=5)

        tk.Label(
            profile,
            text="Administrador",
            bg=COLORS["topbar"],
            fg=COLORS["text"],
            font=(FONT_FAMILY, 9, "bold"),
        ).pack(side="left")

        privacy_control = tk.Frame(
            topbar,
            bg=COLORS["topbar"],
        )
        privacy_control.pack(side="right", padx=(0, 8))

        self.money_privacy_button = tk.Button(
            privacy_control,
            text="\uE890",
            command=self.toggle_money_visibility,
            bg=COLORS["topbar"],
            fg=COLORS["muted"],
            activebackground=COLORS["surface_hover"],
            activeforeground=COLORS["text"],
            font=(ICON_FONT, 14),
            relief="flat",
            bd=0,
            padx=9,
            pady=8,
            cursor="hand2",
        )
        self.money_privacy_button.pack(side="left")
        self.money_privacy_label = tk.Label(
            privacy_control,
            text="Ocultar valores",
            bg=COLORS["topbar"],
            fg=COLORS["muted"],
            font=(FONT_FAMILY, 8),
            cursor="hand2",
        )
        self.money_privacy_label.pack(side="left", padx=(2, 0))
        self.money_privacy_label.bind(
            "<Button-1>",
            lambda _event: self.toggle_money_visibility(),
        )
        self.content_area = ScrollArea(main, style="Page.TFrame", minimum_width=420)
        self.content_area.pack(fill="both", expand=True)
        self.content = self.content_area.body

    def toggle_money_visibility(self) -> None:
        global MONEY_VALUES_HIDDEN
        MONEY_VALUES_HIDDEN = not MONEY_VALUES_HIDDEN
        self.money_privacy_button.configure(
            text="\uED1A" if MONEY_VALUES_HIDDEN else "\uE890"
        )
        self.money_privacy_label.configure(
            text=(
                "Mostrar valores"
                if MONEY_VALUES_HIDDEN
                else "Ocultar valores"
            )
        )

        page = self.pages.get(self.current_page)

        if page is not None:
            background_reads(self).repaint(page)

    def choose_logo(self) -> None:
        branding.choose_logo(self)

    def load_logo(self, show_error: bool = False) -> bool:
        return branding.load_admin_logo(self, show_error)

    def show_page(self, key: str) -> None:
        show_page(self, key)

    def refresh_all(self, except_page: BasePage | None = None) -> None:
        refresh_pages(self)


def main() -> None:
    if "--diagnostico" in sys.argv:
        from diagnostico import main as diagnostic_main
        raise SystemExit(diagnostic_main())
    app = GymSoftApp()

    if app.ready:
        app.mainloop()


if __name__ == "__main__":
    main()
