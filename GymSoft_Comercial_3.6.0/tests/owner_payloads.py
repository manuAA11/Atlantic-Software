"""Los tests PostgreSQL reciben exactamente los parámetros de los formularios Python."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from owner_forms import new_gym_params, renewal_params, contract_params, invite_params, grace_params
gym={'id':'a0000000-0000-4000-8000-000000000001','currency':'COP','active_devices':1,'active_users':2}
payloads={
 'create':new_gym_params({'name':'Gym prueba UI','email':'admin@example.test','price':'200.000',
                        'currency':'COP','devices':'2','days':'7','timezone':'America/Bogota'}),
 'renew':renewal_params(gym,{'months':'2','amount':'400.000','reference':'UI-RECIBO-001'}),
 'contract':contract_params(gym,{'price':'150.000','currency':'cop','devices':'3','users':'4','notes':'Prueba UI'}),
 'invite':invite_params(gym,{'email':'reception@example.test','role':'Recepción'}),
 'grace':grace_params(gym,{'days':'3','reason':'Pago pendiente'}),
}
print(json.dumps(payloads))
