"""Configuración local del LCUS-1; exclusiva de ZTATTUZ."""
from dataclasses import replace
import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser

from desktop_ui import Modal, messagebox, button, BG, TEXT, MUTED, UI_FONT
from door_access import ConfigStore, DoorConfig, DoorController, DoorDatabase, available_ports

DRIVER_URL = 'https://www.wch-ic.com/downloads/CH341SER_EXE.html'


class DoorDialog(Modal):
    def __init__(self, root):
        super().__init__(root, 'Puerta automática · ZTATTUZ')
        self.root = root
        self.preferred_width = 640
        self.responses = queue.Queue()
        self.ports = []
        self.job = None
        self.closed = False
        self.scan_pending = False
        self.error = tk.StringVar(self)
        try:
            self.saved = root.door.store.load()
        except (ValueError, TypeError, OSError):
            self.saved = DoorConfig()
            self.error.set('Revisa y guarda de nuevo la configuración de este equipo.')
        self.enabled = tk.BooleanVar(self, value=self.saved.enabled)
        self.port = tk.StringVar(self, value=self.saved.port)
        self.seconds = tk.StringVar(self, value=f'{self.saved.seconds:g}')
        ttk.Label(self.body, text='Acceso por huella y relé USB', font=(UI_FONT, 15, 'bold')).pack(anchor='w')
        ttk.Label(self.body, text='ZTATTUZ valida el plan y registra la entrada antes de enviar la apertura.',
                  wraplength=565).pack(fill='x', pady=(8, 18))
        ttk.Label(self.body, textvariable=root.door_state, wraplength=565).pack(fill='x', pady=(0, 18))
        if root.door_admin:
            ttk.Checkbutton(self.body, text='Activar puerta automática en este computador',
                            variable=self.enabled).pack(anchor='w', pady=(0, 16))
            fields = ttk.Frame(self.body)
            fields.pack(fill='x')
            fields.columnconfigure(0, weight=1)
            ttk.Label(fields, text='Puerto USB del LCUS-1 (CH340)').grid(row=0, column=0, sticky='w')
            self.combo = ttk.Combobox(fields, textvariable=self.port, state='readonly', width=28)
            self.combo.grid(row=1, column=0, sticky='ew', pady=(6, 14))
            self.scan_button = ttk.Button(fields, text='Buscar puertos', command=self.scan)
            self.scan_button.grid(row=1, column=1, padx=(10, 0), pady=(6, 14))
            ttk.Label(fields, text='Duración de apertura (1 a 10 segundos)').grid(row=2, column=0, sticky='w')
            ttk.Entry(fields, textvariable=self.seconds, width=10).grid(row=3, column=0, sticky='w', pady=(6, 14))
            ttk.Label(self.body, text='Conecta el LCUS-1 y elige su puerto. No selecciones otro equipo CH340. '
                      'Si Windows no lo detecta, instala el controlador del fabricante.',
                      wraplength=565, foreground=MUTED).pack(fill='x')
            ttk.Button(self.body, text='Controlador CH340 · fabricante',
                       command=lambda: webbrowser.open(DRIVER_URL)).pack(anchor='w', pady=(8, 14))
        else:
            ttk.Label(self.body, text=f'Puerto configurado: {self.saved.port or "Sin configurar"} · '
                      f'Pulso: {self.saved.seconds:g} s\nLa configuración se cambia desde Administración.',
                      wraplength=565).pack(fill='x', pady=(0, 16))
        ttk.Label(self.body, text='El botón físico de salida debe funcionar sin el computador. '
                  'El relé no confirma la posición de la puerta; la prueba de instalación es presencial.',
                  wraplength=565, foreground=MUTED).pack(fill='x', pady=(8, 12))
        ttk.Label(self.body, textvariable=self.error, foreground='#fb7185', wraplength=565).pack(fill='x')
        actions = ttk.Frame(self.body)
        actions.pack(fill='x', pady=(10, 0))
        ttk.Button(actions, text='Restablecer relé (OFF)', command=self.secure).pack(side='left')
        if root.door_admin:
            ttk.Button(actions, text='Probar apertura', command=self.test).pack(side='left', padx=(10, 0))
        footer = ttk.Frame(self.body)
        footer.pack(fill='x', pady=(18, 0))
        button(footer, 'Cerrar', self.close).pack(side='right')
        if root.door_admin:
            button(footer, 'Guardar configuración', self.save, primary=True).pack(side='right', padx=(0, 10))
            self.scan()
        self.bind('<Destroy>', self.destroyed, add='+')
        self.job = self.after(100, self.poll)

    def scan(self):
        if self.scan_pending: return
        self.scan_pending = True
        self.scan_button.state(['disabled'])
        def work():
            try:
                ports = [] if self.root.door.offline else available_ports()
                self.responses.put(('ports', ports))
            except Exception:
                self.responses.put(('error', 'No se pudieron consultar los puertos. Revisa el controlador CH340.'))
        threading.Thread(target=work, name='ZTATTUZ-Puertos', daemon=True).start()

    def poll(self):
        if self.closed: return
        try:
            while True:
                kind, value = self.responses.get_nowait()
                self.scan_pending = False
                if self.root.door_admin: self.scan_button.state(['!disabled'])
                if kind == 'ports':
                    self.ports = [p for p in value if p.get('vid') == 0x1A86 and p.get('pid') in (0x7523, 0x5523)]
                    self.combo.configure(values=[self.port_label(p) for p in self.ports])
                    current = next((p for p in self.ports if p['port'] == self.saved.port), None)
                    if current and self.port.get() == self.saved.port:
                        self.port.set(self.port_label(current))
                    if not self.ports:
                        self.error.set('No se encontró un CH340. Puedes cerrar esta ventana y conectarlo después.')
                    else: self.error.set('')
                else: self.error.set(value)
        except queue.Empty: pass
        self.job = self.after(150, self.poll)

    @staticmethod
    def port_label(item):
        return item['port'] + ' · ' + item['description']

    def save(self):
        if not self.root.door_admin: return False
        try:
            seconds = float(self.seconds.get().replace(',', '.'))
            config = replace(self.saved, enabled=self.enabled.get(), seconds=seconds)
            if config.enabled:
                selected = next((p for p in self.ports if self.port_label(p) == self.port.get()), None)
                if selected is None:
                    raise ValueError('Conecta el LCUS-1 y selecciona su puerto antes de activar la puerta.')
                config = DoorConfig(config.enabled, selected['port'], seconds, selected['vid'], selected['pid'],
                                    selected.get('serial_number', ''), selected.get('location', ''))
            self.root.door.save_config(config)
            self.saved = config
            self.error.set('')
            messagebox.showinfo('Configuración guardada',
                'La puerta automática quedó ' + ('activada para este computador. Revisa el estado del relé antes de la prueba.'
                 if config.enabled else 'desactivada. El registro de asistencia sigue disponible.'), parent=self)
            return True
        except (ValueError, TypeError, OSError) as error:
            self.error.set(str(error)); return False

    def secure(self):
        if not self.root.door.secure():
            self.error.set('Activa y guarda la configuración, y espera a que termine cualquier ciclo en curso.')
        else: self.error.set('')

    def test(self):
        if not self.root.door_admin: return
        if not self.saved.enabled:
            self.error.set('Guarda la configuración activada antes de probar la apertura.'); return
        if messagebox.askokcancel('Probar apertura de la puerta',
                f'Se enviará una orden de apertura de {self.saved.seconds:g} segundos al {self.saved.port}. '
                'Realiza esta prueba con una persona junto a la puerta. No registra asistencia.', parent=self):
            if not self.root.door.test_pulse():
                self.error.set('No se inició la prueba. Revisa el estado, restablece el relé y vuelve a intentarlo.')
            else: self.error.set('')

    def destroyed(self, event):
        if event.widget is self:
            self.closed = True
            if self.job:
                self.after_cancel(self.job)


