"""La prueba visual respeta el monitor y sigue rechazando superposiciones."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from tkinter import ttk
from unittest.mock import Mock, patch
from responsive_ui import ScrollArea, work_area
from ui_assertions import (assert_exposed, destroy_root, enable_dpi_awareness,
                           pump, resize_test_window, _restore_minimized_test)


def must_fail(action, message):
    try:
        action()
    except AssertionError as error:
        assert message in str(error), str(error)
    else:
        raise AssertionError('La comprobación aceptó un control que debía rechazar.')


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    root.title('Gym soft · Verificación del área visible')
    failures = []
    root.report_callback_exception = lambda kind, error, tb: failures.append(str(error))
    try:
        resize_test_window(root, '2000x1500')
        x, y, width, height = work_area(root)
        assert root.winfo_width() <= width and root.winfo_height() <= height
        resize_test_window(root, '700x450')
        area = ScrollArea(root)
        area.pack(fill='both', expand=True)
        book = ttk.Notebook(area.body)
        book.pack(fill='both', expand=True)
        tab = ttk.Frame(book)
        book.add(tab, text='Finanzas de prueba')
        tree = ttk.Treeview(tab, columns=('name',), show='headings')
        tree.heading('name', text='Concepto')
        tree.insert('', 'end', values=('Movimiento de demostración',))
        tree.pack(fill='both', expand=True)
        pump(root)
        assert_exposed(book)
        assert_exposed(tree)

        # Una ventana que asoma por el borde no debe consultar fuera del monitor.
        # Se registran las coordenadas reales; la consulta nativa sigue ejecutándose.
        root.overrideredirect(True)
        root.geometry(f'700x450{(x + width - 240):+d}{(y + 20):+d}')
        root.lift();pump(root)
        native_query = root.winfo_containing
        points = []
        def on_screen_query(px, py, *args, **kwargs):
            assert x <= px < x+width and y <= py < y+height, (px, py, work_area(root))
            points.append((px, py))
            return native_query(px, py, *args, **kwargs)
        with patch.object(root, 'winfo_containing', side_effect=on_screen_query):
            assert_exposed(book)
            assert_exposed(tree)
        assert len(points) == 2
        root.overrideredirect(False)
        resize_test_window(root, '700x450')
        pump(root)

        # El contenedor superpuesto que causó las pantallas vacías debe fallar.
        wrapper = book.grid_info()['in']
        wrapper.tkraise(book);pump(root)
        must_fail(lambda: assert_exposed(book), 'Control tapado')
        book.tkraise(wrapper);pump(root)
        assert_exposed(book)
        wrapper = tree.grid_info()['in']
        wrapper.tkraise(tree);pump(root)
        must_fail(lambda: assert_exposed(tree), 'Control tapado')
        tree.tkraise(wrapper);pump(root)
        assert_exposed(tree)

        # Una consulta sin resultado durante la restauración se repite: el
        # éxito posterior exige encontrar realmente el control, no solo su caja.
        native_query = root.winfo_containing
        queries = []
        def restoring_query(px, py, *args, **kwargs):
            queries.append((px, py))
            return None if len(queries) == 1 else native_query(px, py, *args, **kwargs)
        with patch.object(root, 'winfo_containing', side_effect=restoring_query):
            assert_exposed(tree)
        assert len(queries) >= 2

        # Reintentar no debe aceptar una superposición que aparece después.
        wrapper.tkraise(tree);pump(root)
        queries.clear()
        with patch.object(root, 'winfo_containing', side_effect=restoring_query):
            must_fail(lambda: assert_exposed(tree), 'Control tapado')
        tree.tkraise(wrapper);pump(root)

        tree.grid_remove();pump(root)
        must_fail(lambda: assert_exposed(tree), 'Control oculto')
        tree.grid();pump(root)

        # Sin gestor de ventanas (Xvfb) iconify no minimiza. Comprobar siempre
        # la decisión y, en Windows, ejecutar también la minimización real.
        minimized = Mock()
        minimized.state.return_value = 'iconic'
        _restore_minimized_test(minimized)
        minimized.deiconify.assert_called_once()
        hidden = Mock()
        hidden.state.return_value = 'withdrawn'
        _restore_minimized_test(hidden)
        hidden.deiconify.assert_not_called()
        if root.tk.call('tk', 'windowingsystem') == 'win32':
            root.iconify()
            pump(root, .2)
            assert root.state() == 'normal', 'No se restauró la ventana de prueba.'
            assert_exposed(tree)

        # None conserva el fallo: no se convierte en éxito para dejar compilar.
        with patch.object(root, 'winfo_containing', return_value=None):
            must_fail(lambda: assert_exposed(book), 'No se encontró un control')
        assert not failures, failures
        print('PASS: límites del monitor, restauración de prueba, controles ocultos, '
              'superposiciones y consultas sin resultado.')
    finally:
        destroy_root(root)


if __name__ == '__main__':
    main()
