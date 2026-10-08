"""Selector local de archivos oscuro; no depende del tema claro de Windows."""
from __future__ import annotations

from responsive_ui import AutoScrollbar
import fnmatch
import os
from pathlib import Path
import string
import tkinter as tk
from tkinter import ttk
from desktop_ui import BG, SURFACE, TEXT, MUTED, Modal, button, messagebox


class FilePicker(Modal):
    def __init__(self, parent, *, save=False, **options):
        super().__init__(parent, options.get('title') or ('Guardar archivo' if save else 'Abrir archivo'))
        self.save_mode = save
        self.options = options
        self.files = {}
        self.current = Path(options.get('initialdir') or Path.home()).expanduser()
        self.path_var = tk.StringVar(master=self, value=str(self.current))
        self.name_var = tk.StringVar(master=self, value=options.get('initialfile', ''))
        self.feedback = tk.StringVar(master=self)
        nav = tk.Frame(self.body, bg=BG)
        nav.pack(fill='x', pady=(0, 12))
        button(nav, '↑ Subir', lambda: self.navigate(self.current.parent)).pack(side='left')
        path_entry = ttk.Entry(nav, textvariable=self.path_var, width=56)
        path_entry.pack(side='left', fill='x', expand=True, padx=8)
        path_entry.bind('<Return>', lambda _: self.navigate(Path(self.path_var.get()).expanduser()))
        button(nav, 'Ir', lambda: self.navigate(Path(self.path_var.get()).expanduser())).pack(side='left')
        quick = tk.Frame(self.body, bg=BG)
        quick.pack(fill='x', pady=(0, 10))
        for label, path in [('Inicio', Path.home()), ('Documentos', Path.home()/'Documents'), ('Descargas', Path.home()/'Downloads')]:
            if path.is_dir():
                button(quick, label, lambda p=path: self.navigate(p)).pack(side='left', padx=(0, 6))
        if os.name == 'nt':
            drives = [f'{c}:\\' for c in string.ascii_uppercase if Path(f'{c}:\\').is_dir()]
            drive = ttk.Combobox(quick, values=drives, state='readonly', width=5)
            drive.pack(side='right')
            drive.bind('<<ComboboxSelected>>', lambda _: self.navigate(Path(drive.get())))
        table = ttk.Frame(self.body)
        table.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(table, columns=('name','kind'), show='headings', selectmode='browse', height=13)
        self.tree.heading('name', text='Nombre');self.tree.heading('kind', text='Tipo')
        self.tree.column('name', width=490);self.tree.column('kind', width=115)
        scroll = AutoScrollbar(table, orient='vertical', command=self.tree.yview)
        scroll.pack(side='right', fill='y');self.tree.pack(fill='both', expand=True)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind('<<TreeviewSelect>>', self.select)
        self.tree.bind('<Double-1>', self.open_selected)
        types = options.get('filetypes') or [('Todos los archivos', '*')]
        self.patterns = {label: pattern for label, pattern in types}
        self.type_var = tk.StringVar(master=self, value=types[0][0])
        type_box = ttk.Combobox(self.body, values=list(self.patterns), textvariable=self.type_var, state='readonly')
        type_box.pack(fill='x', pady=10)
        type_box.bind('<<ComboboxSelected>>', lambda _: self.navigate(self.current))
        ttk.Label(self.body, text='Nombre del archivo').pack(anchor='w')
        entry = ttk.Entry(self.body, textvariable=self.name_var)
        entry.pack(fill='x', pady=(5, 8));entry.bind('<Return>', lambda _: self.accept())
        tk.Label(self.body, textvariable=self.feedback, bg=BG, fg='#fbbf24', wraplength=620).pack(fill='x')
        controls = tk.Frame(self.body, bg=BG);controls.pack(fill='x', pady=(10, 0))
        button(controls, 'Guardar' if save else 'Abrir', self.accept, primary=True).pack(side='right')
        button(controls, 'Cancelar', self.close).pack(side='right', padx=8)
        self.navigate(self.current)

    def navigate(self, path):
        try:
            path = path.resolve()
            if not path.is_dir():raise ValueError('Selecciona una carpeta existente.')
            entries = sorted(path.iterdir(), key=lambda p:(not p.is_dir(),p.name.casefold()))
        except (OSError, ValueError) as error:
            self.feedback.set(str(error));return
        self.current=path;self.path_var.set(str(path));self.feedback.set('')
        self.tree.delete(*self.tree.get_children());self.files={}
        pattern = self.patterns[self.type_var.get()]
        patterns = list(pattern) if isinstance(pattern,(tuple,list)) else str(pattern).split()
        for p in entries:
            if not p.is_dir() and not any(fnmatch.fnmatch(p.name.casefold(), x.casefold()) or x == '*.*' for x in patterns):
                continue
            key=str(len(self.files));self.files[key]=p
            self.tree.insert('', 'end', iid=key, values=(p.name,'Carpeta' if p.is_dir() else p.suffix))

    def select(self, _event=None):
        selected=self.tree.selection()
        p=self.files.get(selected[0]) if selected else None
        if p and p.is_file():self.name_var.set(p.name)

    def open_selected(self, _event=None):
        selected=self.tree.selection()
        p=self.files.get(selected[0]) if selected else None
        if p and p.is_dir():self.navigate(p)
        elif p:self.name_var.set(p.name);self.accept()

    def accept(self):
        name=self.name_var.get().strip()
        if not name:self.feedback.set('Escribe o selecciona el nombre del archivo.');return
        path=Path(name).expanduser()
        if not path.is_absolute():path=self.current/path
        if path.is_dir():self.navigate(path);return
        extension=self.options.get('defaultextension','')
        if self.save_mode and extension and not path.suffix:path=path.with_suffix(extension)
        if not self.save_mode and not path.is_file():
            self.feedback.set('El archivo no existe.');return
        if self.save_mode:
            if not path.parent.is_dir():self.feedback.set('La carpeta de destino no existe.');return
            if path.exists() and not messagebox.askyesno('Reemplazar archivo', f'Ya existe {path.name}. ¿Reemplazarlo?', parent=self):return
        self.close(str(path.resolve()))


class DarkFileDialogs:
    @staticmethod
    def askopenfilename(**options):
        parent=options.pop('parent',None) or tk._default_root
        return FilePicker(parent,**options).show() or ''

    @staticmethod
    def asksaveasfilename(**options):
        parent=options.pop('parent',None) or tk._default_root
        return FilePicker(parent,save=True,**options).show() or ''


filedialog=DarkFileDialogs()
