"""Lecturas en segundo plano y actualización estable de tablas de escritorio."""
from __future__ import annotations

import queue
import os
import re
import threading
import time
import traceback
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tkinter import ttk
from uuid import uuid4
from tk_window_state import focus_widget, grab_path


@dataclass(frozen=True)
class ReadFailure:
    """Only fixed guidance and safe metadata may leave the error classifier."""
    category: str
    code: str
    reference: str
    message: str


def classify_read_failure(error):
    # API messages may contain credentials, SQL values or record contents.
    # Read them only to choose fixed guidance; never retain or print them.
    raw_code = str(getattr(error, 'code', '')).upper()
    safe_codes = {'PGRST200', 'PGRST201', 'PGRST202', 'PGRST203', 'PGRST204',
                  'PGRST205', 'PGRST301', 'PGRST302', 'PGRST303', '42883',
                  '42703', '42P01', '42501', '28000', '28P01', '57014', '53300'}
    code = raw_code if raw_code in safe_codes else ''
    message = str(getattr(error, 'message', '') or error).casefold()
    kind = type(error).__name__.casefold()
    if code in {'PGRST301', 'PGRST302', 'PGRST303', '28000', '28P01'} or any(
            term in message for term in ('jwt expired', 'invalid jwt', 'refresh token', 'not authenticated')):
        category = 'session'
        guidance = 'No se pudo validar la sesión. Usa Recuperar conexión o Iniciar sesión en el aviso de la aplicación.'
    elif code == '42501' or any(term in message for term in ('permission denied', 'row-level security')):
        category = 'permission'
        guidance = 'Tu cuenta no tiene permiso para consultar esta información. Inicia sesión de nuevo o consulta al responsable del gimnasio.'
    elif code == '57014':
        category = 'server_timeout'
        guidance = ('El servidor interrumpió la consulta o excedió su tiempo límite. Vuelve a actualizar; '
                    'si continúa, solicita revisar el rendimiento del servidor del gimnasio.')
    elif code == '53300':
        category = 'server_busy'
        guidance = ('El servidor está ocupado y no pudo atender la consulta. '
                    'Espera unos instantes y vuelve a actualizar esta sección.')
    elif isinstance(error, (ConnectionError, TimeoutError)) or any(
            term in kind + ' ' + message for term in ('connecterror', 'connecttimeout', 'readtimeout',
            'connection refused', 'connection reset', 'failed to fetch', 'name resolution',
            'timed out', 'network is unreachable')):
        category = 'connection'
        guidance = 'No se pudo conectar con el servidor. Revisa la conexión a Internet y vuelve a actualizar esta sección.'
    elif code in {'PGRST202', '42883'} or 'could not find the function' in message:
        if any(name in message for name in ('membership_population', 'save_membership_plan')):
            category = 'membership_update'
            guidance = ('El servidor no tiene disponible una función de planes y membresías requerida por esta versión. '
                        'El responsable de la base debe verificar las actualizaciones previas del gimnasio y '
                        'la caché de funciones. Si faltan estas actualizaciones, debe aplicar '
                        'ACTUALIZAR_PLANES_INTERNOS.sql y después ACTUALIZAR_REANUDACION_MEMBRESIAS.sql '
                        'en el proyecto existente. '
                        'Conserva la base actual y vuelve a actualizar esta sección.')
        else:
            category = 'server_function'
            guidance = ('El servidor no tiene disponible una función requerida por esta versión. '
                        'Solicita la actualización del servidor del gimnasio y vuelve a intentar.')
    elif code in {'PGRST204', 'PGRST205', '42703', '42P01'} or (
            'schema cache' in message and ('column' in message or 'table' in message)):
        category = 'server_structure'
        guidance = ('La estructura del servidor no coincide con esta versión. '
                    'Solicita aplicar las actualizaciones pendientes en la base existente y vuelve a intentar.')
    else:
        category = 'unknown'
        guidance = ('No se pudo cargar esta sección. Reintenta; si el problema continúa, '
                    'comparte la referencia con soporte.')
    return ReadFailure(category, code, 'GS-LECTURA-' + uuid4().hex[:12].upper(), guidance)


