"""Ventanas y avisos oscuros compartidos; nunca oculta el root de la aplicación."""
from __future__ import annotations

import ast
import ctypes
import json
import os
import sys
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from responsive_ui import UI_FONT
from responsive_ui import ScrollArea, fit_window
from PIL import Image, ImageTk
from ui_visuals import install_indicators, dialog_icon
from tk_window_state import capture_grab, close_native_dropdown, restore_grab

BG = '#0b1220'
SURFACE = '#172235'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#16c784'
LINE = '#2a3953'


def resource_path(name: str) -> Path:
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / name


def set_app_id(component: str) -> None:
    if sys.platform == 'win32':
        try:
            setter=ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
            setter.argtypes=[ctypes.c_wchar_p]
            setter.restype=ctypes.c_long
            setter('GymSoft.Comercial.' + component)
        except (AttributeError, OSError):
            pass


def decorate_window(window: tk.Misc) -> None:
    """Icono GS y barra de título oscura, también para login y formularios."""
    window.configure(bg=BG)
    path = resource_path('icono.ico')
    if path.is_file():
        try:
            window.iconbitmap(str(path))
        except tk.TclError:
            try:
                with Image.open(path) as source:
                    photo = ImageTk.PhotoImage(source.convert('RGBA'), master=window)
                window.iconphoto(True, photo)
                window._gymsoft_icon = photo
            except (OSError, tk.TclError):
                pass
    if sys.platform != 'win32':
        return

    def titlebar():
        try:
            from ctypes import wintypes
            ancestor = ctypes.windll.user32.GetAncestor
            ancestor.argtypes = [wintypes.HWND, wintypes.UINT]
            ancestor.restype = wintypes.HWND
            hwnd = ancestor(window.winfo_id(), 2)
            setter = ctypes.windll.dwmapi.DwmSetWindowAttribute
            setter.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
            dark = ctypes.c_int(1)
            if setter(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark)):
                setter(hwnd, 19, ctypes.byref(dark), ctypes.sizeof(dark))
            # Windows 11: color BGR de título y texto. Versiones anteriores lo ignoran.
            for attribute, value in [(35, 0x20120B), (36, 0xFCFAF8)]:
                color = wintypes.DWORD(value)
                setter(hwnd, attribute, ctypes.byref(color), ctypes.sizeof(color))
        except (OSError, AttributeError, tk.TclError):
            pass
    window.after_idle(titlebar)
    window.bind('<Map>',lambda event: titlebar() if event.widget is window else None,add='+')


