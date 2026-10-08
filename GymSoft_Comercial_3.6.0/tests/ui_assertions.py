"""Comprueba lo que se ve y recibe el ratón, además de la geometría de Tk."""
import time
import tkinter as tk
from tkinter import ttk
from responsive_ui import ScrollArea, enable_dpi_awareness, fit_window, work_area


def pump(root, seconds=.04):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        root.update()
        time.sleep(.005)


def destroy_root(root):
    # Cada escala crea otra aplicación. No heredar temporizadores del Tk cerrado.
    from ui_test_support import window_exists
    if not window_exists(root):
        return
    for job in root.tk.splitlist(root.tk.call('after', 'info')):
        # Sus comandos Python se eliminan al destruir el widget que los creó.
        root.tk.call('after', 'cancel', job)
    root.destroy()


def prepare_test_window(window):
    """Mantiene visible solo la ventana de la comprobación automática.

    En Windows, winfo containing consulta WindowFromPoint en el escritorio:
    minimizar o tapar la prueba puede devolver None aunque el diseño sea válido.
    No se modifica el comportamiento de las ventanas del programa instalado.
    """
    if not getattr(window, '_ui_test_prepared', False):
        window._ui_test_prepared = True

        def restore(event):
            # Los hijos se ocultan al navegar. Tampoco restaurar un withdraw()
            # intencional de las pruebas de carga y de formularios.
            if event.widget is window and window.state() == 'iconic':
                window.after_idle(lambda: _restore_minimized_test(window))

        window.bind('<Unmap>', restore, add='+')
    _restore_minimized_test(window)
    window.attributes('-topmost', True)
    window.lift()


def _restore_minimized_test(window):
    if window.winfo_exists() and window.state() == 'iconic':
        print('PRUEBA: restaurando la ventana minimizada para continuar.', flush=True)
        window.deiconify()
        window.lift()


def resize_test_window(window, size):
    """Solicita el tamaño de prueba dentro del monitor, como la aplicación."""
    width, height = map(int, size.split('x'))
    prepare_test_window(window)
    fit_window(window, width, height)
    window.lift()
    pump(window)
    window._ui_test_size = size


def _geometry_parent(widget):
    if isinstance(widget, (tk.Tk, tk.Toplevel)):
        return None
    manager = widget.winfo_manager()
    if manager == 'grid':
        return widget.grid_info().get('in', widget.master)
    if manager == 'pack':
        return widget.pack_info().get('in', widget.master)
    return widget.master


def _visible_rect(widget):
    # Tk puede informar dimensiones que exceden el monitor. Solo consultar
    # puntos del área útil y del visor; un Toplevel no se recorta por su dueño.
    root = widget.winfo_toplevel()
    x, y, width, height = work_area(root)
    left, top, right, bottom = x, y, x + width, y + height
    current = widget
    while current is not None:
        left, top = max(left, current.winfo_rootx()), max(top, current.winfo_rooty())
        right = min(right, current.winfo_rootx() + current.winfo_width())
        bottom = min(bottom, current.winfo_rooty() + current.winfo_height())
        current = _geometry_parent(current)
    return left, top, right, bottom


def _diagnostic(widget, rect):
    root = widget.winfo_toplevel()
    return (f'control={widget}; visible={rect}; ventana={root.winfo_geometry()}; '
            f'estado={root.state()}; '
            f'área útil={work_area(root)}; escala Tk={root.tk.call("tk", "scaling")}; '
            f'contexto={getattr(root, "_ui_test_context", "ventana de prueba")}')


def assert_exposed(widget):
    root = widget.winfo_toplevel()
    if getattr(root, '_ui_test_prepared', False) and root.state() == 'iconic':
        _restore_minimized_test(root)
        pump(root)
    root.update_idletasks()
    assert widget.winfo_viewable(), f'Control oculto: {widget}'
    # Un control situado debajo del visor debe hacerse accesible al desplazarlo.
    ancestor = _geometry_parent(widget)
    while ancestor is not None:
        if isinstance(ancestor, ScrollArea):
            x = widget.winfo_rootx() - ancestor.body.winfo_rootx()
            y = widget.winfo_rooty() - ancestor.body.winfo_rooty()
            ancestor.canvas.xview_moveto(max(0, x - 12) / max(1, ancestor.body.winfo_width()))
            ancestor.canvas.yview_moveto(max(0, y - 12) / max(1, ancestor.body.winfo_height()))
            pump(root)
        ancestor = _geometry_parent(ancestor)
    root.update_idletasks()
    deadline = time.monotonic() + 1.5
    while True:
        left, top, right, bottom = rect = _visible_rect(widget)
        diagnostic = _diagnostic(widget, rect)
        assert right - left > 2 and bottom - top > 2, f'Control fuera del área visible: {diagnostic}'
        x, y = (left + right) // 2, (top + bottom) // 2
        hit = root.winfo_containing(x, y)
        if hit is not None:
            break
        assert time.monotonic() < deadline, (
            f'No se encontró un control en el punto visible ({x}, {y}): {diagnostic}. '
            'Mantén las ventanas de prueba visibles y el escritorio desbloqueado.'
        )
        if getattr(root, '_ui_test_prepared', False):
            prepare_test_window(root)
        # Windows puede estar restaurando la ventana. Se vuelve a consultar el
        # control real y su geometría; None nunca cuenta como una comprobación.
        pump(root)
    ancestor = hit
    while ancestor is not None and ancestor is not widget:
        ancestor = ancestor.master
    assert ancestor is widget, f'Control tapado: {diagnostic}; el ratón encuentra {hit}'
    return x - widget.winfo_rootx(), y - widget.winfo_rooty()


def click(widget):
    x, y = assert_exposed(widget)
    widget.event_generate('<Enter>', x=x, y=y)
    widget.event_generate('<ButtonPress-1>', x=x, y=y)
    widget.event_generate('<ButtonRelease-1>', x=x, y=y)
    pump(widget.winfo_toplevel())


def assert_content_exposed(parent):
    count = 0
    for child in parent.winfo_children():
        if isinstance(child, (ttk.Notebook, ttk.Treeview)) and child.winfo_viewable():
            assert_exposed(child)
            count += 1
            picker = getattr(child, '_responsive_notebook', None)
            if picker is not None and picker.winfo_viewable():
                assert_exposed(picker)
                count += 1
        if not isinstance(child, tk.Toplevel):
            count += assert_content_exposed(child)
    return count
