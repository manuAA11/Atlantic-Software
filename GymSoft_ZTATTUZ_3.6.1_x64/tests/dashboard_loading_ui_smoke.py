"""Paneles reales Tk: un RPC ausente no oculta el resto ni inventa ceros."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import copy
import threading
import time
from datetime import date
from unittest.mock import patch
from postgrest.exceptions import APIError
import app as admin
from responsive_ui_smoke import shell, pump, descendants
from ui_assertions import destroy_root

RAW_ERROR = 'RAW_PRIVATE_SENTINEL'


class DashboardDB:
    def __init__(self):
        self.main_thread = threading.get_ident()
        self.calls = []
        self.mode = 'missing_population'
        self.today = date(2026, 10, 14)
        self.clients = [{'id': 7, 'first_name': 'Ana', 'last_name': 'Prueba',
                         'birthdate': '1990-10-14', 'document': 'TEST7'}]
        self.tickets = [{'client_id': 7, 'client_name': 'Ana Prueba',
                         'entries_remaining': 8}]
        self.population = {
            'metrics': {'active_clients': 12, 'valid_memberships': 9,
                        'expired_memberships': 3, 'checkins_today': 4,
                        'internal_memberships': 2, 'staff_checkins_today': 1},
            'groups': {key: [] for key, *_ in admin.DashboardPage.EXPIRATION_BUCKETS},
        }
        self.population['groups']['days_0_7'] = [{'id': 7, 'client_name': 'Ana Prueba'}]

    def _read(self, name, result):
        assert threading.get_ident() != self.main_thread, name
        self.calls.append(name)
        time.sleep(.015)
        if self.mode == 'network':
            raise OSError('Connection timed out ' + RAW_ERROR)
        if self.mode == 'missing_population' and name == 'membership_population':
            raise APIError({'code': 'PGRST202',
                'message': 'Could not find the function public.membership_population(p_gym_id) in the schema cache',
                'details': RAW_ERROR, 'hint': None})
        if self.mode == 'missing_tickets_clock' and name in ('ticket_followup', '_today'):
            raise APIError({'code': 'PGRST202',
                'message': f'Could not find the function public.{name} in the schema cache',
                'details': RAW_ERROR, 'hint': None})
        return copy.deepcopy(result)

    def membership_population(self):
        return self._read('membership_population', self.population)

    def ticket_followup(self):
        return self._read('ticket_followup', self.tickets)

    def list_clients(self):
        return self._read('list_clients', self.clients)

    def _today(self):
        return self._read('_today', self.today)


def until(root, predicate, failures, seconds=8):
    deadline = time.monotonic() + seconds
    while not predicate():
        root.update()
        assert not failures, failures
        assert time.monotonic() < deadline, 'Dashboard no terminó sus lecturas independientes.'
        time.sleep(.004)
    pump(root, .04)
    assert not failures, failures


def visible_counts(page):
    return ([label.cget('text') for label in page.metric_labels.values()],
            [card.value_label.cget('text') for card in page.expiration_cards.values()],
            [label.cget('text') for label in page.ticket_dashboard.counts.values()],
            [card.value_label.cget('text') for card in page.birthday_cards.values()],
            page.internal_summary.cget('text'))


def main():
    checked = 0
    for factor in (1, 1.25):
        root = shell(admin.GymSoftApp, factor)
        failures = []
        root.report_callback_exception = lambda kind, error, tb: failures.append(str(error))
        db = DashboardDB()
        root.db = db
        try:
            root.show_page('dashboard')
            page = root.pages['dashboard']
            metrics, memberships, tickets, birthdays, summary = visible_counts(page)
            assert all(value == '—' for value in metrics + memberships + tickets + birthdays)
            assert summary == 'Personal interno: — · Asistencias del personal hoy: —'
            checked += 2
            # Las tarjetas aún no consultadas no deben abrir falsos listados vacíos.
            with patch.object(admin.messagebox, 'showinfo') as info:
                page.show_expiration_list('expired', 'Vencidas')
                page.show_birthday_list('this_week', 'Esta semana')
                page.ticket_dashboard.show('empty', 'Sin entradas')
                assert info.call_count == 3
            checked += 1
            until(root, lambda: not page._view_pending, failures)
            assert page._view_errors == {'membership_population'}, page._view_errors
            assert db.calls.count('membership_population') == 1
            assert not page._memberships_loaded
            assert all(value == '—' for group in visible_counts(page)[0:2] for value in group)
            assert page.ticket_dashboard.counts['six_ten'].cget('text') == '1'
            assert page.birthday_cards['this_week'].value_label.cget('text') == '1'
            assert page._birthdays_loaded and page.ticket_dashboard.loaded
            assert RAW_ERROR not in page._view_status.get()
            checked += 8
            # Una consulta recuperada trae métricas y grupos del mismo snapshot.
            db.mode = 'healthy'
            page.refresh()
            until(root, lambda: not page._view_pending, failures)
            assert not page._view_errors
            assert db.calls.count('membership_population') == 2
            assert page._memberships_loaded
            assert page.metric_labels['active_clients'].cget('text') == '12'
            assert page.expiration_cards['days_0_7'].value_label.cget('text') == '1'
            assert page.internal_summary.cget('text') == 'Personal interno: 2 · Asistencias del personal hoy: 1'
            checked += 6
            # Un fallo posterior conserva el último snapshot y todos los listados.
            previous = visible_counts(page)
            previous_groups = copy.deepcopy((page.expiration_groups, page.birthday_groups,
                                              page.ticket_dashboard.groups))
            db.mode = 'network'
            page.refresh()
            until(root, lambda: not page._view_pending, failures)
            assert page._view_errors == {'membership_population', 'ticket_followup', 'dashboard_birthdays'}
            assert visible_counts(page) == previous
            assert (page.expiration_groups, page.birthday_groups, page.ticket_dashboard.groups) == previous_groups
            assert RAW_ERROR not in page._view_status.get()
            checked += 4
            # Cero se presenta únicamente después de una respuesta válida vacía.
            db.mode = 'healthy'
            db.population['metrics'] = {key: 0 for key in db.population['metrics']}
            db.population['groups'] = {key: [] for key in db.population['groups']}
            db.tickets = []
            db.clients = []
            page.refresh()
            until(root, lambda: not page._view_pending, failures)
            assert not page._view_errors and not page._view_status.get()
            counts = visible_counts(page)
            assert all(value == '0' for group in counts[:4] for value in group)
            assert db.calls.count('membership_population') == 4
            checked += 3
        finally:
            destroy_root(root)
        # El fallo inverso tampoco debe ocultar las membresías ya consultadas.
        root = shell(admin.GymSoftApp, factor)
        failures = []
        root.report_callback_exception = lambda kind, error, tb: failures.append(str(error))
        db = DashboardDB()
        db.mode = 'missing_tickets_clock'
        root.db = db
        try:
            root.show_page('dashboard')
            page = root.pages['dashboard']
            until(root, lambda: not page._view_pending, failures)
            assert page._memberships_loaded and not page._birthdays_loaded
            assert not page.ticket_dashboard.loaded
            assert page.metric_labels['active_clients'].cget('text') == '12'
            assert all(value == '—' for group in visible_counts(page)[2:4] for value in group)
            assert page._view_errors == {'ticket_followup', 'dashboard_birthdays'}
            checked += 5
        finally:
            destroy_root(root)
    print(f'PASS: {checked} comprobaciones Tk de Dashboard independiente al 100 % y 125 %; RPC ausente, valores desconocidos, recuperación y conservación tras fallos de red.')


if __name__ == '__main__':
    main()
