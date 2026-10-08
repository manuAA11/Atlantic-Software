from __future__ import annotations
import base64
import io
from pathlib import Path
from dark_files import filedialog
from desktop_ui import messagebox
from PIL import Image, ImageOps, ImageTk

def read_logo(cloud):
    rows=cloud.client.table('gym_branding').select('logo_data').eq('gym_id',cloud.gym_id).execute().data or []
    data=rows[0].get('logo_data','') if rows else ''
    if not data:
        return None
    raw=base64.b64decode(data.split(',',1)[-1],validate=True)
    with Image.open(io.BytesIO(raw)) as source:
        image=ImageOps.contain(source.convert('RGBA'),(150,95))
        return image.copy()

def load_admin_logo(app, show_error=False):
    try:
        image=read_logo(app.cloud)
        app.logo_image=ImageTk.PhotoImage(image) if image else None
        app.logo_label.configure(image=app.logo_image or '')
        return bool(image)
    except Exception as error:
        if show_error:
            messagebox.showerror('Logotipo',str(error),parent=app)
        return False

def choose_logo(app):
    filename=filedialog.askopenfilename(title='Logo del gimnasio',filetypes=[('Imágenes','*.png *.jpg *.jpeg')],parent=app)
    if not filename:
        return
    try:
        with Image.open(filename) as source:
            image=ImageOps.exif_transpose(source).convert('RGBA')
            image.thumbnail((480,480))
            output=io.BytesIO(); image.save(output,format='PNG',optimize=True)
        data='data:image/png;base64,'+base64.b64encode(output.getvalue()).decode('ascii')
        app.cloud.client.table('gym_branding').upsert({'gym_id':app.cloud.gym_id,'logo_data':data}).execute()
        load_admin_logo(app,True)
        messagebox.showinfo('Logo guardado','El logo pertenece únicamente a este gimnasio y se comparte con sus equipos.',parent=app)
    except Exception as error:
        messagebox.showerror('No se pudo guardar el logotipo',str(error),parent=app)

def show_reception_logo(app, parent):
    import tkinter as tk
    try:
        image=read_logo(app.cloud)
        if image:
            app.gym_logo_image=ImageTk.PhotoImage(image)
            tk.Label(parent,image=app.gym_logo_image,bg=parent.cget('bg')).pack(anchor='w',pady=(0,8))
    except Exception:
        pass
