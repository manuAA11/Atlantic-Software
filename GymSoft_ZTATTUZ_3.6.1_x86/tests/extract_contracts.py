"""Contrasta los nombres de RPC y columnas que usa Python con PostgreSQL."""
import ast
import json
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from cloud_database import EXCEL_IMPORT_COLUMNS
from common.source_layout import resolve_source
from common.deployment_profile import PROFILE
calls=[]
writes={}
for file in sorted(root.glob('*.py')):
    # These RPCs belong to the external Core control plane, tested separately.
    if file.stem in {'core_admin_ui', 'core_client', 'platform_ui', 'updater'}:
        continue
    for node in ast.walk(ast.parse(resolve_source(file).read_text(encoding='utf-8'))):
        if (isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in {'rpc', '_pos_rpc'}
            and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str)):
            args=[]
            if len(node.args)>1 and isinstance(node.args[1],ast.Dict):
                args=[k.value for k in node.args[1].keys if isinstance(k,ast.Constant)]
            if node.func.attr == '_pos_rpc':
                args = ['p_gym_id'] + [k.arg for k in node.keywords if k.arg]
            if file.name in ('marketing_client.py','marketing_ui.py','marketing_reception.py'):
                args += [k.arg for k in node.keywords if k.arg]
                if 'p_gym_id' not in args: args.insert(0,'p_gym_id')
            if file.stem == 'runtime_cloud' and node.args[0].value == 'create_gym' and not PROFILE.legacy_provider:
                continue
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
# RPC names selected by the shared provider adapter must remain in SQL checks.
provider_calls = {PROFILE.context_rpc: [], PROFILE.system_rpc: []}
if PROFILE.legacy_provider:
    provider_calls.update({'join_gym':['p_join_code'], 'redeem_reception_invite':['p_code']})
else:
    provider_calls.update({'commercial_accept_invite':['p_code'], 'commercial_check_license':['p_device_hash','p_device_name']})
for name,args in provider_calls.items():
    calls.append({'file':'common/deployment_profile.py', 'name':name, 'args':args})
columns={k:sorted(set(v.values())) for k,v in EXCEL_IMPORT_COLUMNS.items()}
# RPC seleccionadas dinámicamente por rol o por el editor de pagos.
extra={
 'join_gym':['p_join_code'], 'redeem_reception_invite':['p_code'],
 'ztattuz_client_payments':['p_gym_id','p_client_id','p_include_void','p_offset','p_limit'],
 'ztattuz_change_payment':['p_gym_id','p_membership_id','p_expected_revision','p_action','p_reason','p_amount','p_payment_method','p_payment_reference'],
 'ztattuz_payment_history':['p_gym_id','p_membership_id'],
}
for name,args in extra.items():calls.append({'file':'adaptadores dinámicos','name':name,'args':args})
# Estas columnas se calculan al exportar y se resuelven a sus FK al importar.
derived={'gym_store_settings':{'inventory_request_archive'},'memberships':{'client_document','client_name','plan_name'},'checkins':{'client_document','client_name'},
 'store_products':{'has_image'},'staff_shifts':{'hourly_rate','trainer_name'},'routines':{'client_name','trainer_name'},
 'exercises':{'routine_name'},'classes':{'trainer_name'},'reservations':{'class_name','client_document','client_name'}}
for table,virtual in derived.items():columns[table]=[c for c in columns[table] if c not in virtual]
for table,keys in writes.items():columns[table]=sorted(set(columns.get(table,[]))|keys)
(root/'tests/contracts.json').write_text(json.dumps({'calls':calls,'columns':columns},indent=2))
print('Client contract extracted')
