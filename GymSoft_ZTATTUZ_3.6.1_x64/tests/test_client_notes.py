import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.client_notes import ClientNotesDatabaseMixin, note_sections, access_explanation, sort_expirations


class ClientNotesTests(unittest.TestCase):
    def test_sort_all_dates_without_changing_server_groups_or_days(self):
        rows = [dict(id=1, end_date='2026-10-31', client_name='Ana', days_remaining=4),
                dict(id=2, end_date='2026-10-30', client_name='Zoe', days_remaining=3),
                dict(id=3, end_date=None), dict(id=4, end_date='invalid'),
                dict(id=5, end_date='2026-10-30', client_name='ana', days_remaining=3)]
        self.assertEqual([r['id'] for r in sort_expirations(rows)], [5, 2, 1, 3, 4])
        self.assertEqual([r['id'] for r in rows], [1, 2, 3, 4, 5])
        self.assertEqual(rows[0]['days_remaining'], 4)

    def test_notices_are_plain_text_and_separate(self):
        self.assertEqual(note_sections({}), '')
        text = note_sections({'client_notice': ' Avisar a recepción\n<sin formato> ', 'membership_notes': 'Traer soporte'})
        self.assertEqual(text, 'Aviso del cliente:\nAvisar a recepción\n<sin formato>\n\nNota de la membresía:\nTraer soporte')

    def test_reason_and_warning_are_from_server(self):
        result = {'allowed': True, 'membership_end': '2000-01-01', 'access_detail': 'Membresía vigente.',
                  'expiry_notice': 'La membresía vence mañana.'}
        self.assertEqual(access_explanation(result, 'Reingreso'), 'Membresía vigente.\nLa membresía vence mañana.\nReingreso')
        self.assertEqual(access_explanation({'denial_message': 'Congelada', 'status': 'FROZEN'}), 'Congelada')
        self.assertEqual(access_explanation({'status': 'VENCIDO'}), 'VENCIDO')

    def test_saved_note_scopes_client_and_revision(self):
        db = ClientNotesDatabaseMixin(); db.gym_id = 'gym'; db.client = Mock()
        db._execute = Mock(return_value=SimpleNamespace(data={'revision': 2, 'client_notice': 'Texto'}))
        self.assertEqual(db.save_client_note(42, ' Texto ', 1)['revision'], 2)
        db.client.rpc.assert_called_once_with('save_staff_client_note', {
            'p_gym_id': 'gym', 'p_client_id': 42, 'p_note': 'Texto', 'p_expected_revision': 1})
        with self.assertRaises(ValueError): db.save_client_note(42, 'x'*2001, 2)
        self.assertEqual(db.client.rpc.call_count, 1)


if __name__ == '__main__': unittest.main()