def install(root, database, *, admin):
    folder = Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local' / 'share')) / 'GymControl' / 'puerta'
    root.door = DoorController(ConfigStore(folder, database.gym_id),
                               offline=os.environ.get('GYMSOFT_OFFLINE_QA') == '1')
    root.door_admin = admin
    root.door_state = tk.StringVar(root, value='Puerta automática: iniciando…')
    root._door_window = None
    def open_settings():
        if root._door_window is not None and root._door_window.winfo_exists():
            root._door_window.lift(); return
        dialog = DoorDialog(root)
        root._door_window = dialog
        dialog.show()
        root._door_window = None
    root.open_door_settings = open_settings
    def open_manually():
        try:
            config = root.door.store.load()
            if not config.enabled:
                messagebox.showinfo('Puerta sin configurar',
                    'Activa el relé desde Administración → Configuración → Puerta automática.', parent=root)
                return False
            if messagebox.askokcancel('Abrir puerta',
                    f'Se enviará una apertura de {config.seconds:g} segundos. '
                    'Esta acción manual no valida el plan ni registra asistencia.',
                    yeslabel='Abrir puerta', nolabel='Cancelar', parent=root):
                if root.door.manual_pulse(): return True
                messagebox.showwarning('No se envió la apertura',
                    'Revisa el estado en Puerta / relé. Si hay un ciclo en curso, espera a que termine; '
                    'si ocurrió un fallo USB, revisa la conexión y pulsa Restablecer.', parent=root)
        except (ValueError, TypeError, OSError):
            messagebox.showerror('Revisa la puerta automática',
                'No se pudo leer la configuración del relé de este computador.', parent=root)
        return False
    root.open_door_manually = open_manually
    def poll():
        try:
            while True:
                kind, text = root.door.events.get_nowait()
                root.door_state.set(text)
                # Estado visible sin ventanas modales que interrumpan la siguiente lectura.
        except queue.Empty: pass
        root._door_job = root.after(150, poll)
    root._door_job = root.after(50, poll)
    def destroyed(event):
        if event.widget is root:
            root.after_cancel(root._door_job)
            root.door.close()
    root.bind('<Destroy>', destroyed, add='+')
    return DoorDatabase(database, root.door)


