"""Distribuciones estables normal/maximizada al 100, 120 y 125 por ciento."""
from pathlib import Path
import os
import sys
import time
from types import SimpleNamespace as NS
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app as admin
import reception_app as reception
import responsive_ui as layout
from responsive_ui_smoke import shell, pump, descendants, assert_buttons_fit
from ui_assertions import assert_content_exposed, destroy_root, resize_test_window


def assert_layout_contracts(page):
    """Ningún adaptador puede quitar columnas, spans o el crecimiento vertical."""
    for parent in [page, *descendants(page)]:
        flow = getattr(parent, '_responsive_reflow', None)
        if flow is None or flow.mode != 'grid': continue
        for widget, original in flow.info:
            actual = widget.grid_info()
            for key in ('row', 'column', 'rowspan', 'columnspan', 'sticky'):
                assert actual[key] == original[key], f'Distribución alterada: {widget}; {key}: {actual[key]} != {original[key]}'
        for row, original in enumerate(flow.row_options):
            assert parent.rowconfigure(row)['weight'] == original['weight'], f'Se perdió el crecimiento vertical de {parent}'
        if not parent.winfo_viewable(): continue
        for widget, original in flow.info:
            if 'n' not in original['sticky'] or 's' not in original['sticky']: continue
            column, row = int(original['column']), int(original['row'])
            box = parent.grid_bbox(column, row, column+int(original['columnspan'])-1, row+int(original['rowspan'])-1)
            padding = layout._horizontal_padding(parent, original.get('pady', 0))
            assert widget.winfo_height() + padding + 3 >= box[3], f'Panel sin ocupar su celda: {widget}'


def main():
    checks=0
    errors=[]
    for factor in (1,1.2,1.25):
        for cls in (admin.GymSoftApp,reception.ReceptionApp):
            with patch.object(reception.branding,'show_reception_logo',lambda *_:None):root=shell(cls,factor)
            resize_test_window(root,'1180x740')
            pages={}
            for name,page_type in root.page_types.items():
                with patch.object(page_type,'refresh',lambda *_:None):root.show_page(name)
                pump(root,.15)
                pages[name]=root.pages[name]
            root.report_callback_exception=lambda kind,error,tb:errors.append(str(error))
            root._ui_failures=errors
            simulated=['normal']
            # Xvfb no tiene gestor de ventanas: se simula exclusivamente el estado
            # del SO; geometría, controles, columnas y consultas de hit-test son Tk.
            native_profile=layout.window_profile
            def profile(window):
                if sys.platform=='win32' or window is not root:return native_profile(window)
                return simulated[0],round(layout.scale(window),3)
            def mode(name):
                simulated[0]=name
                if sys.platform=='win32':
                    root.state('zoomed' if name=='maximized' else 'normal')
                    if name=='normal':resize_test_window(root,'1180x740')
                else:
                    resize_test_window(root,'1560x900' if name=='maximized' else '1180x740')
                    layout.layout_modes(root).changed(NS(widget=root))
                pump(root,.32)
            try:
                with patch.object(layout,'window_profile',side_effect=profile):
                    for state in ('normal','maximized','normal'):
                        mode(state)
                        for name,page in pages.items():
                            with patch.object(type(page),'refresh',lambda *_:None):root.show_page(name)
                            pump(root,.16)
                            root._ui_test_context=f'{cls.__name__} / {name} / {state} / {factor*100:g} %'
                            assert_buttons_fit(root)
                            assert_layout_contracts(page)
                            deadline=time.monotonic()+1
                            while True:
                                clipped=[label for label in descendants(page)
                                    if isinstance(label,(tk.Label,ttk.Label)) and label.winfo_viewable()
                                    and len(str(label.cget('text')))>40 and label.winfo_width()+4<label.winfo_reqwidth()]
                                if not clipped:break
                                label=clipped[0]
                                assert time.monotonic()<deadline, (
                                    f'Texto recortado: {label.cget("text")}; ancho={label.winfo_width()}, requerido={label.winfo_reqwidth()}; {root._ui_test_context}')
                                pump(root,.035)
                            checks+=assert_content_exposed(page)+1
                        assert layout.layout_modes(root).profile[0]==state
                    # Mover la ventana no recalcula columnas, fuentes ni vuelve
                    # a crear cuadros; las geometrías conservan sus distribuciones.
                    before=[(w,getattr(w,'_responsive_reflow',None)) for w in descendants(root)]
                    flows=[f for _,f in before if f is not None]
                    states=[(f.state,dict(f.profiles)) for f in flows]
                    calls=[]
                    original=layout.Reflow.layout
                    def observed(self,event=None):
                        calls.append(self)
                        return original(self,event)
                    with patch.object(layout.Reflow,'layout',observed):
                        for delta in range(12):
                            root.geometry(f'+{20+delta*3}+{24+delta*2}')
                            pump(root,.02)
                        pump(root,.12)
                    assert not calls, 'Mover la ventana volvió a calcular las tarjetas.'
                    assert states==[(f.state,dict(f.profiles)) for f in flows]
                    assert not errors, errors
                    checks+=3
                    if os.environ.get('GYMSOFT_QA_IMAGES'):
                        from PIL import ImageGrab
                        folder=Path(os.environ['GYMSOFT_QA_IMAGES']);folder.mkdir(parents=True,exist_ok=True)
                        for state in ('normal','maximized'):
                            mode(state)
                            target='settings' if cls is admin.GymSoftApp else 'access'
                            with patch.object(type(pages[target]),'refresh',lambda *_:None):root.show_page(target)
                            area=root.content_area
                            area.canvas.yview_moveto(0);area.canvas.xview_moveto(0)
                            pump(root,.2)
                            ImageGrab.grab(xdisplay=os.environ.get('DISPLAY')).crop((root.winfo_rootx(),root.winfo_rooty(),
                                root.winfo_rootx()+root.winfo_width(),root.winfo_rooty()+root.winfo_height())).save(
                                folder/f'{cls.__name__}_{state}_{int(factor*100)}.png')
            finally:destroy_root(root)
    print(f'PASS: {checks} comprobaciones de modo normal, maximizado y movimiento sin redistribuir al 100 %, 120 % y 125 %.')


if __name__=='__main__':main()
