"""Contrasta los nombres de RPC y columnas que usa Python con PostgreSQL."""
import ast
import json
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from cloud_database import EXCEL_IMPORT_COLUMNS
from owner_forms import new_gym_params,renewal_params,contract_params,invite_params,grace_params
from owner_editor_forms import profile_params,email_params
calls=[]
writes={}
for file in sorted(root.glob('*.py')):
    for node in ast.walk(ast.parse(file.read_text(encoding='utf-8'))):
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='rpc'
            and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str)):
            args=[]
            if len(node.args)>1 and isinstance(node.args[1],ast.Dict):
                args=[k.value for k in node.args[1].keys if isinstance(k,ast.Constant)]
            if file.name in ('marketing_client.py','marketing_ui.py','marketing_reception.py'):
                args += [k.arg for k in node.keywords if k.arg]
                if 'p_gym_id' not in args: args.insert(0,'p_gym_id')
            calls.append({'file':file.name,'name':node.args[0].value,'args':args})
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
            and node.func.attr in {'insert','update','upsert'} and node.args
            and isinstance(node.args[0],ast.Dict)):
            source=node.func.value
            while isinstance(source,ast.Call) and isinstance(source.func,ast.Attribute):
                if source.func.attr=='table' and source.args and isinstance(source.args[0],ast.Constant):
                    table=source.args[0].value
                    writes.setdefault(table,set()).update(k.value for k in node.args[0].keys if isinstance(k,ast.Constant))
                    break
                source=source.func.value
columns={k:sorted(set(v.values())) for k,v in EXCEL_IMPORT_COLUMNS.items()}
gym={'id':'a0000000-0000-4000-8000-000000000001','currency':'COP'}
owner_calls={
 'owner_create_gym':new_gym_params({'name':'Gym test','email':'gym@example.test','price':'100','currency':'COP','devices':'2','days':'7','timezone':'America/Bogota'}),
 'owner_renew':renewal_params(gym,{'months':'1','amount':'100','reference':'TEST-1'}),
 'owner_update_contract':contract_params(gym,{'price':'100','currency':'COP','devices':'2','users':'10','notes':''}),
 'owner_invite_user':invite_params(gym,{'email':'staff@example.test','role':'Recepción'}),
 'owner_grant_grace':grace_params(gym,{'days':'3','reason':'Prueba'}),
 'owner_set_status':{'p_gym_id':None,'p_status':None,'p_reason':None},
 'owner_set_device':{'p_device_id':None,'p_blocked':None,'p_reason':None},
 'owner_set_user':{'p_user_id':None,'p_enabled':None,'p_reason':None},
 'owner_backup_gym':{'p_gym_id':None},'owner_gym_detail':{'p_gym_id':None},
 'gymsoft_client_payments':{'p_gym_id':None,'p_client_id':None,'p_include_void':None,'p_offset':None,'p_limit':None},
 'gymsoft_change_payment':{'p_gym_id':None,'p_membership_id':None,'p_expected_revision':None,'p_action':None,'p_reason':None,'p_amount':None,'p_payment_method':None,'p_payment_reference':None},
 'gymsoft_payment_history':{'p_gym_id':None,'p_membership_id':None},
 'owner_editor_backup':{'p_gym_id':None},
 'owner_editor_access':{'p_gym_id':None},
 'owner_editor_revoke_invite':{'p_gym_id':None,'p_email':None,'p_reason':None},
 'owner_editor_profile':profile_params(gym,{'name':'Editor','email':'owner@example.test','timezone':'America/Bogota','plan':'Pro','reason':'Prueba'}),
 'owner_editor_email':email_params(gym,{'email':'user@example.test','role':'Recepción','reason':'Prueba'}),
 'owner_editor_rows':{'p_gym_id':None,'p_table':None,'p_search':None,'p_offset':None,'p_limit':None},
 'owner_editor_record':{'p_gym_id':None,'p_table':None,'p_id':None,'p_expected':None,'p_patch':None,'p_reason':None,'p_delete':None},
 'owner_editor_delete_gym':{'p_gym_id':None,'p_name':None,'p_expected':None,'p_reason':None},
 'owner_editor_validate_import':{'p_data':None},
 'owner_editor_import':{'p_gym_id':None,'p_name':None,'p_expected':None,'p_reason':None,'p_data':None},
}
for name,params in owner_calls.items():calls.append({'file':'owner_forms.py / runtime adapters','name':name,'args':list(params)})
# Estas columnas se calculan al exportar y se resuelven a sus FK al importar.
derived={'memberships':{'client_document','client_name','plan_name'},'checkins':{'client_document','client_name'},
 'store_products':{'has_image'},'staff_shifts':{'hourly_rate','trainer_name'},'routines':{'client_name','trainer_name'},
 'exercises':{'routine_name'},'classes':{'trainer_name'},'reservations':{'class_name','client_document','client_name'}}
for table,virtual in derived.items():columns[table]=[c for c in columns[table] if c not in virtual]
for table,keys in writes.items():columns[table]=sorted(set(columns.get(table,[]))|keys)
(root/'tests/contracts.json').write_text(json.dumps({'calls':calls,'columns':columns},indent=2))
print('Client contract extracted')
