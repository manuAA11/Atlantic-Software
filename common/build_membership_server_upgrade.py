"""Build one atomic, prerequisite-checked upgrade from the canonical new SQLs."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('internal_plans.sql', 'early_resume.sql')
OUTPUT = 'ACTUALIZAR_SERVIDOR_MEMBRESIAS.sql'

# Existing server objects only. New STAFF/resume columns are not prerequisites.
TABLE_COLUMNS = {
    'auth.users': 'id email',
    'public.gyms': 'id timezone',
    'public.gym_users': 'gym_id user_id role',
    'public.clients': 'id gym_id active document first_name last_name phone email birthdate birth_date biometric_identifier',
    'public.plans': 'id gym_id name duration_days duration_months price entry_limit active',
    'public.memberships': 'id gym_id client_id plan_id start_date end_date paid_at entry_limit initial_entries_used amount amount_paid payment_status payment_revision payment_source payment_method payment_reference notes recorded_by freeze_archive',
    'public.checkins': 'id gym_id client_id membership_id result notes local_date',
    'public.audit_logs': 'id gym_id actor_user_id actor_email actor_role action entity_type entity_id summary details',
    'public.membership_freeze_policies': 'id gym_id plan_id enabled duration_days max_per_membership',
    'public.membership_freezes': 'id gym_id client_id membership_id request_id start_date resume_date timezone starts_at ends_at days_added days_reversed original_end_date extended_end_date status reason created_by created_at cancelled_by cancelled_at completed_at administrative_override',
    'public.payment_requests': 'id gym_id client_id status',
    'public.marketing_messages': 'gym_id client_id status error_message updated_at payment_request_id automation_type',
    'public.payment_transactions': 'mode provider_transaction_id requires_review',
    'public.automation_runs': 'gym_id automation_id client_id dedupe_key status reason',
    'public.marketing_automations': 'id gym_id',
    'public.ticket_daily_consumptions': 'gym_id client_id membership_id local_date units legacy created_at',
    'private.ticket_import_context': 'transaction_id gym_id',
}
FUNCTIONS = (
    'auth.uid()',
    'private.user_has_gym_role(uuid,text[])',
    'private.gym_server_now()', 'private.gym_timezone(uuid)', 'private.gym_local_date(uuid)',
    'private.ticket_end_date(date,integer,integer)',
    'private.ticket_consumption_units(uuid,bigint)',
    'private.ticket_consumed_on(uuid,bigint,bigint,date)',
    'private.freeze_policy(uuid,bigint)', 'private.freeze_active(uuid,bigint)',
    'private.freeze_complete_due(uuid,bigint)',
    'private.membership_snapshot_before_freezes(uuid,bigint)',
    'private.membership_snapshot_json(uuid,bigint)',
    'private.marketing_audit(uuid,text,text,text,jsonb)',
    'public.add_membership_accumulating(uuid,bigint,bigint,date,bigint,text,text,text)',
    'public.gym_local_clock(uuid)', 'public.reception_list_clients(uuid,text)',
    'public.reception_membership_snapshot(uuid,bigint)', 'public.ticket_followup(uuid)',
)
# Fail before backfills if an installed function cannot receive its exact patch.
PATCH_ANCHORS = (
    ('private.audit_membership_payment()', "- 'updated_at')", 'AUDIT_INTERNAL_FLAG_BACKFILL'),
    ('private.consume_daily_ticket()', "if m.payment_status<>'posted' or new.local_date not between m.start_date and m.end_date", 'INTERNAL_TICKET_GUARD'),
    ('public.marketing_service_apply_payment(uuid,jsonb)', " if r.status='APPROVED' then", 'INTERNAL_LATE_PAYMENT_GUARD'),
    ('public.marketing_service_enqueue(uuid,uuid,bigint,text,text,text,jsonb,uuid)',
     'insert into public.automation_runs(gym_id,automation_id,client_id,dedupe_key,status,reason)', 'INTERNAL_ENQUEUE_GUARD'),
    ('public.marketing_service_send_guard(bigint,uuid)', 'if m.automation_id is not null then', 'INTERNAL_SEND_GUARD'),
    ('public.membership_save_freeze_policy(uuid,boolean,integer,integer,bigint)',
     "not private.user_has_gym_role(p_gym_id,array['admin'])", 'not private.membership_manage_allowed(p_gym_id)'),
)
DATE_COLUMNS = {
    'public.clients': ('birthdate', 'birth_date'),
    'public.memberships': ('start_date', 'end_date'),
    'public.checkins': ('local_date',),
    'public.membership_freezes': ('start_date', 'resume_date', 'original_end_date', 'extended_end_date'),
    'public.ticket_daily_consumptions': ('local_date',),
}
INSTANT_COLUMNS = {
    'public.memberships': ('paid_at',),
    'public.membership_freezes': ('starts_at', 'ends_at', 'created_at', 'cancelled_at', 'completed_at'),
    'public.marketing_messages': ('updated_at',),
    'public.ticket_daily_consumptions': ('created_at',),
}


def literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def values(rows) -> str:
    return ',\n '.join('(' + ','.join(literal(value) for value in row) + ')' for row in rows)


def canonical_body(path: Path) -> str:
    """Remove only the two verified standalone outer transaction lines."""
    lines = path.read_text(encoding='utf-8').splitlines(keepends=True)
    begins = [i for i, line in enumerate(lines) if line.strip().lower() == 'begin;']
    commits = [i for i, line in enumerate(lines) if line.strip().lower() == 'commit;']
    if len(begins) != 1 or len(commits) != 1 or begins[0] >= commits[0]:
        raise ValueError(f'{path.name}: expected one standalone outer BEGIN/COMMIT')
    if any(line.strip() and not line.lstrip().startswith('--') for line in lines[:begins[0]]):
        raise ValueError(f'{path.name}: SQL precedes outer BEGIN')
    if any(line.strip() for line in lines[commits[0] + 1:]):
        raise ValueError(f'{path.name}: SQL follows outer COMMIT')
    return ''.join(line for i, line in enumerate(lines) if i not in (begins[0], commits[0]))


def preflight(source_texts: tuple[str, ...]) -> str:
    patched = set()
    for text in source_texts:
        patched.update(re.findall(r"pg_get_functiondef\('([^']+)'::regprocedure", text))
    functions = sorted(set(FUNCTIONS) | patched)
    columns = [(table, column) for table, names in TABLE_COLUMNS.items() for column in names.split()]
    typed = [(table, column, 'date') for table, names in DATE_COLUMNS.items() for column in names]
    typed += [(table, column, 'timestamp with time zone') for table, names in INSTANT_COLUMNS.items() for column in names]
    return f"""-- Sólo metadatos: ningún cliente, membresía, pago o historial se modifica aquí.
