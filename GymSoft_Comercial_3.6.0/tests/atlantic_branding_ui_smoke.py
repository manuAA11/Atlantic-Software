"""Real Tk icon inheritance and independent Windows installer resource checks."""
from pathlib import Path
import re
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
import reception_app
import desktop_ui
import atlantic_ui
from product_config import ADMIN_NAME, RECEPTION_NAME
from ui_assertions import destroy_root


def main():
    checks = 0
    icons = {}
    for role, module, name, resource in [('admin', app, ADMIN_NAME, 'icono.ico'),
                                         ('reception', reception_app, RECEPTION_NAME, 'icono_recepcion.ico')]:
        with Image.open(ROOT / resource) as icon:
            assert {16, 32, 48, 256}.issubset({s[0] for s in icon.ico.sizes()})
            icons[role] = icon.convert('RGBA').tobytes()
        root = tk.Tk()
        try:
            root.title(name)
            module.set_window_icon(root)
            assert root._atlantic_icon_name == resource
            dialog = tk.Toplevel(root)
            dialog.title('Confirmar operación')
            desktop_ui.decorate_window(dialog)
            root.update()
            assert dialog._atlantic_icon_name == resource, 'Dialog lost its role icon'
            assert dialog.cget('background').lower() == atlantic_ui.COLORS['background'].lower()
            if sys.platform != 'win32':
                assert hasattr(dialog, '_gymsoft_icon'), 'No rendered icon in Tk'
            dialog.destroy()
            checks += 4
        finally:
            destroy_root(root)
    assert icons['admin'] != icons['reception'], 'Role icons are identical'
    checks += 1
    for installer in ROOT.glob('instalador*.iss'):
        source = installer.read_text(encoding='utf-8-sig')
        assert 'AppPublisher=Atlantic Tech Software' in source
        files = source.split('[Files]', 1)[1].split('\n[', 1)[0]
        destinations = set()
        for line in files.splitlines():
            if not line.startswith('Source:'): continue
            src = re.search(r'Source: "([^"]+)"', line).group(1)
            if not src.endswith('.ico'): continue
            assert (ROOT / src).is_file()
            dest = re.search(r'DestDir: "([^"]+)"', line).group(1)
            rename = re.search(r'DestName: "([^"]+)"', line)
            destinations.add(dest + '\\' + (rename.group(1) if rename else src))
        for icon in re.findall(r'IconFilename: "([^"]+)"', source):
            assert icon in destinations, f'{installer.name}: shortcut icon is not installed: {icon}'
            checks += 1
    assert app.APP_NAME == ADMIN_NAME and reception_app.APP_NAME == RECEPTION_NAME
    checks += 1
    print(f'PASS: {checks} Atlantic identity checks; real Tk and installer source resources, no Windows build.')


if __name__ == '__main__':
    main()
