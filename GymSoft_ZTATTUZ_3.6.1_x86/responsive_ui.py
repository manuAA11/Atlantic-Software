"""Diseño adaptable compartido. Conserva el tamaño de texto elegido en Windows."""
from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from tkinter import ttk

from atlantic_ui import COLORS, UI_FONT
BG = COLORS['background']


def enable_dpi_awareness():
    # Antes de crear Tk. No se fuerza tk scaling ni se reduce la fuente al 125 %.
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass


def scale(widget):
    return max(1.0, float(widget.tk.call('tk', 'scaling')) / (96 / 72))


def window_profile(window):
    """Dos distribuciones por escala. La posición no forma parte del perfil."""
    maximized = window.state() == 'zoomed'
    if sys.platform != 'win32':
        try: maximized = maximized or bool(window.attributes('-zoomed'))
        except tk.TclError: pass
    return ('maximized' if maximized else 'normal', round(scale(window), 3))


class LayoutModes:
    def __init__(self, root):
        self.root = root
        self.profile = window_profile(root)
        # Agrupa los eventos del SO en el siguiente ciclo de Tk. No introduce
        # esperas temporizadas ni capas que tapen el contenido.
        self.pending_profile = self.profile
        self.listeners = {}
        self.settled_listeners = {}
        self.job = None
        self.transitioning = False
        root.bind('<Configure>', self.changed, add='+')
        root.bind('<Destroy>', self.destroyed, add='+')

    def _dispatch(self, listeners):
        for widget, callbacks in list(listeners.items()):
            if not widget.winfo_exists():
                continue
            for callback in tuple(callbacks):
                try:
                    callback()
                except Exception:
                    # Un fallo no deja el resto de la ventana sin actualizar.
                    self.root.report_callback_exception(*sys.exc_info())

    def changed(self, event):
        if event.widget is not self.root: return
        if self.root.state() in ('withdrawn', 'iconic'): return
        profile = window_profile(self.root)
        if profile == self.profile:
            self.pending_profile = profile
            if self.job is not None:
                self.root.after_cancel(self.job)
                self.job = None
            if self.transitioning:
                self.transitioning = False
                self._dispatch(self.settled_listeners)
            return
        self.pending_profile = profile
        self.transitioning = True
        if self.job is None:
            self.job = self.root.after_idle(self.notify)

    def notify(self):
        self.job = None
        changed = self.pending_profile != self.profile
        self.profile = self.pending_profile
        self.transitioning = False
        if changed:
            self._dispatch(self.listeners)
        self._dispatch(self.settled_listeners)

    def destroyed(self, event):
        if event.widget is self.root:
            if self.job is not None:
                self.root.after_cancel(self.job)
                self.job = None
            self.listeners.clear()
            self.settled_listeners.clear()

    def register(self, widget, callback):
        if widget not in self.listeners:
            self.listeners[widget] = []
            widget.bind('<Destroy>', lambda e: self.listeners.pop(widget, None)
                        if e.widget is widget else None, add='+')
        self.listeners[widget].append(callback)

    def register_settled(self, widget, callback):
        if widget not in self.settled_listeners:
            self.settled_listeners[widget] = []
            widget.bind(
                '<Destroy>',
                lambda e: self.settled_listeners.pop(widget, None)
                if e.widget is widget else None,
                add='+',
            )
        self.settled_listeners[widget].append(callback)


def layout_modes(widget):
    root = widget.winfo_toplevel()
    if not hasattr(root, '_layout_modes'): root._layout_modes = LayoutModes(root)
    return root._layout_modes


def bind_layout_mode(widget, callback):
    layout_modes(widget).register(widget, callback)
    widget.after_idle(callback)


