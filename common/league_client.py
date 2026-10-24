"""Optional League gateway using the currently signed-in Gym identity."""
import json
import os
import re
from urllib.parse import urlsplit
import httpx


def configured_endpoint():
    from product_config import load_config
    return os.environ.get('ATLANTIC_LEAGUE_ENDPOINT') or load_config(validate=False).get('league_endpoint', '')


class LeagueClient:
    def __init__(self, cloud, endpoint=None, source_url=None, transport=httpx):
        self.cloud, self.transport = cloud, transport
        self.endpoint = endpoint if endpoint is not None else configured_endpoint()
        if source_url is None:
            from product_config import load_config
            source_url = load_config(validate=False).get('supabase_url', '')
        source = source_url
        if not re.fullmatch(r'https://[a-z0-9]{20}\.supabase\.co/functions/v1/atlantic-league', self.endpoint):
            raise ValueError('League todavía no está configurado en este equipo.')
        if not re.fullmatch(r'https://[a-z0-9]{20}\.supabase\.co', source):
            raise ValueError('La conexión del gimnasio no está disponible.')
        self.source_ref = urlsplit(source).hostname.split('.')[0]

    def call(self, action, data=None):
        session = self.cloud.sessions.ensure()
        if not session or not self.cloud.gym_id:
            raise ValueError('Inicia sesión en Atlantic Gym para continuar.')
        payload = {'audience': 'staff', 'project_ref': self.source_ref,
                   'gym_id': self.cloud.gym_id, 'action': action, 'data': data or {}}
        try:
            with self.transport.stream('POST', self.endpoint, headers={'Authorization': 'Bearer '+session.access_token},
                                     json=payload, timeout=25, follow_redirects=False) as response:
                raw = bytearray()
                for chunk in response.iter_bytes(65536):
                    raw.extend(chunk)
                    if len(raw) > 2*1024*1024:
                        raise ValueError('La respuesta es demasiado grande. Reduce la consulta.')
                value = json.loads(raw)
                if response.status_code != 200:
                    raise ValueError('No se pudo completar la operación. Revisa la conexión, tu sesión y los permisos de League.')
                return value['data']
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as error:
            raise ValueError('No se pudo conectar con League. Vuelve a intentarlo.') from None
