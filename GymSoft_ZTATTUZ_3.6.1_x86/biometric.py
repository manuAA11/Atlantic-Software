from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
import tkinter as tk
from tkinter import ttk
from typing import Callable


def normalize_biometric_identifier(value: object) -> str:
    """Normaliza el código emitido por lectores biométricos tipo teclado."""
    return "".join(str(value or "").split()).upper()


class AutomaticHidScanner:
    """Distingue un lector USB tipo teclado de la escritura manual.

    Los lectores HID escriben una secuencia completa en pocos milisegundos.
    La acción solo se dispara cuando todos los caracteres llegaron con ese
    ritmo; pegar texto, escribir manualmente o pulsar Enter no la ejecuta.
    """

    def __init__(
        self,
        owner: tk.Misc,
        entry: tk.Entry | object,
        variable: tk.StringVar,
        on_scan: Callable[[str], None],
        *,
        minimum_length: int = 3,
        idle_ms: int = 110,
        maximum_average_interval: float = 0.075,
        maximum_interval: float = 0.130,
        normalizer: Callable[[object], str] | None = None,
    ) -> None:
        self.owner = owner
        self.variable = variable
        self.on_scan = on_scan
        self.minimum_length = max(2, minimum_length)
        self.idle_ms = max(60, idle_ms)
        self.maximum_average_interval = maximum_average_interval
        self.maximum_interval = maximum_interval
        self.normalizer = normalizer or (lambda value: str(value or "").strip())
        self._key_times: list[float] = []
        self._job: str | None = None
        entry._hid_scanner = self

        entry.bind("<KeyPress>", self._record_key, add="+")
        variable.trace_add("write", self._schedule_evaluation)

    def _record_key(self, event: tk.Event) -> None:
        if event.keysym in {"BackSpace", "Delete", "Escape"}:
            self.reset()
            return

        character = str(getattr(event, "char", "") or "")

        if not character or not character.isprintable():
            return

        current = monotonic()

        if (
            self._key_times
            and current - self._key_times[-1] > self.maximum_interval
        ):
            self._key_times.clear()

        self._key_times.append(current)

    def _schedule_evaluation(self, *_args: object) -> None:
        if self._job is not None:
            try:
                self.owner.after_cancel(self._job)
            except tk.TclError:
                pass

        self._job = self.owner.after(self.idle_ms, self._evaluate)

    def _evaluate(self) -> None:
        self._job = None
        value = self.normalizer(self.variable.get())
        times = self._key_times[:]
        self._key_times.clear()

        if len(value) < self.minimum_length or len(times) < len(value):
            return

        intervals = [
            current - previous
            for previous, current in zip(times, times[1:])
        ]

        if not intervals:
            return

        average = sum(intervals) / len(intervals)

        if (
            average <= self.maximum_average_interval
            and max(intervals) <= self.maximum_interval
        ):
            self.on_scan(value)

    def reset(self) -> None:
        self._key_times.clear()

        if self._job is not None:
            try:
                self.owner.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None


@dataclass(frozen=True)
class AccessMatch:
    matched: bool
    client_id: int | None
    method: str
    message: str


class ManualAccessProvider:
    """Registra accesos seleccionados por el personal del gimnasio."""

    display_name = "Registro manual"

    def identify(self, selected_client_id: int | None) -> AccessMatch:
        if selected_client_id is None:
            return AccessMatch(
                matched=False,
                client_id=None,
                method="REGISTRO MANUAL",
                message="Selecciona un cliente para registrar su ingreso.",
            )
        return AccessMatch(
            matched=True,
            client_id=selected_client_id,
            method="REGISTRO MANUAL",
            message="Cliente seleccionado correctamente.",
        )

class ScanBuffer:
    """Reconoce ráfagas HID; una pulsación aislada o escritura lenta no es lectura."""
    def __init__(self, interval=0.065, average=0.040, minimum=3):
        self.interval, self.average, self.minimum = interval, average, minimum
        self.reset()

    def reset(self):
        self.characters, self.times = [], []

    def feed(self, character, now):
        if self.times and now-self.times[-1] > self.interval:
            self.reset()
        self.characters.append(character); self.times.append(now)
        if len(self.characters) > 128: self.reset()

    def value(self):
        if len(self.characters) < self.minimum: return None
        elapsed = self.times[-1]-self.times[0]
        if elapsed/(len(self.times)-1) > self.average: return None
        return normalize_biometric_identifier(''.join(self.characters))


