"""Comprueba componentes comerciales sin iniciar sesión ni cambiar el gimnasio."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path
import ssl
import struct
import sys
import tempfile
from zoneinfo import ZoneInfo

from product_config import PRODUCT_NAME, VERSION, load_config


EXPECTED_BITS = 64


def check_system():
    if sys.platform != 'win32':
        return 'Entorno de desarrollo ' + sys.platform
    win = sys.getwindowsversion()
    if win.major < 10 or struct.calcsize('P') * 8 != EXPECTED_BITS:
        raise RuntimeError('Esta edición necesita Windows 10 o posterior con proceso de 64 bits.')
    return f'Windows {win.major}.{win.minor}, compilación {win.build}, proceso de {EXPECTED_BITS} bits'


def data_directory():
    # Administrador, Recepción y propietario conservan la carpeta comercial.
    from app import app_data_directory
    return app_data_directory()


def check_storage():
    folder = data_directory()
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=folder) as file:
        file.write(b'Atlantic Gym')
    return 'Carpeta local comercial accesible'


def check_interface():
    import tkinter as tk
    from tkinter import ttk
    from PIL import Image, ImageTk
    from desktop_ui import configure_dark_styles, decorate_window, resource_path

    root = tk.Tk()
    root.withdraw()
    try:
        configure_dark_styles(root)
        box = ttk.Combobox(root, values=['Mensualidad', 'Tiquetera'], state='readonly')
        box.current(0)
        for title, filename in ((PRODUCT_NAME + ' Administrador', 'icono.ico'),
                                (PRODUCT_NAME + ' Recepción', 'icono_recepcion.ico')):
            with Image.open(resource_path(filename)) as source:
                image = ImageTk.PhotoImage(source.convert('RGBA'), master=root)
                if image.width() < 1 or image.height() < 1:
                    raise RuntimeError('No se pudo cargar el icono Atlantic.')
            root.title(title)
            decorate_window(root)
        root.update_idletasks()
        return f"Tk {root.tk.call('info', 'patchlevel')}; estilos Atlantic, iconos y formularios disponibles"
    finally:
        root.destroy()


def check_libraries():
    import certifi
    import httpx
    import openpyxl
    import supabase
    import realtime

    ssl.create_default_context(cafile=certifi.where())
    ZoneInfo('America/Bogota')
    return 'SSL, certificados, base en nube, Excel y zona horaria disponibles'


def check_configuration():
    load_config()
    return 'Configuración pública comercial válida; sin claves privadas'


def check_connection():
    import urllib.request
    import certifi

    config = load_config()
    request = urllib.request.Request(config['supabase_url'] + '/auth/v1/health',
                                     headers={'apikey': config['supabase_publishable_key']})
    with urllib.request.urlopen(request, context=ssl.create_default_context(cafile=certifi.where()),
                                timeout=8) as response:
        if response.status != 200:
            raise RuntimeError('El servicio de acceso no respondió correctamente.')
    return 'Conexión HTTPS verificada; no se usaron cuentas'


def run(*, network=True):
    checks = []

    def check(name, fn):
        try:
            detail = fn()
            checks.append({'comprobacion': name, 'estado': 'OK',
                           'detalle': str(detail or 'Disponible')})
        except Exception as error:
            checks.append({'comprobacion': name, 'estado': 'ERROR', 'detalle': str(error)})

    check('Sistema', check_system)
    check('Almacenamiento local', check_storage)
    check('Interfaz', check_interface)
    check('Componentes incluidos', check_libraries)
    check('Configuración comercial', check_configuration)
    if network:
        check('Conexión al proyecto comercial', check_connection)
    return {'producto': PRODUCT_NAME, 'version': VERSION,
            'fecha': datetime.now(timezone.utc).isoformat(),
            'estado': 'OK' if all(c['estado'] == 'OK' for c in checks) else 'REVISAR',
            'comprobaciones': checks,
            'alcance': 'Diagnóstico de componentes; no acredita cuentas, pagos, WhatsApp, '
                       'licencias operativas ni lector físico. La edición comercial no incluye relé.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--diagnostico', action='store_true')
    parser.add_argument('--sin-red', action='store_true')
    parser.add_argument('--silencioso', action='store_true')
    parser.add_argument('--informe', type=Path)
    args = parser.parse_args()
    report = run(network=not args.sin_red)
    target = args.informe or data_directory() / 'logs' / 'diagnostico.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if not args.silencioso:
        import tkinter as tk
        from desktop_ui import configure_dark_styles, decorate_window, messagebox

        root = tk.Tk()
        root.title('Diagnóstico ' + PRODUCT_NAME)
        configure_dark_styles(root)
        decorate_window(root)
        root.geometry('540x150')
        message = '\n'.join(c['estado'] + ' · ' + c['comprobacion'] for c in report['comprobaciones'])
        messagebox.showinfo(root.title(), message + '\n\nInforme: ' + str(target), parent=root)
        root.destroy()
    return 0 if report['estado'] == 'OK' else 1


if __name__ == '__main__':
    sys.exit(main())
