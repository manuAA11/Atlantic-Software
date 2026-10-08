"""Interfaz real, lector simulado y esperas por respuesta; no requiere hardware."""
import os
os.environ['GYMSOFT_OFFLINE_QA'] = '1'
from contextlib import ExitStack
import faulthandler
from pathlib import Path
import queue
import sys
import traceback
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app as admin
import reception_app as reception
import fingerprint_ui as fp
from product_config import VERSION
from responsive_ui_smoke import shell
from ui_assertions import destroy_root
from ui_test_support import wait_for, settle_geometry


class DeliveredQueue(queue.Queue):
    def __init__(self):
        super().__init__()
        self.delivered = 0

    def get_nowait(self):
        value = super().get_nowait()
        self.delivered += 1
        return value


class Service:
    def __init__(self, *args):
        self.events = DeliveredQueue()
        self.commands = []
        self.paused = True

    def start(self): pass
    def pause(self, paused): self.paused = paused
    def send(self, *args): self.commands.append(args)
    def close(self): pass


def scenario(cls, factor):
    checks = 0
    context = f'{cls.__name__} / {factor*100:g} %'
    print('  HUELLA: '+context+' / inicio', flush=True)
    with patch.object(reception.branding, 'show_reception_logo', lambda *_: None):
        root = shell(cls, factor)
    root.title(f'Validación de huella · Gym soft {VERSION} · {context}')
    errors = []
    root.report_callback_exception = lambda kind, error, tb: errors.append(
        ''.join(traceback.format_exception(kind, error, tb)))
    root.db.gym_id = '00000000-0000-4000-8000-000000000001'
    root.db.list_clients.return_value = [
        dict(id=1, first_name='Cliente', last_name='Prueba', active=True, document='1', membership_status='AL DÍA'),
        dict(id=2, client_name='Otra persona', first_name='Otra', last_name='persona', active=True, document='2', membership_status='AL DÍA')]
    root.ready = True
    try:
        with ExitStack() as mocks:
            # Los avisos permanecen simulados durante TODO el escenario. Una
            # respuesta tardía no puede abrir un modal que espere un clic real.
            info = mocks.enter_context(patch.object(fp.messagebox, 'showinfo'))
            warning = mocks.enter_context(patch.object(fp.messagebox, 'showwarning'))
            error = mocks.enter_context(patch.object(fp.messagebox, 'showerror'))
            confirm = mocks.enter_context(patch.object(fp.messagebox, 'askyesno', return_value=True))
            for name in ('askokcancel', 'askretrycancel', 'askyesnocancel'):
                mocks.enter_context(patch.object(fp.messagebox, name,
                    side_effect=AssertionError('Diálogo inesperado: '+name)))
            mocks.enter_context(patch.object(fp, 'FingerprintService', Service))
            for page_type in set(root.page_types.values()):
                mocks.enter_context(patch.object(page_type, 'refresh', lambda *_: None))
            panel = fp.FingerprintPanel(root.biometric_access)
            root.biometric_access.native_reader = panel

            def step(description):
                print('  HUELLA: '+context+' / '+description, flush=True)

            def event(kind, value, description, *, delay=0):
                step(description)
                delivered = panel.service.events.delivered + 1
                if delay:
                    root.after(delay, lambda: panel.service.events.put((kind, value)))
                else:
                    panel.service.events.put((kind, value))
                wait_for(root, lambda: panel.service.events.delivered >= delivered,
                         description, errors=errors)
                assert not error.called, error.call_args

            key = 'checkin' if cls is admin.GymSoftApp else 'access'
            assert key not in root.pages; checks += 1
            first = dict(result='PERMITIDA', id=1, client_name='Cliente Prueba', document='1', status='AL DÍA')
            event('access', first, 'primer ingreso sin abrir antes Registro de entrada')
            assert root.current_page == key and not errors, errors; checks += 1
            page = root.pages[key]
            page.refresh_history = lambda: None
            if hasattr(page, 'refresh_clients'): page.refresh_clients = lambda: None
            if hasattr(root, 'refresh_all'): root.refresh_all = lambda **_: None
            panel.open()
            wait_for(root, lambda: len(panel.tree.get_children()) == 2,
                     'cargar clientes del gestor', errors=errors)
            checks += 1
            assert panel.tree.item('1', 'values')[0] == 'Cliente Prueba'; checks += 1
            panel.tree.selection_set('1')
            panel.enroll()
            assert confirm.call_args[0][0] == 'Registrar huella'
            assert panel.service.commands[-1] == ('enroll', 1); checks += 1
            event('templates', [1], 'sincronizar la huella registrada')
            # Supera deliberadamente los antiguos 150 ms: comprueba el caso
            # de respuesta tardía sin depender de la velocidad del computador.
            event('enrollment_end', dict(result='saved', message='Registrada y verificada'),
                  'confirmar guardado con respuesta tardía', delay=350)
            assert info.call_count == 1 and info.call_args[0][0] == 'Huella registrada'; checks += 1
            assert panel.tree.item('1', 'values')[1] == 'Registrada' and not panel.enrolling; checks += 1
            panel.delete()
            assert confirm.call_args[0][0] == 'Eliminar huella'
            assert panel.service.commands[-1] == ('delete', 1); checks += 1
            panel.window.destroy(); panel.window = None
            badge = page.badge if hasattr(page, 'badge') else page.status_label
            for other in root.page_types:
                if other == key: continue
                root.show_page(other)
                wait_for(root, lambda: root.pages[other].winfo_viewable(), 'abrir '+other, errors=errors)
                assert root.current_page == other; checks += 1
                event('access', first, 'ingreso automático desde '+other)
                assert root.current_page == key and page.access_tabs.select() == str(page.entry_tab); checks += 1
                assert badge.cget('text') == 'INGRESO REGISTRADO'; checks += 1
            event('access', dict(first, result='DENEGADA', status='SIN ENTRADAS'), 'ingreso sin saldo')
            assert badge.cget('text') == 'INGRESO NO AUTORIZADO'; checks += 1
            settle_geometry(root, (page, page.access_tabs, badge), 'presentar rechazo sin cambios continuos', errors=errors)
            assert not errors, errors; checks += 1
            event('unrecognized', 'Huella no reconocida.', 'huella desconocida')
            assert badge.cget('text') == 'HUELLA NO RECONOCIDA'; checks += 1
            event('uncertain', 'Revisa el historial', 'respuesta de ingreso no confirmada', delay=350)
            assert warning.call_count == 1 and warning.call_args[0][0] == 'No se confirmó el ingreso'; checks += 1
            assert not root.biometric_access.enabled.get(); checks += 1
            assert not errors and not error.called, (errors, error.call_args)
            print('  HUELLA: '+context+' / completado', flush=True)
    finally:
        destroy_root(root)
    return checks


def main():
    faulthandler.enable()
    faulthandler.dump_traceback_later(60, repeat=True)
    try:
        checks = sum(scenario(cls, factor) for cls in (admin.GymSoftApp, reception.ReceptionApp)
                     for factor in (1, 1.25))
    finally:
        faulthandler.cancel_dump_traceback_later()
    print(f'PASS: {checks} comprobaciones gráficas de registro, nube, eliminación y resultado automático; lector simulado y respuestas tardías.')


if __name__ == '__main__': main()