class BiometricAccessControl(ttk.Frame):
    """Estado explícito y compartido por todas las pantallas de la aplicación."""
    def __init__(self, parent, controller):
        super().__init__(parent, style='Page.TFrame')
        self.controller = controller
        top = ttk.Frame(self, style='Page.TFrame')
        top.pack(fill='x')
        self.status = ttk.Label(top, style='Subtitle.TLabel')
        self.status.pack(side='left', fill='x', expand=True, padx=(0, 12))
        self.button = ttk.Button(top, command=self.toggle, width=16)
        self.button.pack(side='left')
        self._trace = controller.enabled.trace_add('write', self._update)
        self.bind('<Destroy>', self._destroyed, add='+')
        native = getattr(controller, 'native_reader', None)
        if native is not None:
            ttk.Button(top, text='Huellas / lector', command=native.open).pack(side='left', padx=(8,0))
            ttk.Label(self, textvariable=native.state, wraplength=680, style='Subtitle.TLabel').pack(fill='x', pady=(4,0))
        from door_ui import access_controls
        access_controls(self, controller.root)
        self._update()

    def toggle(self):
        self.controller.enabled.set(not self.controller.enabled.get())

    def _update(self, *_):
        enabled = self.controller.enabled.get()
        self.status.configure(
            text='Lectura automática de huella: ' + ('activada' if enabled else 'pausada'),
            foreground='#34D399' if enabled else '#FBBF24',
        )
        self.button.configure(text='Pausar lectura' if enabled else 'Activar lectura',
                              style='TButton' if enabled else 'Primary.TButton')

    def _destroyed(self, event):
        if event.widget is self:
            self.controller.enabled.trace_remove('write', self._trace)


