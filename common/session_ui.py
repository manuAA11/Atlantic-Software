"""Atlantic UI recovery strip; no recurring modal prompts and no write replay."""
from tkinter import ttk
from desktop_ui import messagebox, friendly_error
from ui_tasks import run_io

LABELS = {
    'OFFLINE': 'Sin conexión. La sesión se conserva; reintentando…',
    'RECOVERING': 'Recuperando conexión…',
    'AUTH_REQUIRED': 'La sesión necesita autenticación. Puedes recuperarla aquí.',
    'SIGNED_OUT': 'Sesión cerrada.',
}


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
                dialog = LoginDialog(self.root)
                self.root.wait_window(dialog)
                if not dialog.result:
                    return
                email, password = dialog.result
                run_io(self.root, lambda: recover_identity(self.cloud, email, password), title='Recuperando sesión')
            else:
                run_io(self.root, lambda: self.cloud.sessions.ensure(force=True), title='Recuperando conexión')
        except Exception as error:
            messagebox.showerror('Recuperación de sesión', friendly_error(error), parent=self.root)
        # The user refreshes the affected screen after recovery. No automatic writes.


def install(root, cloud):
    return SessionStatus(root, cloud)
