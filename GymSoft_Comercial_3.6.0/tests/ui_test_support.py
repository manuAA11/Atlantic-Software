"""Esperas de QA acotadas: no necesitan que la cola gráfica quede vacía."""
import _tkinter
import time
import tkinter as tk


def window_exists(root):
    try:
        return bool(root.winfo_exists())
    except tk.TclError:
        return False


def wait_for(root, condition, description, *, timeout=8, errors=None):
    deadline = time.monotonic() + timeout
    while True:
        if not window_exists(root):
            raise AssertionError(f'La ventana de prueba se cerró durante: {description}.')
        if errors:
            raise AssertionError(f'Error de interfaz durante {description}: {errors[-1]}')
        if condition():
            return
        if time.monotonic() >= deadline:
            raise AssertionError(f'No terminó en {timeout:g} s: {description}; '
                                 f'página={getattr(root, "current_page", "—")}; '
                                 f'ventana={root.state()}.')
        # update() procesa también eventos que se agregan durante la espera.
        # Un escritorio ocupado puede no vaciar esa cola nunca. Procesar un
        # turno permite comprobar el resultado y el reloj entre cada turno.
        if not root.tk.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            time.sleep(.002)


def settle_geometry(root, widgets, description, *, timeout=8, errors=None):
    previous = [None, time.monotonic()]

    def stable():
        geometry = tuple((w.winfo_x(), w.winfo_y(), w.winfo_width(), w.winfo_height(),
                          w.winfo_reqwidth(), w.winfo_reqheight()) for w in widgets)
        if geometry != previous[0]:
            previous[:] = [geometry, time.monotonic()]
        return all(w.winfo_viewable() for w in widgets) and time.monotonic()-previous[1] >= .08

    wait_for(root, stable, description, timeout=timeout, errors=errors)
