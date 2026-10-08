"""Authenticated desktop adapter. Provider secrets are sent once, never saved locally."""
import json

class MarketingClient:
    def __init__(self, db):
        self.db, self.client, self.gym_id = db, db.client, db.gym_id

    def rpc(self, name, **parameters):
        try:
            data = self.db._execute(self.client.rpc(name, {'p_gym_id': self.gym_id, **parameters})).data
            if isinstance(data, str) and data.lstrip().startswith(('{', '[')):
                data = json.loads(data)
            if data is not None and not isinstance(data, (dict, list, str, int, float, bool)):
                raise ValueError('No se recibió una respuesta válida del servidor.')
            return data
        except Exception as error:
            if str(getattr(error, 'code', '')) == 'P0001':
                raise ValueError(str(getattr(error, 'message', 'Revisa la configuración.'))[:500]) from None
            raise

    def workspace(self):
        return self.rpc('marketing_workspace')

    def lookup(self, search=''):
        return self.rpc('marketing_lookup_clients', p_search=search, p_limit=100)

    def history(self, kind, offset=0):
        return self.rpc('marketing_history', p_kind=kind, p_offset=offset)

    def edge(self, action, **parameters):
        try:
            result = self.client.functions.invoke('marketing/admin', invoke_options={
                'body': {'gym_id': self.gym_id, 'action': action, **parameters}})
        except Exception as error:
            # Do not expose exception repr: requests can contain credentials.
            context = getattr(error, 'context', None)
            if hasattr(context, 'json'):
                try:response = context.json()
                except Exception:response = None
                if isinstance(response, dict) and response.get('message'):
                    raise ValueError(str(response['message'])[:500]) from None
            raise ValueError('No se pudo confirmar la respuesta de Marketing. Revisa Estado de integraciones y vuelve a intentarlo.') from None
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        if isinstance(result, str):
            result = json.loads(result)
        if isinstance(result, dict) and result.get('error'):
            raise ValueError(str(result.get('message') or 'Revisa la configuración de Marketing.'))
        return result

    @staticmethod
    def diagnostic(data):
        summary = data.get('summary') or {}
        flags = summary.get('settings') or {}
        return {'integrations': [{k: c.get(k) for k in ('provider', 'status', 'mode', 'last_checked_at')}
                                 for c in summary.get('connections', [])],
                'features': {k: bool(flags.get(k)) for k in ('whatsapp_enabled', 'online_payments_enabled',
                    'chatbot_enabled', 'marketing_automation_enabled')},
                'scheduler': data.get('health') or {}, 'active_rules': summary.get('automations_active', 0)}
