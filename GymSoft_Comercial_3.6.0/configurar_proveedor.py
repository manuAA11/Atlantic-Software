from __future__ import annotations
import json
from pathlib import Path
import tkinter as tk
from desktop_ui import configure_dark_styles, decorate_window, messagebox, simpledialog
from product_config import load_config

def main():
    root=tk.Tk();root.withdraw();configure_dark_styles(root);decorate_window(root)
    messagebox.showinfo('Configurar Gym soft','Necesitas un proyecto NUEVO de Supabase con INSTALAR_BASE_NUEVA.sql ya instalado. Usa exclusivamente la clave publicable.',parent=root)
    url=simpledialog.askstring('Proyecto comercial','URL del proyecto nuevo (https://…supabase.co):',parent=root)
    if not url:return
    key=simpledialog.askstring('Clave publicable','Clave publicable del proyecto comercial:',parent=root)
    if not key:return
    path=Path(__file__).resolve().parent/'gymsoft_config.json'
    previous=path.read_bytes() if path.exists() else None
    try:
        path.write_text(json.dumps({'supabase_url':url.strip(),'supabase_publishable_key':key.strip()},indent=2),encoding='utf-8')
        load_config()
        from cloud import CloudService
        CloudService()
        messagebox.showinfo('Configuración lista','Conexión comercial verificada. Ya puedes crear los instaladores.',parent=root)
    except Exception as error:
        if previous is None:path.unlink(missing_ok=True)
        else:path.write_bytes(previous)
        messagebox.showerror('No se pudo configurar',str(error),parent=root)
    finally:root.destroy()

if __name__=='__main__':main()
