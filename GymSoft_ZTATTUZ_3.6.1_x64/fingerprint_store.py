"""Gym-scoped cloud templates. Memory only: no raw fingerprint files or logs."""
import base64

class CloudTemplateStore:
    def __init__(self, db):
        self.db = db; self.values = {}; self.revisions = {}
    def request(self, action, client=None, template=None, expected=None):
        try:
            return self.db._execute(self.db.client.rpc('gym_fingerprints',{
                'p_gym_id':self.db.gym_id,'p_action':action,'p_client_id':client,
                'p_template':template,'p_expected':expected})).data
        except Exception as error:
            from fingerprint_diagnostics import record
            record('cloud_' + action, error)
            code = str(getattr(error,'code',''))
            if code == '40001': raise RuntimeError('La huella cambió en otro equipo. Actualiza e inténtalo de nuevo.') from error
            if code == '42501': raise RuntimeError('No se autorizó el acceso a las huellas. Revisa la sesión, el rol y el acceso del equipo al gimnasio.') from error
            if code in ('PGRST202','42883'): raise RuntimeError('Falta instalar ACTUALIZAR_HUELLAS_3.5.0.sql en la base del gimnasio.') from error
            raise RuntimeError('No se pudo confirmar la sincronización de huellas. Revisa la conexión y actualiza antes de repetir la operación.') from error
    def load(self):
        rows = self.request('list'); values = {}; revisions = {}
        if not isinstance(rows,list): raise ValueError('Respuesta de huellas no válida.')
        for row in rows:
            value = base64.b64decode(row['template'],validate=True)
            if not value.startswith(b'FMR\0') or not 30<=len(value)<=4096: raise ValueError('Plantilla de huella no válida.')
            key = int(row['client_id']); values[key] = value; revisions[key] = row['revision']
        self.values,self.revisions = values,revisions
        return dict(values)
    def save(self, proposed):
        changed = [key for key in set(proposed)|set(self.values) if proposed.get(key)!=self.values.get(key)]
        if len(changed)!=1: raise ValueError('Solo se puede modificar una huella por operación.')
        key=changed[0]; value=proposed.get(key)
        result = self.request('save' if value is not None else 'delete',key,
                          base64.b64encode(value).decode() if value is not None else None,self.revisions.get(key))
        if not isinstance(result,dict) or not result.get('saved'): raise RuntimeError('No se confirmó el guardado de la huella.')
        self.values=dict(proposed)
        if value is None:self.revisions.pop(key,None)
        else:self.revisions[key]=result['revision']
