"""Operaciones de datos fuera de Tk, con espera modal y resultado único.

El trabajador sólo recibe una función de datos. Toda interacción con Tk se
realiza en el hilo de la ventana. No reintenta escrituras automáticamente.
"""
from functools import wraps
import queue
import threading
import tkinter as tk
from tkinter import ttk

from tk_window_state import capture_grab, close_native_dropdown, restore_grab


def submit_payment(dialog, payload, submit):
    """Cerrar el formulario sólo después de confirmar el guardado."""
    if getattr(dialog, '_submitting_payment', False):
        return
    dialog._submitting_payment = True
    try:
        if submit is not None:
            dialog.saved_result = submit(payload)
    except Exception as error:
        from desktop_ui import messagebox
        messagebox.showerror('No se pudo registrar el pago', str(error), parent=dialog)
        return
    finally:
        dialog._submitting_payment = False
    dialog.result = payload
    dialog.destroy()


def run_io(parent, operation, title='Procesando operación'):
    root = parent._root()
    if getattr(root, '_foreground_io', False):
        raise RuntimeError('Hay una operación en curso. Espera su resultado antes de continuar.')
    root._foreground_io = True
    responses = queue.Queue(maxsize=1)
    previous = None
    window = None
    jobs = set()

    def worker():
        try:
            responses.put((True, operation()))
        except Exception as error:
            responses.put((False, error))

    try:
        threading.Thread(target=worker, name='GymSoft-Operacion', daemon=True).start()
        # Las respuestas locales rápidas no abren una ventana de progreso.
        try:
            outcome = responses.get_nowait()
        except queue.Empty:
            from desktop_ui import BG, TEXT, MUTED, UI_FONT, decorate_window
            close_native_dropdown(parent)
            previous = capture_grab(parent)
            window = tk.Toplevel(parent.winfo_toplevel())
            window.withdraw()
            window.title(title)
            window.configure(bg=BG)
            window.transient(parent.winfo_toplevel())
            window.protocol('WM_DELETE_WINDOW', window.bell)
            done = tk.BooleanVar(root, False)
            result = []
            window.bind('<Destroy>', lambda e: done.set(True) if e.widget is window else None, add='+')
            # Un grab local protege también durante los primeros milisegundos,
            # antes de que haga falta mostrar el aviso. Conserva el modal previo.
            window.grab_set()

            def schedule(delay, callback):
                identity = None
                def invoke():
                    jobs.discard(identity)
                    callback()
                identity = root.after(delay, invoke)
                jobs.add(identity)

            def show():
                if done.get():
                    return
                decorate_window(window)
                ttk.Label(window, text=title, foreground=TEXT,
                          font=(UI_FONT, 12, 'bold')).pack(anchor='w', padx=24, pady=(22, 8))
                ttk.Label(window, text='Esperando la respuesta del servidor…', foreground=MUTED).pack(
                    anchor='w', padx=24, pady=(0, 12))
                progress = ttk.Progressbar(window, mode='indeterminate')
                progress.pack(fill='x', padx=24, pady=(0, 22))
                from responsive_ui import fit_window
                fit_window(window, 450, 170, parent=parent.winfo_toplevel(), minimum=(300, 140))
                window.deiconify()
                window.lift()
                progress.start(25)

            def poll():
                try:
                    result.append(responses.get_nowait())
                except queue.Empty:
                    schedule(10, poll)
                else:
                    done.set(True)

            schedule(120, show)
            poll()
            if not done.get():
                root.wait_variable(done)
            if not result:
                raise RuntimeError('La ventana se cerró durante la operación. Comprueba el historial antes de repetirla.')
            outcome = result[0]
        if outcome[0]:
            return outcome[1]
        raise outcome[1]
    finally:
        root._foreground_io = False
        for job in jobs:
            try:
                root.after_cancel(job)
            except tk.TclError:
                pass
        if window is not None:
            try:
                window.destroy()
                restore_grab(parent, previous)
            except tk.TclError:
                pass


class UiDatabase:
    """Adapta la base existente sin cambiar sus permisos, consultas ni retornos.

    Las páginas conservan su flujo secuencial. Las lecturas que ya ejecuta
    BackgroundReads pasan directamente a la base; una llamada desde Tk usa
    run_io y deja que el SO siga dibujando y moviendo la ventana.
    """
    def __init__(self, database, root):
        self._database = database
        self._root_window = root
        self._ui_thread = threading.get_ident()

    def __getattr__(self, name):
        value = getattr(self._database, name)
        if not callable(value) or name == 'invalidate_today_cache':
            return value

        @wraps(value)
        def call(*args, **kwargs):
            if threading.get_ident() != self._ui_thread:
                return value(*args, **kwargs)
            return run_io(self._root_window, lambda: value(*args, **kwargs),
                          'Consultando información' if name.startswith(
                              ('list_', 'get_', 'check_', '_today', 'today', 'dashboard', 'membership_', 'ticket_', 'session_'))
                          else 'Procesando operación')
        return call