-- Si falta una actualización anterior, se detiene TODO el archivo antes de escribir.
do $atlantic_membership_preflight$
declare missing text[] := array[]::text[]; item record; definition text;
begin
 for item in select * from (values {values((name,) for name in ('public', 'private', 'auth'))}) as required(name) loop
  if not exists(select 1 from pg_namespace where nspname=item.name) then
   missing:=array_append(missing,'esquema '||item.name);
  end if;
 end loop;
 for item in select * from (values {values((name,) for name in ('anon', 'authenticated'))}) as required(name) loop
  if not exists(select 1 from pg_roles where rolname=item.name) then
   missing:=array_append(missing,'rol '||item.name);
  end if;
 end loop;
 for item in select * from (values {values((table,) for table in TABLE_COLUMNS)}) as required(name) loop
  if to_regclass(item.name) is null then missing:=array_append(missing,'tabla '||item.name);end if;
 end loop;
 for item in select * from (values {values(columns)}) as required(relation_name,column_name) loop
  if to_regclass(item.relation_name) is not null and not exists(
   select 1 from pg_attribute where attrelid=to_regclass(item.relation_name)
    and attname=item.column_name and attnum>0 and not attisdropped) then
   missing:=array_append(missing,'columna '||item.relation_name||'.'||item.column_name);
  end if;
 end loop;
 for item in select * from (values {values(typed)}) as required(relation_name,column_name,type_name) loop
  if exists(select 1 from pg_attribute where attrelid=to_regclass(item.relation_name)
   and attname=item.column_name and attnum>0 and not attisdropped and atttypid<>to_regtype(item.type_name)) then
   missing:=array_append(missing,'tipo '||item.relation_name||'.'||item.column_name||' debe ser '||item.type_name);
  end if;
 end loop;
 for item in select * from (values {values((name,) for name in functions)}) as required(signature) loop
  if to_regprocedure(item.signature) is null then
   missing:=array_append(missing,'función '||item.signature);
  end if;
 end loop;
 for item in select * from (values {values(PATCH_ANCHORS)}) as required(signature,old_anchor,new_marker) loop
  if to_regprocedure(item.signature) is not null then
   definition:=pg_get_functiondef(to_regprocedure(item.signature));
   if position(item.old_anchor in definition)=0 and position(item.new_marker in definition)=0 then
    missing:=array_append(missing,'versión compatible de '||item.signature);
   end if;
  end if;
 end loop;
 if cardinality(missing)>0 then
  raise exception using errcode='P0001',
   message='No se aplicó la actualización de membresías: faltan requisitos anteriores o su versión no es compatible.',
   detail=array_to_string(missing,E'\\n'),
   hint='Ejecuta DIAGNOSTICAR_PANEL.sql y revisa el historial de migraciones del proyecto. No ejecutes el esquema inicial ni repitas migraciones antiguas a ciegas. Esta transacción no guardó cambios.';
 end if;
end $atlantic_membership_preflight$;

"""


def build() -> bytes:
    paths = tuple(ROOT / 'common' / name for name in SOURCES)
    texts = tuple(path.read_text(encoding='utf-8') for path in paths)
    header = ('-- Atlantic Gym: actualización aditiva de membresías, STAFF y reanudación.\n'
              '-- Ejecutar este archivo COMPLETO en el SQL Editor del proyecto existente.\n'
              '-- Una sola transacción: cualquier fallo revierte los dos upgrades.\n'
              '-- No instala una base nueva ni aplica migraciones históricas.\n')
    for path in paths:
        header += f'-- Fuente canónica {path.name}; SHA256 {hashlib.sha256(path.read_bytes()).hexdigest()}\n'
    header += "begin;\nset local lock_timeout='8s';\nset local statement_timeout='90s';\n"
    bodies = ''.join(f'-- INICIO FUENTE {path.name}\n{canonical_body(path)}-- FIN FUENTE {path.name}\n\n' for path in paths)
    return (header + preflight(texts) + bodies + 'commit;\n').encode('utf-8')


def generate() -> list[Path]:
    content = build()
    targets = [ROOT / OUTPUT, *(edition / OUTPUT for edition in sorted(ROOT.glob('GymSoft_*')) if edition.is_dir())]
    for path in targets:
        path.write_bytes(content)
    return targets


if __name__ == '__main__':
    for target in generate():
        print(target.relative_to(ROOT))
