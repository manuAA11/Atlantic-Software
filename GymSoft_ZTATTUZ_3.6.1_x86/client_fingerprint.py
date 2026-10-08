"""Optional fingerprint enrollment inside the client's existing form.

Writes happen off Tk's thread. A client is saved once before enrollment so its
cloud template always has a real client id. Closing never silently rolls back
an already confirmed client save.
"""
import queue
import sqlite3
import threading
import tkinter as tk
from tkinter import ttk
from desktop_ui import messagebox


class ClientFingerprintForm(ttk.Frame):
    def __init__(self, dialog, parent, data=None, *, style='Surface.TFrame'):
        super().__init__(dialog.body, style=style, padding=(0, 8))
        self.dialog = dialog
        self.db = getattr(parent, 'db', None)
        controller = getattr(dialog._root(), 'biometric_access', None)
        self.native = getattr(controller, 'native_reader', None)
        self.client_id = (data or {}).get('id')
        self.saved_payload = None
        self.busy = False
        self.operation = None
        self.uncertain = False
        self.events = queue.Queue()
        self.closed = False
        self.registered_state = None
        self.locked_fields = []
        dialog.client_saved = False
        dialog.saved_client_id = self.client_id
        self.columnconfigure(0, weight=1)
        ttk.Label(self, text='Huella digital (opcional)', style='Field.TLabel').grid(row=0, column=0, sticky='w')
        self.status = tk.StringVar(dialog, value='')
        ttk.Label(self, textvariable=self.status, wraplength=450, style='CardMuted.TLabel').grid(row=1, column=0, sticky='ew', pady=(4, 7))
        actions = ttk.Frame(self, style=style)
        actions.grid(row=2, column=0, sticky='w')
        self.enroll_button = ttk.Button(actions, text='Registrar huella', command=self.enroll)
        self.enroll_button.pack(side='left')
        self.delete_button = ttk.Button(actions, text='Eliminar huella', command=self.delete)
        self.delete_button.pack(side='left', padx=6)
        self.cancel_button = ttk.Button(actions, text='Cancelar lectura', command=self.cancel)
        self.cancel_button.pack(side='left')
        self.verify_button = ttk.Button(self, text='Comprobar huella', command=self.verify)
        self.verify_button.grid(row=3, column=0, sticky='w', pady=(6,0))
        self.note = tk.StringVar(dialog, value='Para registrar la huella se guardarán primero los datos del cliente.')
        ttk.Label(self, textvariable=self.note, wraplength=450, style='CardMuted.TLabel').grid(row=4, column=0, sticky='ew', pady=(7, 0))
        self.refresh()
        self.job = dialog.after(60, self.poll)
        dialog.bind('<Destroy>', self.destroyed, add='+')

    def refresh(self):
        registered = bool(self.native and self.client_id in self.native.templates)
        self.registered_state = registered
        blocked = self.busy or self.operation is not None or self.uncertain
        self.freeze_fields(blocked)
        self.enroll_button.configure(text='Reemplazar huella' if registered else 'Registrar huella',
                                    state='disabled' if blocked or not self.native or not self.db else 'normal')
        self.delete_button.configure(state='normal' if registered and not blocked else 'disabled')
        self.verify_button.configure(state='normal' if registered and not blocked else 'disabled')
        self.cancel_button.configure(state='normal' if self.operation in ('enroll','verify') else 'disabled')
        if not blocked:
            self.status.set('Huella registrada en la nube.' if registered else
                            'Sin huella registrada. Puedes guardar al cliente sin ella.' if self.native else
                            'El lector está disponible en la aplicación de Windows. La huella es opcional.')

    def freeze_fields(self, disabled):
        # Keep the confirmed identity visible and unchanged while saving/capturing.
        if disabled and not self.locked_fields:
            def walk(widget):
                for child in widget.winfo_children():
                    if child is self: continue
                    if isinstance(child, (ttk.Entry, ttk.Combobox, ttk.Checkbutton)) and 'disabled' not in child.state():
                        self.locked_fields.append(child)
                        child.state(['disabled'])
                    walk(child)
            walk(self.dialog.body)
        elif not disabled and self.locked_fields:
            for widget in self.locked_fields:
                if widget.winfo_exists(): widget.state(['!disabled'])
            self.locked_fields.clear()

    def poll(self):
        if self.closed: return
        try:
            while True:
                ok, value, payload, callback = self.events.get_nowait()
                self.busy = False
                if ok:
                    self.client_id = value
                    self.dialog.saved_client_id = value
                    self.dialog.client_saved = True
                    self.saved_payload = dict(payload)
                    self.note.set('Cliente guardado. Cerrar conserva sus datos y la huella confirmada.')
                    self.dialog.cancel_button.configure(text='Cerrar')
                    self.dialog.title('Editar cliente')
                    callback()
                    if self.closed: return
                else:
                    known = isinstance(value, (ValueError, sqlite3.IntegrityError, PermissionError)) or str(getattr(value, 'code', '')) in {'23505','23514','42501','22007','22008','22P02','P0001'}
                    self.uncertain = not known
                    text = ('No se guardaron los cambios. Revisa los datos del cliente. ' + str(value)) if known else (
                        'No se pudo confirmar el guardado. Cierra y revisa la lista de clientes antes de repetirlo. No se inició el registro de huella.')
                    self.status.set(text)
                    messagebox.showerror('No se pudo confirmar el cliente', text, parent=self.dialog)
                self.refresh_buttons()
        except queue.Empty: pass
        current = bool(self.native and self.client_id in self.native.templates)
        if current != self.registered_state and not self.busy and not self.operation and not self.uncertain:
            self.refresh()
        if not self.closed: self.job = self.dialog.after(60, self.poll)

    def refresh_buttons(self):
        # Refresh control states without discarding progress or failure text.
        text = self.status.get()
        self.refresh()
        self.status.set(text)

    def persist(self, payload, callback):
        if self.busy or self.uncertain: return
        if self.dialog.client_saved and payload == self.saved_payload:
            callback(); return
        self.busy = True
        self.status.set('Guardando los datos del cliente…')
        self.refresh_buttons()
        client_id = self.client_id
        def worker():
            try:
                value = self.db.save_client(dict(payload), client_id)
                if type(value) is not int or value <= 0:
                    raise RuntimeError('El servidor no confirmó el identificador del cliente.')
                self.events.put((True, value, payload, callback))
            except Exception as error:
                self.events.put((False, error, payload, callback))
        threading.Thread(target=worker, daemon=True, name='GuardarClienteHuella').start()

    def enroll(self):
        if self.busy or self.operation or self.uncertain or not self.native: return
        if self.native.enrolling:
            self.status.set('Espera a que termine la lectura anterior.'); return
        payload = self.dialog.collect_data()
        if payload is None: return
        name = (payload.get('first_name', '')+' '+payload.get('last_name', '')).strip()
        if not messagebox.askyesno('Registrar huella',
                f'¿Registrar la huella de {name}?\n\nConfirma su identidad y autorización. Se guardarán los datos del cliente antes de leer el dedo. Cancelar la lectura no elimina al cliente.', parent=self.dialog): return
        self.persist(payload, self.begin_enrollment)

    def begin_enrollment(self):
        self.operation = 'enroll'
        self.native.inline_editor = self
        self.native.enrolling = True
        self.native.service.pause(True)
        self.status.set('Coloca el mismo dedo y sigue las instrucciones de lectura.')
        self.native.service.send('enroll', self.client_id)
        self.refresh_buttons()

    def reader_status(self, value):
        if self.operation: self.status.set(value)

    def enrollment_finished(self, value):
        self.operation = None
        result = value if isinstance(value, dict) else {'message':str(value)}
        self.status.set(result['message'])
        self.refresh_buttons()
        self.native.show_completion(result, self.dialog)

    def verify(self):
        if self.busy or self.operation or self.uncertain or not self.native: return
        if self.native.enrolling:
            self.status.set('Espera a que termine la lectura anterior.'); return
        if self.client_id not in self.native.templates: return
        self.operation = 'verify'; self.native.inline_editor = self; self.native.enrolling = True
        self.native.service.pause(True)
        self.status.set('Coloca el dedo registrado para comprobarlo. Esta prueba no registra una entrada.')
        self.native.service.send('verify', self.client_id)
        self.refresh_buttons()

    def templates_updated(self):
        if not self.operation and not self.busy and not self.uncertain: self.refresh()

    def template_deleted(self, client_id):
        if client_id == self.client_id:
            self.operation = None
            self.status.set('Huella eliminada del gimnasio y sus equipos.')
            self.refresh_buttons()

    def delete(self):
        if self.busy or self.operation or self.uncertain or not self.native or self.client_id not in self.native.templates: return
        if not messagebox.askyesno('Eliminar huella', '¿Eliminar la huella de este cliente en todos los equipos del gimnasio? Sus datos, pagos y asistencias se conservan.', parent=self.dialog): return
        self.operation = 'delete'
        self.native.inline_editor = self
        self.status.set('Eliminando la huella…')
        self.native.service.send('delete', self.client_id)
        self.refresh_buttons()

    def cancel(self):
        if self.operation not in ('enroll','verify'): return
        self.status.set('Cancelando lectura…')
        self.native.service.send('cancel')

    def finish(self, payload):
        """Return True when this component owns/blocks the normal save action."""
        if self.busy or self.operation or self.uncertain:
            if self.operation: self.status.set('Finaliza o cancela la lectura antes de guardar y cerrar.')
            return True
        if not self.dialog.client_saved: return False
        def close():
            self.dialog.result = payload
            self.dialog.destroy()
        self.persist(payload, close)
        return True

    def before_close(self):
        if self.busy or self.operation == 'delete':
            self.status.set('Espera la respuesta del servidor antes de cerrar.')
            return False
        if self.native and getattr(self.native, 'inline_editor', None) is self:
            if self.operation in ('enroll','verify'): self.native.service.send('cancel')
            self.native.inline_editor = None
        return True

    def destroyed(self, event):
        if event.widget is self.dialog:
            self.closed = True
            if self.native and getattr(self.native, 'inline_editor', None) is self:
                self.native.service.send('cancel')
                self.native.inline_editor = None
            try: self.dialog.after_cancel(self.job)
            except tk.TclError: pass
