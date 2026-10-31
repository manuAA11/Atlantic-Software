"""Staff presentation only: the server decides access and calendar warnings."""
import json
from datetime import date

MAX_NOTE_LENGTH = 2000


def note_sections(context):
    sections = []
    for key, title in (('client_notice', 'Aviso del cliente'),
                       ('membership_notes', 'Nota de la membresía')):
        text = str((context or {}).get(key) or '').strip()
        if text:
            sections.append(f'{title}:\n{text}')
    return '\n\n'.join(sections)


def access_explanation(context, ticket_note=''):
    """Render authoritative fields; support older servers without guessing dates."""
    messages = []
    for value in (context.get('access_detail') or context.get('denial_message')
                  or context.get('status'), context.get('expiry_notice'), ticket_note):
        text = str(value or '').strip()
        if text and text not in messages:
            messages.append(text)
    return '\n'.join(messages)


def sort_expirations(rows):
    """Order server dates, keeping undated records last; do not classify access."""
    def key(row):
        raw = row.get('end_date') or row.get('membership_end')
        try:
            expiry = raw if type(raw) is date else date.fromisoformat(str(raw))
            missing = False
        except (ValueError, TypeError):
            expiry = date.max
            missing = True
        name = str(row.get('client_name') or row.get('name') or
                   f"{row.get('first_name', '')} {row.get('last_name', '')}").casefold()
        return missing, expiry, name, str(row.get('id') or row.get('client_id') or '')
    return sorted(rows, key=key)


class ClientNotesDatabaseMixin:
    def _notes_rpc(self, name, params):
        value = self._execute(self.client.rpc(name, {'p_gym_id': self.gym_id, **params})).data
        if isinstance(value, str):
            value = json.loads(value)
        if not isinstance(value, dict):
            raise ValueError('No se pudieron consultar las notas del cliente.')
        return value

    def get_client_notes(self, client_id):
        return self._notes_rpc('staff_client_notes', {'p_client_id': int(client_id)})

    def save_client_note(self, client_id, note, revision):
        clean = note.strip()
        if len(clean) > MAX_NOTE_LENGTH:
            raise ValueError(f'La nota admite un máximo de {MAX_NOTE_LENGTH} caracteres.')
        return self._notes_rpc('save_staff_client_note', {
            'p_client_id': int(client_id), 'p_note': clean,
            'p_expected_revision': int(revision),
        })
