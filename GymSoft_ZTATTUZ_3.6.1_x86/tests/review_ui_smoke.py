"""Regresiones de transición, scroll, operaciones lentas y reintentos seguros."""
from pathlib import Path
import sys
import threading
import time
from datetime import date
from types import SimpleNamespace as NS
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import responsive_ui as layout
from desktop_ui import configure_dark_styles
from responsive_ui_smoke import pump, shell, assert_buttons_fit
from ui_assertions import destroy_root, resize_test_window
from ui_tasks import UiDatabase, run_io
from tk_window_state import grab_path


def payment_forms():
    import app as admin
    import reception_app as reception
    import desktop_ui
    plans = [dict(id=1, name='Mensualidad', price=55000, duration_days=30,
                  duration_months=None, entry_limit=None)]
    checks = 0
    for module, cls in ((admin, admin.GymSoftApp), (reception, reception.ReceptionApp)):
        with patch.object(reception.branding, 'show_reception_logo', lambda *_: None):
            root = shell(cls, 1.25)
        failures = []
        root.report_callback_exception = lambda kind, error, tb: failures.append(error)
        calls = []
        def write(payload):
            calls.append(dict(payload)); time.sleep(.15)
            if len(calls) == 1: raise TimeoutError('Resultado no confirmado')
            return dict(start_date=payload['start_date'], end_date='2026-10-13')
        try:
            if module is admin:
                db = NS(list_plans=lambda: plans, _today=lambda: date(2026, 9, 14))
                dialog = admin.MembershipDialog(root, db, 'Cliente de prueba')
            else:
                dialog = reception.PaymentDialog(root, dict(client_name='Cliente de prueba'), plans, date(2026, 9, 14))
            dialog.on_submit = lambda payload: run_io(dialog, lambda: write(payload))
            dialog.reference.set('PAGO-DE-PRUEBA'); dialog.notes.set('Conservar el formulario')
            with patch.object(desktop_ui.messagebox, 'showerror') as error, \
                 patch.object(desktop_ui.messagebox, 'showwarning') as warning:
                dialog.amount.set('15,50'); dialog.save()
                assert not calls and dialog.winfo_exists() and warning.call_count == 1
                dialog.amount.set('55.000'); dialog.save()
                assert len(calls) == 1 and dialog.winfo_exists() and error.call_count == 1
                assert dialog.result is None and dialog.reference.get() == 'PAGO-DE-PRUEBA'
                assert dialog.amount.get() == '55.000' and dialog.notes.get() == 'Conservar el formulario'
                root.after(30, dialog.save)  # Otro clic mientras espera respuesta.
                dialog.save()
                assert len(calls) == 2 and not dialog.winfo_exists()
                assert dialog.result['amount'] == 55000 and dialog.saved_result['end_date'] == '2026-10-13'
            assert not failures, failures
            checks += 7
        finally:
            destroy_root(root)
    return checks


def catalog_layout():
    import reception_app as reception
    checks = 0
    products = [dict(id=i, name=f'Producto {i}: bebida deportiva con sabor a frutos rojos',
                     sale_price=15000, stock_quantity=12, low_stock_threshold=2, sku=f'GYM-{i}')
                for i in range(1, 8)]
    for factor in (1, 1.2, 1.25):
        with patch.object(reception.branding, 'show_reception_logo', lambda *_: None):
            root = shell(reception.ReceptionApp, factor)
        failures = []
        root.report_callback_exception = lambda kind, error, tb: failures.append(error)
        try:
            with patch.object(reception.ReceptionShopPage, 'refresh', lambda self: None):
                root.show_page('shop')
            page = root.pages['shop']; page._render_refresh_products(products); pump(root)
            assert len(page.product_cards) == 7
            assert getattr(page.catalog_frame, '_responsive_reflow', None) is None
            normal_columns = page.catalog_columns
            resize_test_window(root, '1050x700');pump(root)
            assert page.catalog_columns == normal_columns
            resize_test_window(root, '1400x850');pump(root)
            modes = layout.layout_modes(root)
            with patch.object(layout, 'window_profile', return_value=('maximized', round(layout.scale(root), 3))):
                modes.changed(NS(widget=root));pump(root)
                assert page.catalog_columns >= normal_columns
                assert_buttons_fit(page)
            resize_test_window(root, '960x680')
            modes.changed(NS(widget=root));pump(root)
            assert page.catalog_columns == normal_columns
            assert all(page.catalog_frame.columnconfigure(i)['weight'] == 0
                       for i in range(page.catalog_columns, page.catalog_frame.grid_size()[0]))
            assert_buttons_fit(page)
            for card in page.product_cards:
                button = next(w for w in card.winfo_children() if isinstance(w, ttk.Button))
                assert button.winfo_y() + button.winfo_height() <= card.winfo_height(), 'Vender quedó cortado.'
            previous_cards = list(page.product_cards)
            page._render_refresh_products(products)
            assert page.product_cards == previous_cards, 'Se reconstruyeron productos sin cambios.'
            assert not failures, failures
            checks += 9
        finally:
            destroy_root(root)
    return checks


