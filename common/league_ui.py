"""Exercise library and assignment, sharing Gym's dialogs and server permissions."""
import tkinter as tk
from tkinter import ttk
from common.league_client import LeagueClient, configured_endpoint


def add_league_tab(notebook, page):
    tab = ttk.Frame(notebook, padding=14, style='Card.TFrame')
    notebook.add(tab, text='Catálogo de ejercicios')
    if not configured_endpoint():
        ttk.Label(tab, text='El catálogo compartido estará disponible cuando se configure League.',
                  style='Field.TLabel', wraplength=500).pack(anchor='w')
        return
    CatalogPanel(tab, page).pack(fill='both', expand=True)


class CatalogPanel(ttk.Frame):
    def __init__(self, parent, page):
        super().__init__(parent, style='Card.TFrame')
        self.page = page
        self.api = LeagueClient(page.db.cloud)
        self.rows = []
        self.checked = set()
        self.search = tk.StringVar()
        ttk.Label(self, text='Crea cada ejercicio una vez y selecciónalo al preparar una rutina.',
                  style='Field.TLabel', wraplength=600).pack(anchor='w', pady=(0, 10))
        entry = ttk.Entry(self, textvariable=self.search)
        entry.pack(fill='x')
        self.search.trace_add('write', lambda *_: self.render())
        self.tree = ttk.Treeview(self, columns=('selected', 'name', 'muscle', 'equipment'), show='headings', selectmode='browse')
        for name, title, width in [('selected', 'Elegir', 65), ('name', 'Ejercicio', 230), ('muscle', 'Grupo muscular', 160), ('equipment', 'Equipamiento', 180)]:
            self.tree.heading(name, text=title)
            self.tree.column(name, width=width, minwidth=55)
        self.tree.pack(fill='both', expand=True, pady=10)
        self.tree.bind('<ButtonRelease-1>', self.toggle)
        self.tree.bind('<space>', self.toggle_keyboard)
        actions = ttk.Frame(self, style='Card.TFrame')
        actions.pack(fill='x')
        for label, command in [('Actualizar catálogo', self.refresh), ('Crear ejercicio', self.create), ('Asignar seleccionados', self.assign)]:
            ttk.Button(actions, text=label, command=command).pack(side='left', padx=(0, 8))
        self.count = ttk.Label(self, text='Ningún ejercicio seleccionado', style='Field.TLabel')
        self.count.pack(anchor='w', pady=8)

    def call(self, action, data=None):
        from ui_tasks import run_io
        return run_io(self, lambda: self.api.call(action, data), 'Consultando League')

    def refresh(self):
        self.rows = self.call('catalog') or []
        self.checked.intersection_update(row['id'] for row in self.rows)
        self.render()

    def render(self):
        self.tree.delete(*self.tree.get_children())
        query = self.search.get().strip().casefold()
        for row in self.rows:
            if query and query not in ' '.join(str(row.get(key, '')) for key in ('name', 'muscle', 'equipment')).casefold():
                continue
            self.tree.insert('', 'end', iid=row['id'], values=('✓' if row['id'] in self.checked else '○', row['name'], row.get('muscle', ''), row.get('equipment', '')))
        self.count.configure(text=f'{len(self.checked)} ejercicios seleccionados')

    def toggle(self, event):
        item = self.tree.identify_row(event.y)
        if item and self.tree.identify_column(event.x) == '#1':
            self._toggle(item)

    def toggle_keyboard(self, event):
        if self.tree.focus():
            self._toggle(self.tree.focus())
        return 'break'

    def _toggle(self, item):
        if item in self.checked:
            self.checked.remove(item)
        else:
            self.checked.add(item)
        self.render()
        if self.tree.exists(item):
            self.tree.focus(item)
            self.tree.selection_set(item)

    def create(self):
        from app import BaseDialog, center_window, messagebox
        panel = self
        class Editor(BaseDialog):
            def __init__(self):
                super().__init__(panel, 'Crear ejercicio', 510, 500)
                self.fields = {key: tk.StringVar(value=default) for key, default in [('name', ''), ('muscle', ''), ('equipment', 'Sin equipamiento'), ('instructions', '')]}
                for index, (key, title) in enumerate([('name', 'Nombre'), ('muscle', 'Grupo muscular'), ('equipment', 'Equipamiento o máquina'), ('instructions', 'Indicaciones')]):
                    self.add_entry(title, self.fields[key], index)
                self.add_buttons(self.save, 10)
                center_window(self, panel)
            def save(self):
                data = {key: value.get().strip() for key, value in self.fields.items()}
                if not 2 <= len(data['name']) <= 120:
                    messagebox.showwarning('Revisa el nombre', 'Escribe un nombre de 2 a 120 caracteres.', parent=self)
                    return
                panel.call('catalog_create', data)
                self.destroy()
                panel.refresh()
        self.wait_window(Editor())

    def assign(self):
        from app import BaseDialog, ExerciseDialog, center_window, messagebox
        from ui_tasks import run_io
        selected = [row for row in self.rows if row['id'] in self.checked]
        if not selected:
            messagebox.showinfo('Selecciona los ejercicios', 'Marca los ejercicios que quieres incluir en la rutina.', parent=self)
            return
        clients, trainers = run_io(self, lambda: (self.page.db.list_clients(), self.page.db.list_trainers(active_only=True)))
        panel = self
        class Assignment(BaseDialog):
            def __init__(self):
                super().__init__(panel, 'Asignar rutina', 530, 450)
                self.name = tk.StringVar(value='Plan de entrenamiento')
                self.client = tk.StringVar()
                self.trainer = tk.StringVar(value='Sin asignar')
                self.people = {f"{c.get('first_name','')} {c.get('last_name','')} · {c.get('document','')}": c['id'] for c in clients}
                self.coaches = {f"{t['name']} · {t['id']}": t['id'] for t in trainers}
                self.add_entry('Nombre de la rutina', self.name, 0)
                for row, (label, var, options) in enumerate([('Cliente', self.client, list(self.people)), ('Entrenador', self.trainer, ['Sin asignar', *self.coaches])], 1):
                    ttk.Label(self.body, text=label, style='Field.TLabel').grid(row=row*2, column=0, sticky='w')
                    ttk.Combobox(self.body, textvariable=var, values=options, state='readonly').grid(row=row*2+1, column=0, sticky='ew')
                self.add_buttons(self.save, 8)
                center_window(self, panel)
            def save(self):
                client = self.people.get(self.client.get())
                if client is None or len(self.name.get().strip()) < 2:
                    messagebox.showwarning('Faltan datos', 'Selecciona el cliente y escribe el nombre de la rutina.', parent=self)
                    return
                exercises = []
                # Each item uses the existing Gym editor; values become immutable assigned copies.
                for exercise in selected:
                    editor = ExerciseDialog(self)
                    editor.vars['name'].set(exercise['name'])
                    editor.vars['notes'].set(exercise.get('instructions', ''))
                    self.wait_window(editor)
                    if not editor.result:
                        return
                    value = editor.result
                    try:
                        sets, reps = int(value['sets']), int(value['reps'])
                        weight = float(value['weight'].replace(',', '.') or '0')
                        if not (1 <= sets <= 20 and 1 <= reps <= 100 and 0 <= weight <= 1000):
                            raise ValueError()
                    except ValueError:
                        messagebox.showwarning('Revisa el ejercicio', 'Usa series de 1 a 20, repeticiones de 1 a 100 y peso de 0 a 1000 kg.', parent=self)
                        return
                    exercises.append({'catalog_id': exercise['id'], 'day': value['day_name'], 'sets': sets, 'reps': reps,
                                      'weight_kg': weight, 'notes': value['notes'], 'rest_seconds': 90, 'position': len(exercises)+1})
                profile = panel.call('provision', {'client_id': client})
                panel.call('routine.assign', {'name': self.name.get().strip(), 'trainer_id': self.coaches.get(self.trainer.get()),
                                             'profiles': [profile['profile_id']], 'exercises': exercises})
                self.destroy()
                panel.page.refresh()
                messagebox.showinfo('Rutina asignada', 'La rutina quedó guardada para el cliente seleccionado.', parent=panel)
        self.wait_window(Assignment())
