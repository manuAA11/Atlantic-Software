from __future__ import annotations
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

_config = load_config(validate=False)
SUPABASE_URL = _config.get('supabase_url', '')
SUPABASE_KEY = _config.get('supabase_publishable_key', '')

class CloudService:
    def __init__(self) -> None:
        config = load_config()
        self.client: Client = create_client(config['supabase_url'], config['supabase_publishable_key'])
        info = self.client.rpc('commercial_system_info').execute().data
        if not isinstance(info, dict) or info.get('product') != 'gymsoft-commercial' or info.get('schema_version') != '3.0.0':
            raise ValueError('El servidor no tiene instalada la base comercial compatible. Contacta al proveedor.')
        self.user_id: str | None = None
        self.email = ''
        self.gym_id: str | None = None
        self.gym_name = self.join_code = self.role = ''
        self.timezone = 'America/Bogota'
        self.license_status: dict[str, Any] = {}

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
        ctx = self.client.rpc('commercial_context').execute().data or {}
        if not ctx.get('gym_id'):
            self.clear_gym()
            return False
        if not ctx.get('enabled'):
            raise PermissionError('Tu cuenta fue desactivada. Contacta al proveedor.')
        self.gym_id, self.gym_name, self.role = str(ctx['gym_id']), str(ctx['gym_name']), str(ctx['role'])
        self.timezone = str(ctx.get('timezone') or 'America/Bogota')
        return True

    def join_gym(self, code: str) -> None:
        self.client.rpc('commercial_accept_invite', {'p_code': code.strip()}).execute()
        if not self.load_gym():
            raise ValueError('No se pudo activar la cuenta.')

class LoginDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, creating_account: bool = False, *, owner: bool = False) -> None:
        super().__init__(parent)
        decorate_window(self)
        self.result: tuple[str, str] | None = None
        self.title('Gym soft · Crear cuenta' if creating_account else 'Gym soft · Iniciar sesión')
        fit_window(self,540,390,parent=parent)
        # Si un host oculta el root durante el inicio de sesión, una ventana
        # transient ligada a ese root puede quedar detrás de VS Code. El root
        # comercial normalmente permanece visible, pero este fallback también
        # permite abrir el diálogo correctamente en modo diagnóstico.
        if str(parent.state()) != 'withdrawn':
            self.transient(parent)
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.viewport = ScrollArea(self, padding=28, width=540, height=390)
        self.viewport.pack(fill='both', expand=True)
        body = self.viewport.body
        ttk.Label(body, text='Gym soft', font=(UI_FONT, 23, 'bold')).pack(anchor='w')
        subtitle = ('Acceso privado del propietario del software.' if owner else
                    'Crea tu cuenta con el correo de tu invitación.' if creating_account else
                    'Inicia sesión con la cuenta asignada a tu gimnasio.')
        ttk.Label(body, text=subtitle).pack(anchor='w', pady=(4, 18))
        self.email, self.password = tk.StringVar(), tk.StringVar()
        for text, var, hidden in [('Correo electrónico', self.email, False), ('Contraseña', self.password, True)]:
            ttk.Label(body, text=text).pack(anchor='w')
            entry = ttk.Entry(body, textvariable=var, show='*' if hidden else '')
            entry.pack(fill='x', pady=(3, 12))
            if not hidden:
                entry.focus_set()
        ttk.Button(body, text='Crear cuenta' if creating_account else 'Iniciar sesión', command=self.accept).pack(anchor='e')
        self.bind('<Return>', lambda _: self.accept())
        self.bind('<Escape>', lambda _: self.destroy())
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()
        self.geometry(
            f'+{max((screen_width - dialog_width) // 2, 0)}'
            f'+{max((screen_height - dialog_height) // 2, 0)}'
        )
        self.deiconify()
        self.lift()
        self.focus_force()
        self.grab_set()

    def accept(self) -> None:
        if '@' not in self.email.get() or not self.password.get():
            messagebox.showerror('Datos incompletos', 'Introduce tu correo electrónico y contraseña.', parent=self)
            return
        self.result = (self.email.get().strip(), self.password.get())
        self.destroy()

def _record_login_error(error: Exception) -> None:
    """Conserva el detalle técnico sin guardar contraseñas ni sesiones."""
    try:
        root = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'GymSoft' / 'logs'
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
    if 'schema cache' in lowered or 'commercial_system_info' in lowered:
        return 'El servicio no está disponible. Contacta al soporte de Gym soft para revisar la configuración.'
    return message

def connect_cloud(parent: tk.Misc, *, reception: bool = False) -> CloudService | None:
    from licensing import check_license
    # None significa que todavía no se ha elegido entre iniciar sesión y
    # crear una cuenta. Después de conocer el modo, un reintento vuelve
    # directamente al formulario de correo y contraseña, sin mostrar de
    # nuevo una pregunta que interrumpe el flujo.
    account_mode: bool | None = None  # True: existente; False: crear
    while True:
        try:
            cloud = CloudService()
            if account_mode is None:
                account_mode = messagebox.askyesno(
                    'Gym soft',
                    'Accede con tu correo y contraseña. Si es tu primera vez, '
                    'crea tu cuenta con la invitación del gimnasio.',
                    yeslabel='Iniciar sesión', nolabel='Crear cuenta', icon_kind='account',
                    parent=parent,
                )
            dialog = LoginDialog(parent, creating_account=account_mode is False)
            parent.wait_window(dialog)
            if not dialog.result:
                return None
            email, password = dialog.result
            if account_mode:
                cloud.sign_in(email, password)
            elif cloud.sign_up(email, password):
                pass
            else:
                messagebox.showinfo(
                    'Confirma tu correo',
                    'Abre el correo de confirmación. Después pulsa Aceptar '
                    'para volver a la pantalla de inicio de sesión.',
                    parent=parent,
                )
                # A partir de aquí el usuario ya creó la cuenta: el siguiente
                # formulario siempre es el de correo y contraseña.
                account_mode = True
                continue

            if not cloud.load_gym():
                code = simpledialog.askstring(
                    'Activar cuenta',
                    'Introduce el código de activación que recibiste para este gimnasio:',
                    parent=parent,
                )
                if not code:
                    return None
                cloud.join_gym(code)
            if not reception and cloud.role != 'admin':
                raise PermissionError('Esta cuenta utiliza Gym soft Recepción.')
            if cloud.role not in {'admin', 'receptionist'}:
                raise PermissionError('Rol no autorizado.')
            status = check_license(cloud)
            if status.get('allowed') is not True:
                raise PermissionError(status.get('message', 'Suscripción no disponible.'))
            return cloud
        except Exception as error:
            _record_login_error(error)
            message = _friendly_login_error(error)
            retry = messagebox.askretrycancel(
                'No se pudo iniciar sesión',
                message + '\n\nLa aplicación permanecerá abierta. '
                'Pulsa Reintentar después de corregir el dato o Cancelar '
                'para salir.',
                parent=parent,
            )
            if not retry:
                return None
            # Mantiene el modo elegido. Reintentar abre directamente el
            # formulario de acceso y permite corregir correo o contraseña.
