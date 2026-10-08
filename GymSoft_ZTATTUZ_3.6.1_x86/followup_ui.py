"""Listas consultables y exportables para el seguimiento manual de clientes."""
import csv
import tkinter as tk
from tkinter import ttk
from datetime import date
from dark_files import filedialog
from desktop_ui import messagebox
from responsive_ui import adapt_tree, UI_FONT
from ui_performance import DataTreeview, clear_tree
from followup import TICKET_BUCKETS, ticket_groups, spreadsheet_text


def display_date(value):
    try:
        return date.fromisoformat(str(value)[:10]).strftime('%d/%m/%Y')
    except ValueError:
        return str(value or '')


def open_client(app, client_id):
    app.show_page('clients')
    page = app.pages.get('clients')
    tree = getattr(page, 'tree', None)
    def select():
        if tree is not None and tree.exists(str(client_id)):
            tree.selection_set(str(client_id))
            tree.focus(str(client_id))
            tree.see(str(client_id))
    if hasattr(page, 'when_loaded'):
        page.when_loaded(select)
    else:
        select()



class ContactList(ttk.Frame):
    def __init__(self, parent, columns, *, open_record=None):
        super().__init__(parent, style='Card.TFrame')
        self.columns = columns
        self.rows = []
        self.visible = []
        self.open_record = open_record
        self.search = tk.StringVar(self)
        toolbar = ttk.Frame(self, style='Card.TFrame')
        toolbar.pack(fill='x', pady=(0, 8))
        ttk.Label(toolbar, text='Buscar cliente o contacto:').pack(side='left')
        ttk.Entry(toolbar, textvariable=self.search, width=22).pack(side='left', fill='x', expand=True, padx=8)
        actions = ttk.Frame(self, style='Card.TFrame')
        actions.pack(fill='x', pady=(0, 8))
        ttk.Button(actions, text='Copiar contacto', command=self.copy_contact).pack(side='left', padx=(0, 8))
        ttk.Button(actions, text='Exportar listado', command=self.export).pack(side='left', padx=(0, 8))
        if open_record:
            ttk.Button(actions, text='Abrir cliente', command=self.open_selected).pack(side='left')
        self.status = ttk.Label(self, text='Sin registros.', style='CardMuted.TLabel')
        self.status.pack(fill='x', pady=(0, 8))
        self.tree = DataTreeview(self, columns=[x[0] for x in columns], show='headings', selectmode='browse', height=10)
        for key, title, width in columns:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=75, anchor='center')
        self.tree.pack(fill='both', expand=True)
        adapt_tree(self.tree)
        self.search.trace_add('write', lambda *_: self.render())
        self.tree.bind('<Double-1>', lambda _: self.open_selected())

    def set_rows(self, rows):
        self.rows = list(rows)
        self.render()

    def render(self):
        term = self.search.get().strip().casefold()
        self.visible = [r for r in self.rows if not term or term in ' '.join(str(r.get(k, '')) for k in ('client_name', 'document', 'phone', 'email')).casefold()]
        clear_tree(self.tree)
        for row in self.visible:
            values = [display_date(row.get(k)) if k in ('end_date', 'last_visit') else row.get(k, '') for k, *_ in self.columns]
            self.tree.insert('', 'end', iid=str(row['client_id']), values=values)
        self.status.configure(text=(f'{len(self.visible)} de {len(self.rows)} clientes.' if self.rows else 'No hay clientes en este rango.'))

    def selected(self):
        ids = self.tree.selection()
        return next((r for r in self.visible if ids and str(r['client_id']) == ids[0]), None)

    def copy_contact(self):
        row = self.selected()
        if row is None:
            self.status.configure(text='Selecciona un cliente para copiar sus datos.')
            return
        text = f"{row['client_name']}\nTeléfono: {row.get('phone') or 'Sin teléfono'}\nCorreo: {row.get('email') or 'Sin correo'}"
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.configure(text='Contacto copiado.')

    def open_selected(self):
        row = self.selected()
        if row is not None and self.open_record:
            self.open_record(int(row['client_id']))

    def export(self):
        if not self.visible:
            self.status.configure(text='No hay registros para exportar.')
            return
        filename = filedialog.asksaveasfilename(parent=self, title='Exportar seguimiento',
            initialfile=f'Seguimiento-clientes-{date.today():%Y%m%d}.csv', defaultextension='.csv', filetypes=[('CSV para Excel', '*.csv')])
        if not filename:
            return
        try:
            with open(filename, 'w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.writer(stream, delimiter=';')
                writer.writerow([title for _key, title, _width in self.columns])
                for row in self.visible:
                    writer.writerow([spreadsheet_text(display_date(row.get(k)) if k in ('end_date', 'last_visit') else row.get(k, '')) for k, *_ in self.columns])
            self.status.configure(text=f'Listado exportado: {len(self.visible)} clientes.')
        except OSError as error:
            messagebox.showerror('No se pudo exportar el listado', str(error), parent=self)


class TicketDashboard(ttk.Frame):
    def __init__(self, parent, app, dialog_class):
        super().__init__(parent, style='Card.TFrame', padding=14)
        self.app = app
        self.dialog_class = dialog_class
        self.groups = ticket_groups([])
        self.counts = {}
        ttk.Label(self, text='Tiqueteras · entradas restantes', style='Section.TLabel').pack(anchor='w')
        ttk.Label(self, text='Clientes activos con tiquetera vigente por fecha. Haz clic en un bloque para ver el listado.',
                  style='CardMuted.TLabel', wraplength=720).pack(fill='x', pady=(4, 12))
        cards = ttk.Frame(self, style='Card.TFrame')
        cards.pack(fill='x')
        palette = [('#43232b', '#ff8b97'), ('#44341c', '#ffd28a'), ('#44341c', '#ffd28a'), ('#1c3454', '#8bc5ff'), ('#1c3454', '#8bc5ff'), ('#193e36', '#7ce0bc')]
        for index, (key, title, _low, _high) in enumerate(TICKET_BUCKETS):
            cards.columnconfigure(index % 3, weight=1)
            bg, fg = palette[index]
            card = tk.Frame(cards, bg=bg, cursor='hand2', takefocus=True, highlightthickness=1, highlightbackground=fg)
            card.grid(row=index // 3, column=index % 3, sticky='nsew', padx=5, pady=5)
            label = tk.Label(card, text=title, bg=bg, fg=fg, font=(UI_FONT, 9, 'bold'), anchor='w')
            label.pack(fill='x', padx=12, pady=(10, 0))
            count = tk.Label(card, text='0', bg=bg, fg=fg, font=(UI_FONT, 22, 'bold'), anchor='w')
            count.pack(fill='x', padx=12)
            hint = tk.Label(card, text='Ver clientes →', bg=bg, fg=fg, font=(UI_FONT, 9), anchor='w')
            hint.pack(fill='x', padx=12, pady=(0, 10))
            for widget in (card, label, count, hint):
                widget.bind('<Button-1>', lambda _event, k=key, t=title: self.show(k, t))
            card.bind('<Return>', lambda _event, k=key, t=title: self.show(k, t))
            self.counts[key] = count

    def refresh(self):
        self.set_rows(self.app.db.ticket_followup())

    def set_rows(self, rows):
        self.groups = ticket_groups(rows)
        for key, label in self.counts.items():
            label.configure(text=str(len(self.groups[key])))

    def show(self, key, title):
        window = self.dialog_class(self, f'Tiqueteras · {title}', 1060, 600)
        ttk.Label(window.body, text=title, style='Section.TLabel').pack(anchor='w', pady=(0, 10))
        def visit(client_id):
            window.destroy()
            open_client(self.app, client_id)
        listing = ContactList(window.body, [
            ('document', 'Documento', 110), ('client_name', 'Cliente', 190),
            ('phone', 'Teléfono', 125), ('email', 'Correo', 210), ('plan_name', 'Tiquetera', 150),
            ('entries_remaining', 'Restantes', 85), ('entries_used', 'Utilizadas', 85), ('end_date', 'Vencimiento', 115),
        ], open_record=visit)
        listing.pack(fill='both', expand=True)
        listing.set_rows(self.groups[key])
        ttk.Button(window.body, text='Cerrar', command=window.destroy).pack(anchor='e', pady=(12, 0))