def configure_dark_styles(root: tk.Misc) -> None:
    style = ttk.Style(root)
    if 'clam' in style.theme_names():
        style.theme_use('clam')
    style.configure('.', background=BG, foreground=TEXT, font=(UI_FONT, 10))
    for pattern, value in {
        '*TCombobox*Listbox.background': SURFACE,
        '*TCombobox*Listbox.foreground': TEXT,
        '*TCombobox*Listbox.selectBackground': '#214a70',
        '*TCombobox*Listbox.selectForeground': TEXT,
        '*Listbox.background': SURFACE, '*Listbox.foreground': TEXT,
    }.items():
        root.option_add(pattern, value)
    style.configure('TFrame', background=BG)
    style.configure('TLabel', background=BG, foreground=TEXT)
    style.configure('TEntry', fieldbackground=SURFACE, foreground=TEXT,
                    insertcolor=TEXT, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, padding=7)
    style.configure('TCombobox', fieldbackground=SURFACE, background=SURFACE,
                    foreground=TEXT, arrowcolor=TEXT, bordercolor=LINE, padding=7)
    style.map('TCombobox', fieldbackground=[('readonly', SURFACE), ('disabled', BG)],
              foreground=[('readonly', TEXT), ('disabled', MUTED)])
    style.configure('TButton', background='#24354f', foreground=TEXT, padding=(12, 9), borderwidth=0)
    style.configure('TButton', bordercolor=LINE, lightcolor=LINE, darkcolor=LINE,
                    focuscolor='#93c5fd')
    style.map('TButton', background=[('disabled', SURFACE), ('active', '#305180')],
              foreground=[('disabled', MUTED)])
    for name in ['TCheckbutton', 'TRadiobutton']:
        style.configure(name, background=BG, foreground=TEXT, indicatorbackground=SURFACE)
        style.map(name, background=[('active', BG)], foreground=[('disabled', MUTED), ('active', TEXT)])
    install_indicators(root)
    for name in ['Vertical.TScrollbar', 'Horizontal.TScrollbar']:
        style.configure(name, background='#33465f', troughcolor=BG, arrowcolor=TEXT,
                        bordercolor=BG, lightcolor=BG, darkcolor=BG)
        style.map(name, background=[('active', '#4a6688')])
    style.configure('TLabelframe', background=BG, bordercolor=LINE)
    style.configure('TLabelframe.Label', background=BG, foreground=TEXT)
    style.configure('TNotebook', background=BG, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
    style.configure('TNotebook.Tab', background=SURFACE, foreground=MUTED,
                    bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, focuscolor='#93c5fd', padding=(16, 9))
    style.map('TNotebook.Tab', background=[('selected', SURFACE), ('active', '#24354f')],
              foreground=[('selected', TEXT), ('active', TEXT)])
    style.configure('TSeparator', background=LINE)


def friendly_error(error) -> str:
    message = getattr(error, 'message', None)
    if not message:
        message = str(error).strip()
        if message.startswith('{'):
            try:
                first, separator, remainder = message.partition('\n')
                try:value = json.loads(first)
                except ValueError:value = ast.literal_eval(first)
                if isinstance(value, dict):
                    message = str(value.get('message') or message) + (separator+remainder if separator else '')
            except (ValueError, SyntaxError):
                pass
    lowered = str(message).casefold()
    if 'invalid login credentials' in lowered:
        return 'Correo o contraseña incorrectos.'
    if 'email not confirmed' in lowered:
        return 'Confirma tu correo antes de iniciar sesión.'
    if 'user already registered' in lowered:
        return 'Ya existe una cuenta con ese correo. Selecciona Iniciar sesión.'
    if 'email rate limit' in lowered or 'too many requests' in lowered:
        return 'Se realizaron varios intentos en poco tiempo. Espera unos minutos y vuelve a intentarlo.'
    if 'error sending confirmation email' in lowered:
        return 'No se pudo enviar el correo de confirmación. Contacta al soporte de Gym soft.'
    if any(term in lowered for term in ('connecterror','connection refused','connection reset','failed to fetch','name resolution','timed out','network is unreachable')):
        return 'No se pudo confirmar la operación con el servidor. Revisa tu conexión, actualiza los datos y consulta el historial antes de repetirla.'
    if 'permission denied' in lowered:
        return 'Tu cuenta no tiene permiso para esta acción. Inicia sesión de nuevo o consulta al responsable del gimnasio.'
    if 'jwt expired' in lowered or 'refresh token' in lowered:
        return 'La sesión venció. Cierra y vuelve a abrir la aplicación para iniciar sesión.'
    if 'schema cache' in lowered or 'could not find the function' in lowered:
        return 'El servidor no tiene disponible esta función. Contacta al proveedor; no reinstales la base completa.'
    if 'duplicate key value' in lowered:
        return 'Ya existe un registro con ese dato. Revisa el documento, nombre, SKU o referencia antes de guardar.'
    if 'violates check constraint' in lowered or 'out of range' in lowered:
        return 'Hay un valor fuera de los límites permitidos. Revisa importes, cantidades, fechas y cupos.'
    if 'violates not-null constraint' in lowered:
        return 'Falta un campo obligatorio. Completa los datos del registro.'
    if 'violates foreign key constraint' in lowered:
        return 'La operación afecta registros relacionados. Revisa las relaciones y el gimnasio de destino.'
    if 'deadlock detected' in lowered:
        return 'Coincidieron dos operaciones. Actualiza la lista y revisa el historial antes de reintentar.'
    if 'statement timeout' in lowered:
        return 'La base canceló la operación por tiempo límite. Actualiza y revisa el historial; para un respaldo grande solicita una importación asistida.'
    return str(message or 'No se pudo completar la operación.')


def install_error_handler(root):
    """Los fallos de callbacks no quedan ocultos al ejecutar sin consola."""
    def handle(kind,error,tb):
        if not root.winfo_exists():return
        reference='GS-'+datetime.now().strftime('%Y%m%d-%H%M%S')
        try:
            folder=Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'GymSoft' / 'logs'
            folder.mkdir(parents=True,exist_ok=True)
            with (folder/'aplicacion.log').open('a',encoding='utf-8') as f:
                # Sin variables locales, tokens, credenciales ni contenido de registros.
                frames=traceback.extract_tb(tb)
                f.write(f'\n{reference} {kind.__name__}\n'+''.join(
                    f'  {frame.filename}:{frame.lineno} · {frame.name}\n' for frame in frames))
        except OSError:pass
        messagebox.showerror('No se pudo completar la acción',
            'Actualiza esta sección y revisa el resultado antes de repetir la operación. '
            'Si el problema continúa, contacta al soporte de Gym soft.\n\nReferencia: '+reference,parent=root)
    root.report_callback_exception=handle


def button(parent, text, command, *, primary=False):
    return tk.Button(parent, text=text, command=command,
                     bg=ACCENT if primary else '#24354f', fg='#04130d' if primary else TEXT,
                     activebackground='#0ead70' if primary else '#305180',
                     activeforeground=TEXT, relief='flat', borderwidth=0,
                     highlightbackground=LINE, highlightcolor='#93c5fd', highlightthickness=1,
                     font=(UI_FONT, 10, 'bold'), padx=16, pady=9, cursor='hand2')


class Modal(tk.Toplevel):
    def __init__(self, parent, title):
        close_native_dropdown(parent)
        super().__init__(parent)
        self.withdraw()
        self.title(title)
        decorate_window(self)
        self.result = None
        self.previous_grab = capture_grab(parent)
        host = parent.winfo_toplevel()
        if host.state() != 'withdrawn':
            self.transient(host)
        self.viewport = ScrollArea(self, padding=22, width=650, height=440)
        self.viewport.pack(fill='both', expand=True)
        self.body = self.viewport.body
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.bind('<Escape>', lambda _: self.close())

    def show(self):
        self.update_idletasks()
        requested_width = getattr(self, 'preferred_width', min(980, max(480, self.body.winfo_reqwidth()+24)))
        requested_height = min(850, max(getattr(self, 'minimum_height', 300), self.body.winfo_reqheight()+48))
        fit_window(self, requested_width, requested_height, parent=self.master.winfo_toplevel())
        self.deiconify()
        self.lift()
        self.focus_force()
        self.grab_set()
        initial=getattr(self,'initial_focus',None)
        if initial is not None:self.after_idle(initial.focus_set)
        self.wait_window(self)
        return self.result

    def close(self, result=None):
        self.result = result
        self.destroy()

    def destroy(self):
        previous = getattr(self, 'previous_grab', None)
        super().destroy()
        restore_grab(self.master, previous)


def _parent(options):
    parent = options.get('parent') or tk._default_root
    if parent is None:
        raise RuntimeError('Los diálogos de Gym soft requieren una ventana principal.')
    return parent


def _message(title, message, choices, icon, options, default=None):
    win = Modal(_parent(options), title or 'Gym soft')
    win.result = default
    win.protocol('WM_DELETE_WINDOW', lambda: win.close(default))
    win.bind('<Escape>', lambda _: win.close(default))
    win.minimum_height = 180
    win.preferred_width = 580
    heading = tk.Frame(win.body, bg=BG)
    heading.pack(fill='x', pady=(0, 16))
    kind = options.get('icon_kind') or {'i':'info', '!':'warning', '×':'error', '?':'confirm'}.get(icon, 'info')
    scale = float(win.tk.call('tk', 'scaling')) / (96 / 72)
    win._message_icon = ImageTk.PhotoImage(dialog_icon(kind, round(40 * scale)), master=win)
    tk.Label(heading, image=win._message_icon, bg=BG).pack(side='left', padx=(0, 14))
    tk.Label(heading, text=title or 'Gym soft', bg=BG, fg=TEXT, font=(UI_FONT, 14, 'bold'),
             wraplength=435, anchor='w', justify='left').pack(side='left', fill='x', expand=True)
    content = friendly_error(message)
    if options.get('detail'):
        content += '\n\n' + str(options['detail'])
    tk.Label(win.body, text=content, bg=BG, fg=TEXT, wraplength=525, anchor='w', justify='left',
             font=(UI_FONT, 11)).pack(fill='x', pady=(0, 22))
    tk.Frame(win.body, height=1, bg=LINE).pack(fill='x', pady=(0, 16))
    controls = tk.Frame(win.body, bg=BG)
    controls.pack(fill='x')
    # Primaria a la derecha. Cancelar/No conserva el resultado y el cierre originales.
    for label, value in choices:
        label = options.get('yeslabel', label) if value is True else options.get('nolabel', label) if value is False else label
        b = button(controls, label, lambda v=value: win.close(v), primary=value is True or value == 'ok')
        b.pack(side='right', padx=(8, 0))
        if value == default and not isinstance(default, bool):
            win.initial_focus = b
    # Enter confirms only single-button notices; questions require a deliberate choice.
    if len(choices) == 1:
        win.bind('<Return>', lambda _: win.close(choices[0][1]))
    return win.show()


class DarkMessageBox:
    @staticmethod
    def showinfo(title=None, message=None, **options):
        return _message(title, message, [('Aceptar', 'ok')], 'i', options, 'ok')

    @staticmethod
    def showwarning(title=None, message=None, **options):
        return _message(title, message, [('Aceptar', 'ok')], '!', options, 'ok')

    @staticmethod
    def showerror(title=None, message=None, **options):
        return _message(title, message, [('Aceptar', 'ok')], '×', options, 'ok')

    @staticmethod
    def askyesno(title=None, message=None, **options):
        return _message(title, message, [('Sí', True), ('No', False)], '?', options, False)

    @staticmethod
    def askokcancel(title=None, message=None, **options):
        return _message(title, message, [('Continuar', True), ('Cancelar', False)], '?', options, False)

    @staticmethod
    def askretrycancel(title=None, message=None, **options):
        return _message(title, message, [('Reintentar', True), ('Cancelar', False)], '!', options, False)

    @staticmethod
    def askyesnocancel(title=None, message=None, **options):
        return _message(title, message, [('Sí', True), ('No', False), ('Cancelar', None)], '?', options)


class DarkSimpleDialog:
    @staticmethod
    def askstring(title, prompt, **options):
        win = Modal(_parent(options), title)
        tk.Label(win.body, text=prompt, bg=BG, fg=TEXT, wraplength=500, justify='left',
                 font=(UI_FONT, 11)).pack(anchor='w', pady=(0, 14))
        var = tk.StringVar(master=win, value=options.get('initialvalue', ''))
        entry = tk.Entry(win.body, textvariable=var, bg=SURFACE, fg=TEXT, insertbackground=TEXT,
                         show=options.get('show', ''), width=48, font=(UI_FONT, 11), relief='flat')
        entry.pack(fill='x', ipady=8, pady=(0, 15))
        error = tk.Label(win.body, bg=BG, fg='#fb7185', wraplength=480, justify='left')
        error.pack(fill='x')
        def accept():
            result = var.get()
            validate = options.get('validate')
            try:
                if validate:
                    result = validate(result)
            except ValueError as exc:
                error.configure(text=str(exc))
                entry.focus_set()
                return
            win.close(result)
        controls = tk.Frame(win.body, bg=BG)
        controls.pack(fill='x', pady=(10, 0))
        button(controls, 'Continuar', accept, primary=True).pack(side='right')
        button(controls, 'Cancelar', win.close).pack(side='right', padx=8)
        win.bind('<Return>', lambda _: accept())
        win.initial_focus=entry
        return win.show()

    @staticmethod
    def askinteger(title, prompt, **options):
        def validate(value):
            try:
                number = int(value.strip())
            except ValueError:
                raise ValueError('Escribe un número entero.') from None
            if options.get('minvalue') is not None and number < options['minvalue']:
                raise ValueError(f"El mínimo es {options['minvalue']}.")
            if options.get('maxvalue') is not None and number > options['maxvalue']:
                raise ValueError(f"El máximo es {options['maxvalue']}.")
            return number
        return DarkSimpleDialog.askstring(title, prompt, **{**options, 'validate': validate})


messagebox = DarkMessageBox()
simpledialog = DarkSimpleDialog()