def work_area(window):
    if sys.platform == 'win32':
        try:
            from ctypes import wintypes
            class Info(ctypes.Structure):
                _fields_ = [('size', wintypes.DWORD), ('monitor', wintypes.RECT),
                            ('work', wintypes.RECT), ('flags', wintypes.DWORD)]
            monitor = ctypes.windll.user32.MonitorFromWindow
            monitor.argtypes = [wintypes.HWND, wintypes.DWORD]
            monitor.restype = wintypes.HANDLE
            get_info = ctypes.windll.user32.GetMonitorInfoW
            get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Info)]
            info = Info(); info.size = ctypes.sizeof(info)
            if get_info(monitor(window.winfo_id(), 2), ctypes.byref(info)):
                r = info.work
                return r.left, r.top, r.right-r.left, r.bottom-r.top
        except (AttributeError, OSError, tk.TclError):
            pass
    return 0, 0, window.winfo_screenwidth(), window.winfo_screenheight()-40


def fit_window(window, width=None, height=None, *, parent=None, minimum=(380, 260)):
    window.update_idletasks()
    x, y, sw, sh = work_area(parent or window)
    width = min(int(width or window.winfo_width()), max(240, sw-32))
    height = min(int(height or window.winfo_height()), max(180, sh-56))
    window.minsize(min(minimum[0], width), min(minimum[1], height))
    window.resizable(True, True)
    if parent is not None and parent.winfo_viewable():
        px = parent.winfo_rootx()+(parent.winfo_width()-width)//2
        py = parent.winfo_rooty()+(parent.winfo_height()-height)//2
    else:
        px, py = x+(sw-width)//2, y+(sh-height)//2
    px = max(x+8, min(px, x+sw-width-8))
    py = max(y+8, min(py, y+sh-height-40))
    window.geometry(f'{width}x{height}{px:+d}{py:+d}')


def invalidate_minimum_width(widget):
    while isinstance(widget, tk.Misc):
        widget.__dict__.pop('_layout_minimum_cache', None)
        widget = widget.master


def _horizontal_padding(widget, value):
    values = value if isinstance(value, (tuple, list)) else widget.tk.splitlist(str(value))
    if not values: return 0
    pixels = [widget.winfo_pixels(v) for v in values]
    return pixels[0] * 2 if len(pixels) == 1 else pixels[0] + pixels[1]


