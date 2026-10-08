"""Regresión gráfica: los mensajes no redimensionan las columnas de ingreso.

Tk real, sin red, lector ni controlador; incluye márgenes, nombres largos,
ventana mediana/grande, desplazamiento y escalas 100/120/125 %.
"""
import os
os.environ['GYMSOFT_OFFLINE_QA'] = '1'
import faulthandler
from pathlib import Path
import sys
import time
import tkinter as tk
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as admin
import reception_app as reception
from responsive_ui import wrap_label
from responsive_ui_smoke import shell
from ui_assertions import destroy_root, resize_test_window
from ui_test_support import wait_for, settle_geometry


MESSAGES = ('INGRESO REGISTRADO', 'INGRESO NO AUTORIZADO', 'HUELLA NO RECONOCIDA')


def assert_text_fits(label):
    # Una etiqueta sin width fijo permite medir el rectángulo natural del texto
    # envuelto, incluidos sus márgenes reales. No se muestra en pantalla.
    options = {key: label.cget(key) for key in (
        'text', 'font', 'wraplength', 'padx', 'pady', 'borderwidth',
        'highlightthickness', 'justify')}
    measuring = tk.Label(label.master, **options)
    try:
        assert measuring.winfo_reqwidth() <= label.winfo_width() + 2, (
            f'Texto fuera del aviso: {label.cget("text")}; '
            f'necesita={measuring.winfo_reqwidth()}, disponible={label.winfo_width()}')
        assert measuring.winfo_reqheight() <= label.winfo_height() + 2, 'Aviso recortado en altura'
    finally:
        measuring.destroy()


def check_padding(factor):
    root = tk.Tk()
    root.tk.call('tk', 'scaling', 96/72*factor)
    root.geometry('360x250+10+10')
    label = tk.Label(root, text=MESSAGES[1], font=('Arial', 15, 'bold'),
                     width=1, padx=20, pady=18, borderwidth=3, highlightthickness=2)
    wrap_label(label)
    label.pack(fill='x')
    try:
        settle_geometry(root, (label,), 'envolver texto con márgenes')
        assert_text_fits(label)
        # El cálculo debe reservar los 50 píxeles interiores, incluso si una
        # palabra casualmente cabe con un wraplength incorrecto.
        assert int(label.cget('wraplength')) <= label.winfo_width()-50, 'El texto invade los márgenes'
    finally:
        destroy_root(root)
    return 2


def scenario(cls, factor):
    context = f'{cls.__name__} / {factor*100:g} %'
    print('  DISEÑO DE INGRESO: '+context, flush=True)
    with patch.object(reception.branding, 'show_reception_logo', lambda *_: None):
        root = shell(cls, factor)
    errors = []
    root.report_callback_exception = lambda *error: errors.append(error)
    key = 'checkin' if cls is admin.GymSoftApp else 'access'
    with patch.object(root.page_types[key], 'refresh', lambda *_: None):
        root.show_page(key)
    page = root.pages[key]
    badge = page.badge if cls is admin.GymSoftApp else page.status_label
    card, upper = badge.master, badge.master.master
    configure_count = [0]
    upper.bind('<Configure>', lambda _: configure_count.__setitem__(0, configure_count[0]+1), add='+')
    card.bind('<Configure>', lambda _: configure_count.__setitem__(0, configure_count[0]+1), add='+')
    checks = 0
    try:
        for width in (960, 1088, 1366, 1088):
            resize_test_window(root, f'{width}x900')
            reference = None
            for message in MESSAGES:
                badge.configure(text=message)
                settle_geometry(root, (upper, card, badge), context+' / '+message, errors=errors)
                # Excluye el alto: un nombre largo puede necesitar varias líneas,
                # pero no debe hacer crecer una columna a costa de su vecina.
                columns = tuple(upper.grid_bbox(column, 0)[2] for column in (0, 1))
                if reference is None:
                    reference = columns
                assert columns == reference, f'Columnas cambian con el mensaje: {reference} -> {columns}'
                assert_text_fits(badge)
                before = configure_count[0]
                until = time.monotonic()+.10
                wait_for(root, lambda: time.monotonic() >= until, 'vigilar parpadeo', errors=errors)
                assert configure_count[0] == before, 'El panel sigue recalculándose sin cambios'
                checks += 3
            name = 'María Alejandra Rodríguez Fernández de la Cruz'
            if cls is admin.GymSoftApp:
                page.result_name.configure(text=name)
                page.result_details.configure(text='Documento: 1234567890 · Estado: SIN ENTRADAS · Vencimiento: sin plan vigente')
            else:
                page.status_name.set(name)
                page.status_detail.set('Documento: 1234567890 · Estado: SIN ENTRADAS · Vencimiento: sin plan vigente')
            settle_geometry(root, (upper, card, badge), 'nombre y estado largos', errors=errors)
            assert tuple(upper.grid_bbox(c, 0)[2] for c in (0, 1)) == reference, 'El nombre empuja las columnas'
            before = tuple((card.winfo_width(), badge.winfo_width(), badge.cget('wraplength')))
            root.content_area.canvas.yview_scroll(2, 'units')
            settle_geometry(root, (upper, card, badge), 'desplazamiento', errors=errors)
            assert tuple((card.winfo_width(), badge.winfo_width(), badge.cget('wraplength'))) == before
            checks += 2
        assert not errors, errors
    finally:
        destroy_root(root)
    return checks


def main():
    faulthandler.enable()
    faulthandler.dump_traceback_later(60, repeat=True)
    try:
        count = 0
        for factor in (1, 1.2, 1.25):
            count += check_padding(factor)
            for cls in (admin.GymSoftApp, reception.ReceptionApp):
                count += scenario(cls, factor)
    finally:
        faulthandler.cancel_dump_traceback_later()
    print(f'PASS: {count} comprobaciones de avisos completos, columnas estables y ausencia de recálculo continuo; 100 %, 120 % y 125 %.')


if __name__ == '__main__': main()
