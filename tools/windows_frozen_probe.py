"""Exercise frozen Windows dependencies and branding without accounts or hardware."""
import argparse
import json
from pathlib import Path
import ssl
import struct
import sys
import tkinter as tk
from zoneinfo import ZoneInfo
import certifi
import httpx
import openpyxl
import realtime
import supabase
from PIL import Image, ImageTk
from desktop_ui import configure_dark_styles, decorate_window
import app
import reception_app
from product_config import PRODUCT_NAME


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    assert sys.platform == 'win32', 'This probe must run on Windows.'
    assert callable(app.GymSoftApp) and callable(reception_app.ReceptionApp)
    if PRODUCT_NAME == 'Atlantic Gym':
        import owner_panel
        assert callable(owner_panel.OwnerPanel)
    else:
        import serial
        from serial.tools import list_ports
        from door_access import RELAY_ON, RELAY_OFF
        assert len(RELAY_ON) == len(RELAY_OFF) == 4
    root = tk.Tk()
    root.withdraw()
    try:
        configure_dark_styles(root)
        decorate_window(root)
        photo = ImageTk.PhotoImage(Image.new('RGBA', (32, 32), '#0055ff'), master=root)
        assert photo.width() == 32
        root.update_idletasks()
        ssl.create_default_context(cafile=certifi.where())
        assert ZoneInfo('America/Bogota').key == 'America/Bogota'
        report = {'status': 'PASS', 'python': sys.version, 'process_bits': struct.calcsize('P') * 8,
                  'tk': root.tk.call('info', 'patchlevel'), 'frozen': bool(getattr(sys, 'frozen', False)),
                  'checks': ['Frozen Admin and Reception module imports', 'Product-specific module imports',
                             'Tk and Atlantic dark styles', 'Role window icons', 'Pillow ImageTk',
                             'Supabase/realtime/httpx imports', 'Excel import', 'SSL certificates', 'Bogota timezone'],
                  'scope': 'Windows frozen component probe only. No account, hardware, installer or final release acceptance.'}
        assert report['frozen'], 'Run the generated Windows probe executable.'
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('FROZEN WINDOWS COMPONENTS PASS')
    finally:
        root.destroy()


if __name__ == '__main__':
    main()