def _safe_label(value):
    return re.sub(r'[^A-Za-z0-9_.-]', '_', str(value))[:80]


def record_read_failure(owner, key, error):
    failure = classify_read_failure(error)
    if not hasattr(owner, '_view_error_details'):
        owner._view_error_details = {}
    owner._view_error_details[key] = failure
    try:
        folder = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'GymControl' / 'logs'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / 'lecturas.log'
        if path.exists() and path.stat().st_size > 1_000_000:
            path.replace(folder / 'lecturas.anterior.log')
        with path.open('a', encoding='utf-8') as stream:
            stream.write(f'{datetime.now(timezone.utc).isoformat()} {failure.reference} '
                         f'{_safe_label(type(owner).__name__)}/{_safe_label(key)} '
                         f'category={failure.category} code={failure.code or "NONE"}\n')
            # Stack locations only: no error text, source lines, locals or paths.
            for frame in traceback.extract_tb(error.__traceback__):
                stream.write(f'  {_safe_label(Path(frame.filename).name)}:{frame.lineno} '
                             f'{_safe_label(frame.name)}\n')
    except OSError:
        pass
    return failure


def read_error_status(owner):
    prefix = ('No se pudo actualizar toda la información.' if owner._view_loaded
              else 'No se pudo actualizar.')
    return prefix + ' Haz clic aquí para ver el motivo y reintentar.'