def reception_invite():
    import app as admin
    import reception_app as reception
    import desktop_ui
    from unittest.mock import Mock
    with patch.object(reception.branding, 'show_reception_logo', lambda *_: None):
        root = shell(admin.GymSoftApp, 1)
    failures = []
    root.report_callback_exception = lambda kind, error, tb: failures.append(error)
    main_thread = threading.get_ident()
    calls = []
    code = '00000000-0000-4000-8000-000000000001'
    def request():
        assert threading.get_ident() != main_thread
        calls.append(1);time.sleep(.15)
        return NS(data=code)
    root.cloud.client = Mock()
    root.cloud.client.rpc.return_value.execute.side_effect = request
    try:
        with patch.object(admin.SettingsPage, 'refresh', lambda self: None): root.show_page('settings')
        page = root.pages['settings'];pump(root)
        with patch.object(desktop_ui.messagebox, 'askyesno', return_value=True), \
             patch.object(desktop_ui.messagebox, 'showinfo') as info:
            page.generate_reception_invite()
            assert calls == [1] and page.reception_invite.get() == code
            assert info.call_count == 1 and not root._foreground_io
        assert not failures, failures
    finally:
        destroy_root(root)
    return 4


def main():
    root = tk.Tk()
    configure_dark_styles(root)
    resize_test_window(root, '1000x680')
    root.ready = True
    errors = []
    root.report_callback_exception = lambda kind, error, tb: errors.append(error)
    checks = 0
    try:
        area = layout.ScrollArea(root)
        area.pack(fill='both', expand=True)
        row = ttk.Frame(area.body); row.pack(fill='x')
        cards = [ttk.Button(row, text=f'Tarjeta {i}') for i in range(4)]
        for i, card in enumerate(cards): card.grid(row=0, column=i, sticky='ew')
        long = ttk.Frame(area.body, height=1400); long.pack(fill='x')
        pump(root, .2)
        unmapped = []
        for card in cards: card.bind('<Unmap>', lambda event: unmapped.append(event.widget), add='+')
        modes = layout.layout_modes(root)
        for name in ('maximized', 'normal', 'maximized', 'normal'):
            with patch.object(layout, 'window_profile', return_value=(name, round(layout.scale(root), 3))):
                modes.changed(NS(widget=root))
                # Sin esperar a after(120/65/55): el ciclo de geometría basta.
                root.update_idletasks()
                assert modes.profile[0] == name, 'El modo sigue esperando un temporizador.'
                assert not any(w.winfo_manager() == 'place' for w in root.winfo_children()), 'Una capa tapa la aplicación.'
                assert all(card.winfo_viewable() for card in cards)
                root.update()
        pump(root, .05)
        assert not unmapped, 'Cambiar columnas ocultó y volvió a mostrar los controles.'
        checks += 13
        layout_calls = []
        original_layout = area._layout
        def observe_layout():
            layout_calls.append((area._layout_inputs,
                                 (area.canvas.winfo_width(), area.canvas.winfo_height(), area.body.winfo_reqheight())))
            original_layout()
        with patch.object(area, '_layout', side_effect=observe_layout) as calculations:
            for _ in range(30):
                area.canvas.yview_scroll(1, 'units'); root.update()
            assert calculations.call_count == 0, f'El scroll volvió a calcular tamaños: {layout_calls}'
        checks += 1
        seen = []
        def fail(): raise ValueError('Error de distribución controlado')
        modes.register(row, fail)
        modes.register(long, lambda: seen.append('continúa'))
        with patch.object(layout, 'window_profile', return_value=('maximized', round(layout.scale(root), 3))):
            modes.changed(NS(widget=root));root.update_idletasks()
        assert seen == ['continúa'] and len(errors) == 1
        errors.clear(); checks += 2
        area.destroy()
        # Pago lento: la ventana mantiene su pulso, se envía una sola vez y
        # vuelve al formulario con su grab tanto en éxito como en error.
        form = tk.Toplevel(root);form.title('Pago de prueba')
        entry = ttk.Entry(form);entry.pack();entry.insert(0, 'REF-CONSERVADA')
        form.grab_set();pump(root)
        main_thread = threading.get_ident()
        calls, ticks = [], []
        heartbeat_job = None
        def beat():
            nonlocal heartbeat_job
            ticks.append(time.monotonic())
            heartbeat_job = root.after(10, beat)
        beat()
        def save():
            assert threading.get_ident() != main_thread
            calls.append(1);time.sleep(.22)
            return {'payment_id': 17}
        proxy = UiDatabase(NS(save=save, gym_id='gym-test'), root)
        assert proxy.gym_id == 'gym-test'
        result = proxy.save()
        assert result == {'payment_id': 17} and calls == [1]
        assert len(ticks) >= 8, 'La operación congeló el bucle de Tk.'
        assert grab_path(root) == str(form) and entry.get() == 'REF-CONSERVADA'
        checks += 5
        def fail_save():
            calls.append(2);time.sleep(.15)
            raise TimeoutError('Resultado de pago no confirmado')
        try:
            run_io(form, fail_save)
        except TimeoutError:
            pass
        else:
            raise AssertionError('El fallo de red se convirtió en éxito.')
        assert calls == [1, 2], 'Se reintentó una escritura automáticamente.'
        assert grab_path(root) == str(form) and not root._foreground_io
        assert entry.get() == 'REF-CONSERVADA'
        assert run_io(form, lambda: 18) == 18, 'No se recuperó la siguiente operación.'
        checks += 5
        root.after_cancel(heartbeat_job)
        form.destroy()
        assert not errors, errors
    finally:
        destroy_root(root)
    checks += payment_forms() + catalog_layout() + reception_invite()
    print(f'PASS: {checks} comprobaciones de transiciones sin capas ni esperas, scroll sin cálculos, pagos reales de interfaz con red simulada, respuesta única, recuperación, invitaciones y catálogo al 100/120/125 %.')


if __name__ == '__main__': main()
