"""Optional rounded presentations using native Tk controls and the Atlantic UI Kit.

Changes surfaces, never recreates pages or touches data/session/hardware services.
Rounded ttk image elements keep native focus, commands, validation and state.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk
from common import atlantic_ui as kit
from common.theme_settings import THEMES, save_theme


def _surface(widget):
    if widget is None:
        return kit.COLORS['background']
    if isinstance(widget, ttk.Widget):
        style = str(widget.cget('style') or widget.winfo_class())
        if style in ('Card.TFrame', 'Surface.TFrame'):
            return kit.COLORS['surface']
        return ttk.Style(widget).lookup(style, 'background') or kit.COLORS['background']
    if getattr(widget, '_appearance_panel', None) and kit.THEME != 'dark':
        return kit.COLORS['surface']
    try:
        return widget.cget('background')
    except tk.TclError:
        return kit.COLORS['background']


def _rounded(fill, outline, radius=12, size=40):
    # Nine-slice stretchable, antialiased asset; drawn once per interpreter.
    factor = 3
    im = Image.new('RGBA', (size*factor, size*factor))
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle((1, 1, size*factor-2, size*factor-2), radius=radius*factor,
                           fill=fill, outline=outline, width=factor)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def circle_icon(name, size=36, *, selected=False, color=None):
    """Original vector glyphs; no OS-specific private-use font dependency."""
    c = kit.COLORS
    factor = 3
    image = Image.new('RGBA', (size*factor, size*factor))
    draw = ImageDraw.Draw(image)
    fill = c['primary'] if selected else c['surface_hover']
    ink = ('#FFFFFF' if kit.THEME.startswith('league_') else c['background']) if selected else (color or c['blue'])
    draw.ellipse((1, 1, size*factor-2, size*factor-2), fill=fill)
    def xy(points):
        return [(round(x*size*factor/36), round(y*size*factor/36)) for x,y in points]
    def line(points):
        draw.line(xy(points), fill=ink, width=max(3, round(size*factor/20)), joint='curve')
    def rect(box):
        points=xy([(box[0],box[1]),(box[2],box[3])])
        draw.rounded_rectangle((*points[0],*points[1]),radius=2*factor,outline=ink,width=max(3,round(size*factor/20)))
    def oval(box):
        points=xy([(box[0],box[1]),(box[2],box[3])])
        draw.ellipse((*points[0],*points[1]),outline=ink,width=max(3,round(size*factor/20)))
    name = str(name).casefold()
    if any(x in name for x in ('dashboard','inicio')):
        line([(9,17),(18,9),(27,17)]);line([(12,16),(12,27),(24,27),(24,16)])
        line([(16,27),(16,21),(20,21),(20,27)])
    elif any(x in name for x in ('cliente','persona','staff')):
        oval((14,8,22,16));line([(9,27),(10,22),(14,19),(22,19),(26,22),(27,27)])
    elif any(x in name for x in ('tienda','producto','venta')):
        rect((10,14,26,28));line([(14,15),(14,11),(16,8),(20,8),(22,11),(22,15)])
    elif any(x in name for x in ('config','ajuste')):
        oval((10,10,26,26));oval((15,15,21,21))
        for a,b in [((18,6),(18,11)),((18,25),(18,30)),((6,18),(11,18)),((25,18),(30,18))]:line([a,b])
    elif any(x in name for x in ('entrada','recep','acceso')):
        rect((11,8,25,28));line([(7,18),(21,18),(17,14)]);line([(21,18),(17,22)])
    elif any(x in name for x in ('finanza','estad','ingreso','reporte')):
        line([(10,27),(10,20)]);line([(18,27),(18,14)]);line([(26,27),(26,8)])
    elif any(x in name for x in ('clase','reserva','calend')):
        rect((9,11,27,28));line([(9,16),(27,16)]);line([(14,8),(14,13)]);line([(22,8),(22,13)])
    elif any(x in name for x in ('rutina','ejercicio')):
        line([(9,18),(27,18)]);line([(11,11),(11,25)]);line([(25,11),(25,25)])
    elif any(x in name for x in ('membres','pago','renova')):
        rect((8,11,28,26));line([(8,16),(28,16)]);line([(12,22),(17,22)])
    else:
        oval((10,10,26,26));line([(14,18),(17,21),(23,14)])
    return image.resize((size,size), Image.Resampling.LANCZOS)


class RoundedPanel:
    """A passive backdrop below existing native children; never intercepts input."""
    def __init__(self, host):
        self.host = host
        self.original = {key:host.cget(key) for key in ('background','highlightthickness')}
        self.original['background'] = getattr(host,'_appearance_dark_options',{}).get('background',kit.DARK_COLORS['surface'])
        self.backdrop = tk.Label(host, bd=0, highlightthickness=0, takefocus=False)
        self.backdrop._appearance_decoration = True
        self.dimensions = None
        self.photo = None
        self.job = None
        host.bind('<Configure>', self.schedule, add='+')
        host.bind('<Destroy>', self.destroy, add='+')

    def destroy(self, event):
        if event.widget is self.host:
            if self.job:
                self.host.after_cancel(self.job)
                self.job = None
            # Release Tk images on the UI thread, before interpreter teardown.
            self.photo = None

    def schedule(self, event=None):
        if (event is None or event.widget is self.host) and self.job is None:
            self.job = self.host.after_idle(self.paint)

    def paint(self):
        self.job = None
        if not self.host.winfo_exists():
            return
        if kit.THEME == 'dark':
            self.backdrop.place_forget()
            self.host.configure(**self.original)
            return
        c=kit.COLORS
        width,height=self.host.winfo_width(),self.host.winfo_height()
        outer=_surface(self.host.master)
        if self.host.cget('background') != outer or int(self.host.cget('highlightthickness')) != 0:
            self.host.configure(background=outer,highlightthickness=0)
        key=(width,height,outer,c['surface'],c['line'])
        if min(width,height)<2:
            return
        if key != self.dimensions:
            im=Image.new('RGB',(width*2,height*2),outer)
            draw=ImageDraw.Draw(im)
            draw.rounded_rectangle((0,0,width*2-1,height*2-1),radius=24,
                                   fill=c['surface'],outline=c['line'],width=2)
            self.photo=ImageTk.PhotoImage(im.resize((width,height),Image.Resampling.LANCZOS),master=self.host)
            self.backdrop.configure(image=self.photo)
            self.dimensions=key
        if not self.backdrop.winfo_manager():
            self.backdrop.place(x=0,y=0,relwidth=1,relheight=1)
            self.backdrop.lower()


class Appearance:
    def __init__(self, root):
        self.root = root
        self.style = ttk.Style(root)
        self.layouts = {}
        self.images = {}
        self.job = None
        self.applying = False
        self.styled_theme = None
        self.pending_widgets = set()
        self.host_styles = set()
        self.notebook_margins = self.style.lookup('TNotebook','tabmargins')
        root.bind_all('<Map>', self.mapped, add='+')
        root.bind('<Destroy>', self.destroyed, add='+')
        self.schedule()

    def destroyed(self, event):
        if event.widget is self.root:
            if self.job:
                self.root.after_cancel(self.job)
                self.job = None
            self.images.clear()

    def mapped(self, event):
        if kit.THEME != 'dark' and not self.applying:
            self.schedule(event.widget)

    def schedule(self, widget=None):
        self.pending_widgets.add(self.root if widget is None else widget)
        if self.job is None:
            self.job = self.root.after_idle(self.present)

    def _element(self, key, fill, outline, radius, size=40):
        key = key + '.' + kit.THEME
        if key in self.images:
            return key
        def tone(color, amount):
            values=[int(color[index:index+2],16) for index in (1,3,5)]
            return '#'+''.join(f'{max(0,min(255,value+amount)):02x}' for value in values)
        photos = [ImageTk.PhotoImage(_rounded(color, border, radius, size), master=self.root)
                  for color,border in [(fill,outline),(tone(fill,12),outline),
                                       (tone(fill,-10),outline),(kit.COLORS['surface_hover'],outline),
                                       (fill,kit.COLORS['blue'])]]
        self.images[key] = photos
        self.style.element_create(key, 'image', photos[0], ('disabled', photos[3]),
                                  ('pressed',photos[2]),('active',photos[1]),('focus',photos[4]),
                                  border=radius+2, sticky='nswe')
        return key

    def _layout(self, name, layout):
        if name not in self.layouts:
            self.layouts[name] = self.style.layout(name)
        self.style.layout(name, layout)

    def styles(self):
        s, c = self.style, kit.COLORS
        if kit.THEME == 'dark':
            for name, layout in self.layouts.items():
                s.layout(name, layout)
            s.configure('TNotebook',tabmargins=self.notebook_margins or (0,0,0,0))
            # Per-widget label backgrounds must return to the legacy defaults.
            return
        if not self.layouts:
            # Capture inherited layouts before replacing TButton itself; otherwise
            # derived buttons would remember a themed layout as their dark base.
            for name in ('TButton','Primary.TButton','Login.Primary.TButton','Accent.TButton',
                         'Danger.TButton','Calendar.TButton','TEntry','Card.TFrame','TNotebook.Tab'):
                self.layouts[name]=s.layout(name)
        # Some legacy screens define fixed dark label/table colors. Override the
        # semantic styles as well as surfaces so light themes remain readable.
        for name in ('TLabel','Title.TLabel','Section.TLabel','Field.TLabel'):
            s.configure(name, foreground=c['text'])
        for name in ('Subtitle.TLabel','CardMuted.TLabel','Muted.TLabel'):
            s.configure(name, foreground=c['muted'])
        s.configure('Surface.TFrame',background=c['surface'])
        s.configure('Treeview',foreground=c['text'],bordercolor=c['line'])
        s.configure('Treeview.Heading',foreground=c['muted'],bordercolor=c['line'])
        s.map('Treeview',background=[('selected',c['primary'])],
              foreground=[('selected','#FFFFFF' if kit.THEME.startswith('league_') else c['text'])])
        for name, fill, ink in [('TButton',c['surface_hover'],c['text']),
                                ('Primary.TButton',c['primary'],'#FFFFFF' if kit.THEME.startswith('league_') else c['background']),
                                ('Login.Primary.TButton',c['primary'],'#FFFFFF' if kit.THEME.startswith('league_') else c['background']),
                                ('Accent.TButton',c['accent'],c['text']),
                                ('Danger.TButton',c['danger_bg'],c['danger']),
                                ('Calendar.TButton',c['surface_hover'],c['text'])]:
            compact=kit.THEME.startswith('league_')
            radius=8 if name=='Calendar.TButton' else (10 if compact else 12)
            el=self._element('Atlantic.Minimal.'+name,fill,fill,radius,24 if name=='Calendar.TButton' else (28 if compact else 40))
            self._layout(name,[(el,{'sticky':'nswe','children':[
                ('Button.focus',{'sticky':'nswe','children':[
                    ('Button.padding',{'sticky':'nswe','children':[
                        ('Button.label',{'sticky':'nswe'})]})]})]})])
            s.configure(name, background=c['background'], foreground=ink,
                        relief='flat', borderwidth=0, padding=(4,3) if name=='Calendar.TButton' else ((12,6) if compact else (16,10)))
            s.map(name,foreground=[('disabled',c['muted'])])
        entry=self._element('Atlantic.Minimal.Entry',c['surface'],c['line'],10,28 if kit.THEME.startswith('league_') else 40)
        self._layout('TEntry',[(entry,{'sticky':'nswe','children':[
            ('Entry.padding',{'sticky':'nswe','children':[
                ('Entry.textarea',{'sticky':'nswe'})]})]})])
        s.configure('TEntry',fieldbackground=c['surface'],foreground=c['text'],insertcolor=c['text'],borderwidth=0,padding=(10,6) if kit.THEME.startswith('league_') else (12,10))
        # Keep native combobox arrow, editing and dropdown behavior.
        s.configure('TCombobox',relief='flat',borderwidth=0,fieldbackground=c['surface'],
                    lightcolor=c['line'],darkcolor=c['line'],bordercolor=c['line'],foreground=c['text'],arrowcolor=c['muted'])
        s.map('TCombobox',fieldbackground=[('readonly',c['surface']),('disabled',c['background'])],
              foreground=[('disabled',c['muted']),('readonly',c['text'])])
        for scrollbar in ('Vertical.TScrollbar','Horizontal.TScrollbar'):
            s.configure(scrollbar,background=c['surface_hover'],troughcolor=c['background'],arrowcolor=c['muted'],
                        bordercolor=c['line'],lightcolor=c['line'],darkcolor=c['line'])
            s.map(scrollbar,background=[('active',c['line'])])
        card=self._element('Atlantic.Minimal.Card',c['surface'],c['line'],14)
        self._layout('Card.TFrame',[(card,{'sticky':'nswe'})])
        s.configure('Card.TFrame',background=c['background'],borderwidth=0,relief='flat')
        tab=self._element('Atlantic.Minimal.Tab',c['surface'],c['line'],10)
        self._layout('TNotebook.Tab',[(tab,{'sticky':'nswe','children':[
            ('Notebook.padding',{'sticky':'nswe','children':[
                ('Notebook.label',{'sticky':'nswe'})]})]})])
        s.configure('TNotebook',background=c['background'],borderwidth=0,
                    tabmargins=(0,4,0,0))
        s.configure('TNotebook.Tab',padding=(18,10),borderwidth=0)
        s.map('TNotebook.Tab',foreground=[('selected',c['blue']),('active',c['text'])])
        s.configure('Treeview',rowheight=38,borderwidth=0,relief='flat',
                    background=c['surface'],fieldbackground=c['surface'])
        s.configure('Treeview.Heading',background=c['surface'],relief='flat',padding=(10,12))
        s.configure('TLabelframe',relief='flat',borderwidth=0)

    def _icon(self, label, name, selected=False):
        if not hasattr(label,'_appearance_icon_original'):
            label._appearance_icon_original={key:label.cget(key) for key in ('image','text','width','height')}
        if hasattr(label,'_appearance_glyph') and not hasattr(label,'_appearance_glyph_background'):
            color=str(label.cget('background')).lower()
            label._appearance_glyph_background=next((kit.DARK_COLORS[token] for token,value in kit.COLORS.items() if value.lower()==color),color)
        if kit.THEME == 'dark':
            label.configure(**label._appearance_icon_original)
            if hasattr(label,'_appearance_glyph_background'):
                label.configure(background=label._appearance_glyph_background)
            return
        size=round(32*max(1,float(self.root.tk.call('tk','scaling'))/(96/72)))
        key=('icon',kit.THEME,name,size,selected)
        if key not in self.images:
            self.images[key]=ImageTk.PhotoImage(circle_icon(name,size,selected=selected),master=self.root)
        color=_surface(label.master)
        if str(label.cget('image')) != str(self.images[key]) or str(label.cget('background')) != color:
            label.configure(image=self.images[key],text='',width=0,height=0,bd=0,background=color)

    def widget(self, widget, surface_context=None):
        if getattr(widget,'_appearance_decoration',False):
            return
        if isinstance(widget,tk.Frame):
            if (kit.THEME != 'dark' and not hasattr(widget,'_appearance_panel')
                    and int(widget.cget('highlightthickness')) == 1
                    and str(widget.cget('background')).lower() in {
                        color.lower() for key,color in kit.COLORS.items()
                        if key in ('surface','surface_alt','blue_bg','success_bg','danger_bg','warning_bg','purple_bg')}):
                widget._appearance_panel=RoundedPanel(widget)
            if hasattr(widget,'_appearance_panel'):
                widget._appearance_panel.paint()
        if hasattr(widget,'_appearance_panel'):
            surface_context=kit.COLORS['surface'] if kit.THEME != 'dark' else None
        if isinstance(widget,(tk.Label,tk.Frame)) and not hasattr(widget,'_appearance_panel'):
            if kit.THEME != 'dark' and surface_context:
                if not hasattr(widget,'_appearance_flat_background'):
                    value=str(widget.cget('background'))
                    widget._appearance_flat_background=getattr(widget,'_appearance_dark_options',{}).get('background',
                        next((kit.DARK_COLORS[key] for key,color in kit.COLORS.items() if color.lower()==value.lower()),value))
                if str(widget.cget('background')) != surface_context:
                    widget.configure(background=surface_context)
            elif kit.THEME == 'dark' and hasattr(widget,'_appearance_flat_background'):
                widget.configure(background=widget._appearance_flat_background)
        if isinstance(widget,ttk.Widget) and not isinstance(widget,(ttk.Label,ttk.Notebook,ttk.Treeview)):
            original=getattr(widget,'_appearance_original_style',None)
            if kit.THEME != 'dark':
                if original is None:
                    original=str(widget.cget('style'))
                    widget._appearance_original_style=original
                base=original or widget.winfo_class()
                # Native state/focus layouts are inherited, only the host surface changes.
                if widget.winfo_class() in ('TFrame','TCheckbutton','TRadiobutton','TButton','TEntry','TCombobox') and base not in ('Card.TFrame','Surface.TFrame'):
                    color=_surface(widget.master)
                    name='Host'+color.lstrip('#')+'.'+base
                    if name not in self.host_styles:
                        self.style.configure(name,background=color)
                        if isinstance(widget,(ttk.Checkbutton,ttk.Radiobutton)):
                            self.style.map(name,background=[('active',color),('disabled',color)])
                        self.host_styles.add(name)
                    if str(widget.cget('style')) != name:
                        widget.configure(style=name)
            elif original is not None:
                widget.configure(style=original)
        if isinstance(widget,ttk.Label):
            if kit.THEME != 'dark':
                if not hasattr(widget,'_appearance_background'):
                    widget._appearance_background=widget.cget('background')
                # Matching the host is the key to removing old text rectangles.
                color=_surface(widget.master)
                if str(widget.cget('background')) != color:
                    widget.configure(background=color)
            elif hasattr(widget,'_appearance_background'):
                widget.configure(background=widget._appearance_background)
        if hasattr(widget,'_appearance_glyph'):
            self._icon(widget,widget._appearance_glyph)
        if hasattr(widget,'appearance_icon'):
            label = getattr(widget,'icon_label',None) or getattr(widget,'icon',None)
            if label is not None:
                self._icon(label,widget.appearance_icon,getattr(widget,'active',False))
        # Labels tagged by the existing component constructors, not by text sniffing.
        for child in widget.winfo_children():
            self.widget(child,surface_context)

    def present(self):
        self.job=None
        if not self.root.winfo_exists() or self.applying:
            return
        self.applying=True
        try:
            pending=self.pending_widgets
            self.pending_widgets=set()
            if self.styled_theme != kit.THEME:
                self.styles()
                self.styled_theme=kit.THEME
                pending={self.root}
            # Mapping a dialog/control must not rescan every hidden page.
            # Coalesce children when their parent is already queued.
            for widget in pending:
                if not widget.winfo_exists():
                    continue
                ancestor=widget.master
                while ancestor is not None and ancestor not in pending:
                    ancestor=ancestor.master
                if ancestor is None:
                    self.widget(widget)
        finally:
            self.applying=False

    def change(self, name, *, persist=True):
        if name not in THEMES:
            raise ValueError('Selecciona un tema disponible.')
        # A failed disk write must leave the current theme intact.
        if persist:
            save_theme(name)
        old_name=kit.THEME
        old = dict(kit.COLORS)
        kit.select_theme(name)
        replacements={value.lower():kit.COLORS[key] for key,value in old.items()}
        self._recolor(self.root,replacements,old_name,name)
        # Refresh constants used by legacy modal helpers without reimporting modules.
        import sys
        for module_name in ('desktop_ui','common.desktop_ui'):
            module=sys.modules.get(module_name)
            if module:
                for const,key in [('BG','background'),('SURFACE','surface'),('TEXT','text'),
                                  ('MUTED','muted'),('ACCENT','primary'),('LINE','line')]:
                    setattr(module,const,kit.COLORS[key])
        configure = getattr(self.root,'configure_styles',None)
        if configure:
            configure()
        else:
            from desktop_ui import configure_dark_styles
            configure_dark_styles(self.root)
        self.styled_theme=None
        self.present()
        self._sync_choices(self.root,name)
        self.root.event_generate('<<AtlanticAppearanceChanged>>',when='tail')

    def _sync_choices(self, widget, name):
        if hasattr(widget,'theme_variable'):
            widget.theme_variable.set(name)
        for child in widget.winfo_children():
            self._sync_choices(child,name)

    def _recolor(self, widget, replacements, old_name, new_name):
        if getattr(widget,'_appearance_decoration',False):
            return
        if not isinstance(widget,ttk.Widget):
            keys=widget.keys()
            original=getattr(widget,'_appearance_dark_options',{})
            for key in ('background','foreground','activebackground','activeforeground',
                        'highlightbackground','highlightcolor','selectbackground','insertbackground'):
                if key in keys:
                    value=str(widget.cget(key)).lower()
                    if old_name == 'dark':
                        original[key]=widget.cget(key)
                    original_value=str(original.get(key,'')).lower()
                    expected_previous=next((kit.PALETTES[old_name][token].lower()
                        for token,color in kit.DARK_COLORS.items() if color.lower()==original_value),original_value)
                    if new_name == 'dark' and key in original and value==expected_previous:
                        widget.configure(**{key:original[key]})
                    elif value in replacements:
                        widget.configure(**{key:replacements[value]})
            widget._appearance_dark_options=original
            if isinstance(widget,tk.Canvas):
                for item in widget.find_all():
                    for key in ('fill','outline'):
                        try:
                            value=str(widget.itemcget(item,key)).lower()
                            if value in replacements:widget.itemconfigure(item,**{key:replacements[value]})
                        except tk.TclError:
                            pass  # Embedded windows/images do not have fill/outline.
        if hasattr(widget,'normal_background'):
            widget.normal_background=replacements.get(widget.normal_background.lower(),widget.normal_background)
        for child in widget.winfo_children():
            self._recolor(child,replacements,old_name,new_name)


def install(root):
    root=root._root()
    if not hasattr(root,'appearance'):
        root.appearance=Appearance(root)
    return root.appearance


def refresh_icon(widget):
    manager=getattr(widget._root(),'appearance',None)
    if manager:
        if hasattr(widget,'_appearance_panel'):
            manager.widget(widget)
        else:
            label=getattr(widget,'icon_label',None) or getattr(widget,'icon',None)
            if label is not None:
                manager._icon(label,widget.appearance_icon,getattr(widget,'active',False))


def appearance_settings(parent):
    """The same local preference control in Admin, Reception and system dialogs."""
    panel=ttk.Frame(parent,style='Card.TFrame',padding=22)
    ttk.Label(panel,text='Apariencia',style='Section.TLabel').pack(anchor='w')
    ttk.Label(panel,text='Elige cómo quieres ver Atlantic Gym en este equipo.',
              style='CardMuted.TLabel',wraplength=560).pack(anchor='w',pady=(6,16))
    current=tk.StringVar(panel,value=kit.THEME)
    for name,title,detail in [('league_light','League claro','Fondo claro, tarjetas blancas y el azul de Atlantic League.'),
                              ('league_dark','League oscuro','El mismo estilo de League con fondo azul oscuro.'),
                              ('minimal','Minimal','Azul uniforme, iconos circulares y controles redondeados.'),
                              ('dark','Oscuro','El diseño oscuro clásico de Atlantic Gym.')]:
        row=ttk.Frame(panel,style='Surface.TFrame',padding=12)
        row.pack(fill='x',pady=5)
        ttk.Radiobutton(row,text=title,variable=current,value=name).pack(anchor='w')
        ttk.Label(row,text=detail,style='CardMuted.TLabel',wraplength=520).pack(anchor='w',padx=26,pady=(3,0))
    status=tk.StringVar(panel,value='La preferencia se guarda en este equipo.')
    def apply():
        try:
            install(panel).change(current.get())
        except OSError:
            status.set('No se pudo guardar el tema. Revisa los permisos de este equipo e inténtalo de nuevo.')
            return
        status.set('Tema '+THEMES[current.get()]+' aplicado y guardado.')
    ttk.Button(panel,text='Aplicar tema',style='Primary.TButton',command=apply).pack(anchor='w',pady=(16,10))
    ttk.Label(panel,textvariable=status,style='CardMuted.TLabel',wraplength=560).pack(anchor='w')
    panel.theme_variable=current
    panel.theme_status=status
    return panel


def open_appearance(root):
    window=tk.Toplevel(root)
    from desktop_ui import decorate_window
    from responsive_ui import fit_window
    window.title('Atlantic Gym · Apariencia')
    decorate_window(window)
    fit_window(window,620,440,parent=root)
    appearance_settings(window).pack(fill='both',expand=True,padx=16,pady=16)
    return window