class BackgroundReads:
    """Dos trabajadores; Tk solo se utiliza desde el hilo de la ventana.

    Cada sección conserva una petición pendiente. Una búsqueda nueva sustituye
    a la anterior y las respuestas invalidadas nunca actualizan la pantalla.
    """
    def __init__(self, root):
        self.root = root
        self.epoch = 0
        self.slots = {}
        self.work = queue.Queue()
        self.results = queue.Queue()
        self.owners = set()
        self.job = None
        self.polling = False
        self.wake_requested = False
        self.closed = False
        for index in range(2):
            threading.Thread(target=self._worker, name=f'GymSoft-Lecturas-{index}', daemon=True).start()
        root.bind('<Destroy>', self._destroyed, add='+')
        root.bind('<Map>', self._mapped, add='+')

    def invalidate(self):
        self.epoch += 1

    def submit(self, owner, key, parameters, load, render):
        if self.closed:
            return
        identity = (owner, key)
        self.owners.add(owner)
        slot = self.slots.setdefault(identity, {'running': False, 'last': None})
        signature = (self.epoch, parameters)
        slot['request'] = (signature, load, render)
        owner._view_errors.discard(key)
        getattr(owner, '_view_error_details', {}).pop(key, None)
        owner._view_pending.add(key)
        owner._view_status.set('Actualizando…' if owner._view_loaded else 'Cargando información…')
        if not slot['running']:
            self._start(identity, slot)
        self._schedule()

    def _schedule(self, *, idle=False):
        # Un renderizador puede iniciar otra lectura. Se arma un solo
        # temporizador al salir del sondeo, también en ese caso.
        if self.polling:
            self.wake_requested = True
            return
        if not self.closed and self.job is None:
            self.job = self.root.after_idle(self._poll) if idle else self.root.after(25, self._poll)

    def _mapped(self, event):
        # Una respuesta rápida puede llegar antes del primer Map. Despertar
        # al mostrar la página (o restaurar su ventana), sin sondear páginas
        # ocultas ni hacer trabajo por cada botón o etiqueta que aparece.
        if event.widget in self.owners:
            self.show(event.widget)
        elif event.widget is self.root:
            for owner in tuple(self.owners):
                self.show(owner)

    def _start(self, identity, slot):
        slot['running'] = True
        request = slot['request']
        self.work.put((identity, request))

    def _worker(self):
        while True:
            task = self.work.get()
            if task is None:
                return
            identity, request = task
            try:
                result, error = request[1](), None
            except Exception as failure:
                result, error = None, failure
            self.results.put((identity, request, result, error))

    def _poll(self):
        self.job = None
        if self.closed:
            return
        self.polling = True
        self.wake_requested = False
        try:
            deferred = self._drain()
        finally:
            self.polling = False
        if deferred or self.wake_requested or any(slot['running'] for slot in self.slots.values()):
            self._schedule()

    def _drain(self):
        while True:
            try:
                identity, request, data, error = self.results.get_nowait()
            except queue.Empty:
                break
            owner, key = identity
            slot = self.slots.get(identity)
            if slot is None:
                continue
            slot['running'] = False
            if not owner.winfo_exists():
                self.slots.pop(identity, None)
                continue
            if slot['request'] is not request:
                self._start(identity, slot)
                continue
            if request[0][0] != self.epoch:
                owner._view_pending.discard(key)
                owner._view_dirty = True
                if not owner._view_pending:
                    owner._view_status.set(read_error_status(owner) if owner._view_errors else '')
                continue
            if error is not None:
                owner._view_pending.discard(key)
                owner._view_errors.add(key)
                owner._view_dirty = True
                record_read_failure(owner, key, error)
                owner._view_status.set(read_error_status(owner))
                continue
            # Un modal abierto puede estar editando esos datos. Guardar la
            # respuesta y aplicarla al cerrarlo, sin modificar su formulario.
            slot['ready'] = (request, data)
        deferred = False
        for (owner, key), slot in list(self.slots.items()):
            ready = slot.get('ready')
            if ready is None:
                continue
            if not owner.winfo_exists():
                self.slots.pop((owner, key), None)
                continue
            request, data = ready
            if request is not slot['request'] or request[0][0] != self.epoch:
                slot.pop('ready', None)
                if request is slot['request']:
                    owner._view_pending.discard(key)
                owner._view_dirty = True
                continue
            if grab_path(self.root) or getattr(self.root, '_foreground_io', False):
                deferred = True
                continue
            # Las pantallas ocultas conservan sus datos para el siguiente acceso.
            if not owner.winfo_viewable():
                owner._view_dirty = True
                # El Map puede procesarse antes de que Windows considere
                # visibles todos los contenedores. La página seleccionada
                # conserva el temporizador hasta presentar la respuesta;
                # no depende de recibir otro Map. Las páginas apartadas y
                # las ventanas minimizadas/retiradas permanecen en reposo.
                active = getattr(self.root, 'pages', {}).get(
                    getattr(self.root, 'current_page', None))
                if (owner is active and owner.winfo_manager()
                        and self.root.state() in ('normal', 'zoomed')):
                    deferred = True
                continue
            slot.pop('ready', None)
            if slot['last'] != (request[0][1], data):
                try:
                    request[2](data)
                except Exception as error:
                    import sys
                    self.root.report_callback_exception(*sys.exc_info())
                    if request is slot['request']:
                        owner._view_pending.discard(key)
                    owner._view_dirty = True
                    owner._view_errors.add(key)
                    record_read_failure(owner, key, error)
                    owner._view_status.set(read_error_status(owner))
                    continue
                slot['last'] = (request[0][1], data)
                slot['paint'] = (request[2], data)
            # Recibir datos no completa la carga: también deben presentarse.
            # Si el renderizador inició otra consulta de la misma clave, esa
            # nueva solicitud sigue pendiente.
            if request is slot['request']:
                owner._view_pending.discard(key)
                owner._view_error_details.pop(key, None)
            owner._view_loaded = True
            owner._view_updated_at = time.monotonic()
            if not owner._view_pending:
                owner._view_dirty = bool(owner._view_errors)
                owner._view_status.set(read_error_status(owner) if owner._view_errors else '')
                callbacks, owner._view_callbacks = owner._view_callbacks, []
                for callback in callbacks:
                    try:
                        callback()
                    except Exception:
                        import sys
                        self.root.report_callback_exception(*sys.exc_info())
        return deferred

    def show(self, owner):
        available = any(identity[0] is owner and 'ready' in slot
                        and slot['ready'][0][0][0] == self.epoch
                        for identity, slot in self.slots.items())
        if available:
            self._schedule(idle=True)
        return available

    def has_obsolete_request(self, owner):
        return any(page is owner and slot['request'][0][0] != self.epoch
                   for (page, _key), slot in self.slots.items())

    def repaint(self, owner):
        for (page, _key), slot in self.slots.items():
            slot['last'] = None
            if page is owner and 'paint' in slot:
                render, data = slot['paint']
                render(data)
            elif 'paint' in slot:
                page._view_dirty = True

    def _destroyed(self, event):
        if event.widget in self.owners:
            self.owners.discard(event.widget)
            for identity in [key for key in self.slots if key[0] is event.widget]:
                self.slots.pop(identity, None)
        if event.widget is self.root:
            self.closed = True
            if self.job is not None:
                self.root.after_cancel(self.job)
            self.slots.clear()
            self.owners.clear()
            while True:
                try:
                    self.work.get_nowait()
                except queue.Empty:
                    break
            for _ in range(2):
                self.work.put(None)


