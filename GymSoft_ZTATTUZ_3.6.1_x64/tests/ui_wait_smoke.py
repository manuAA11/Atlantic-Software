"""Regresión: cola gráfica ocupada, respuesta perdida y cierre durante una prueba."""
import sys
import time
import tkinter as tk
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ui_assertions import destroy_root
from ui_test_support import wait_for


def main():
    root = tk.Tk()
    # Terminar el mapeo inicial antes de introducir deliberadamente una cola
    # infinita; Tk realiza su propia espera de geometría al mapear el root.
    root.update()
    turns = [0]
    active = [True]
    try:
        def busy_queue():
            turns[0] += 1
            if active[0]: root.after_idle(busy_queue)
        root.after_idle(busy_queue)
        wait_for(root, lambda: turns[0] >= 25, 'cola gráfica que nunca se vacía', timeout=2)
        # La cola sigue activa: una respuesta inexistente debe terminar con
        # error acotado, aunque update() quedaría esperando indefinidamente.
        started = time.monotonic()
        try:
            wait_for(root, lambda: False, 'respuesta simulada perdida', timeout=.15)
        except AssertionError as error:
            assert 'respuesta simulada perdida' in str(error)
        else:
            raise AssertionError('Una respuesta perdida se aceptó como correcta.')
        assert time.monotonic()-started < 1
        active[0] = False
        root.after(10, root.destroy)
        try:
            wait_for(root, lambda: False, 'cierre del usuario', timeout=2)
        except AssertionError as error:
            assert 'se cerró' in str(error)
        else:
            raise AssertionError('El cierre de la ventana se aceptó como PASS.')
    finally:
        destroy_root(root)
        destroy_root(root)
    print('PASS: cola gráfica continua, espera acotada, cierre detectado y limpieza repetida sin ocultar el error original.')


if __name__ == '__main__': main()
