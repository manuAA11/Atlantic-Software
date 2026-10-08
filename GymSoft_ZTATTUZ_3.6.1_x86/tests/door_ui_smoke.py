"""Configuración de puerta y ambos roles con USB simulado, nunca físico."""
from pathlib import Path
import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['GYMSOFT_OFFLINE_QA'] = '1'
import app, reception_app, door_ui
from door_access import DoorConfig, RELAY_ON, RELAY_OFF
from test_door_access import FakeUSB
from responsive_ui_smoke import shell, descendants, assert_buttons_fit
from ui_assertions import pump, destroy_root, resize_test_window
from responsive_ui import fit_window


def main():
    checks = 0
    port = dict(port='COM7', vid=0x1A86, pid=0x7523, serial_number='SIMULADO',
                location='USB1', description='LCUS-1 simulado')
    for scale in (1, 1.2, 1.25):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, LOCALAPPDATA=temp):
            for cls in (app.GymSoftApp, reception_app.ReceptionApp):
                root = shell(cls, scale)
                root.db.gym_id = '00000000-0000-4000-8000-000000000001'
                root.db = door_ui.install(root, root.db, admin=cls is app.GymSoftApp)
                usb = FakeUSB(); usb.on = root.door._cancel.set
                root.door.transport = lambda config: usb
                root.door.offline = False  # Transporte sustituido antes de habilitar.
                failures = []
                root.report_callback_exception = lambda kind, error, tb: failures.append(str(error))
                try:
                    key = 'checkin' if root.door_admin else 'access'
                    with patch.object(root.page_types[key], 'refresh', lambda *_: None): root.show_page(key)
                    pump(root)
                    assert any(isinstance(w, ttk.Button) and w.cget('text') == 'Puerta / relé'
                               for w in descendants(root.pages[key])); checks += 1
                    with patch('door_ui.available_ports', return_value=[port]):
                        win = door_ui.DoorDialog(root)
                        win.update_idletasks()
                        fit_window(win, 640, 740, parent=root)
                        win.deiconify(); pump(root, .25)
                        assert_buttons_fit(win)
                        if root.door_admin:
                            assert not win.enabled.get()
                            win.enabled.set(True); win.port.set(win.port_label(port)); win.seconds.set('2')
                            with patch.object(door_ui.messagebox, 'showinfo') as confirmation:
                                assert win.save(); confirmation.assert_called_once()
                            pump(root, .15)
                            assert root.door.store.load().port == 'COM7'
                            assert RELAY_ON not in usb.frames
                            with patch.object(door_ui.messagebox, 'askokcancel', return_value=False): win.test()
                            assert RELAY_ON not in usb.frames
                            with patch.object(door_ui.messagebox, 'askokcancel', return_value=True): win.test()
                            pump(root, .15)
                            assert usb.frames.count(RELAY_ON) == 1 and usb.frames[-1] == RELAY_OFF
                            win.seconds.set('50')
                            assert not win.save(); assert root.door.store.load().seconds == 2
                            win.seconds.set('2')
                            if os.environ.get('GYMSOFT_QA_IMAGES'):
                                from PIL import ImageGrab
                                target = Path(os.environ['GYMSOFT_QA_IMAGES']); target.mkdir(exist_ok=True, parents=True)
                                ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).crop((win.winfo_rootx(),win.winfo_rooty(),
                                    win.winfo_rootx()+win.winfo_width(),win.winfo_rooty()+win.winfo_height())).save(target/f'puerta_{round(scale*100)}.png')
                            checks += 8
                        else:
                            assert win.saved.enabled and win.saved.port == 'COM7'
                            labels = [w.cget('text') for w in descendants(win) if isinstance(w, (ttk.Button, tk.Button))]
                            assert 'Probar apertura' not in labels and 'Guardar configuración' not in labels
                            assert win.save() is False
                            win.secure(); pump(root, .15)
                            assert RELAY_ON not in usb.frames
                            checks += 4
                        win.destroy(); pump(root)
                    # El botón manual existe en ambos roles. Cancelar no hace
                    # I/O y confirmar no llama a los RPC de asistencia/pagos.
                    assert any(isinstance(w, ttk.Button) and w.cget('text') == 'Abrir puerta'
                               for w in descendants(root.pages[key]))
                    before = usb.frames.count(RELAY_ON)
                    root.db.database.register_checkin.reset_mock()
                    with patch.object(door_ui.messagebox, 'askokcancel', return_value=False):
                        assert root.open_door_manually() is False
                    assert usb.frames.count(RELAY_ON) == before
                    with patch.object(door_ui.messagebox, 'askokcancel', return_value=True):
                        assert root.open_door_manually() is True
                    pump(root, .15)
                    assert usb.frames.count(RELAY_ON) == before + 1
                    root.db.database.register_checkin.assert_not_called()
                    checks += 4
                    for size in ('960x640', '1366x768'):
                        resize_test_window(root, size); pump(root, .15); assert_buttons_fit(root.pages[key]); checks += 1
                    assert not failures, failures
                finally: destroy_root(root)
    print(f'PASS: {checks} comprobaciones de puerta, configuración, confirmación, roles y escalas; USB simulado.')


if __name__ == '__main__': main()
