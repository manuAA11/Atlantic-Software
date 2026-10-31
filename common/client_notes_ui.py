"""Shared Atlantic controls for staff-only client and membership notices."""
import tkinter as tk
from tkinter import ttk
from common.client_notes import MAX_NOTE_LENGTH, note_sections
from atlantic_ui import COLORS
from responsive_ui import UI_FONT
from desktop_ui import messagebox


class NotesPanel(ttk.Frame):
    def __init__(self, parent, *, height=4):
        super().__init__(parent, style='Card.TFrame')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text='Notas y avisos', style='Field.TLabel').grid(row=0, column=0, sticky='w', pady=(0, 4))
        self.text = tk.Text(self, height=height, width=1, wrap='word', font=(UI_FONT, 10),
                            bg=COLORS['surface'], fg=COLORS['text'], relief='flat',
                            highlightthickness=1, highlightbackground=COLORS['line'],
                            padx=8, pady=6, insertbackground=COLORS['text'])
        self.text.grid(row=1, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.text.yview)
        scrollbar.grid(row=1, column=1, sticky='ns')
        self.text.configure(yscrollcommand=scrollbar.set)
        self.set_context({})

    def set_context(self, context):
        self.text.configure(state='normal')
        self.text.delete('1.0', 'end')
        self.text.insert('1.0', note_sections(context) or 'Sin notas ni avisos registrados.')
        self.text.configure(state='disabled')
        self.text.yview_moveto(0)


def open_client_notes(parent, db, client_id, client_name, dialog_factory, on_saved):
    # Load before creating the modal: errors never leave an incomplete window.
    try:
        context = db.get_client_notes(client_id)
    except Exception as error:
        messagebox.showerror('No se pudieron consultar las notas', str(error), parent=parent)
        return None
    dialog = dialog_factory(parent, f'Notas y avisos · {client_name}', 640, 610)
    body = dialog.body
    body.columnconfigure(0, weight=1)
    ttk.Label(body, text=client_name, style='Section.TLabel', wraplength=520).grid(row=0, column=0, sticky='ew')
    ttk.Label(body, text='Aviso general del cliente · visible durante el chequeo',
              style='Field.TLabel').grid(row=1, column=0, sticky='w', pady=(14, 5))
    editor_frame = ttk.Frame(body, style='Card.TFrame')
    editor_frame.grid(row=2, column=0, sticky='ew')
    editor_frame.columnconfigure(0, weight=1)
    editor = tk.Text(editor_frame, width=1, height=7, wrap='word', font=(UI_FONT, 10),
                     bg=COLORS['surface'], fg=COLORS['text'], insertbackground=COLORS['text'],
                     highlightthickness=1, highlightbackground=COLORS['line'], relief='flat', padx=8, pady=8)
    editor.grid(row=0, column=0, sticky='ew')
    scrollbar = ttk.Scrollbar(editor_frame, orient='vertical', command=editor.yview)
    scrollbar.grid(row=0, column=1, sticky='ns')
    editor.configure(yscrollcommand=scrollbar.set)
    editor.insert('1.0', context.get('client_notice') or '')
    count = tk.StringVar()
    def update_count(_event=None):
        count.set(f'{len(editor.get("1.0", "end-1c"))} / {MAX_NOTE_LENGTH} caracteres')
    editor.bind('<KeyRelease>', update_count)
    update_count()
    ttk.Label(body, textvariable=count, style='CardMuted.TLabel').grid(row=3, column=0, sticky='w', pady=(4, 8))
    ttk.Label(body, text='El aviso permanece hasta que lo edites o borres y guardes.',
              style='CardMuted.TLabel', wraplength=520).grid(row=4, column=0, sticky='ew')
    membership = NotesPanel(body, height=4)
    membership.grid(row=5, column=0, sticky='ew', pady=(14, 0))
    membership.set_context({'membership_notes': context.get('membership_notes')})
    buttons = ttk.Frame(body, style='Card.TFrame')
    buttons.grid(row=6, column=0, sticky='ew', pady=(18, 0))
    def clear():
        editor.delete('1.0', 'end'); update_count()
    def save():
        if getattr(dialog, '_saving_note', False):
            return
        dialog._saving_note = True
        try:
            note = editor.get('1.0', 'end-1c').strip()
            if len(note) > MAX_NOTE_LENGTH:
                raise ValueError(f'La nota admite un máximo de {MAX_NOTE_LENGTH} caracteres.')
            result = db.save_client_note(client_id, note, context['revision'])
        except Exception as error:
            messagebox.showerror('No se pudo guardar la nota', str(error), parent=dialog)
        else:
            dialog.result = result
            dialog.destroy()
            on_saved()
        finally:
            dialog._saving_note = False
    ttk.Button(buttons, text='Borrar texto', command=clear).pack(side='left')
    ttk.Button(buttons, text='Cancelar', command=dialog.destroy).pack(side='right')
    ttk.Button(buttons, text='Guardar nota', command=save, style='Primary.TButton').pack(side='right', padx=(0, 8))
    dialog.note_editor, dialog.save_note = editor, save
    editor.focus_set()
    return dialog
