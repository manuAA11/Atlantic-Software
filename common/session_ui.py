"""Atlantic UI session recovery and explicit sign-out, without write replay."""
import tkinter as tk
from tkinter import ttk
from desktop_ui import messagebox, friendly_error
from ui_tasks import run_io

LABELS = {
    'OFFLINE': 'Sin conexión. Reintentaremos automáticamente.',
    'RECOVERING': 'Recuperando conexión…',
    'AUTH_REQUIRED': 'Inicia sesión de nuevo para continuar.',
    'SIGNED_OUT': 'Sesión cerrada.',
}


def logout_button(parent, root):
    control = ttk.Button(parent, text='Cerrar sesión', style='Danger.TButton',
                         command=lambda: root.session_status.sign_out())
    control.pack(fill='x', pady=(4, 6))
    return control


def run_application(factory):
    """Build a fresh workspace after logout; never reuse another user's pages."""
    while True:
        app = factory()
        if app.ready:
            app.mainloop()
        if not getattr(app, '_return_to_login', False):
            return


def close_workspace(root):
    if getattr(root, '_foreground_io', False):
        root.bell()
        return
    listener = getattr(root, 'realtime_listener', None)
    if listener is not None:
        listener.stop()
    # A fresh Tk/login follows explicit logout. Do not let callbacks from the
    # destroyed workspace fire while the new interpreter is processing events.
    for job in root.tk.splitlist(root.tk.call('after', 'info')):
        root.tk.call('after', 'cancel', job)
    root.destroy()


def sign_out_session(sessions, before_signout=None):
    """An offline server must not retain local credentials after explicit logout."""
    with sessions.quiesce():
        if before_signout is not None:
            before_signout()
        try:
            sessions.logout()
        except Exception:
            # logout() clears local state in finally. Only continue if that
            # removal really succeeded; a disk/permission error is not success.
            if (sessions.state != 'SIGNED_OUT' or sessions.session is not None
                    or sessions.store.load() is not None):
                raise


def logout_busy(root):
    if getattr(root, '_foreground_io', False):
        return True
    door = getattr(root, 'door', None)
    if door is not None and door.is_busy:
        return True
    service = getattr(getattr(getattr(root, 'biometric_access', None), 'native_reader', None), 'service', None)
    if service is not None and (service.target is not None or service.pending is not None):
        return True
    for page in getattr(root, 'pages', {}).values():
        pos = getattr(page, 'pos', None)
        if pos is not None and (getattr(pos, 'pending', None) or getattr(pos, 'inventory_pending', None)
                                or getattr(getattr(pos, 'cart', None), 'rows', {})):
            return True
    return any(isinstance(child, tk.Toplevel) and child.winfo_exists()
               for child in root.winfo_children())


def recover_identity(cloud, email, password):
    """A recovered credential may not silently switch an open gym workspace."""
    expected = (cloud.user_id, cloud.gym_id, cloud.role)
    expected_email = cloud.email
    if email.strip().casefold() != expected_email.strip().casefold():
        raise ValueError('Usa la misma cuenta con la que abriste este gimnasio.')
    try:
        cloud.sign_in(email, password)
        if not cloud.load_gym() or (cloud.user_id, cloud.gym_id, cloud.role) != expected:
            raise PermissionError('La cuenta o sus permisos cambiaron. Contacta al administrador.')
    except Exception:
        try:
            cloud.sessions.logout()
        except Exception:
            pass
        cloud.user_id, cloud.gym_id, cloud.role = expected
        cloud.email = expected_email
        raise
    cloud.sessions.start()


class SessionStatus:
    def __init__(self, root, cloud):
        self.root, self.cloud = root, cloud
        self.frame = ttk.Frame(root, style='Card.TFrame', padding=(12, 6))
        self.label = ttk.Label(self.frame, text='', wraplength=620)
        self.label.pack(side='left', fill='x', expand=True)
        self.button = ttk.Button(self.frame, text='Recuperar conexión', command=self.recover)
        self.button.pack(side='right', padx=(8, 0))
        self.closed = False
        self.job = None
        root.bind('<Destroy>', self.destroy, add='+')
        self.job = root.after(500, self.poll)

    def destroy(self, event):
        if event.widget is not self.root:
            return
        self.closed = True
        if self.job:
            self.root.after_cancel(self.job)
            self.job = None

    def poll(self):
        self.job = None
        if self.closed:
            return
        state = self.cloud.sessions.state
        if state in LABELS:
            self.label.configure(text=LABELS[state], wraplength=max(180, self.root.winfo_width()-240))
            self.button.configure(text='Iniciar sesión' if state in {'AUTH_REQUIRED', 'SIGNED_OUT'} else 'Recuperar conexión')
            if not self.frame.winfo_manager():
                # Insert before the expanding shell, retaining existing navigation.
                others = [widget for widget in self.root.pack_slaves() if widget is not self.frame]
                options = {'before': others[0]} if others else {}
                self.frame.pack(side='bottom', fill='x', **options)
        else:
            self.frame.pack_forget()
        self.job = self.root.after(1000, self.poll)

    def recover(self):
        if getattr(self.root, '_foreground_io', False):
            self.root.bell()
            return
        try:
            if self.cloud.sessions.state in {'AUTH_REQUIRED', 'SIGNED_OUT'}:
                from runtime_cloud import LoginDialog
                from common.runtime_cloud import _friendly_login_error
                feedback = ''
                while True:
                    dialog = LoginDialog(self.root, allow_signup=False,
                        initial_email=self.cloud.email, error_message=feedback)
                    self.root.wait_window(dialog)
                    if not dialog.result:
                        return
                    email, password = dialog.result
                    try:
                        run_io(self.root, lambda: recover_identity(self.cloud, email, password), title='Recuperando sesión')
                    except Exception as error:
                        feedback = _friendly_login_error(error)
                    else:
                        return
            else:
                run_io(self.root, lambda: self.cloud.sessions.ensure(force=True), title='Recuperando conexión')
        except Exception as error:
            messagebox.showerror('Recuperación de sesión', friendly_error(error), parent=self.root)
        # The user refreshes the affected screen after recovery. No automatic writes.

    def sign_out(self):
        if getattr(self.root, '_signing_out', False):
            return
        if logout_busy(self.root):
            messagebox.showinfo('Finaliza las operaciones',
                'Finaliza las ventas, lecturas y formularios abiertos antes de cerrar sesión.', parent=self.root)
            return
        self.root._signing_out = True
        was_ready = self.root.ready
        self.root.ready = False
        door = getattr(self.root, 'door', None)
        stop_access = getattr(door, 'close', None)
        try:
            run_io(self.root, lambda: sign_out_session(self.cloud.sessions, stop_access), title='Cerrando sesión')
        except Exception:
            self.root._signing_out = False
            self.root.ready = was_ready and self.cloud.sessions.state == 'ONLINE'
            messagebox.showerror('No se pudo completar el cierre de sesión',
                'No se pudo completar la limpieza de la sesión de este equipo. Contacta al soporte antes de volver a iniciar sesión.',
                parent=self.root)
            return
        # Destroy the old workspace and its hardware/read workers. The entry
        # point then opens a new credential form from the cleared session store.
        self.root._return_to_login = True
        self.root.withdraw()
        self.root.close_app()


def install(root, cloud):
    return SessionStatus(root, cloud)
