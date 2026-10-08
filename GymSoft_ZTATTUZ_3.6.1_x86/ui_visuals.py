"""Indicadores e iconos vectoriales rasterizados una vez por ventana/escala."""
from PIL import Image, ImageDraw, ImageTk
from tkinter import ttk


def indicator_image(size=20, *, selected=False, alternate=False, disabled=False,
                    active=False, radio=False):
    scale = 4
    canvas = Image.new('RGBA', (size * scale, size * scale))
    draw = ImageDraw.Draw(canvas)
    def box(values): return tuple(int(v * size * scale / 20) for v in values)
    border = '#61738f' if disabled else '#93c5fd' if active else '#8196b3'
    fill = '#33465f' if disabled else '#2563a6' if selected or alternate else '#172235'
    shape = draw.ellipse if radio else draw.rounded_rectangle
    args = {} if radio else {'radius': 4 * scale}
    shape(box((1, 1, 19, 19)), fill=fill, outline=border, width=scale, **args)
    if selected:
        if radio:
            draw.ellipse(box((6, 6, 14, 14)), fill='white')
        else:
            draw.line([box((5, 10)), box((9, 14)), box((15, 6))],
                      fill='white', width=2 * scale, joint='curve')
    elif alternate:
        draw.line([box((5, 10)), box((15, 10))], fill='white', width=2 * scale)
    icon = canvas.resize((size, size), Image.Resampling.LANCZOS)
    padded = Image.new('RGBA', (size + max(5, round(size * .3)), size))
    padded.paste(icon, (0, 0))
    return padded


def install_indicators(root):
    """Preserva la semántica, el teclado, foco y variables nativas de ttk."""
    host = root._root()
    style = ttk.Style(root)
    size = max(18, min(36, round(20 * float(root.tk.call('tk', 'scaling')) / (96 / 72))))
    cache = getattr(host, '_gymsoft_indicators', {})
    for kind in ('Checkbutton', 'Radiobutton'):
        name = f'Gymsoft{size}.{kind}.indicator'
        if name not in style.element_names():
            images = {}
            for state in ('normal', 'selected', 'alternate', 'disabled', 'disabled_selected',
                          'disabled_alternate', 'active', 'active_selected', 'active_alternate'):
                images[state] = ImageTk.PhotoImage(indicator_image(size,
                    selected='selected' in state, alternate='alternate' in state,
                    disabled='disabled' in state, active='active' in state,
                    radio=kind == 'Radiobutton'), master=root)
            cache[name] = images
            style.element_create(name, 'image', images['normal'],
                ('disabled', 'selected', images['disabled_selected']),
                ('disabled', 'alternate', images['disabled_alternate']),
                ('disabled', images['disabled']),
                ('active', 'selected', images['active_selected']),
                ('active', 'alternate', images['active_alternate']),
                ('selected', images['selected']), ('alternate', images['alternate']),
                ('active', images['active']), border=0, sticky='')
        style.layout('T' + kind, [(kind + '.padding', {'sticky': 'nswe', 'children': [
            (name, {'side': 'left', 'sticky': ''}),
            (kind + '.focus', {'side': 'left', 'sticky': 'w', 'children': [
                (kind + '.label', {'sticky': 'nswe'})]})]})])
        style.configure('T' + kind, padding=(2, 4), focusthickness=1, focuscolor='#93c5fd')
    host._gymsoft_indicators = cache


def dialog_icon(kind, size=40):
    """Sin glifos dependientes de fuentes ni signos de interrogación decorativos."""
    scale = 4
    im = Image.new('RGBA', (size * scale, size * scale))
    draw = ImageDraw.Draw(im)
    color = {'info': '#60a5fa', 'confirm': '#60a5fa', 'account': '#34d399',
             'warning': '#fbbf24', 'error': '#fb7185'}.get(kind, '#60a5fa')
    def xy(values): return tuple(round(v * size * scale / 40) for v in values)
    def line(points): draw.line([xy(p) for p in points], fill=color, width=2 * scale, joint='curve')
    draw.rounded_rectangle(xy((0, 0, 39, 39)), radius=10 * scale, fill='#172235')
    if kind == 'account':
        draw.ellipse(xy((15, 8, 25, 18)), outline=color, width=2 * scale)
        draw.arc(xy((9, 19, 31, 38)), 180, 360, fill=color, width=2 * scale)
    elif kind == 'confirm':
        draw.rounded_rectangle(xy((9, 8, 31, 32)), radius=3 * scale, outline=color, width=2 * scale)
        line([(14, 20), (18, 24), (26, 15)])
    elif kind == 'warning':
        line([(20, 8), (33, 31), (7, 31), (20, 8)])
        line([(20, 16), (20, 23)])
        draw.ellipse(xy((19, 26, 21, 28)), fill=color)
    else:
        draw.ellipse(xy((8, 8, 32, 32)), outline=color, width=2 * scale)
        if kind == 'error':
            line([(15, 15), (25, 25)]); line([(25, 15), (15, 25)])
        else:
            line([(20, 18), (20, 27)])
            draw.ellipse(xy((19, 12, 21, 14)), fill=color)
    return im.resize((size, size), Image.Resampling.LANCZOS)