def background_reads(root):
    if not hasattr(root, '_background_reads'):
        root._background_reads = BackgroundReads(root)
    return root._background_reads


class AsyncPageMixin:
    def init_reads(self):
        self._view_pending = set()
        self._view_errors = set()
        self._view_error_details = {}
        self._view_loaded = False
        self._view_dirty = True
        self._view_updated_at = 0.0
        self._view_status = tk.StringVar(self, '')
        self._view_callbacks = []

    def load_view(self, key, load, render, parameters=()):
        background_reads(self.winfo_toplevel()).submit(self, key, parameters, load, render)

    def mark_dirty(self):
        self._view_dirty = True

    def show_read_error(self):
        failures = list(self._view_error_details.values())
        if not failures:
            self.refresh()
            return
        from desktop_ui import messagebox
        details = []
        for failure in failures:
            code = f' · Código: {failure.code}' if failure.code else ''
            details.append(f'{failure.message}\nReferencia: {failure.reference}{code}')
        if messagebox.askretrycancel('No se pudo cargar la información', '\n\n'.join(details), parent=self):
            self.refresh()

    def when_loaded(self, callback):
        if self._view_pending or not self._view_loaded or self._view_dirty:
            self._view_callbacks.append(callback)
        else:
            callback()


def show_page(app, key):
    if getattr(app, '_foreground_io', False):
        return
    if key == app.current_page and key in app.pages and app.pages[key].winfo_manager():
        background_reads(app).show(app.pages[key])
        return
    if app.current_page in app.pages:
        previous = app.pages[app.current_page]
        previous._page_scroll = app.content_area.canvas.yview()[0]
        previous.pack_forget()
    created = key not in app.pages
    if created:
        app.pages[key] = app.page_types[key](app.content, app)
    page = app.pages[key]
    app.current_page = key
    page.pack(fill='both', expand=True)
    reads = background_reads(app)
    available = reads.show(page)
    if created or reads.has_obsolete_request(page) or (not available and not page._view_pending and
                   (page._view_dirty or time.monotonic()-page._view_updated_at > 20)):
        page.refresh()
    def settle():
        if app.current_page != key or not page.winfo_exists():
            return
        app.content_area.canvas.yview_moveto(getattr(page, '_page_scroll', 0))
        entry = getattr(page, 'search_entry', None)
        if entry is not None and not grab_path(app):
            entry.focus_set()
    page.after_idle(settle)
    for nav_key, button in app.nav_buttons.items():
        button.set_active(nav_key == key)


def refresh_pages(app):
    background_reads(app).invalidate()
    for page in app.pages.values():
        page.mark_dirty()
    active = app.pages.get(app.current_page)
    if active is not None:
        active.refresh()


