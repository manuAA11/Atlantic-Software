"""Foco y modalidad de Tk, incluidos los controles internos de Tcl/ttk."""
import tkinter as tk
from tkinter import ttk


def python_widget(window, path):
    """Resuelve el dueño Python de una ventana interna, como .popdown.f.l."""
    path = str(path or '')
    while path:
        try:
            return window.nametowidget(path)
        except KeyError:
            if path == '.':
                break
            path = path.rpartition('.')[0] or '.'
    return None


def focus_widget(window):
    try:
        return python_widget(window, window.tk.call('focus', '-displayof', window._w))
    except tk.TclError:
        return None


def grab_path(window):
    """Conserva un grab interno: devolver None habilitaría refrescos indebidos."""
    try:
        return str(window.tk.call('grab', 'current', window._w) or '')
    except tk.TclError:
        return ''


def close_native_dropdown(window):
    path = grab_path(window)
    owner = python_widget(window, path)
    if isinstance(owner, ttk.Combobox) and path != str(owner):
        # ttk conserva el grab anterior al desplegable. Restaurarlo antes de
        # crear el aviso evita que su Unmap posterior libere el grab del aviso.
        window.tk.call('ttk::releaseGrab', path)
        window.tk.call('ttk::combobox::Unpost', str(owner))


def capture_grab(window):
    path = grab_path(window)
    return (path, str(window.tk.call('grab', 'status', path))) if path else None


def restore_grab(window, saved):
    if saved is None:
        return
    path, mode = saved
    try:
        if not window.tk.getboolean(window.tk.call('winfo', 'exists', path)):
            return
        if not window.tk.getboolean(window.tk.call('winfo', 'viewable', path)):
            return
        window.tk.call('grab', 'set', *(('-global',) if mode == 'global' else ()), path)
        window.tk.call('focus', path)
    except tk.TclError:
        pass  # El formulario puede estar cerrándose junto con su aviso.
