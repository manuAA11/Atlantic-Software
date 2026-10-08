"""Contraste, teclado y resultados de los avisos, con Tk real y sin red."""
from pathlib import Path
import os
import sys
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['GYMSOFT_OFFLINE_QA'] = '1'
from PIL import ImageTk, ImageGrab
from desktop_ui import configure_dark_styles, Modal, messagebox, BG
from ui_visuals import indicator_image
from ui_assertions import pump, destroy_root, assert_exposed, resize_test_window
import app, reception_app


def children(w):
    for c in w.winfo_children():
        yield c
        yield from children(c)


def main():
    checks = 0
    for factor in (1, 1.2, 1.25):
        for cls in (app.GymSoftApp, reception_app.ReceptionApp):
            root = tk.Tk(); root.tk.call('tk', 'scaling', 96/72*factor)
            resize_test_window(root, '1000x680')
            root.configure(bg=BG); cls.configure_styles(root)
            errors = []
            root.report_callback_exception = lambda kind, value, tb: errors.append(str(value))
            try:
                value = tk.BooleanVar(root, value=False)
                check = ttk.Checkbutton(root, text='Cliente activo', variable=value)
                check.pack(anchor='w', padx=24, pady=24)
                radio = ttk.Radiobutton(root, text='Mensualidad', value='month', variable=tk.StringVar(root))
                radio.pack(anchor='w', padx=24)
                pump(root)
                assert not check.instate(['selected'])
                check.invoke(); assert value.get() and check.instate(['selected'])
                check.invoke(); assert not value.get()
                root.focus_force(); check.focus_force(); pump(root)
                check.event_generate('<KeyPress-space>'); check.event_generate('<KeyRelease-space>'); pump(root)
                assert value.get(), 'El teclado debe marcar el checkbox.'
                check.state(['disabled']); check.invoke(); assert value.get()
                check.state(['!disabled']); assert_exposed(check); checks += 6
                cache = root._gymsoft_indicators
                for images in cache.values():
                    for state in ('selected', 'disabled_selected', 'active_selected'):
                        pixels = ImageTk.getimage(images[state]).convert('RGBA').get_flattened_data()
                        assert any(r > 245 and g > 245 and b > 245 and a == 255 for r,g,b,a in pixels)
                    a = ImageTk.getimage(images['normal']).tobytes()
                    b = ImageTk.getimage(images['selected']).tobytes()
                    assert a != b; checks += 4
                original_show = Modal.show
                cases = [('showinfo', 'Aceptar', 'ok'), ('showwarning', 'Aceptar', 'ok'),
                         ('showerror', 'Aceptar', 'ok'), ('askyesno', 'Sí', True),
                         ('askyesno', 'No', False), ('askokcancel', 'Cancelar', False),
                         ('askretrycancel', 'Reintentar', True), ('askyesnocancel', 'Cancelar', None)]
                for name, selected, expected in cases:
                    def show(win):
                        def inspect():
                            try:
                                labels = [str(w.cget('text')) for w in children(win) if isinstance(w, tk.Label)]
                                assert '?' not in labels
                                buttons = [w for w in children(win) if isinstance(w, tk.Button)]
                                assert len(buttons) >= 1
                                for control in buttons: assert_exposed(control)
                                if os.environ.get('GYMSOFT_QA_IMAGES') and name == 'askyesno' and selected == 'Sí' and cls is app.GymSoftApp:
                                    target = Path(os.environ['GYMSOFT_QA_IMAGES']); target.mkdir(parents=True, exist_ok=True)
                                    ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).crop((win.winfo_rootx(),win.winfo_rooty(),
                                        win.winfo_rootx()+win.winfo_width(),win.winfo_rooty()+win.winfo_height())).save(target/f'aviso_{round(factor*100)}.png')
                                next(w for w in buttons if w.cget('text') == selected).invoke()
                            except BaseException as error:
                                errors.append(repr(error)); win.close()
                        win.after(180, inspect)
                        return original_show(win)
                    with patch.object(Modal, 'show', show):
                        result = getattr(messagebox, name)('Confirmar operación',
                            'Revisa los datos antes de continuar. Los cambios se aplicarán al gimnasio seleccionado.', parent=root)
                    assert not errors, errors
                    assert result == expected; checks += 3
                # Cerrar una pregunta nunca debe confirmar una acción.
                def close_question(win):
                    win.after(80, lambda: win.event_generate('<Escape>'))
                    return original_show(win)
                with patch.object(Modal, 'show', close_question):
                    assert messagebox.askyesno('Confirmar', '¿Deseas continuar?', parent=root) is False
                checks += 1
                assert not errors, errors
            finally: destroy_root(root)
    print(f'PASS: {checks} comprobaciones de marcas blancas, teclado, avisos y cancelación al 100/120/125 %.')


if __name__ == '__main__': main()