def process_realtime(app):
    """Agrupa ráfagas y actualiza solo la sección visible, sin tocar formularios."""
    try:
        received = False
        while True:
            try:
                app.realtime_events.get_nowait()
                received = True
            except queue.Empty:
                break
        now = time.monotonic()
        if received:
            if not app.realtime_refresh_pending:
                app._realtime_first = now
            app._realtime_last = now
            app.realtime_refresh_pending = True
        page = app.pages.get(app.current_page)
        focused = focus_widget(app)
        editing = app.current_page in ('settings', 'marketing') and isinstance(
            focused, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox, ttk.Spinbox))
        settled = now-getattr(app, '_realtime_last', now) >= .18 or now-getattr(app, '_realtime_first', now) >= .6
        if (app.ready and app.realtime_refresh_pending and settled and page is not None
                and not editing and not grab_path(app) and not getattr(app, '_foreground_io', False)):
            app.realtime_refresh_pending = False
            refresh_pages(app)
        app.after(80, lambda: process_realtime(app))
    except tk.TclError:
        return


class DataTreeview(ttk.Treeview):
    """Reutiliza filas y conserva selección y desplazamiento al refrescar."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._batch = None
        self._batch_job = None
        self._row_cache = {}
        self.bind('<Destroy>', self._destroyed, add='+')

    def begin_update(self):
        self.finish_update()
        children = self.get_children()
        anchor = next((self.identify_row(y) for y in range(1, min(self.winfo_height(), 80), 4)
                       if self.identify_row(y)), '')
        self._batch = {'old': children, 'existing': set(children), 'seen': [], 'anchor': anchor,
                       'yview': self.yview(), 'xview': self.xview()}
        self._batch_job = self.after_idle(self.finish_update)

    def insert(self, parent, index, iid=None, **kwargs):
        if self._batch is None:
            inserted = super().insert(parent, index, iid=iid, **kwargs)
            self._row_cache[inserted] = dict(kwargs)
            return inserted
        iid = str(iid) if iid is not None else f'row_{len(self._batch["seen"])}'
        self._batch['seen'].append(iid)
        if iid in self._batch['existing']:
            before = self._row_cache.get(iid)
            if before is None:
                before = self.item(iid)
            changed = {}
            for key, value in kwargs.items():
                if key in ('values', 'tags'):
                    wanted = tuple(map(str, value)) if isinstance(value, (list, tuple)) else (str(value),)
                    current = tuple(map(str, before.get(key, ())))
                else:
                    wanted, current = str(value), str(before.get(key, ''))
                if wanted != current:
                    changed[key] = value
            if changed:
                super().item(iid, **changed)
                self._row_cache[iid] = {**before, **changed}
            return iid
        inserted = super().insert(parent, index, iid=iid, **kwargs)
        self._row_cache[inserted] = dict(kwargs)
        self._batch['existing'].add(inserted)
        return inserted

    def item(self, item, option=None, **kwargs):
        if kwargs:
            self._row_cache.pop(str(item), None)
        return super().item(item, option, **kwargs)

    def delete(self, *items):
        self.finish_update()
        for item in items:
            self._row_cache.pop(str(item), None)
        return super().delete(*items)

    def finish_update(self):
        if self._batch_job is not None:
            self.after_cancel(self._batch_job)
            self._batch_job = None
        batch, self._batch = self._batch, None
        if batch is None or not self.winfo_exists():
            return
        seen = set(batch['seen'])
        removed = [key for key in batch['old'] if key not in seen]
        if removed:
            super().delete(*removed)
            for key in removed:
                self._row_cache.pop(key, None)
        current = self.get_children()
        if tuple(batch['seen']) != current:
            for position, key in enumerate(batch['seen']):
                self.move(key, '', position)
        if batch['anchor'] in seen and batch['seen']:
            fraction = batch['seen'].index(batch['anchor']) / len(batch['seen'])
        else:
            fraction = batch['yview'][0] if batch['yview'] else 0
        self.yview_moveto(fraction)
        if batch['xview']:
            self.xview_moveto(batch['xview'][0])

    def _destroyed(self, event):
        if event.widget is self and self._batch_job is not None:
            self.after_cancel(self._batch_job)
            self._batch_job = None


def clear_tree(tree):
    if isinstance(tree, DataTreeview):
        tree.begin_update()
    else:
        children = tree.get_children()
        if children:
            tree.delete(*children)
