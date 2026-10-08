"""Desplegables REALES de ttk durante pagos, refrescos, lecturas y avisos."""
from pathlib import Path
import os
import queue
import sys
import tempfile
from datetime import date
from unittest.mock import Mock, patch
import tkinter as tk
from tkinter import ttk
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as admin
import reception_app as reception
import desktop_ui
from responsive_ui_smoke import shell, pump, descendants
from performance_ui_smoke import FixtureDB, until
from ui_assertions import destroy_root
from ui_performance import background_reads, process_realtime
from tk_window_state import focus_widget, grab_path, close_native_dropdown


def post(combo):
    root = combo.winfo_toplevel()
    combo.tk.call('ttk::combobox::Post', str(combo))
    pump(root, .04)
    popup = str(combo.tk.call('ttk::combobox::PopdownWindow', str(combo)))
    combo.tk.call('focus', '-force', popup + '.f.l')
    pump(root, .04)
    assert '.popdown' in grab_path(root), grab_path(root)
    assert focus_widget(root) is combo
    return popup


def main():
    checked = 0
    plans = [dict(id=1, name='Mensual', price=60000, duration_days=30, entry_limit=None),
             dict(id=2, name='Tiquetera 20', price=80000, duration_days=60, duration_months=2, entry_limit=20)]
    for cls in (admin.GymSoftApp, reception.ReceptionApp):
        with patch.object(reception.branding, 'show_reception_logo', lambda *_: None):
            root = shell(cls, 1)
        errors = []
        root.report_callback_exception = lambda kind, error, tb: errors.append(error)
        root._ui_failures = errors
        root.db = FixtureDB()
        root.ready = True
        root.realtime_events = queue.Queue()
        root.realtime_refresh_pending = False
        root.show_page('clients')
        page = root.pages['clients']
        until(root, lambda: page._view_loaded and not page._view_pending)
        process_realtime(root)
        try:
            db = Mock()
            db.list_plans.return_value = plans
            db._today.return_value = date(2026, 9, 10)
            dialog = (admin.MembershipDialog(root, db, 'Ana de prueba') if cls is admin.GymSoftApp
                      else reception.PaymentDialog(root, {'client_name': 'Ana de prueba'}, plans, date(2026, 9, 10)))
            pump(root)
            combos = [w for w in descendants(dialog) if isinstance(w, ttk.Combobox)]
            assert len(combos) >= 2
            for combo in combos:
                popup = post(combo)
                assert not root.biometric_access.active(), 'El lector se activó durante un desplegable.'
                calls = len(root.db.calls)
                root.realtime_events.put({'event': 'pago de otro equipo'})
                pump(root, .3)
                assert root.realtime_refresh_pending and len(root.db.calls) == calls
                assert not errors, errors
                # La carga iniciada mientras el desplegable tiene el grab debe
                # esperar; cerrar el desplegable conserva el grab del formulario.
                page.refresh()
                until(root, lambda: any('ready' in slot for slot in background_reads(root).slots.values()))
                assert page._view_pending
                close_native_dropdown(root)
                pump(root, .04)
                assert grab_path(root) == str(dialog), grab_path(root)
                assert page._view_pending
                checked += 5

            # El mismo callback de error de la aplicación se ejecuta con la
            # lista abierta. El aviso oscuro debe abrirse y devolver el control.
            post(combos[-1])
            notices = []
            deadline = root.after(3000, lambda: dialog.destroy())
            def close_notice():
                wins = [w for w in descendants(root) if isinstance(w, desktop_ui.Modal)
                        and w.title() == 'No se pudo completar la acción']
                if not wins:
                    root.after(20, close_notice)
                    return
                notice = wins[0]
                assert grab_path(root) == str(notice), grab_path(root)
                assert notice.cget('bg') == desktop_ui.BG
                notices.append(notice.previous_grab)
                notice.close('ok')
            with tempfile.TemporaryDirectory() as logs, patch.dict(os.environ, {'LOCALAPPDATA': logs}):
                desktop_ui.install_error_handler(root)
                root.after(20, close_notice)
                root.report_callback_exception(ValueError, ValueError('Error controlado de demostración'), None)
                assert (Path(logs) / 'GymSoft/logs/aplicacion.log').is_file()
            root.after_cancel(deadline)
            assert len(notices) == 1 and grab_path(root) == str(dialog)
            root.report_callback_exception = lambda kind, error, tb: errors.append(error)
            checked += 4

            dialog.method.set('Transferencia' if cls is admin.GymSoftApp else 'TRANSFERENCIA')
            dialog.reference.set('SIM-PAGO-001')
            dialog.save()
            assert dialog.result['amount'] == 60000
            assert dialog.result['payment_reference'] == 'SIM-PAGO-001'
            assert not grab_path(root)
            until(root, lambda: not root.realtime_refresh_pending and not page._view_pending)
            assert not errors, errors
            # Un fallo del servidor es recuperable y no deja pendiente la vista.
            page.load_view('falla', lambda: (_ for _ in ()).throw(ValueError('Conexión de prueba')), lambda _: None)
            until(root, lambda: not page._view_pending)
            assert 'reintentar' in page._view_status.get()
            page.load_view('falla', lambda: 'recuperada', lambda _: None)
            until(root, lambda: not page._view_pending)
            assert not page._view_errors
            checked += 6
        finally:
            destroy_root(root)
    print(f'PASS: {checked} comprobaciones de desplegables, pagos, refrescos, avisos y recuperación en Administración y Recepción.')


if __name__ == '__main__':
    main()
