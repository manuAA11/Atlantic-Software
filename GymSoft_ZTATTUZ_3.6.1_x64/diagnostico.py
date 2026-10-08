"""Diagnóstico del ejecutable: no inicia sesión ni cambia datos del gimnasio."""
from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import ssl
import struct
import sys
import tempfile
from zoneinfo import ZoneInfo
from product_config import VERSION, load_config


EXPECTED_BITS = 64


def check_system():
    if sys.platform != 'win32':
        return 'Entorno de desarrollo ' + sys.platform
    win = sys.getwindowsversion()
    if win.major < 10 or struct.calcsize('P') * 8 != EXPECTED_BITS:
        raise RuntimeError(f'Esta edición necesita Windows 10 o posterior con proceso de {EXPECTED_BITS} bits.')
    return f'Windows {win.major}.{win.minor}, compilación {win.build}, proceso de {EXPECTED_BITS} bits'


def run(*, network=True):
    checks=[]
    def check(name, fn):
        try:
            detail=fn()
            checks.append({'comprobacion':name,'estado':'OK','detalle':str(detail or 'Disponible')})
        except Exception as error:
            checks.append({'comprobacion':name,'estado':'ERROR','detalle':str(error)})
    def writable():
        folder=Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'GymControl'
        folder.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryFile(dir=folder) as file:file.write(b'ZTATTUZ')
        return 'Carpeta local accesible'
    def interface():
        import tkinter as tk
        from tkinter import ttk
        from PIL import Image, ImageTk
        root=tk.Tk();root.withdraw()
        try:
            box=ttk.Combobox(root,values=['Mensualidad','Tiquetera']);box.current(0)
            image=ImageTk.PhotoImage(Image.new('RGBA',(16,16)),master=root)
            root.update_idletasks()
            return f"Tk {root.tk.call('info','patchlevel')}; imágenes y formularios disponibles"
        finally:root.destroy()
    def libraries():
        import certifi, httpx, openpyxl, supabase, realtime, serial
        from serial.tools import list_ports
        from door_access import RELAY_ON, RELAY_OFF
        assert len(RELAY_ON) == len(RELAY_OFF) == 4
        ssl.create_default_context(cafile=certifi.where())
        ZoneInfo('America/Bogota')
        return 'SSL, certificados, base en nube, Excel y zona horaria disponibles'
    def connection():
        import urllib.request,certifi
        config=load_config()
        request=urllib.request.Request(config['supabase_url']+'/auth/v1/health',headers={'apikey':config['supabase_publishable_key']})
        with urllib.request.urlopen(request,context=ssl.create_default_context(cafile=certifi.where()),timeout=8) as response:
            if response.status!=200:raise RuntimeError('El servicio de acceso no respondió correctamente.')
        return 'Conexión HTTPS verificada; no se usaron cuentas'
    check('Sistema',check_system);check('Almacenamiento local',writable);check('Interfaz',interface)
    check('Componentes incluidos',libraries);check('Configuración ZTATTUZ',lambda:bool(load_config()))
    if network:check('Conexión al proyecto original',connection)
    return {'producto':'Gym soft · ZTATTUZ','version':VERSION,'fecha':datetime.now(timezone.utc).isoformat(),
            'estado':'OK' if all(c['estado']=='OK' for c in checks) else 'REVISAR','comprobaciones':checks,
            'alcance':'Diagnóstico de componentes; no certifica todas las variantes de Windows Mini ni el lector físico.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--diagnostico',action='store_true')
    parser.add_argument('--sin-red',action='store_true');parser.add_argument('--silencioso',action='store_true')
    parser.add_argument('--informe',type=Path)
    args=parser.parse_args()
    report=run(network=not args.sin_red)
    target=args.informe or Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'GymControl/logs/diagnostico.json'
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if not args.silencioso:
        import tkinter as tk
        from desktop_ui import configure_dark_styles,decorate_window,messagebox
        root=tk.Tk();configure_dark_styles(root);decorate_window(root)
        root.title('Diagnóstico ZTATTUZ');root.geometry('540x150')
        message='\n'.join(c['estado']+' · '+c['comprobacion'] for c in report['comprobaciones'])
        messagebox.showinfo('Diagnóstico ZTATTUZ',message+'\n\nInforme: '+str(target),parent=root)
        root.destroy()
    return 0 if report['estado']=='OK' else 1


if __name__=='__main__':sys.exit(main())