def minimum_layout_width(widget):
    """Ancho legible de la distribución, sin imponer el ancho de las tablas.

    Conserva las columnas. Los textos pueden envolver; tablas y listas tienen
    su propio visor. Sólo se calcula de nuevo al cambiar controles o escala.
    """
    factor = scale(widget)
    cached = getattr(widget, '_layout_minimum_cache', None)
    if cached is not None and cached[0] == factor:
        return cached[1]
    if isinstance(widget, (ttk.Treeview, tk.Text, tk.Listbox)):
        width = int(260 * factor)
    elif isinstance(widget, tk.Canvas):
        width = min(widget.winfo_reqwidth(), int(260 * factor))
    elif isinstance(widget, (tk.Label, ttk.Label)):
        info = widget.pack_info() if widget.winfo_manager() == 'pack' else {}
        fixed = info.get('side') in ('left', 'right') and info.get('fill') == 'none'
        width = widget.winfo_reqwidth() if fixed else min(widget.winfo_reqwidth(), int(120 * factor))
    elif isinstance(widget, (tk.Entry, ttk.Entry, ttk.Combobox, ttk.Spinbox)):
        width = widget.winfo_reqwidth() if widget.winfo_manager() == 'pack' else min(widget.winfo_reqwidth(), int(190 * factor))
    elif isinstance(widget, ttk.Notebook):
        selected = widget.select()
        width = minimum_layout_width(widget.nametowidget(selected)) + 8 if selected else 0
    else:
        packed, gridded = widget.pack_slaves(), widget.grid_slaves()
        def child_width(child, info):
            return (minimum_layout_width(child) + _horizontal_padding(widget, info.get('padx', 0))
                    + 2 * widget.winfo_pixels(info.get('ipadx', 0)))
        if packed:
            horizontal, vertical = [], []
            for child in packed:
                info = child.pack_info()
                (horizontal if info['side'] in ('left', 'right') else vertical).append(child_width(child, info))
            width = max([sum(horizontal), *vertical])
        elif gridded:
            original = getattr(widget, '_layout_original_minima', {})
            for i in range(widget.grid_size()[0]):
                if i not in original: original[i] = int(widget.columnconfigure(i)['minsize'])
            widget._layout_original_minima = original
            columns = [original[i] for i in range(widget.grid_size()[0])]
            cells = [(child, child.grid_info()) for child in gridded]
            for child, info in sorted(cells, key=lambda cell: int(cell[1]['columnspan'])):
                start, span = int(info['column']), int(info['columnspan'])
                deficit = max(0, child_width(child, info) - sum(columns[start:start+span]))
                for i in range(start, start+span): columns[i] += (deficit + span - 1) // span
            groups = {}
            for i in range(len(columns)):
                options = widget.columnconfigure(i)
                if options['uniform']:
                    groups.setdefault(options['uniform'], []).append((i, max(1, int(options['weight']))))
            for group in groups.values():
                unit = max((columns[i] + weight - 1) // weight for i, weight in group)
                for i, weight in group: columns[i] = unit * weight
            # grid reparte el espacio según el tamaño solicitado de cada
            # hijo. Fijar también el mínimo de cada columna impide que una
            # tabla ancha comprima los botones de la columna vecina.
            for i, minimum in enumerate(columns):
                if int(widget.columnconfigure(i)['minsize']) != minimum:
                    widget.columnconfigure(i, minsize=minimum)
            width = sum(columns)
        else:
            width = widget.winfo_reqwidth()
        if packed or gridded:
            if isinstance(widget, (ttk.Frame, ttk.LabelFrame)):
                padding = widget.tk.splitlist(widget.cget('padding'))
                if padding:
                    width += widget.winfo_pixels(padding[0]) + widget.winfo_pixels(padding[2] if len(padding) > 2 else padding[0])
            elif isinstance(widget, (tk.Frame, tk.LabelFrame)):
                width += 2 * (widget.winfo_pixels(widget.cget('padx')) + widget.winfo_pixels(widget.cget('highlightthickness')))
    width = max(1, int(width))
    widget._layout_minimum_cache = (factor, width)
    return width


class ScrollArea(ttk.Frame):
    """Primero adapta el ancho; desplaza lo que exceda el alto disponible."""
    def __init__(self, parent, *, style='TFrame', padding=0, background=BG,
                 minimum_width=300, width=600, height=450, adaptive=True):
        super().__init__(parent, style=style)
        self.minimum_width = minimum_width
        self.adaptive = adaptive
        self._job = None
        self._adapt_pending = True
        self._dimensions = None
        self._layout_inputs = None
        self._bars = (False, False)
        self.canvas = tk.Canvas(self, bg=background, highlightthickness=0,
                                width=width, height=height, yscrollincrement=24)
        self.ybar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.xbar = ttk.Scrollbar(self, orient='horizontal', command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.ybar.set, xscrollcommand=self.xbar.set)
        self.columnconfigure(0, weight=1); self.rowconfigure(0, weight=1)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.body = ttk.Frame(self.canvas, padding=padding, style=style)
        self.handle = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.canvas.bind('<Configure>', self._schedule)
        self.body.bind('<Configure>', self._schedule)
        self.body.bind('<Map>', self._schedule)
        self.bind('<Destroy>', self._destroyed, add='+')
        root = self.winfo_toplevel()
        layout_modes(root).register_settled(self, self._settled)
        # Una sola ruta por ventana; no se roba la rueda a tablas o listas.
        if not getattr(root, '_responsive_wheel', False):
            root._responsive_wheel = True
            for sequence in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                root.bind(sequence, _wheel, add='+')
            root.bind('<FocusIn>', _reveal_focus, add='+')
            root.bind('<Map>', _adapt_mapped, add='+')
            root.bind('<Configure>', _content_configured, add='+')
            root.bind('<Destroy>', _content_destroyed, add='+')
        self._schedule()

    def _settled(self):
        self._schedule()

    def _schedule(self, event=None):
        root = self.winfo_toplevel()
        if event is not None and getattr(layout_modes(root), 'transitioning', False):
            return
        inputs = (self.canvas.winfo_width(), self.canvas.winfo_height(), self.body.winfo_reqheight(), self.body.winfo_reqwidth())
        # El scroll mueve el Frame y emite Configure sin cambiar su tamaño.
        # No recalcular geometría por cada movimiento del contenido.
        if not self._adapt_pending and inputs == self._layout_inputs:
            return
        if self._job is None:
            self._job = self.after_idle(self._layout)

    def _layout(self):
        self._job = None
        if not self.winfo_exists(): return
        if self._adapt_pending:
            self._adapt_pending = False
            if self.adaptive:
                adapt_tree(self.body)
            else:
                wrap_tree_labels(self.body)
        self._layout_inputs = (self.canvas.winfo_width(), self.canvas.winfo_height(), self.body.winfo_reqheight(), self.body.winfo_reqwidth())
        # Al achicar manualmente una ventana, conserva su distribución y ofrece
        # desplazamiento solo si el ancho ya no alcanza. No recoloca tarjetas.
        # El canvas ocupa el ancho disponible. Sólo muestra una barra cuando
        # el contenido legible supera el ancho o el alto de su visor.
        width = max(self.minimum_width, minimum_layout_width(self.body), self.canvas.winfo_width())
        height = max(self.body.winfo_reqheight(), self.canvas.winfo_height())
        if self._dimensions != (width, height):
            self._dimensions = (width, height)
            self.canvas.itemconfigure(self.handle, width=width, height=height)
            self.canvas.configure(scrollregion=(0, 0, width, height))
        bars = (height > self.canvas.winfo_height()+2, width > self.canvas.winfo_width()+2)
        if bars[0] != self._bars[0]:
            if bars[0]: self.ybar.grid(row=0, column=1, sticky='ns')
            else: self.ybar.grid_remove(); self.canvas.yview_moveto(0)
        if bars[1] != self._bars[1]:
            if bars[1]: self.xbar.grid(row=1, column=0, sticky='ew')
            else: self.xbar.grid_remove(); self.canvas.xview_moveto(0)
        self._bars = bars

    def _destroyed(self, event):
        if event.widget is self and self._job is not None:
            self.after_cancel(self._job); self._job = None


def _content_configured(event):
    # El canvas fija el alto del cuerpo: una fila puede cambiar su alto
    # solicitado sin provocar Configure en el cuerpo. Recoger ese cambio
    # evita esperar al primer scroll para corregir la región desplazable.
    widget = event.widget
    if isinstance(widget, (tk.Button, ttk.Button, ttk.Checkbutton, ttk.Radiobutton)):
        cached = getattr(widget, '_layout_minimum_cache', None)
        if cached is not None and cached[1] != widget.winfo_reqwidth():
            invalidate_minimum_width(widget)
    while isinstance(widget, tk.Misc) and not isinstance(widget, ScrollArea):
        widget = widget.master
    if isinstance(widget, ScrollArea):
        widget._schedule(event)


def _content_destroyed(event):
    widget = event.widget
    if isinstance(widget, tk.Misc):
        invalidate_minimum_width(widget.master)


def _wheel(event):
    widget = event.widget
    if isinstance(widget, (ttk.Treeview, tk.Text, tk.Listbox, ttk.Combobox)):
        return
    while widget is not None:
        if isinstance(widget, tk.Canvas) and widget.cget('yscrollcommand') and widget.cget('scrollregion'):
            if widget.yview() != (0.0, 1.0):
                direction = -1 if getattr(event, 'num', None) == 4 or getattr(event, 'delta', 0)>0 else 1
                widget.yview_scroll(direction*3, 'units')
                return 'break'
        if isinstance(widget, ScrollArea):
            direction = (-1 if getattr(event, 'num', None) == 4 else
                         1 if getattr(event, 'num', None) == 5 else
                         -int(event.delta / 120) if abs(event.delta) >= 120 else
                         -1 if event.delta > 0 else 1)
            if event.state & 1:
                widget.canvas.xview_scroll(direction*3, 'units')
            else:
                widget.canvas.yview_scroll(direction*3, 'units')
            return 'break'
        widget = widget.master


def _adapt_mapped(event):
    widget = event.widget
    if not isinstance(widget, tk.Misc): return
    invalidate_minimum_width(widget)
    area = widget
    while area is not None and not isinstance(area, ScrollArea):
        area = area.master
    if area is None:
        return
    if not area.adaptive:
        if isinstance(widget, (tk.Label, ttk.Label)):
            wrap_label(widget)
        area._schedule()
        return
    if isinstance(widget, (ttk.Treeview, ttk.Notebook)):
        adapt_tree(widget.master)
    elif isinstance(widget, (tk.Frame, ttk.Frame, ttk.LabelFrame)):
        adapt_tree(widget)
    elif isinstance(widget, (tk.Label, ttk.Label)):
        wrap_label(widget)
    while widget is not None:
        if isinstance(widget, ScrollArea):
            widget._schedule()
            return
        widget = widget.master


def _reveal_focus(event):
    focused = event.widget
    if not isinstance(focused, tk.Misc): return
    widget = focused.master
    while widget is not None:
        if isinstance(widget, ScrollArea):
            x = focused.winfo_rootx()-widget.body.winfo_rootx()
            left = widget.canvas.canvasx(0)
            right = left+widget.canvas.winfo_width()
            if x < left or x+focused.winfo_width() > right:
                target_x = x-12 if x < left else x+focused.winfo_width()+12-widget.canvas.winfo_width()
                widget.canvas.xview_moveto(max(0, target_x)/max(1, widget.body.winfo_width()))
            y = focused.winfo_rooty()-widget.body.winfo_rooty()
            top = widget.canvas.canvasy(0)
            bottom = top+widget.canvas.winfo_height()
            target = y-12 if y < top else y+focused.winfo_height()+12-widget.canvas.winfo_height()
            if y < top or y+focused.winfo_height() > bottom:
                widget.canvas.yview_moveto(max(0, target)/max(1, widget.body.winfo_height()))
        widget = widget.master


class Reflow:
    """Conserva columnas, spans, proporciones y crecimiento vertical originales."""
    def __init__(self, parent, items, mode):
        self.parent, self.items, self.mode = parent, items, mode
        self.info = [(w, dict(w.pack_info() if mode == 'pack' else w.grid_info())) for w in items]
        self.state = None
        self.last_width = None
        self.profiles = {}
        self.job = None
        self.current_profile = None
        self.columns = parent.grid_size()[0]
        self.column_options = [parent.grid_columnconfigure(c) for c in range(self.columns)]
        self.row_options = [parent.grid_rowconfigure(r) for r in range(parent.grid_size()[1])]
        parent.bind('<Configure>', self.schedule, add='+')
        parent.bind('<Map>', self.schedule, add='+')
        parent.bind('<Destroy>', self.destroyed, add='+')
        bind_layout_mode(parent, self.schedule)

    def destroyed(self, event):
        if event.widget is self.parent and self.job is not None:
            self.parent.after_cancel(self.job)
            self.job = None

    def schedule(self, event=None):
        profile = layout_modes(self.parent).profile
        if self.current_profile == profile: return
        if self.job is None:
            self.job = self.parent.after_idle(self.layout)

    def layout(self, event=None):
        self.job = None
        if not self.parent.winfo_exists(): return
        if not self.parent.winfo_viewable(): return
        if any(not w.winfo_exists() for w in self.items): return
        if self.parent.winfo_width() < 30: return
        profile = layout_modes(self.parent).profile
        self.last_width = self.parent.winfo_width()
        state = (self.columns, False)
        self.profiles[profile] = state
        self.current_profile = profile
        if state == self.state: return
        self.state = state
        if self.mode == 'grid':
            # Una fila con weight=1 y sticky=nsew debe seguir creciendo.
            # Cambiarla a sticky=ew dejaba huecos en estadísticas y paneles.
            equal = self.column_options and all(int(o['weight']) == 1 for o in self.column_options)
            if equal:
                for c in range(self.columns): self.parent.columnconfigure(c, uniform='responsive')
        invalidate_minimum_width(self.parent)


def _label_text_padding(widget):
    """Espacio horizontal que no puede utilizar el texto del control."""
    if isinstance(widget, tk.Label):
        return 2 * sum(widget.winfo_pixels(widget.cget(option))
                       for option in ('padx', 'borderwidth', 'highlightthickness'))
    style = ttk.Style(widget)
    name = widget.cget('style') or 'TLabel'
    values = widget.tk.splitlist(widget.cget('padding') or style.lookup(name, 'padding') or '')
    padding = (widget.winfo_pixels(values[0]) +
               widget.winfo_pixels(values[2] if len(values) > 2 else values[0])) if values else 0
    border = widget.winfo_pixels(style.lookup(name, 'borderwidth') or 0)
    return max(8, padding + 2 * border)


def wrap_label(widget):
    if getattr(widget, '_responsive_wrap', False): return
    widget._responsive_wrap = True
    dimensions = [None]
    job = [None]
    # Se reorganiza el texto sin reducir el tamaño de la fuente.
    def resize(event=None):
        job[0] = None
        if not widget.winfo_exists(): return
        if not widget.winfo_viewable(): return
        parent_width = widget.master.winfo_width()
        if parent_width < 30: return
        current = (parent_width, widget.winfo_width())
        if current == dimensions[0]: return
        padding = 24
        if isinstance(widget.master, tk.Frame):
            padding += 2*int(widget.master.cget('padx') or 0)
        elif isinstance(widget.master, (ttk.Frame, ttk.LabelFrame)):
            values = widget.tk.splitlist(widget.master.cget('padding'))
            if values:
                padding += int(str(values[0])) + int(str(values[2] if len(values)>2 else values[0]))
        # wraplength mide solamente el texto. Los márgenes y bordes de una
        # etiqueta Tk se suman al ancho solicitado; no son espacio para letras.
        inset = _label_text_padding(widget)
        width = max(40, parent_width-padding-inset)
        if widget.winfo_manager() == 'pack':
            if widget.pack_info()['fill'] in ('x', 'both') and widget.winfo_width()>50:
                width = max(1, widget.winfo_width()-inset)
        elif widget.winfo_manager() == 'grid':
            info = widget.grid_info()
            if 'e' in info['sticky'] and 'w' in info['sticky'] and widget.winfo_width()>50:
                width = max(1, widget.winfo_width()-inset)
        if abs(int(float(widget.cget('wraplength') or 0))-width) > 3:
            widget.configure(wraplength=width)
        dimensions[0] = current
    def schedule(event=None):
        if event is not None and getattr(layout_modes(widget), 'transitioning', False):
            return
        current = (widget.master.winfo_width(), widget.winfo_width())
        if current == dimensions[0]: return
        if job[0] is None:
            job[0] = widget.after_idle(resize)
    def destroyed(event):
        if event.widget is widget and job[0] is not None:
            widget.after_cancel(job[0]); job[0] = None
    widget.master.bind('<Configure>', schedule, add='+')
    widget.bind('<Configure>', schedule, add='+')
    widget.bind('<Destroy>', destroyed, add='+')
    layout_modes(widget).register_settled(widget, lambda: schedule())


def wrap_tree_labels(parent):
    for child in parent.winfo_children():
        if isinstance(child, (tk.Label, ttk.Label)):
            if any(c.isalnum() for c in str(child.cget('text'))):
                wrap_label(child)
        else:
            wrap_tree_labels(child)


def _keep_above_container(widget, container):
    # grid(in_=...) cambia el contenedor geométrico, pero no el padre Tk.
    # El contenedor se creó después: sin elevar el control lo tapa por completo.
    def show(event=None):
        if event is None or event.widget is widget:
            widget.tkraise(container)
    widget.bind('<Map>', show, add='+')
    show()


class AutoScrollbar(ttk.Scrollbar):
    """Reserva espacio únicamente cuando el contenido necesita desplazamiento."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._placement = None
        self._shown = True

    def set(self, first, last):
        super().set(first, last)
        needed = float(first) > .00001 or float(last) < .99999
        if needed == self._shown:
            return
        if not needed:
            manager = self.winfo_manager()
            if manager not in ('grid', 'pack'):
                return
            info = dict(self.grid_info() if manager == 'grid' else self.pack_info())
            if manager == 'pack':
                siblings = self.master.pack_slaves()
                index = siblings.index(self)
                if index+1 < len(siblings): info['before'] = siblings[index+1]
            self._placement = (manager, info)
            self.grid_remove() if manager == 'grid' else self.pack_forget()
        elif self._placement:
            manager, info = self._placement
            self.grid(**info) if manager == 'grid' else self.pack(**info)
        self._shown = needed


def table_scrollbars(tree):
    if getattr(tree, '_responsive_table', False): return
    if not getattr(tree, '_responsive_columns', False):
        from tkinter import font
        metric = font.Font(tree, font=ttk.Style(tree).lookup('Treeview.Heading', 'font') or (UI_FONT, 9))
        tree.configure(height=min(6, int(tree.cget('height'))))
        for column in tree['columns']:
            minimum = max(int(65*scale(tree)), metric.measure(tree.heading(column, 'text'))+24)
            tree.column(column, minwidth=minimum, stretch=True)
        tree._responsive_columns = True
    if tree.cget('xscrollcommand') and tree.cget('yscrollcommand'): return
    manager = tree.winfo_manager()
    if manager not in ('pack', 'grid'): return
    info = dict(tree.pack_info() if manager == 'pack' else tree.grid_info())
    parent = tree.master
    frame = ttk.Frame(parent)
    frame._responsive_skip = True
    if manager == 'pack':
        following = parent.pack_slaves()
        index = following.index(tree)
        if index+1 < len(following): info['before'] = following[index+1]
        tree.pack_forget(); frame.pack(**info)
    else:
        tree.grid_forget(); frame.grid(**info)
    frame.columnconfigure(0, weight=1); frame.rowconfigure(0, weight=1)
    tree.grid(in_=frame, row=0, column=0, sticky='nsew')
    _keep_above_container(tree, frame)
    sy = AutoScrollbar(frame, orient='vertical', command=tree.yview)
    sx = AutoScrollbar(frame, orient='horizontal', command=tree.xview)
    sy.grid(row=0, column=1, sticky='ns'); sx.grid(row=1, column=0, sticky='ew')
    tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
    # Primero encajar columnas y una lista corta; el resto se consulta dentro
    # de la lista, sin obligar a desplazar toda la página por su altura inicial.
    tree._responsive_table = frame


def notebook_selector(notebook):
    """Todas las pestañas siguen accesibles cuando sus títulos no caben."""
    if getattr(notebook, '_responsive_notebook', False): return
    manager = notebook.winfo_manager()
    if manager not in ('pack','grid'): return
    from tkinter import font
    info = dict(notebook.pack_info() if manager=='pack' else notebook.grid_info())
    parent = notebook.master
    frame = ttk.Frame(parent); frame._responsive_skip = True
    if manager=='pack':
        siblings=parent.pack_slaves(); index=siblings.index(notebook)
        if index+1<len(siblings): info['before']=siblings[index+1]
        notebook.pack_forget(); frame.pack(**info)
    else:
        notebook.grid_forget(); frame.grid(**info)
    frame.columnconfigure(0,weight=1);frame.rowconfigure(1,weight=1)
    picker=ttk.Combobox(frame,state='readonly',takefocus=True)
    notebook.grid(in_=frame,row=1,column=0,sticky='nsew')
    _keep_above_container(notebook, frame)
    style=ttk.Style(notebook); original=notebook.cget('style') or 'TNotebook'
    compact='Compact.'+original
    style.layout(compact+'.Tab',[])
    metric=font.Font(notebook,font=style.lookup('TNotebook.Tab','font') or (UI_FONT,10))
    def update(event=None):
        if not notebook.winfo_exists():return
        ids=notebook.tabs();titles=[str(notebook.tab(i,'text')) for i in ids]
        if tuple(picker.cget('values')) != tuple(titles): picker.configure(values=titles)
        needed=sum(metric.measure(title)+int(42*scale(notebook)) for title in titles)
        narrow=needed>frame.winfo_width()-8
        if narrow:
            if not picker.winfo_manager(): picker.grid(row=0,column=0,sticky='ew',pady=(0,8))
            if notebook.cget('style')!=compact:notebook.configure(style=compact)
        else:
            if picker.winfo_manager(): picker.grid_remove()
            if notebook.cget('style')!=original:notebook.configure(style=original)
        if notebook.select() in ids:picker.current(ids.index(notebook.select()))
        if notebook.select():
            tab = notebook.nametowidget(notebook.select())
            wanted = max(80, tab.winfo_reqheight())
            if int(notebook.cget('height') or 0) != wanted:
                notebook.configure(height=wanted)
    picker.bind('<<ComboboxSelected>>',lambda _:notebook.select(picker.current()))
    notebook.bind('<<NotebookTabChanged>>',update,add='+')
    frame.bind('<Configure>',update,add='+')
    for tab in notebook.tabs():
        notebook.nametowidget(tab).bind('<Configure>', update, add='+')
    notebook._responsive_notebook=picker
    notebook.after_idle(update)


def adapt_tree(parent):
    if isinstance(parent, ScrollArea): return
    children = list(parent.winfo_children())
    seen = getattr(parent, '_responsive_seen', set())
    parent._responsive_seen = set(children)
    for child in children:
        if child in seen: continue
        if isinstance(child, ttk.Treeview): table_scrollbars(child)
        elif isinstance(child, ttk.Notebook):
            notebook_selector(child)
            adapt_tree(child)
        elif isinstance(child, (tk.Label, ttk.Label)): wrap_label(child)
        elif not isinstance(child, (tk.Toplevel, tk.Canvas)): adapt_tree(child)
    if getattr(parent, '_responsive_reflow', None) or getattr(parent, '_responsive_skip', False): return
    if not isinstance(parent, (tk.Frame, ttk.Frame, ttk.LabelFrame)): return
    packed = parent.pack_slaves()
    gridded = parent.grid_slaves()
    forbidden = (ttk.Scrollbar, tk.Canvas, ttk.Treeview)
    if len(packed)==2 and all(isinstance(w,(tk.Label,ttk.Label)) for w in packed):
        icons=[w for w in packed if len(str(w.cget('text')))==1 and ord(str(w.cget('text')))>=0xE000]
        if icons:
            info=[(w,dict(w.pack_info())) for w in packed]
            for w,_ in info:w.pack_forget()
            for w,options in sorted(info,key=lambda item:item[0] not in icons):
                if w not in icons:options.update(fill='x',expand=True)
                w.pack(**options)
            parent._responsive_skip=True
            return
    # Las barras con pack conservan su alineación natural. No estirar una
    # etiqueta o un botón pequeño hasta ocupar una fracción de toda la fila.
    if len(gridded)>1 and len({w.grid_info()['column'] for w in gridded})>1 and not any(isinstance(w, forbidden) for w in gridded):
        items = sorted(gridded, key=lambda w:(int(w.grid_info()['row']),int(w.grid_info()['column'])))
        parent._responsive_reflow = Reflow(parent, items, 'grid')


def page_header(page, title, subtitle, actions):
    frame = ttk.Frame(page, style='Page.TFrame'); frame.pack(fill='x', pady=(0, 16))
    title_row = ttk.Frame(frame, style='Page.TFrame'); title_row.pack(fill='x')
    ttk.Label(title_row, text=title, style='Title.TLabel').pack(side='left')
    if hasattr(page, '_view_status'):
        status = ttk.Label(title_row, textvariable=page._view_status, style='Subtitle.TLabel', anchor='e', justify='right')
        status.pack(side='right', fill='x', expand=True, padx=(16, 0))
        status.bind('<Button-1>', lambda _: page.refresh())
    ttk.Label(frame, text=subtitle, style='Subtitle.TLabel').pack(anchor='w', fill='x', pady=(4, 8))
    if actions:
        buttons = ttk.Frame(frame, style='Page.TFrame'); buttons.pack(fill='x')
        for label, command, style in actions:
            ttk.Button(buttons, text=label, command=command, style=style or 'TButton').pack(side='left', padx=(0,8))
