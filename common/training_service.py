"""Gym training RPC: reuses the current user/session, never a privileged key."""
import json
from urllib.parse import urlsplit
from uuid import uuid4


class TrainingDatabaseMixin:
    def training(self, action, data=None):
        payload = dict(data or {})
        if action == 'catalog.save' and 'source_ref' not in payload:
            from product_config import load_config
            payload['source_ref'] = (urlsplit(load_config(validate=False).get('supabase_url', '')).hostname or '').split('.')[0]
        try:
            result = self._execute(self.client.rpc('gym_training', {
                'p_gym_id': self.gym_id, 'p_action': action, 'p_data': payload})).data
        except Exception as error:
            if str(getattr(error, 'code', '')) in ('PGRST202', '42883'):
                raise ValueError('Estas herramientas necesitan una actualización del servidor. Contacta a soporte; las funciones anteriores siguen disponibles.') from None
            raise
        return result


class PendingWrites:
    """Same form + retry => same UUID. A changed form always gets a new UUID."""
    def __init__(self):
        self.pending = {}

    def payload(self, action, data):
        fingerprint = json.dumps([action, data], sort_keys=True, ensure_ascii=False)
        if fingerprint not in self.pending:
            self.pending[fingerprint] = str(uuid4())
        return dict(data, request_id=self.pending[fingerprint])

    def complete(self):
        self.pending.clear()