class BiometricAccessController:
    """Captura dentro de Gym soft, sin hooks del sistema ni captura de contraseñas.

    El lector se reconoce por su ráfaga de teclas. La entrada sólo se intenta
    después de encontrar un código biométrico exacto en el gimnasio actual.
    Los formularios modales y otros lectores (por ejemplo tienda) tienen prioridad.
    """
    def __init__(self, root, lookup, on_match, on_unknown, on_error):
        import queue
        from tkinter import ttk
        self.root, self.lookup = root, lookup
        self.on_match, self.on_unknown, self.on_error = on_match, on_unknown, on_error
        self.enabled = tk.BooleanVar(root, value=True)
        self.enabled.trace_add('write', lambda *_: self._focus_out(None))
        self.buffer = ScanBuffer()
        self.queue = queue.Queue()
        self.busy = False
        self.recent = {}
        self.searches = {}
        self.job = None
        self.origin = None
        self.snapshot = None
        self.closed = False
        self.generation = 0
        self.tag = 'GymSoftBiometric'+str(id(self))
        root.bind_class(self.tag, '<KeyPress>', self.key)
        root.bind('<Map>', self._mapped, add='+')
        root.bind('<FocusOut>', self._focus_out, add='+')
        root.bind('<Destroy>', self._destroyed, add='+')
        self._tag_children(root)
        self.poll_job = root.after(60, self.poll)
        from fingerprint_ui import install
        install(self)

    def _tag_children(self, widget):
        if widget.winfo_toplevel() is not self.root: return
        tags = widget.bindtags()
        if self.tag not in tags: widget.bindtags((self.tag,)+tags)
        for child in widget.winfo_children(): self._tag_children(child)

    def _mapped(self, event):
        # Cada control nuevo recibe su propio Map. Recorrer de nuevo todo el
        # subárbol por cada evento multiplicaba el trabajo al abrir páginas.
        widget = event.widget
        if widget.winfo_toplevel() is not self.root: return
        tags = widget.bindtags()
        if self.tag not in tags: widget.bindtags((self.tag,)+tags)

    def active(self):
        try:
            from tk_window_state import focus_widget, grab_path
            focused = focus_widget(self.root)
            return (self.enabled.get() and getattr(self.root, 'ready', True)
                    and not grab_path(self.root)
                    and focused is not None and focused.winfo_toplevel() is self.root)
        except tk.TclError:
            return False

    def _focus_out(self, event):
        # También invalida una consulta pendiente si aparece un formulario.
        self.generation += 1
        self.reset()

    def reset(self):
        self.buffer.reset()
        self.origin = None; self.snapshot = None
        if self.job is not None:
            self.root.after_cancel(self.job); self.job = None

    def attach_search(self, entry, variable):
        self.searches[str(entry)] = (entry, variable)
        pending = [None]
        def changed(*_):
            if pending[0] is not None:
                entry.after_cancel(pending[0]); pending[0] = None
            def search():
                pending[0] = None
                code = normalize_biometric_identifier(variable.get())
                if code and entry.winfo_viewable() and self.active():
                    self.request(code, entry, variable.get(), manual=True)
            if variable.get().strip(): pending[0] = entry.after(700, search)
        variable.trace_add('write', changed)
        entry.bind('<Destroy>', lambda e: entry.after_cancel(pending[0]) if pending[0] else None, add='+')
        self._tag_children(entry)

    def key(self, event):
        if not self.active(): self.reset(); return
        widget = event.widget
        if getattr(widget, '_hid_scanner', None) is not None:
            self.reset(); return
        if event.state & (0x4 | 0x8): self.reset(); return
        if self.origin is not None and self.origin is not widget: self.reset()
        if event.keysym in {'Return', 'KP_Enter', 'Tab'}:
            candidate = self.buffer.value()
            if candidate:
                self.finish(); return 'break'
            if str(widget) in self.searches and event.keysym != 'Tab':
                code = self.searches[str(widget)][1].get()
                if code.strip(): self.request(code, widget, code, manual=True)
                return 'break'
            self.reset(); return
        char = str(getattr(event, 'char', '') or '')
        if not char or not char.isprintable():
            if event.keysym in {'BackSpace','Delete','Escape'}: self.reset()
            return
        now = monotonic()
        if self.buffer.times and now-self.buffer.times[-1] > self.buffer.interval: self.reset()
        if self.origin is None:
            self.origin = widget
            try:
                self.snapshot = (widget.get(), int(widget.index('insert')))
            except (AttributeError, tk.TclError, TypeError):
                self.snapshot = None
        self.buffer.feed(char, now)
        if self.job is not None: self.root.after_cancel(self.job)
        self.job = self.root.after(120, self.finish)

    def finish(self):
        if self.job is not None:
            self.root.after_cancel(self.job)
        self.job = None
        code, origin, snapshot = self.buffer.value(), self.origin, self.snapshot
        current = None
        try: current = origin.get() if snapshot is not None else None
        except (AttributeError, tk.TclError, TypeError): pass
        self.reset()
        if code: self.request(code, origin, current, snapshot=snapshot)

    def request(self, code, origin=None, expected=None, *, manual=False, snapshot=None):
        import threading
        code = normalize_biometric_identifier(code)
        now = monotonic()
        self.recent = {k:v for k,v in self.recent.items() if now-v < 5}
        if not code or self.busy or code in self.recent or not self.active(): return
        self.busy = True
        generation = self.generation
        def worker():
            try: result = (self.lookup(code), None)
            except Exception as error: result = (None, error)
            self.queue.put((generation, code, origin, expected, snapshot, manual, result))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        import queue
        try:
            generation, code, origin, expected, snapshot, manual, (client, error) = self.queue.get_nowait()
            self.busy = False
            if generation != self.generation or not self.active(): return
            # No actuar sobre una búsqueda que el usuario ya cambió.
            if origin is not None and expected is not None:
                if not origin.winfo_exists() or origin.get() != expected: return
            if error is not None:
                self.recent[code] = monotonic()
                self.on_error(error); return
            if client is None:
                if not manual: self.on_unknown(code)
                return
            self.recent[code] = monotonic()
            if origin is not None and origin.winfo_exists():
                if str(origin) in self.searches:
                    self.searches[str(origin)][1].set('')
                elif snapshot is not None and expected is not None:
                    origin.delete(0, 'end'); origin.insert(0, snapshot[0]); origin.icursor(snapshot[1])
            self.on_match(client)
        except queue.Empty:
            pass
        finally:
            if not self.closed: self.poll_job = self.root.after(60, self.poll)

    def _destroyed(self, event):
        if event.widget is self.root:
            self.closed = True
            self.reset()
            self.root.after_cancel(self.poll_job)
            self.root.unbind_class(self.tag, '<KeyPress>')