def access_controls(parent, root):
    if not hasattr(root, 'door'): return
    frame = ttk.Frame(parent, style='Page.TFrame')
    frame.pack(fill='x', pady=(6, 0))
    ttk.Button(frame, text='Puerta / relé', command=root.open_door_settings).pack(side='right', padx=(10, 0))
    ttk.Button(frame, text='Abrir puerta', command=root.open_door_manually,
               style='Primary.TButton').pack(side='right', padx=(10, 0))
    ttk.Label(frame, textvariable=root.door_state, style='Subtitle.TLabel',
              wraplength=600, width=1, anchor='w', justify='left').pack(side='left', fill='x', expand=True)


def settings_tab(notebook, root):
    if not hasattr(root, 'door'): return
    tab = ttk.Frame(notebook, padding=22, style='Card.TFrame')
    notebook.add(tab, text='Puerta automática')
    ttk.Label(tab, text='Entrada por huella · LCUS-1', style='Section.TLabel').pack(anchor='w')
    ttk.Label(tab, text='Configura el relé de este computador y la duración de apertura. '
              'Solo se activa tras una entrada biométrica autorizada.',
              style='CardMuted.TLabel', wraplength=660).pack(fill='x', pady=(8, 16))
    ttk.Label(tab, textvariable=root.door_state, style='CardMuted.TLabel', wraplength=660).pack(fill='x')
    ttk.Button(tab, text='Configurar puerta / relé', command=root.open_door_settings,
               style='Primary.TButton').pack(anchor='w', pady=(16, 0))
