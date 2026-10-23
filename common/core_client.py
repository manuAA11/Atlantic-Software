"""Optional control plane: outages never become a database outage."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import platform
import re
import struct
import threading
from urllib.parse import urlsplit

import httpx
from device_identity import device_identifier
from session_manager import default_store, MemorySessionStore

CONFIG_KEYS={'update_channel','notifications_enabled','automatic_door_enabled','store_enabled','whatsapp_enabled'}


class CoreClient:
    def __init__(self, cloud, endpoint, version, edition, *, store=None, http=None, variant='ztattuz'):
        self.variant=variant
        self.cloud, self.endpoint, self.version, self.edition = cloud, endpoint, version, edition
        self.device_id = device_identifier()
        self.architecture='windows-x86' if struct.calcsize('P')==4 else 'windows-x64'
        source=urlsplit(str(cloud.client.raw.supabase_url)).hostname or ''
        self.project_ref=source.split('.')[0]
        parsed=urlsplit(endpoint)
        if endpoint and (parsed.scheme!='https' or not parsed.hostname or not re.fullmatch(r'[a-z0-9]{20}\.supabase\.co',parsed.hostname)
            or parsed.path!='/functions/v1/atlantic-core' or parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port not in (None,443)):
            raise ValueError('Endpoint de Core no permitido.')
        namespace='core-cache|'+self.project_ref+'|'+str(cloud.gym_id)+'|'+self.device_id
        try:self.store=store if store is not None else default_store(namespace)
        except OSError:self.store=MemorySessionStore()
        self.http=http or httpx.Client(timeout=15,follow_redirects=False)
        self.snapshot=None
        self.state='DISABLED' if not endpoint else 'CORE_OFFLINE'
        self.stop_event=threading.Event();self.thread=None;self.lock=threading.Lock()
        try:
            value=self.store.load()
            if value:self.snapshot=self.validate(value)
        except Exception:pass # Invalid/unreadable cache is never an explicit suspension.
        self.update_status='NO_UPDATE'
        self.hardware_metadata={}

    def validate(self, value):
        if not isinstance(value,dict) or value.get('gym_id')!=self.cloud.gym_id:
            raise ValueError('La respuesta de Core no corresponde al gimnasio.')
        if value.get('product_variant')!=self.variant:raise ValueError('La respuesta de Core corresponde a otro perfil de instalación.')
        if value.get('status') not in {'ACTIVE','SUSPENDED','CANCELLED'} or value.get('license_status') not in {'ACTIVE','SUSPENDED','CANCELLED'}:
            raise ValueError('Estado de Core no válido.')
        if value.get('device_status') not in {'AUTHORIZED','REVOKED'}:raise ValueError('Estado del equipo no válido.')
        configuration=value.get('configuration',{})
        if not isinstance(configuration,dict) or set(configuration)-CONFIG_KEYS:raise ValueError('Configuración de Core no permitida.')
        if configuration.get('update_channel','stable') not in {'stable','beta'}:raise ValueError('Canal no permitido.')
        for key,val in configuration.items():
            if key!='update_channel' and type(val) is not bool:raise ValueError('Opción de Core no válida.')
        now=datetime.now(timezone.utc)
        received=datetime.fromisoformat(value['server_time'].replace('Z','+00:00'))
        if received.tzinfo is None or received>now.replace(microsecond=0)+timedelta(minutes=5):raise ValueError('Reloj de Core no válido.')
        if type(value.get('grace_days')) is not int or not 0<=value['grace_days']<=90:raise ValueError('Período de gracia no válido.')
        for name in ('notifications','releases'):
            if not isinstance(value.get(name),list) or len(value[name])>1000:raise ValueError('Respuesta de Core demasiado grande.')
        return value

    def metadata(self):
        return dict(device_name=platform.node()[:120] or 'Computador',architecture=self.architecture,
            os=platform.system()+' '+platform.release(),app_version=self.version,edition=self.edition,
            sync_status='SYNCED' if self.cloud.sessions.state=='ONLINE' else 'OFFLINE',
            update_status=self.update_status,**self.hardware_metadata)

    def sync(self, read_id=None):
        if not self.endpoint:return None
        with self.lock:
            try:
                session=self.cloud.client.auth.get_session()
                if not session:raise PermissionError('La sesión necesita autenticación.')
                response=self.http.post(self.endpoint,headers={'Authorization':'Bearer '+session.access_token},
                    json=dict(project_ref=self.project_ref,device_id=self.device_id,metadata=self.metadata(),read_id=read_id))
                response.raise_for_status()
                if len(response.content)>2*1024*1024:raise ValueError('Respuesta de Core demasiado grande.')
                snapshot=self.validate(response.json())
                self.store.save(snapshot)
                self.snapshot=snapshot;self.state='ONLINE'
                return snapshot
            except Exception:
                self.state='CORE_OFFLINE'
                # Never clear valid cached license or close the application for this.
                return self.snapshot

    def require_operation(self):
        value=self.snapshot
        if value and (value['license_status'] in {'SUSPENDED','CANCELLED'} or value['status'] in {'SUSPENDED','CANCELLED'} or value['device_status']=='REVOKED'):
            raise PermissionError('Atlantic Core comunica una suspensión explícita de licencia o equipo. Contacta al proveedor.')

    def grace_state(self):
        if not self.snapshot:return 'NO_CACHED_LICENSE'
        then=datetime.fromisoformat(self.snapshot['server_time'].replace('Z','+00:00'))
        days=(datetime.now(timezone.utc)-then).total_seconds()/86400
        return 'WITHIN_GRACE' if days<=self.snapshot['grace_days'] else 'GRACE_EXCEEDED'

    def start(self):
        if not self.endpoint or (self.thread and self.thread.is_alive()):return
        self.stop_event.clear()
        def run():
            self.sync()
            while not self.stop_event.wait(300):self.sync()
        self.thread=threading.Thread(target=run,name='Atlantic-Core',daemon=True);self.thread.start()

    def close(self):
        self.stop_event.set()
