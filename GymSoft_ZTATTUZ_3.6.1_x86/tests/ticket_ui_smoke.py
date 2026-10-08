"""Prueba de escritura real en Tk, formularios y seguimiento a dos escalas."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import ttk
from datetime import date
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import app as admin
import reception_app as reception
from followup_ui import TicketDashboard, ContactList
from responsive_ui_smoke import pump, descendants, assert_buttons_fit
from ui_assertions import enable_dpi_awareness, resize_test_window


def main():
    enable_dpi_awareness()
    checked = 0
    failures = []
    for factor in (1, 1.25):
        root = admin.GymSoftApp.__new__(admin.GymSoftApp)
        tk.Tk.__init__(root)
        root.tk.call('tk', 'scaling', 96 / 72 * factor)
        resize_test_window(root,'960x640')
        root.configure_styles()
        root.report_callback_exception = lambda kind, error, tb: failures.append(str(error))
        pump(root)
        try:
            for dialog_type in (admin.ClientDialog, reception.ClientDialog):
                dialog = dialog_type(root)
                variable = (dialog.vars if hasattr(dialog, 'vars') else dialog.variables)['birthdate']
                entry = next(w for w in descendants(dialog) if isinstance(w, ttk.Entry) and str(w.cget('textvariable')) == str(variable))
                pump(root)
                entry.focus_force()
                pump(root)
                for index, char in enumerate('12031990'):
                    entry.event_generate('<KeyPress>', keysym=char)
                    entry.event_generate('<KeyRelease>', keysym=char)
                    pump(root, .012)
                    if index in (1, 3):
                        assert entry.index(tk.INSERT) == (3 if index == 1 else 6), (variable.get(), entry.index(tk.INSERT))
                        checked += 1
                assert variable.get() == '12/03/1990', variable.get()
                assert entry.index(tk.INSERT) == 10
                checked += 1
                entry.selection_range(0, 'end')
                entry.event_generate('<KeyPress>', keysym='BackSpace')
                pump(root)
                root.clipboard_clear(); root.clipboard_append('01022000')
                entry.event_generate('<<Paste>>'); pump(root)
                assert variable.get() == '01/02/2000'
                assert entry.index(tk.INSERT) == 10
                checked += 1
                entry.icursor(5)
                entry.event_generate('<KeyPress>', keysym='BackSpace'); pump(root)
                assert entry.index(tk.INSERT) < 6  # No salta al final al corregir el mes.
                checked += 1
                dialog.destroy(); pump(root)
            plan = {'id': 1, 'name': 'Tiquetera flexible', 'duration_days': 60, 'duration_months': 2, 'entry_limit': 20, 'price': 80000}
            dialog = admin.PlanDialog(root, plan); pump(root)
            dialog.months.set('3'); dialog.entries.set('25'); dialog.save()
            assert dialog.result == ('Tiquetera flexible', 90, 80000, 25, 3)
            checked += 1
            db = Mock(); db.list_plans.return_value = [plan]; db._today.return_value = date(2026, 9, 8)
            for factory in (lambda: admin.MembershipDialog(root, db, 'Ana'),
                            lambda: reception.PaymentDialog(root, {'client_name': 'Ana'}, [plan], date(2026, 9, 8))):
                dialog = factory(); pump(root)
                dialog.start_date.set('01/09/2026')
                dialog.ticket_fields.enabled.set(True)
                dialog.ticket_fields.used.set('7')
                pump(root)
                assert '13 de 20' in dialog.ticket_fields.preview.cget('text')
                assert 'número 8' in dialog.ticket_fields.preview.cget('text')
                assert dialog.amount.get() == '0'
                dialog.geometry('700x520+0+0'); pump(root); assert_buttons_fit(dialog)
                dialog.save()
                assert dialog.result['initial_entries_used'] == 7 and dialog.result['carryover']
                checked += 1
            rows = [{'client_id': 1, 'client_name': 'Ana Prueba', 'document': '123', 'phone': '+573001234567', 'email': 'ana@example.test', 'plan_name': plan['name'], 'entries_remaining': 13, 'entries_used': 7, 'end_date': '2026-10-31'}]
            db.ticket_followup.return_value = rows
            widget = TicketDashboard(root, NS(db=db, pages={}), admin.BaseDialog)
            widget.pack(fill='x'); widget.refresh(); pump(root)
            assert widget.counts['eleven_fifteen'].cget('text') == '1'
            widget.show('eleven_fifteen', '11–15 entradas'); pump(root)
            window = next(w for w in descendants(widget) if isinstance(w, tk.Toplevel))
            listing = next(w for w in descendants(window) if isinstance(w, ContactList))
            assert listing.tree.get_children() == ('1',)
            listing.search.set('ana@example'); pump(root)
            assert listing.tree.get_children() == ('1',)
            listing.tree.selection_set('1'); listing.copy_contact()
            assert 'ana@example.test' in root.clipboard_get()
            checked += 1
            window.destroy(); widget.destroy()
            with patch.object(admin.StatisticsPage, 'refresh', lambda self: None):
                page = admin.StatisticsPage(root, NS(db=db))
            page.pack(fill='both', expand=True)
            db.session_followup.return_value = [dict(rows[0], entries=3, last_visit='2026-09-07', current_plan='Mensual', current_status='AL DÍA')]
            for label, days in page.session_periods.items():
                page.session_days.set(label); page.refresh_sessions(); pump(root)
                db.session_followup.assert_called_with(days)
                assert page.session_contacts.tree.get_children() == ('1',)
                checked += 1
            page.destroy()
            assert not failures, failures
        finally:
            root.destroy()
    print(f'PASS: {checked} comprobaciones gráficas de fechas, tiqueteras y seguimiento al 100 % y 125 %.')


if __name__ == '__main__':
    main()
