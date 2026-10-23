from __future__ import annotations
from atlantic_ui import COPYRIGHT
from product_config import PRODUCT_NAME
from common.deployment_profile import PROFILE
import os
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk
from responsive_ui import UI_FONT
from responsive_ui import ScrollArea, fit_window
from desktop_ui import decorate_window, messagebox, simpledialog, friendly_error
from typing import Any
from pathlib import Path
import traceback
from supabase import Client, create_client
from product_config import load_config
from session_manager import managed_client

_config = load_config(validate=False)
SUPABASE_URL = _config.get('supabase_url', '')
SUPABASE_KEY = _config.get('supabase_publishable_key', '')

class CloudService:
    def __init__(self, *, session_role='admin') -> None:
        config = load_config()
        self.client = managed_client(config['supabase_url'], config['supabase_publishable_key'],
            config['supabase_url']+'|'+session_role, create_client=create_client)
        self.sessions = self.client.session_manager
        self.user_id: str | None = None
        self.email = ''
        self.gym_id: str | None = None
        self.gym_name = self.join_code = self.role = ''
        self.timezone = 'America/Bogota'
        self.license_status: dict[str, Any] = {}

    def restore_session(self) -> bool:
        session = self.sessions.restore()
        if not session:
            return False
        session = self.sessions.ensure(force=True)
        self.user_id = str(session.user.id)
        self.email = session.user.email or ''
        return True

    def sign_in(self, email: str, password: str) -> None:
        response = self.client.auth.sign_in_with_password({'email': email.strip(), 'password': password})
        if not response.user:
            raise ValueError('No fue posible iniciar sesión.')
        self.user_id = str(response.user.id)
        self.email = response.user.email or email.strip()

    def sign_up(self, email: str, password: str) -> bool:
        if len(password) < 12:
            raise ValueError('Usa una contraseña de al menos 12 caracteres.')
        response = self.client.auth.sign_up({'email': email.strip(), 'password': password})
        if not response.user:
            raise ValueError('No fue posible crear la cuenta.')
        if not response.session:
            return False
        self.user_id = str(response.user.id)
        self.email = response.user.email or email.strip()
        return True

    def clear_gym(self) -> None:
        self.gym_id = None
        self.gym_name = self.join_code = self.role = ''

    def load_gym(self) -> bool:
        try:
            ctx = self.client.rpc(PROFILE.context_rpc).execute().data or {}
        except Exception as error:
            if not PROFILE.legacy_provider or getattr(error, 'code', None) != 'P0002':
                raise
            self.clear_gym()
            return False
        if not isinstance(ctx, dict) or not ctx.get('gym_id'):
            self.clear_gym()
            return False
        if not PROFILE.legacy_provider and not ctx.get('enabled'):
            raise PermissionError('Tu cuenta fue desactivada. Contacta al proveedor.')
        self.gym_id, self.gym_name, self.role = str(ctx['gym_id']), str(ctx['gym_name']), str(ctx['role'])
        self.timezone = str(ctx.get('timezone') or 'America/Bogota')
        return True

    def verify_server(self) -> None:
        info = self.client.rpc(PROFILE.system_rpc).execute().data
        if not isinstance(info, dict) or info.get('product') != PROFILE.server_product or info.get('schema_version') != PROFILE.server_schema:
            raise ValueError('El servidor necesita una actualización compatible. Contacta al proveedor.')

    def join_gym(self, code: str, *, reception: bool = False) -> None:
        if PROFILE.legacy_provider:
            name, param = ('redeem_reception_invite', 'p_code') if reception else ('join_gym', 'p_join_code')
        else:
            name, param = 'commercial_accept_invite', 'p_code'
        self.client.rpc(name, {param: code.strip()}).execute()
        if not self.load_gym():
            raise ValueError('No se pudo activar la cuenta.')

    def create_gym(self, name: str) -> None:
        if not PROFILE.legacy_provider:
            raise PermissionError('El propietario registra el gimnasio desde Core.')
        self.client.rpc('create_gym', {'p_name': name.strip()}).execute()
        if not self.load_gym():
            raise ValueError('No se pudo confirmar el gimnasio creado.')

class LoginDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, creating_account: bool = False, *, owner: bool = False, allow_signup: bool = True) -> None:
        super().__init__(parent)
        self.result: tuple[str, str] | None = None
        self.owner = owner
        self.allow_signup = allow_signup and not owner
        self.creating_account = bool(creating_account and self.allow_signup)
        decorate_window(self)
        fit_window(self, 520, 640, parent=parent, minimum=(380, 400))
        if str(parent.state()) != 'withdrawn':
            self.transient(parent)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        from common import atlantic_ui as appearance_kit
        minimal = appearance_kit.THEME == 'minimal'
        self._minimal_brand = None
        self._login_width = 940 if minimal else 520
        if minimal:
            from atlantic_ui import COLORS
            self._minimal_brand = tk.Frame(self, bg=COLORS['background'], width=340)
            self._minimal_brand.pack(side='left', fill='both', expand=True, padx=(30,10))
            from product_config import resource_root
            from PIL import Image, ImageTk
            with Image.open(resource_root() / self._atlantic_icon_name) as source:
                brand_image = source.convert('RGBA')
                brand_image.thumbnail((112,112))
            self._minimal_brand_image = ImageTk.PhotoImage(brand_image, master=self)
            tk.Label(self._minimal_brand,image=self._minimal_brand_image,bg=COLORS['background']).pack(expand=True,anchor='s',pady=(24,14))
            tk.Label(self._minimal_brand,text=PRODUCT_NAME,bg=COLORS['background'],fg=COLORS['text'],
                     font=(UI_FONT,28,'bold')).pack()
            tk.Label(self._minimal_brand,text='La gestión de tu gimnasio,\nen un solo lugar.',
                     bg=COLORS['background'],fg=COLORS['muted'],justify='center',
                     font=(UI_FONT,12)).pack(expand=True,anchor='n',pady=(12,24))
        self.viewport = ScrollArea(self, padding=28, width=480 if minimal else 520, height=640)
        self.viewport.pack(side='right' if minimal else 'top', fill='both', expand=True)
        body = self.viewport.body
        from atlantic_ui import COLORS
        from product_config import resource_root
        from PIL import Image, ImageTk
        header = ttk.Frame(body)
        header.pack(fill='x', pady=(0, 24))
        with Image.open(resource_root() / self._atlantic_icon_name) as source:
            image = source.convert('RGBA')
            image.thumbnail((48, 48))
        self.brand_icon = ImageTk.PhotoImage(image, master=self)
        ttk.Label(header, image=self.brand_icon).pack(side='left', padx=(0, 12))
        ttk.Label(header, text=PRODUCT_NAME, font=(UI_FONT, 23, 'bold')).pack(side='left')
        self.heading = ttk.Label(body, font=(UI_FONT, 18, 'bold'))
        self.heading.pack(anchor='w')
        self.subtitle = ttk.Label(body, wraplength=420, foreground=COLORS['muted'])
        self.subtitle.pack(anchor='w', fill='x', pady=(6, 22))
        self.email, self.password = tk.StringVar(), tk.StringVar()
        ttk.Label(body, text='Correo electrónico').pack(anchor='w')
        self.email_entry = ttk.Entry(body, textvariable=self.email)
        self.email_entry.pack(fill='x', pady=(6, 16))
        ttk.Label(body, text='Contraseña').pack(anchor='w')
        self.password_entry = ttk.Entry(body, textvariable=self.password, show='*')
        self.password_entry.pack(fill='x', pady=(6, 8))
        self.show_password = tk.BooleanVar(value=False)
        ttk.Checkbutton(body, text='Mostrar contraseña', variable=self.show_password,
                        command=lambda: self.password_entry.configure(show='' if self.show_password.get() else '*')).pack(anchor='w')
        self.password_hint = ttk.Label(body, text='Usa al menos 12 caracteres.', foreground=COLORS['muted'])
        self.password_hint.pack(anchor='w', pady=(6, 0))
        self.feedback = tk.StringVar()
        self.feedback_label = ttk.Label(body, textvariable=self.feedback, foreground=COLORS['danger'], wraplength=420)
        self.feedback_label.pack(anchor='w', fill='x', pady=(10, 10))
        style = ttk.Style(self)
        style.configure('Login.Primary.TButton', background=COLORS['primary'], foreground=COLORS['background'],
                        font=(UI_FONT, 10, 'bold'), padding=(12, 12))
        style.map('Login.Primary.TButton', background=[('active', COLORS['primary_dark'])])
        self.submit = ttk.Button(body, style='Login.Primary.TButton', command=self.accept)
        self.submit.pack(fill='x')
        self.mode_button = ttk.Button(body, command=self.switch_mode)
        if self.allow_signup:
            self.mode_button.pack(fill='x', pady=(10, 0))
        ttk.Separator(body).pack(fill='x', pady=(22, 14))
        ttk.Label(body, text=COPYRIGHT, wraplength=420, foreground=COLORS['muted'], font=(UI_FONT, 8)).pack(anchor='w')
        self.render_mode()
        self.bind('<Return>', lambda _: self.accept())
        self.bind('<Escape>', lambda _: self.destroy())
        self.bind('<Configure>', self.resize_text, add='+')
        self.update_idletasks()
        fit_window(self, self._login_width, max(640, self.viewport.body.winfo_reqheight()+60), parent=parent, minimum=(380, 400))
        self.deiconify()
        self.lift()
        self.grab_set()
        self.email_entry.focus_force()

    def resize_text(self, event):
        if event.widget is self:
            if self._minimal_brand is not None:
                if self.winfo_width() < 820:
                    self._minimal_brand.pack_forget()
                elif not self._minimal_brand.winfo_manager():
                    self._minimal_brand.pack(side='left', fill='both', expand=True, padx=(30,10),before=self.viewport)
            width = max(220, self.viewport.winfo_width() - 72)
            self.subtitle.configure(wraplength=width)
            self.feedback_label.configure(wraplength=width)

    def render_mode(self):
        title = 'Crear cuenta' if self.creating_account else 'Iniciar sesión'
        self.title(f'{PRODUCT_NAME} · {title}')
        self.heading.configure(text=title)
        self.subtitle.configure(text='Administración de gimnasios y suscripciones.' if self.owner else
            'Usa el correo al que recibiste la invitación del gimnasio.' if self.creating_account else
            'Ingresa con la cuenta de tu gimnasio.')
        self.submit.configure(text=title)
        self.mode_button.configure(text='Ya tengo una cuenta' if self.creating_account else 'Crear una cuenta')
        # Reserve the same line in both modes to keep the form stable.
        self.password_hint.configure(text='Usa al menos 12 caracteres.' if self.creating_account else '')

    def switch_mode(self):
        if not self.allow_signup:
            return
        self.creating_account = not self.creating_account
        self.password.set('')
        self.show_password.set(False)
        self.password_entry.configure(show='*')
        self.feedback.set('')
        self.render_mode()
        self.email_entry.focus_set()

    def accept(self) -> None:
        email = self.email.get().strip()
        local, separator, domain = email.partition('@')
        if not separator or not local or not domain or '@' in domain or any(char.isspace() for char in email):
            self.feedback.set('Escribe un correo electrónico válido.')
            self.email_entry.focus_set()
            return
        if not self.password.get():
            self.feedback.set('Escribe tu contraseña.')
            self.password_entry.focus_set()
            return
        if self.creating_account and len(self.password.get()) < 12:
            self.feedback.set('La contraseña debe tener al menos 12 caracteres.')
            self.password_entry.focus_set()
            return
        self.result = (email, self.password.get())
        self.destroy()

