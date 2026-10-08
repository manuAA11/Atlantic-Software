"""Comprobaciones Tk con consultas lentas simuladas; nunca conecta al servidor."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import hashlib
import queue
import threading
import time
import traceback
from collections import defaultdict
from datetime import date
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
import tkinter as tk
from tkinter import ttk
import app as admin
import reception_app as reception
from ui_performance import AsyncPageMixin, DataTreeview, background_reads, clear_tree, refresh_pages, process_realtime
from responsive_ui import AutoScrollbar, ScrollArea, adapt_tree
from responsive_ui_smoke import shell, pump
from ui_assertions import destroy_root, resize_test_window, enable_dpi_awareness


def diagnostic(root):
    page=getattr(root, 'pages', {}).get(getattr(root, 'current_page', ''))
    reads=getattr(root, '_background_reads', None)
    requests={} if reads is None else {
        f'{type(owner).__name__}/{key}': {
            'consultando': slot['running'], 'respuesta_recibida': 'ready' in slot,
            'visible': bool(owner.winfo_viewable()),
            'seleccionada': owner is page, 'gestor': owner.winfo_manager(),
        }
        for (owner, key), slot in reads.slots.items() if page is None or owner is page
    }
    return (f"{getattr(root, '_ui_test_context', 'Carga de prueba')}; "
            f"ventana={root.state()}; "
            f"pendientes={sorted(page._view_pending) if page is not None else []}; "
            f"estado={page._view_status.get() if page is not None else ''}; "
            f"temporizador={reads.job if reads else None}; solicitudes={requests}")


def until(root, condition, seconds=6):
    deadline = time.monotonic()+seconds
    while not condition():
        failures=getattr(root, '_ui_failures', [])
        assert not failures, f'Error al mostrar la página: {failures[-1]}; {diagnostic(root)}'
        assert time.monotonic() < deadline, f'La respuesta de prueba no llegó a tiempo. {diagnostic(root)}'
        root.update()
        time.sleep(.004)
    pump(root, .035)


class Page(AsyncPageMixin, ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.init_reads()
        self.values = []


class FixtureDB:
    def __init__(self):
        self.calls = []
        self.main = threading.get_ident()
    def __getattr__(self, name):
        def read(*args, **kwargs):
            assert threading.get_ident() != self.main, f'Consulta en el hilo de Tk: {name}'
            self.calls.append((name, args))
            time.sleep(.018)
            if name in ('_today', 'today'): return date(2026, 9, 9)
            if name == 'dashboard_metrics': return defaultdict(int)
            if name.startswith('list_') or name in ('ticket_followup', 'session_followup', 'marketing_contacts', 'marketing_activity'): return []
            return {}
        return read


def main():
    enable_dpi_awareness()
    coordinator = Path(__file__).resolve().parents[1] / 'ui_performance.py'
    print('COORDINADOR DE CARGA:', hashlib.sha256(coordinator.read_bytes()).hexdigest()[:12], flush=True)
    # Un Map de un control no debe volver a forzar el estilo DWM ni vaciar
    # la cola de geometría de toda la ventana (regresión específica de Windows).
    for module in (admin, reception):
        window=Mock()
        with patch.object(module, 'sys', NS(platform='win32')):
            module.enable_dark_title_bar(window)
        callback=next(call.args[1] for call in window.bind.call_args_list if call.args[0]=='<Map>')
        callback(NS(widget=Mock()))
        window.winfo_id.assert_not_called()
        window.update_idletasks.assert_not_called()
    root=tk.Tk(); resize_test_window(root, '800x600')
    failures=[]
    def callback_error(kind, error, tb):
        failures.append(str(error))
        traceback.print_exception(kind, error, tb)
    root._ui_failures=failures
    root.report_callback_exception=callback_error
    page=Page(root);page.pack(fill='both',expand=True);pump(root)
    reads=background_reads(root)
    gate=threading.Event();started=threading.Event();paint=[];loads=[];ticks=[]
    def delayed(value):
        def load():
            loads.append(value);started.set()
            if value == 'old': assert gate.wait(4)
            return value
        return load
    def heartbeat():
        ticks.append(time.monotonic());root.after(15, heartbeat)
    heartbeat()
    before=time.perf_counter()
    page.load_view('query', delayed('old'), paint.append, ('old',))
    dispatch_ms=(time.perf_counter()-before)*1000
    until(root, started.is_set)
    pump(root, .25)
    assert len(ticks)>8 and not paint, 'La espera de red bloqueó la ventana.'
    for value in ('intermediate', 'latest'):
        page.load_view('query', delayed(value), paint.append, (value,))
    gate.set();until(root, lambda: paint == ['latest'])
    assert loads == ['old', 'latest'], loads
    # La misma respuesta no repinta; una invalidación descarta datos anteriores.
    page.load_view('query', lambda: 'latest', paint.append, ('latest',))
    until(root, lambda: not page._view_pending)
    assert paint == ['latest']
    gate.clear();started.clear()
    page.load_view('query', delayed('old'), paint.append, ('old',))
    until(root, started.is_set);reads.invalidate();gate.set()
    until(root, lambda: not page._view_pending)
    assert paint == ['latest']
    # Los modales y secciones ocultas no reciben repintados.
    modal=tk.Toplevel(root);modal.grab_set();pump(root)
    page.load_view('query', lambda: 'after_modal', paint.append)
    pump(root, .1);assert paint == ['latest'];modal.destroy()
    until(root, lambda: paint[-1] == 'after_modal')
    page.pack_forget();page.load_view('query', lambda: 'hidden', paint.append)
    pump(root,.12);assert paint[-1] == 'after_modal'
    page.pack(fill='both',expand=True)
    until(root, lambda: paint[-1] == 'hidden')
    # La respuesta llega ANTES de que el contenedor se muestre. En 3.4.0
    # quedaba lista, sin temporizador, pero el primer Map nunca la presentaba.
    container=ttk.Frame(root)
    early=Page(container);early.pack(fill='both',expand=True)
    early_paint=[]
    early.load_view('first', lambda: 'respuesta temprana', early_paint.append)
    until(root, lambda: 'ready' in reads.slots[(early, 'first')])
    assert not early._view_loaded and not early_paint
    assert reads.job is None, 'No se debe sondear continuamente una página oculta.'
    page.pack_forget();container.pack(fill='both',expand=True)
    until(root, lambda: early._view_loaded)
    assert early_paint == ['respuesta temprana']
    # Restaurar también reanuda respuestas recibidas con la ventana retirada.
    root.withdraw()
    early.load_view('first', lambda: 'al restaurar', early_paint.append)
    until(root, lambda: 'ready' in reads.slots[(early, 'first')])
    assert early_paint == ['respuesta temprana']
    root.deiconify()
    until(root, lambda: early_paint[-1] == 'al restaurar')
    # Una lectura encadenada desde render no debe duplicar temporizadores.
    chain_gate=threading.Event();chain_started=threading.Event();chain_paint=[]
    def chained_load():
        chain_started.set()
        assert chain_gate.wait(4)
        return 'segunda respuesta'
    early.load_view('chain_first', lambda: 'primera respuesta',
                    lambda _: early.load_view('chain_second', chained_load, chain_paint.append))
    until(root, chain_started.is_set)
    timers=root.tk.splitlist(root.tk.call('after','info'))
    read_timers=[timer for timer in timers if '_poll' in str(root.tk.call('after','info',timer)[0])]
    assert len(read_timers)==1, f'Sondeos duplicados: {read_timers}'
    chain_gate.set();until(root, lambda: chain_paint == ['segunda respuesta'])
    # Si un renderizador reemplaza su propia consulta, no se da por terminada
    # la nueva solicitud al finalizar el renderizador anterior.
    chain_gate.clear();chain_started.clear();same_key=[]
    def replace_same_key(value):
        early.load_view('replacement', chained_load, same_key.append)
    early.load_view('replacement', lambda: 'inicial', replace_same_key)
    until(root, chain_started.is_set)
    assert 'replacement' in early._view_pending
    chain_gate.set();until(root, lambda: same_key == ['segunda respuesta'])
    assert 'replacement' not in early._view_pending
    early.destroy();container.destroy();page.pack(fill='both',expand=True);pump(root)
    # Filas: no borrar ni reinsertar mil registros sin cambios.
    tree=DataTreeview(page,columns=('name',),show='headings',height=8)
    tree.heading('name',text='Cliente');tree.pack(fill='both',expand=True)
    for n in range(1000): tree.insert('', 'end', iid=str(n), values=(f'Cliente {n}',))
    pump(root);tree.selection_set('512');tree.yview_moveto(.45);pump(root)
    old_position=tree.yview()[0]
    commands=[]
    def spy(*args): commands.append(args[0])
    command=root.register(spy)
    root.tk.call('trace','add','execution',str(tree),'enter',command)
    start=time.perf_counter();clear_tree(tree)
    for n in range(1000):tree.insert('', 'end', iid=str(n), values=(f'Cliente {n}',))
    tree.finish_update();row_ms=(time.perf_counter()-start)*1000
    root.tk.call('trace','remove','execution',str(tree),'enter',command)
    assert tree.selection() == ('512',)
    assert abs(tree.yview()[0]-old_position)<.005
    assert not any(' delete ' in c or ' insert ' in c for c in commands)
    clear_tree(tree)
    for n in range(1,1001):tree.insert('', 'end', iid=str(n), values=(f'Cliente {n}',))
    tree.finish_update();assert not tree.exists('0') and tree.exists('1000')
    tree.destroy()
    # Las barras aparecen solo por desbordamiento, y vuelven a ocultarse.
    box=ttk.Frame(page);box.pack(fill='both',expand=True)
    listing=ttk.Treeview(box,columns=('name',),show='headings',height=4)
    listing.column('name',width=120,minwidth=60,stretch=True)
    bar=AutoScrollbar(box,command=listing.yview);bar.pack(side='right',fill='y')
    listing.configure(yscrollcommand=bar.set);listing.pack(fill='both',expand=True);pump(root)
    assert not bar.winfo_manager(), 'Barra visible en una lista vacía.'
    for n in range(100):listing.insert('','end',values=(n,))
    pump(root);assert bar.winfo_manager() == 'pack'
    listing.delete(*listing.get_children());pump(root);assert not bar.winfo_manager()
    page.destroy();assert not failures, failures;destroy_root(root)
    # Todas las páginas reales cargan por el trabajador, y navegar a una página
    # ya cargada no provoca otra consulta ni reconstruye sus widgets.
    page_count=0
    for cls in (admin.GymSoftApp, reception.ReceptionApp):
        with patch.object(reception.branding,'show_reception_logo',lambda *_:None):root=shell(cls, 1)
        root._ui_failures=failures
        root.report_callback_exception=callback_error
        db=FixtureDB();root.db=db
        root.cloud.client=NS(rpc=lambda *args,**kwargs:NS(execute=lambda:NS(data={})))
        try:
            for key in root.page_types:
                root._ui_test_context=f'{cls.__name__} / {key}'
                print('CARGA:',root._ui_test_context,flush=True)
                if cls is reception.ReceptionApp and key == 'access':
                    # Reproducir exactamente el estado del informe de Windows:
                    # ambas respuestas llegan antes de confirmarse la visibilidad.
                    # Al volver True no se genera otro Map que despierte la carga.
                    with patch.object(reception.AccessPage, 'winfo_viewable', return_value=False):
                        root.show_page(key);page=root.pages[key]
                        reads=background_reads(root)
                        until(root, lambda: all('ready' in reads.slots[(page, name)]
                                               for name in ('refresh_clients', 'refresh_history')))
                        pump(root,.12)
                        assert not page._view_loaded
                        assert page._view_pending == {'refresh_clients', 'refresh_history'}
                        assert reads.job is not None, 'La página seleccionada perdió su temporizador.'
                        loaded=[]
                        page.when_loaded(lambda: loaded.append(
                            not any('ready' in slot for (owner, _), slot in reads.slots.items() if owner is page)))
                        assert not loaded, 'Se notificó la carga antes de presentar los datos.'
                        calls_before_map=len(db.calls)
                    until(root, lambda: page._view_loaded and not page._view_pending)
                    assert loaded == [True], 'Se notificó la carga antes de completar ambas respuestas.'
                    assert len(db.calls)==calls_before_map, 'Restaurar la presentación repitió las consultas.'
                else:
                    root.show_page(key);page=root.pages[key]
                until(root, lambda: page._view_loaded and not page._view_pending)
                assert not page._view_status.get(), (key,page._view_status.get())
                calls=len(db.calls);children=page.winfo_children()
                root.show_page(key);pump(root,.05)
                assert len(db.calls)==calls and page.winfo_children()==children, key
                page_count+=1
            # Mover una ventana ya construida no consulta ni vuelve a crear tarjetas.
            calls=len(db.calls);children=root.pages[root.current_page].winfo_children()
            for position in range(10):
                root.geometry(f'+{30+position*2}+{40+position*2}')
                pump(root,.01)
            assert len(db.calls)==calls
            assert root.pages[root.current_page].winfo_children()==children
            root.show_page('clients');pump(root,.12)
            before_calls=len(db.calls)
            refresh_pages(root)
            until(root,lambda:not root.pages['clients']._view_pending)
            new_calls=[name for name,_ in db.calls[before_calls:]]
            assert new_calls and set(new_calls)<= {'list_clients','today'}, new_calls
            # Ráfaga de notificaciones -> una actualización de la página activa.
            root.ready=True;root.realtime_events=queue.Queue();root.realtime_refresh_pending=False
            for n in range(20):root.realtime_events.put({'n':n})
            before_calls=len(db.calls);process_realtime(root);pump(root,.7)
            expected=1 if cls is admin.GymSoftApp else 2
            assert len(db.calls)-before_calls == expected,(cls.__name__,db.calls[before_calls:])
            if cls is reception.ReceptionApp:
                assert 'dashboard' not in root.page_types
                # Una respuesta aplazada no mantiene sondeos en otra sección.
                # Al volver se presenta una sola vez, sin repetir la consulta.
                root.show_page('access');access=root.pages['access']
                with patch.object(access,'winfo_viewable',return_value=False):
                    access.refresh()
                    until(root,lambda:all('ready' in reads.slots[(access,name)]
                                         for name in ('refresh_clients','refresh_history')))
                    root.show_page('clients');pump(root,.12)
                    assert reads.job is None, 'Se sondeó una página apartada.'
                    assert access._view_pending == {'refresh_clients','refresh_history'}
                calls_before_return=len(db.calls)
                root.show_page('access')
                until(root,lambda:not access._view_pending)
                assert len(db.calls)==calls_before_return
                root.show_page('shop');shop=root.pages['shop'];pump(root,.1)
                products=[{'id':n,'name':f'Producto {n}','sale_price':1000,'stock_quantity':20,'low_stock_threshold':2,'sku':str(n)} for n in range(1,4)]
                shop._render_refresh_products(copy.deepcopy(products));pump(root)
                cards=list(shop.product_cards)
                products[1]['stock_quantity']=19
                shop._render_refresh_products(copy.deepcopy(products));pump(root)
                assert shop.product_cards[0] is cards[0] and shop.product_cards[2] is cards[2]
                assert shop.product_cards[1] is not cards[1]
                access=root.pages['access']
                access._access_result_visible=True
                access._result_search=''
                access.status_name.set('Ana Prueba')
                access.status_label.configure(text='INGRESO REGISTRADO')
                access._render_refresh_clients([])
                assert access.status_label.cget('text')=='INGRESO REGISTRADO'
        finally:destroy_root(root)
    assert not failures, failures
    print(f'PASS: {page_count} páginas con consultas fuera de Tk; recepción sin Dashboard; respuestas vigentes, ráfagas agrupadas, modales y selección conservados, barras condicionales y tarjetas reutilizadas.')
    print(f'MEDICIÓN LOCAL: despacho de consulta {dispatch_ms:.2f} ms; tabla sin cambios de 1.000 filas {row_ms:.2f} ms; 0 borrados y 0 inserciones.')

if __name__=='__main__':main()