def _record_login_error(error: Exception) -> None:
    """Conserva el detalle técnico sin guardar contraseñas ni sesiones."""
    try:
        root = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / PROFILE.data_folder / 'logs'
        root.mkdir(parents=True, exist_ok=True)
        path = root / 'inicio.log'
        with path.open('a', encoding='utf-8') as file:
            file.write(f'\n[{datetime.now(timezone.utc).isoformat()}] {type(error).__name__}\n')
            for frame in traceback.extract_tb(error.__traceback__):
                file.write(f'  {frame.filename}:{frame.lineno} · {frame.name}\n')
    except Exception:
        pass

def _friendly_login_error(error: Exception) -> str:
    message = friendly_error(error)
    lowered = message.casefold()
    if 'invalid login credentials' in lowered:
        return 'Correo o contraseña incorrectos.'
    if 'email not confirmed' in lowered:
        return 'Confirma tu correo electrónico antes de iniciar sesión.'
    if 'failed to fetch' in lowered or 'connection' in lowered or 'connecterror' in lowered:
        return 'No se pudo conectar con el servidor. Revisa tu conexión a internet y vuelve a intentarlo.'
    if 'schema cache' in lowered or 'commercial_system_info' in lowered or 'ztattuz_system_info' in lowered:
        return 'No se pudo conectar con el servicio. Si el problema continúa, contacta al soporte de Atlantic Gym.'
    return message

def connect_cloud(parent: tk.Misc, *, reception: bool = False) -> CloudService | None:
    from licensing import check_license
    from ui_tasks import run_io
    # The sign-in form includes account creation; no preliminary modal.
    account_mode = True
    while True:
        try:
            cloud = CloudService(session_role='reception' if reception else 'admin')
            restored = run_io(parent, cloud.restore_session)
            if not restored:
                dialog = LoginDialog(parent, creating_account=account_mode is False)
                parent.wait_window(dialog)
                if not dialog.result:
                    return None
                email, password = dialog.result
                account_mode = not dialog.creating_account
                if account_mode:
                    run_io(parent, lambda: cloud.sign_in(email, password))
                elif run_io(parent, lambda: cloud.sign_up(email, password)):
                    pass
                else:
                    messagebox.showinfo(
                        'Confirma tu correo',
                        'Te enviamos un enlace para confirmar tu correo. Ábrelo y luego vuelve a iniciar sesión.',
                        parent=parent,
                    )
                    # A partir de aquí el usuario ya creó la cuenta: el siguiente
                    # formulario siempre es el de correo y contraseña.
                    account_mode = True
                    continue
            if not run_io(parent, cloud.load_gym):
                code = simpledialog.askstring(
                    'Activar cuenta',
                    'Escribe el código de invitación de tu gimnasio:',
                    parent=parent,
                )
                if not code:
                    return None
                run_io(parent, lambda: cloud.join_gym(code, reception=reception))
            if not reception and cloud.role != 'admin':
                raise PermissionError('Esta cuenta tiene acceso a Atlantic Gym Recepción. Abre Recepción para continuar.')
            if cloud.role not in {'admin', 'receptionist'}:
                raise PermissionError('Tu cuenta no tiene acceso a esta aplicación. Consulta al administrador del gimnasio.')
            run_io(parent, cloud.verify_server)
            status = run_io(parent, lambda: check_license(cloud))
            if status.get('allowed') is not True:
                raise PermissionError(status.get('message', 'Suscripción no disponible.'))
            cloud.sessions.start()
            parent.bind('<Destroy>', lambda event, service=cloud: service.sessions.close() if event.widget is parent else None, add='+')
            return cloud
        except Exception as error:
            _record_login_error(error)
            message = _friendly_login_error(error)
            retry = messagebox.askretrycancel(
                'No se pudo iniciar sesión',
                message + '\n\nPuedes volver a intentarlo o cancelar el acceso.',
                parent=parent,
            )
            if not retry:
                return None
            # Mantiene el modo elegido. Reintentar abre directamente el
            # formulario de acceso y permite corregir correo o contraseña.
