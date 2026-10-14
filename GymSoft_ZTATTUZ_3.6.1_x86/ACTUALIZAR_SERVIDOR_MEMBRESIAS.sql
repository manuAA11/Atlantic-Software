-- Atlantic Gym: actualización aditiva de membresías, STAFF y reanudación.
-- Ejecutar este archivo COMPLETO en el SQL Editor del proyecto existente.
-- Una sola transacción: cualquier fallo revierte los dos upgrades.
-- No instala una base nueva ni aplica migraciones históricas.
-- Fuente canónica internal_plans.sql; SHA256 71067a4f5ee8006325f5eee51daf5e2b9fb67c8515f93892e3b9b5a5f8851735
-- Fuente canónica early_resume.sql; SHA256 86ad5be7dcd089b2d533320899e285023f1cc132557ad3779a0bbe08e0bc7952
begin;
set local lock_timeout='8s';
set local statement_timeout='90s';
-- Sólo metadatos: ningún cliente, membresía, pago o historial se modifica aquí.
-- Si falta una actualización anterior, se detiene TODO el archivo antes de escribir.
do $atlantic_membership_preflight$
declare missing text[] := array[]::text[]; item record; definition text;
begin
 for item in select * from (values ('public'),
 ('private'),
 ('auth')) as required(name) loop
  if not exists(select 1 from pg_namespace where nspname=item.name) then
   missing:=array_append(missing,'esquema '||item.name);
  end if;
 end loop;
 for item in select * from (values ('anon'),
 ('authenticated')) as required(name) loop
  if not exists(select 1 from pg_roles where rolname=item.name) then
   missing:=array_append(missing,'rol '||item.name);
  end if;
 end loop;
 for item in select * from (values ('auth.users'),
 ('public.gyms'),
 ('public.gym_users'),
 ('public.clients'),
 ('public.plans'),
 ('public.memberships'),
 ('public.checkins'),
 ('public.audit_logs'),
 ('public.membership_freeze_policies'),
 ('public.membership_freezes'),
 ('public.payment_requests'),
 ('public.marketing_messages'),
 ('public.payment_transactions'),
 ('public.automation_runs'),
 ('public.marketing_automations'),
 ('public.ticket_daily_consumptions'),
 ('private.ticket_import_context')) as required(name) loop
  if to_regclass(item.name) is null then missing:=array_append(missing,'tabla '||item.name);end if;
 end loop;
 for item in select * from (values ('auth.users','id'),
 ('auth.users','email'),
 ('public.gyms','id'),
 ('public.gyms','timezone'),
 ('public.gym_users','gym_id'),
 ('public.gym_users','user_id'),
 ('public.gym_users','role'),
 ('public.clients','id'),
 ('public.clients','gym_id'),
 ('public.clients','active'),
 ('public.clients','document'),
 ('public.clients','first_name'),
 ('public.clients','last_name'),
 ('public.clients','phone'),
 ('public.clients','email'),
 ('public.clients','birthdate'),
 ('public.clients','birth_date'),
 ('public.clients','biometric_identifier'),
 ('public.plans','id'),
 ('public.plans','gym_id'),
 ('public.plans','name'),
 ('public.plans','duration_days'),
 ('public.plans','duration_months'),
 ('public.plans','price'),
 ('public.plans','entry_limit'),
 ('public.plans','active'),
 ('public.memberships','id'),
 ('public.memberships','gym_id'),
 ('public.memberships','client_id'),
 ('public.memberships','plan_id'),
 ('public.memberships','start_date'),
 ('public.memberships','end_date'),
 ('public.memberships','paid_at'),
 ('public.memberships','entry_limit'),
 ('public.memberships','initial_entries_used'),
 ('public.memberships','amount'),
 ('public.memberships','amount_paid'),
 ('public.memberships','payment_status'),
 ('public.memberships','payment_revision'),
 ('public.memberships','payment_source'),
 ('public.memberships','payment_method'),
 ('public.memberships','payment_reference'),
 ('public.memberships','notes'),
 ('public.memberships','recorded_by'),
 ('public.memberships','freeze_archive'),
 ('public.checkins','id'),
 ('public.checkins','gym_id'),
 ('public.checkins','client_id'),
 ('public.checkins','membership_id'),
 ('public.checkins','result'),
 ('public.checkins','notes'),
 ('public.checkins','local_date'),
 ('public.audit_logs','id'),
 ('public.audit_logs','gym_id'),
 ('public.audit_logs','actor_user_id'),
 ('public.audit_logs','actor_email'),
 ('public.audit_logs','actor_role'),
 ('public.audit_logs','action'),
 ('public.audit_logs','entity_type'),
 ('public.audit_logs','entity_id'),
 ('public.audit_logs','summary'),
 ('public.audit_logs','details'),
 ('public.membership_freeze_policies','id'),
 ('public.membership_freeze_policies','gym_id'),
 ('public.membership_freeze_policies','plan_id'),
 ('public.membership_freeze_policies','enabled'),
 ('public.membership_freeze_policies','duration_days'),
 ('public.membership_freeze_policies','max_per_membership'),
 ('public.membership_freezes','id'),
 ('public.membership_freezes','gym_id'),
 ('public.membership_freezes','client_id'),
 ('public.membership_freezes','membership_id'),
 ('public.membership_freezes','request_id'),
 ('public.membership_freezes','start_date'),
 ('public.membership_freezes','resume_date'),
 ('public.membership_freezes','timezone'),
 ('public.membership_freezes','starts_at'),
 ('public.membership_freezes','ends_at'),
 ('public.membership_freezes','days_added'),
 ('public.membership_freezes','days_reversed'),
 ('public.membership_freezes','original_end_date'),
 ('public.membership_freezes','extended_end_date'),
 ('public.membership_freezes','status'),
 ('public.membership_freezes','reason'),
 ('public.membership_freezes','created_by'),
 ('public.membership_freezes','created_at'),
 ('public.membership_freezes','cancelled_by'),
 ('public.membership_freezes','cancelled_at'),
 ('public.membership_freezes','completed_at'),
 ('public.membership_freezes','administrative_override'),
 ('public.payment_requests','id'),
 ('public.payment_requests','gym_id'),
 ('public.payment_requests','client_id'),
 ('public.payment_requests','status'),
 ('public.marketing_messages','gym_id'),
 ('public.marketing_messages','client_id'),
 ('public.marketing_messages','status'),
 ('public.marketing_messages','error_message'),
 ('public.marketing_messages','updated_at'),
 ('public.marketing_messages','payment_request_id'),
 ('public.marketing_messages','automation_type'),
 ('public.payment_transactions','mode'),
 ('public.payment_transactions','provider_transaction_id'),
 ('public.payment_transactions','requires_review'),
 ('public.automation_runs','gym_id'),
 ('public.automation_runs','automation_id'),
 ('public.automation_runs','client_id'),
 ('public.automation_runs','dedupe_key'),
 ('public.automation_runs','status'),
 ('public.automation_runs','reason'),
 ('public.marketing_automations','id'),
 ('public.marketing_automations','gym_id'),
 ('public.ticket_daily_consumptions','gym_id'),
 ('public.ticket_daily_consumptions','client_id'),
 ('public.ticket_daily_consumptions','membership_id'),
 ('public.ticket_daily_consumptions','local_date'),
 ('public.ticket_daily_consumptions','units'),
 ('public.ticket_daily_consumptions','legacy'),
 ('public.ticket_daily_consumptions','created_at'),
 ('private.ticket_import_context','transaction_id'),
 ('private.ticket_import_context','gym_id')) as required(relation_name,column_name) loop
  if to_regclass(item.relation_name) is not null and not exists(
   select 1 from pg_attribute where attrelid=to_regclass(item.relation_name)
    and attname=item.column_name and attnum>0 and not attisdropped) then
   missing:=array_append(missing,'columna '||item.relation_name||'.'||item.column_name);
  end if;
 end loop;
 for item in select * from (values ('public.clients','birthdate','date'),
 ('public.clients','birth_date','date'),
 ('public.memberships','start_date','date'),
 ('public.memberships','end_date','date'),
 ('public.checkins','local_date','date'),
 ('public.membership_freezes','start_date','date'),
 ('public.membership_freezes','resume_date','date'),
 ('public.membership_freezes','original_end_date','date'),
 ('public.membership_freezes','extended_end_date','date'),
 ('public.ticket_daily_consumptions','local_date','date'),
 ('public.memberships','paid_at','timestamp with time zone'),
 ('public.membership_freezes','starts_at','timestamp with time zone'),
 ('public.membership_freezes','ends_at','timestamp with time zone'),
 ('public.membership_freezes','created_at','timestamp with time zone'),
 ('public.membership_freezes','cancelled_at','timestamp with time zone'),
 ('public.membership_freezes','completed_at','timestamp with time zone'),
 ('public.marketing_messages','updated_at','timestamp with time zone'),
 ('public.ticket_daily_consumptions','created_at','timestamp with time zone')) as required(relation_name,column_name,type_name) loop
  if exists(select 1 from pg_attribute where attrelid=to_regclass(item.relation_name)
   and attname=item.column_name and attnum>0 and not attisdropped and atttypid<>to_regtype(item.type_name)) then
   missing:=array_append(missing,'tipo '||item.relation_name||'.'||item.column_name||' debe ser '||item.type_name);
  end if;
 end loop;
 for item in select * from (values ('auth.uid()'),
 ('private.audit_membership_payment()'),
 ('private.consume_daily_ticket()'),
 ('private.freeze_active(uuid,bigint)'),
 ('private.freeze_complete_due(uuid,bigint)'),
 ('private.freeze_policy(uuid,bigint)'),
 ('private.gym_local_date(uuid)'),
 ('private.gym_server_now()'),
 ('private.gym_timezone(uuid)'),
 ('private.marketing_audit(uuid,text,text,text,jsonb)'),
 ('private.marketing_capture_event()'),
 ('private.membership_snapshot_before_freezes(uuid,bigint)'),
 ('private.membership_snapshot_json(uuid,bigint)'),
 ('private.ticket_consumed_on(uuid,bigint,bigint,date)'),
 ('private.ticket_consumption_units(uuid,bigint)'),
 ('private.ticket_end_date(date,integer,integer)'),
 ('private.user_has_gym_role(uuid,text[])'),
 ('public.add_membership_accumulating(uuid,bigint,bigint,date,bigint,text,text,text)'),
 ('public.gym_local_clock(uuid)'),
 ('public.marketing_service_apply_payment(uuid,jsonb)'),
 ('public.marketing_service_enqueue(uuid,uuid,bigint,text,text,text,jsonb,uuid)'),
 ('public.marketing_service_payment_request(uuid,bigint,bigint,text)'),
 ('public.marketing_service_send_guard(bigint,uuid)'),
 ('public.membership_save_freeze_policy(uuid,boolean,integer,integer,bigint)'),
 ('public.reception_list_clients(uuid,text)'),
 ('public.reception_membership_snapshot(uuid,bigint)'),
 ('public.ticket_followup(uuid)')) as required(signature) loop
  if to_regprocedure(item.signature) is null then
   missing:=array_append(missing,'función '||item.signature);
  end if;
 end loop;
 for item in select * from (values ('private.audit_membership_payment()','- ''updated_at'')','AUDIT_INTERNAL_FLAG_BACKFILL'),
 ('private.consume_daily_ticket()','if m.payment_status<>''posted'' or new.local_date not between m.start_date and m.end_date','INTERNAL_TICKET_GUARD'),
 ('public.marketing_service_apply_payment(uuid,jsonb)',' if r.status=''APPROVED'' then','INTERNAL_LATE_PAYMENT_GUARD'),
 ('public.marketing_service_enqueue(uuid,uuid,bigint,text,text,text,jsonb,uuid)','insert into public.automation_runs(gym_id,automation_id,client_id,dedupe_key,status,reason)','INTERNAL_ENQUEUE_GUARD'),
 ('public.marketing_service_send_guard(bigint,uuid)','if m.automation_id is not null then','INTERNAL_SEND_GUARD'),
 ('public.membership_save_freeze_policy(uuid,boolean,integer,integer,bigint)','not private.user_has_gym_role(p_gym_id,array[''admin''])','not private.membership_manage_allowed(p_gym_id)')) as required(signature,old_anchor,new_marker) loop
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
   detail=array_to_string(missing,E'\n'),
   hint='Ejecuta DIAGNOSTICAR_PANEL.sql y revisa el historial de migraciones del proyecto. No ejecutes el esquema inicial ni repitas migraciones antiguas a ciegas. Esta transacción no guardó cambios.';
 end if;
end $atlantic_membership_preflight$;

-- INICIO FUENTE internal_plans.sql
-- Additive upgrade. Historical sales stay commercial; internal assignments are not payments.
set local lock_timeout='8s';
set local statement_timeout='90s';
alter table public.plans
 add column if not exists plan_type text not null default 'COMMERCIAL',
 add column if not exists unlimited_access boolean not null default true,
 add column if not exists has_expiration boolean not null default true,
 add column if not exists include_in_financial_stats boolean not null default true;
alter table public.plans alter column duration_days drop not null;
alter table public.memberships
 add column if not exists membership_type text not null default 'COMMERCIAL',
 add column if not exists unlimited_access boolean not null default true,
 add column if not exists has_expiration boolean not null default true,
 add column if not exists include_in_financial_stats boolean not null default true,
 add column if not exists membership_active boolean not null default true,
 add column if not exists assignment_request_id uuid;
alter table public.memberships alter column end_date drop not null;
alter table public.memberships alter column paid_at drop not null;
-- Ignore only newly introduced descriptive flags in an unchanged historical payment audit.
do $$declare def text;begin
 def:=pg_get_functiondef('private.audit_membership_payment()'::regprocedure);
 if position('AUDIT_INTERNAL_FLAG_BACKFILL' in def)=0 then
  def:=replace(def,$x$- 'updated_at')$x$,$x$- 'updated_at' - 'membership_type' - 'unlimited_access' - 'has_expiration' - 'include_in_financial_stats') /* AUDIT_INTERNAL_FLAG_BACKFILL */$x$);
  execute def;
 end if;
end$$;
update public.plans set unlimited_access=(entry_limit is null) where plan_type='COMMERCIAL' and unlimited_access is distinct from (entry_limit is null);
update public.memberships m set unlimited_access=coalesce(m.entry_limit,p.entry_limit) is null
 from public.plans p where m.plan_id=p.id and m.gym_id=p.gym_id and m.membership_type='COMMERCIAL' and m.unlimited_access is distinct from (coalesce(m.entry_limit,p.entry_limit) is null);
create unique index if not exists internal_assignment_request on public.memberships(gym_id,assignment_request_id)
 where assignment_request_id is not null;
-- Replace only the installed payment-status check; preserve revision/history semantics.
do $$declare c record;begin
 for c in select conname from pg_constraint where conrelid='public.memberships'::regclass
 and contype='c' and pg_get_constraintdef(oid) like '%payment_status%' loop
 execute format('alter table public.memberships drop constraint %I',c.conname);end loop;
end$$;
alter table public.memberships add constraint membership_payment_kind_valid
 check(payment_status in ('posted','void','non_commercial') and payment_revision>=0);
alter table public.plans drop constraint if exists plan_behavior_valid;
alter table public.plans add constraint plan_behavior_valid check(
 plan_type in ('COMMERCIAL','INTERNAL') and
 (unlimited_access and entry_limit is null or not unlimited_access and entry_limit is not null) and
 (has_expiration and duration_days is not null and duration_days>0 or
  not has_expiration and duration_days is null and duration_months is null) and
 (plan_type='INTERNAL' and price=0 and not include_in_financial_stats or plan_type='COMMERCIAL' and has_expiration));
alter table public.memberships drop constraint if exists membership_behavior_valid;
alter table public.memberships add constraint membership_behavior_valid check(
 membership_type in ('COMMERCIAL','INTERNAL') and
 (has_expiration and end_date is not null or not has_expiration and end_date is null) and
 (membership_type='COMMERCIAL' and payment_status in ('posted','void') or
  membership_type='INTERNAL' and payment_status='non_commercial' and amount=0 and amount_paid=0
  and not include_in_financial_stats and paid_at is null));

create or replace function private.membership_manage_allowed(p_gym_id uuid) returns boolean
language plpgsql stable security definer set search_path='' as $$
declare owner_allowed boolean:=false;begin
 if auth.uid() is null or not exists(select 1 from public.gyms where id=p_gym_id) then return false;end if;
 if private.user_has_gym_role(p_gym_id,array['admin']) then return true;end if;
 if to_regclass('private.software_owners') is not null then
  execute 'select exists(select 1 from private.software_owners where user_id=auth.uid())' into owner_allowed;
 end if;return owner_allowed;
end$$;
revoke all on function private.membership_manage_allowed(uuid) from public,anon,authenticated;

create or replace function private.validate_plan_behavior() returns trigger
language plpgsql security definer set search_path='' as $$begin
 if new.plan_type='COMMERCIAL' then new.unlimited_access:=new.entry_limit is null;end if;
 if new.plan_type='INTERNAL' or tg_op='UPDATE' and old.plan_type='INTERNAL' then
  if auth.uid() is not null and not private.membership_manage_allowed(new.gym_id) then
   raise exception 'Solo Administración o el propietario puede administrar planes internos.' using errcode='42501';end if;
 end if;
 if tg_op='UPDATE' and (new.plan_type,new.unlimited_access,new.has_expiration)
 is distinct from (old.plan_type,old.unlimited_access,old.has_expiration)
 and exists(select 1 from public.memberships where gym_id=old.gym_id and plan_id=old.id) then
  raise exception 'Este plan ya tiene membresías. Crea otro plan para cambiar su tipo de acceso o vigencia.' using errcode='22023';end if;
 return new;
end$$;
drop trigger if exists b_validate_plan_behavior on public.plans;
create trigger b_validate_plan_behavior before insert or update on public.plans for each row execute function private.validate_plan_behavior();

create or replace function private.validate_membership_behavior() returns trigger
language plpgsql security definer set search_path='' as $$declare p public.plans;begin
 if tg_op='INSERT' then
  select * into p from public.plans where gym_id=new.gym_id and id=new.plan_id for share;
  if not found then raise exception 'El plan no pertenece al gimnasio.' using errcode='23503';end if;
  new.membership_type:=p.plan_type;new.unlimited_access:=p.unlimited_access;
  new.has_expiration:=p.has_expiration;new.include_in_financial_stats:=p.include_in_financial_stats;
 elsif (new.membership_type,new.unlimited_access,new.has_expiration,new.include_in_financial_stats,new.plan_id,new.gym_id,new.client_id,new.assignment_request_id)
 is distinct from (old.membership_type,old.unlimited_access,old.has_expiration,old.include_in_financial_stats,old.plan_id,old.gym_id,old.client_id,old.assignment_request_id) then
  raise exception 'No se puede convertir una membresía existente ni modificar su identidad o condiciones.' using errcode='22023';end if;
 if new.membership_type='INTERNAL' then
  if auth.uid() is not null and not private.membership_manage_allowed(new.gym_id) then
   raise exception 'No tienes permiso para asignar o modificar una membresía interna.' using errcode='42501';end if;
  if new.amount<>0 or new.amount_paid<>0 then raise exception 'Una membresía interna no genera cobros.';end if;
  new.payment_status:='non_commercial';new.payment_source:='INTERNAL';new.payment_method:='';
  new.payment_reference:='';new.paid_at:=null;new.include_in_financial_stats:=false;
  if not new.has_expiration then new.end_date:=null;end if;
  if new.unlimited_access then new.entry_limit:=null;new.initial_entries_used:=0;end if;
  if tg_op='INSERT' and private.freeze_active(new.gym_id,new.client_id) is not null then
   raise exception 'Reanuda la congelación vigente antes de asignar un plan interno.';end if;
 end if;return new;
end$$;
drop trigger if exists b_validate_membership_behavior on public.memberships;
create trigger b_validate_membership_behavior before insert or update on public.memberships
for each row execute function private.validate_membership_behavior();

-- Extend the existing audit trigger, rather than reporting internal assignments as sales.
do $$declare def text;branch text;begin
 def:=pg_get_functiondef('private.audit_membership_payment()'::regprocedure);
 if position('INTERNAL_MEMBERSHIP_ASSIGNED' in def)=0 then
 branch:=$code$
 if (case when tg_op='DELETE' then old.membership_type else new.membership_type end)='INTERNAL' then
  insert into public.audit_logs(gym_id,actor_user_id,actor_email,actor_role,action,entity_type,entity_id,summary,details)
  values(coalesce(new.gym_id,old.gym_id),auth.uid(),coalesce((select email from auth.users where id=auth.uid()),'Sistema'),
   case when auth.uid() is null then 'system' else coalesce((select role from public.gym_users where gym_id=coalesce(new.gym_id,old.gym_id) and user_id=auth.uid()),'owner') end,
   case when tg_op='INSERT' then 'INTERNAL_MEMBERSHIP_ASSIGNED' when tg_op='DELETE' then 'INTERNAL_MEMBERSHIP_REMOVED'
    when new.membership_active is distinct from old.membership_active then case when new.membership_active then 'INTERNAL_MEMBERSHIP_ACTIVATED' else 'INTERNAL_MEMBERSHIP_DEACTIVATED' end
    else 'INTERNAL_MEMBERSHIP_UPDATED' end,'memberships',coalesce(new.id,old.id)::text,'Membresía interna · sin operación financiera',
   jsonb_build_object('before',case when tg_op<>'INSERT' then to_jsonb(old) end,'after',case when tg_op<>'DELETE' then to_jsonb(new) end));
  if tg_op='DELETE' then return old;end if;return new;
 end if;
 $code$;
 def:=regexp_replace(def,E'(?i)\\mbegin\\M', 'begin'||branch);
 execute def;
 end if;
end$$;

create or replace function public.assign_internal_membership(p_gym_id uuid,p_client_id bigint,p_plan_id bigint,
 p_request_id uuid,p_start_date date default null,p_notes text default '')
returns table(membership_id bigint,start_date date,end_date date)
language plpgsql security definer set search_path='' as $$
declare p public.plans;m public.memberships;start_on date;begin
 if not private.membership_manage_allowed(p_gym_id) then raise exception 'La asignación de planes internos requiere Administración.' using errcode='42501';end if;
 if p_request_id is null then raise exception 'Falta la referencia de asignación.';end if;
 perform pg_advisory_xact_lock(p_client_id);
 if not exists(select 1 from public.clients where id=p_client_id and gym_id=p_gym_id and active) then raise exception 'Cliente no disponible.';end if;
 select * into m from public.memberships where gym_id=p_gym_id and assignment_request_id=p_request_id;
 if found then
  if m.client_id<>p_client_id or m.plan_id<>p_plan_id or p_start_date is not null and m.start_date<>p_start_date then raise exception 'La referencia pertenece a otra asignación.';end if;
  return query select m.id,m.start_date,m.end_date;return;
 end if;
 select * into p from public.plans where id=p_plan_id and gym_id=p_gym_id and active and plan_type='INTERNAL' for share;
 if not found then raise exception 'Selecciona un plan interno activo de este gimnasio.';end if;
 start_on:=coalesce(p_start_date,private.gym_local_date(p_gym_id));
 insert into public.memberships(gym_id,client_id,plan_id,start_date,end_date,entry_limit,amount,amount_paid,
  payment_method,notes,recorded_by,assignment_request_id)
 values(p_gym_id,p_client_id,p.id,start_on,case when p.has_expiration then private.ticket_end_date(start_on,p.duration_days,p.duration_months) end,
  case when not p.unlimited_access then p.entry_limit end,0,0,'',trim(coalesce(p_notes,'')),auth.uid(),p_request_id) returning * into m;
 update public.payment_requests set status='VOIDED' where gym_id=p_gym_id and client_id=p_client_id and status='PENDING';
 update public.marketing_messages set status='SKIPPED',error_message='INTERNAL_MEMBERSHIP',updated_at=private.gym_server_now()
 where gym_id=p_gym_id and client_id=p_client_id and status='QUEUED'
 and (payment_request_id is not null or automation_type in ('MEMBERSHIP_BEFORE','MEMBERSHIP_TODAY','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','MEMBERSHIP_RENEWED','TICKET_REMAINING','TICKET_EXPIRING','TICKET_CONSUMED','FIRST_CHECK_IN_RENEWAL','INACTIVITY','MANUAL_PAYMENT','ONLINE_APPROVED','ONLINE_DECLINED','PAYMENT_PENDING','UNUSED_PAYMENT_LINK'));
 return query select m.id,m.start_date,m.end_date;
end$$;
create or replace function public.set_internal_membership_active(p_gym_id uuid,p_membership_id bigint,p_active boolean,p_reason text)
returns jsonb language plpgsql security definer set search_path='' as $$declare m public.memberships;begin
 if not private.membership_manage_allowed(p_gym_id) then raise exception 'No tienes permiso para cambiar esta membresía.' using errcode='42501';end if;
 if p_active is null or length(trim(coalesce(p_reason,''))) not between 3 and 500 then raise exception 'Indica el motivo del cambio.';end if;
 select * into m from public.memberships where id=p_membership_id and gym_id=p_gym_id and membership_type='INTERNAL';
 if not found then raise exception 'Membresía interna no encontrada.';end if;
 perform pg_advisory_xact_lock(m.client_id);
 update public.memberships set membership_active=p_active,notes=trim(p_reason) where id=m.id and gym_id=p_gym_id and membership_active is distinct from p_active;
 return private.membership_snapshot_json(p_gym_id,m.client_id);
end$$;
-- Old clients also cannot turn an internal plan into a cash sale.
do $$begin
 if to_regprocedure('private.add_membership_before_internal(uuid,bigint,bigint,date,bigint,text,text,text)') is null then
  alter function public.add_membership_accumulating(uuid,bigint,bigint,date,bigint,text,text,text) rename to add_membership_before_internal;
  alter function public.add_membership_before_internal(uuid,bigint,bigint,date,bigint,text,text,text) set schema private;
 end if;
end$$;
create or replace function public.add_membership_accumulating(p_gym_id uuid,p_client_id bigint,p_plan_id bigint,p_requested_start date,
 p_amount bigint,p_payment_method text,p_payment_reference text default '',p_notes text default '')
returns table(membership_id bigint,start_date date,end_date date) language plpgsql security definer set search_path='' as $$begin
 if exists(select 1 from public.plans where gym_id=p_gym_id and id=p_plan_id and plan_type='INTERNAL') then
  if coalesce(p_amount,0)<>0 then raise exception 'Un plan interno no requiere pago.';end if;
  return query select * from public.assign_internal_membership(p_gym_id,p_client_id,p_plan_id,gen_random_uuid(),p_requested_start,p_notes);
 else return query select * from private.add_membership_before_internal(p_gym_id,p_client_id,p_plan_id,p_requested_start,p_amount,p_payment_method,p_payment_reference,p_notes);end if;
end$$;
revoke all on function private.add_membership_before_internal(uuid,bigint,bigint,date,bigint,text,text,text) from public,anon,authenticated;

-- Retain the installed commercial snapshot. Internal access is decided explicitly by the server.
do $$begin
 if to_regprocedure('private.membership_snapshot_before_internal(uuid,bigint)') is null then
  alter function private.membership_snapshot_json(uuid,bigint) rename to membership_snapshot_before_internal;end if;
end$$;
create or replace function private.membership_snapshot_json(p_gym_id uuid,p_client_id bigint) returns jsonb
language plpgsql security definer set search_path='' as $$
declare m public.memberships;c public.clients;p public.plans;s jsonb;used bigint:=0;today date:=private.gym_local_date(p_gym_id);allowed boolean;begin
 perform private.freeze_complete_due(p_gym_id,p_client_id);
 select * into m from public.memberships where gym_id=p_gym_id and client_id=p_client_id and membership_type='INTERNAL' and start_date<=today order by id desc limit 1;
 if m.id is null then select * into m from public.memberships where gym_id=p_gym_id and client_id=p_client_id and membership_type='INTERNAL' and start_date>today order by start_date,id desc limit 1;end if;
 if private.freeze_active(p_gym_id,p_client_id) is not null or m.id is null or m.start_date>today and exists(select 1 from public.memberships where gym_id=p_gym_id and client_id=p_client_id and membership_type='COMMERCIAL' and payment_status='posted' and start_date<=today and end_date>=today) or exists(select 1 from public.memberships where gym_id=p_gym_id and client_id=p_client_id and membership_type='COMMERCIAL' and payment_status='posted' and start_date<=today and id>m.id) then
  s:=private.membership_snapshot_before_internal(p_gym_id,p_client_id);
  return s||jsonb_build_object('membership_type','COMMERCIAL','has_expiration',true,'unlimited_access',s->>'entry_limit' is null,
   'membership_state',case when coalesce((s->>'frozen')::boolean,false) then 'FROZEN' when coalesce((s->>'allowed')::boolean,false) then 'ACTIVE' else 'INACTIVE' end);
 end if;
 select * into c from public.clients where gym_id=p_gym_id and id=p_client_id;
 if not found then raise exception 'Cliente no encontrado.';end if;
 select * into p from public.plans where gym_id=p_gym_id and id=m.plan_id;
 if not m.unlimited_access then used:=private.ticket_consumption_units(p_gym_id,m.id)+m.initial_entries_used;end if;
 allowed:=c.active and m.membership_active and today>=m.start_date and (not m.has_expiration or today<=m.end_date)
  and (m.unlimited_access or used<m.entry_limit or private.ticket_consumed_on(p_gym_id,p_client_id,m.id,today));
 return jsonb_build_object('id',c.id,'document',c.document,'first_name',c.first_name,'last_name',c.last_name,'client_name',trim(c.first_name||' '||c.last_name),
  'phone',c.phone,'email',c.email,'birthdate',coalesce(c.birthdate,c.birth_date),'biometric_identifier',c.biometric_identifier,'active',c.active,
  'membership_id',m.id,'plan_id',m.plan_id,'plan_name',p.name,'membership_type','INTERNAL','membership_active',m.membership_active,
  'has_expiration',m.has_expiration,'unlimited_access',m.unlimited_access,'include_in_financial_stats',false,
  'membership_start',m.start_date,'start_date',m.start_date,'membership_end',m.end_date,'end_date',m.end_date,
  'allowed',allowed,'status',case when allowed then 'ACTIVE' when not c.active or not m.membership_active then 'INACTIVE' when m.has_expiration and today>m.end_date then 'EXPIRED' when today<m.start_date then 'SCHEDULED' else 'SIN ENTRADAS' end,
  'entry_limit',case when not m.unlimited_access then m.entry_limit end,'entries_used',used,
  'entries_remaining',case when not m.unlimited_access then greatest(m.entry_limit-used,0) end,
  'already_consumed_today',case when m.unlimited_access then false else private.ticket_consumed_on(p_gym_id,p_client_id,m.id,today) end,'local_date',today,'frozen',false,'can_freeze',false,
  'freeze_policy',private.freeze_policy(p_gym_id,m.plan_id),'freeze_count',0);
end$$;

-- Finance keeps its existing permissions, joins, void history and date filters.
create or replace view private.financial_memberships as
 select * from public.memberships where membership_type='COMMERCIAL' and include_in_financial_stats;
revoke all on private.financial_memberships from public,anon,authenticated;
do $$declare f record;def text;begin
 for f in select p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('public','private')
 and p.proname in ('get_finance_dashboard','gymsoft_client_payments','ztattuz_client_payments','gymsoft_payment_history','ztattuz_payment_history') loop
 def:=pg_get_functiondef(f.oid);
 def:=regexp_replace(def,'(?i)from public\.memberships','from private.financial_memberships','g');execute def;
 end loop;
 -- Prevent changing an internal assignment through a payment-edit RPC.
 for f in select p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('public','private')
 and p.proname in ('gymsoft_change_payment','ztattuz_change_payment') loop
 def:=pg_get_functiondef(f.oid);
 if position('INTERNAL_PAYMENT_GUARD' in def)=0 then
  def:=regexp_replace(def,E'(?i)\\mbegin\\M',$x$begin
  -- INTERNAL_PAYMENT_GUARD
  if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then raise exception 'Sin permiso.' using errcode='42501';end if;
  if exists(select 1 from public.memberships where gym_id=p_gym_id and id=p_membership_id and membership_type='INTERNAL') then raise exception 'La membresía interna no tiene pagos que modificar.';end if;
  $x$);execute def;
 end if;end loop;
end$$;
-- Attendance remains auditable; commercial charts omit personal/internal visits.
create or replace view private.commercial_checkins as select ci.* from public.checkins ci
 where not exists(select 1 from public.memberships mi where mi.id=ci.membership_id and mi.gym_id=ci.gym_id and mi.membership_type='INTERNAL');
revoke all on private.commercial_checkins from public,anon,authenticated;
do $$declare f record;def text;begin
 for f in select p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('public','private')
 and p.proname in ('get_attendance_statistics','get_attendance_statistics_internal','session_followup') loop
  def:=pg_get_functiondef(f.oid);
  def:=regexp_replace(def,'(?i)from public\.checkins','from private.commercial_checkins','g');
  if strpos(def,'membership_type'' is distinct from ''INTERNAL')=0 then def:=replace(def,'and c.active = true','and c.active = true and private.membership_snapshot_json(p_gym_id,c.id)->>''membership_type'' is distinct from ''INTERNAL''');end if;
  execute def;
 end loop;
 -- Extend only the authorized import's explicit field lists, without editing old migrations.
 for f in select p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='private'
 and p.proname in ('gymsoft_import_insert_before_daily','ztattuz_import_insert_before_daily','owner_import_insert_before_daily') loop
  def:=pg_get_functiondef(f.oid);
  def:=replace(def,'''name'',''duration_days'',''price'',''entry_limit'',''active''',
    '''name'',''duration_days'',''price'',''entry_limit'',''active'',''plan_type'',''unlimited_access'',''has_expiration'',''include_in_financial_stats''');
  execute def;
 end loop;
end$$;
-- No billing events or payment requests for internal members; attendance still emits events.
do $$declare def text;begin
 def:=pg_get_functiondef('private.consume_daily_ticket()'::regprocedure);
 if position('INTERNAL_TICKET_GUARD' in def)=0 then
  def:=replace(def,$x$if m.payment_status<>'posted' or new.local_date not between m.start_date and m.end_date$x$,
   $x$-- INTERNAL_TICKET_GUARD
   if (m.membership_type='COMMERCIAL' and m.payment_status<>'posted') or not m.membership_active
    or new.local_date<m.start_date or (m.has_expiration and new.local_date>m.end_date)$x$);
  if position('INTERNAL_TICKET_GUARD' in def)=0 then raise exception 'No se encontró la validación actual de tiqueteras.';end if;
  execute def;
 end if;
 def:=pg_get_functiondef('private.marketing_capture_event()'::regprocedure);
 if position('INTERNAL_RENEWAL_GUARD' in def)=0 then
  def:=regexp_replace(def,E'(?i)\\mbegin\\M',$x$begin
  -- INTERNAL_RENEWAL_GUARD
  if tg_table_name='memberships' and to_jsonb(new)->>'membership_type'='INTERNAL' then return new;end if;
  $x$);execute def;
 end if;
 def:=pg_get_functiondef('public.marketing_service_payment_request(uuid,bigint,bigint,text)'::regprocedure);
 if position('INTERNAL_WOMPI_GUARD' in def)=0 then
  def:=regexp_replace(def,E'(?i)\\mbegin\\M',$x$begin
  -- INTERNAL_WOMPI_GUARD
  if exists(select 1 from public.plans where gym_id=p_gym_id and id=p_plan_id and plan_type='INTERNAL')
   or private.membership_snapshot_json(p_gym_id,p_client_id)->>'membership_type'='INTERNAL' then
    raise exception 'Los planes internos no generan enlaces ni transacciones de pago.';end if;
  $x$);execute def;
 end if;
 def:=pg_get_functiondef('public.marketing_service_apply_payment(uuid,jsonb)'::regprocedure);
 if position('INTERNAL_LATE_PAYMENT_GUARD' in def)=0 then
  def:=replace(def,$x$ if r.status='APPROVED' then$x$,$x$
 -- INTERNAL_LATE_PAYMENT_GUARD: a confirmed old charge remains visible for review, never creates staff debt/renewal.
 if private.membership_snapshot_json(p_gym_id,r.client_id)->>'membership_type'='INTERNAL' then
  update public.payment_transactions set requires_review=true where mode=v_mode and provider_transaction_id=tid;
  perform private.marketing_audit(p_gym_id,'PAYMENT_REQUIRES_REVIEW','payment_request',r.id::text,jsonb_build_object('transaction_id',tid,'reason','INTERNAL_MEMBERSHIP','status',v_status));
  return jsonb_build_object('requires_review',true,'reason','INTERNAL_MEMBERSHIP','status',v_status,'duplicate',existing.id is not null);
 end if;
 if r.status='APPROVED' then$x$);
  if position('INTERNAL_LATE_PAYMENT_GUARD' in def)=0 then raise exception 'No se encontró la función actual de confirmación de pagos.';end if;execute def;
 end if;
 -- Owner's existing editor exposes the new plan fields; membership snapshots remain immutable.
 if to_regprocedure('private.owner_editor_fields(text)') is not null then
  if to_regprocedure('private.owner_editor_fields_before_internal(text)') is null then
   alter function private.owner_editor_fields(text) rename to owner_editor_fields_before_internal;end if;
  execute $x$create or replace function private.owner_editor_fields(p_table text) returns text[] language sql immutable set search_path='' as $body$
   select case when private.owner_editor_fields_before_internal(p_table) is null then null else
    array(select v from unnest(private.owner_editor_fields_before_internal(p_table)||case when p_table='plans'
      then array['duration_months','plan_type','unlimited_access','has_expiration','include_in_financial_stats'] else array[]::text[] end)
      with ordinality f(v,pos) group by v order by min(pos)) end
  $body$ $x$;
  revoke all on function private.owner_editor_fields(text) from public,anon,authenticated;
 end if;
end$$;
-- Defense in depth: server enqueue and final send also reject internal billing.
do $$declare def text;begin
 def:=pg_get_functiondef('public.marketing_service_enqueue(uuid,uuid,bigint,text,text,text,jsonb,uuid)'::regprocedure);
 if position('INTERNAL_ENQUEUE_GUARD' in def)=0 then
  def:=replace(def,'insert into public.automation_runs(gym_id,automation_id,client_id,dedupe_key,status,reason)',
  $x$-- INTERNAL_ENQUEUE_GUARD
  if snap->>'membership_type'='INTERNAL' and (p_payment_request_id is not null or a.include_payment_link
   or a.trigger_type in ('MEMBERSHIP_BEFORE','MEMBERSHIP_TODAY','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','MEMBERSHIP_RENEWED','TICKET_REMAINING','TICKET_EXPIRING','TICKET_CONSUMED','FIRST_CHECK_IN_RENEWAL','INACTIVITY','MANUAL_PAYMENT','ONLINE_APPROVED','ONLINE_DECLINED','PAYMENT_PENDING','UNUSED_PAYMENT_LINK')) then
   v_status:='SKIPPED';reason:='INTERNAL_MEMBERSHIP';end if;
  insert into public.automation_runs(gym_id,automation_id,client_id,dedupe_key,status,reason)$x$);
  if position('INTERNAL_ENQUEUE_GUARD' in def)=0 then raise exception 'No se encontró la función actual de encolado.';end if;execute def;
 end if;
 def:=pg_get_functiondef('public.marketing_service_send_guard(bigint,uuid)'::regprocedure);
 if position('INTERNAL_SEND_GUARD' in def)=0 then
  def:=replace(def,'if m.automation_id is not null then',$x$-- INTERNAL_SEND_GUARD
   if m.payment_request_id is not null or m.automation_type in ('MEMBERSHIP_BEFORE','MEMBERSHIP_TODAY','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','MEMBERSHIP_RENEWED','TICKET_REMAINING','TICKET_EXPIRING','TICKET_CONSUMED','FIRST_CHECK_IN_RENEWAL','INACTIVITY','MANUAL_PAYMENT','ONLINE_APPROVED','ONLINE_DECLINED','PAYMENT_PENDING','UNUSED_PAYMENT_LINK') then
    snap:=private.membership_snapshot_json(m.gym_id,m.client_id);
    if snap->>'membership_type'='INTERNAL' then return '{"allowed":false,"reason":"INTERNAL_MEMBERSHIP"}';end if;end if;
   if m.automation_id is not null then$x$);
  if position('INTERNAL_SEND_GUARD' in def)=0 then raise exception 'No se encontró la validación actual de envío.';end if;execute def;
 end if;
end$$;
create or replace function public.save_membership_plan(p_gym_id uuid,p_data jsonb,p_plan_id bigint default null,p_reason text default '') returns jsonb
language plpgsql security definer set search_path='' as $$declare p public.plans;k text;begin
 if not private.membership_manage_allowed(p_gym_id) then raise exception 'No tienes permiso para administrar planes.' using errcode='42501';end if;
 if length(trim(coalesce(p_reason,''))) not between 3 and 500 then raise exception 'Indica el motivo del cambio.';end if;
 for k in select jsonb_object_keys(p_data) loop
  if k not in ('name','duration_days','duration_months','price','entry_limit','active','plan_type','unlimited_access','has_expiration','include_in_financial_stats') then
   raise exception 'Campo no editable: %',k;end if;end loop;
 if p_plan_id is null then
  insert into public.plans(gym_id,name,duration_days,duration_months,price,entry_limit,active,plan_type,unlimited_access,has_expiration,include_in_financial_stats)
  values(p_gym_id,trim(p_data->>'name'),(p_data->>'duration_days')::integer,(p_data->>'duration_months')::integer,
   coalesce((p_data->>'price')::bigint,0),(p_data->>'entry_limit')::integer,coalesce((p_data->>'active')::boolean,true),
   coalesce(p_data->>'plan_type','COMMERCIAL'),coalesce((p_data->>'unlimited_access')::boolean,p_data->>'entry_limit' is null),
   coalesce((p_data->>'has_expiration')::boolean,true),coalesce((p_data->>'include_in_financial_stats')::boolean,true)) returning * into p;
 else
  select * into p from public.plans where gym_id=p_gym_id and id=p_plan_id for update;
  if not found then raise exception 'Plan no encontrado.';end if;
  p:=jsonb_populate_record(p,p_data);
  update public.plans set name=p.name,duration_days=p.duration_days,duration_months=p.duration_months,price=p.price,entry_limit=p.entry_limit,
   active=p.active,plan_type=p.plan_type,unlimited_access=p.unlimited_access,has_expiration=p.has_expiration,include_in_financial_stats=p.include_in_financial_stats
  where gym_id=p_gym_id and id=p_plan_id returning * into p;
 end if;
 insert into public.audit_logs(gym_id,actor_user_id,action,entity_type,entity_id,summary,details)
 values(p_gym_id,auth.uid(),case when p.plan_type='INTERNAL' then case when p_plan_id is null then 'INTERNAL_PLAN_CREATED' else 'INTERNAL_PLAN_UPDATED' end
 else 'PLAN_SAVED' end,'plans',p.id::text,'Plan: '||p.name,jsonb_build_object('plan',to_jsonb(p),'reason',trim(p_reason)));
 return to_jsonb(p);
end$$;
create or replace function public.membership_population(p_gym_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare c record;s jsonb;rows jsonb:='[]';groups jsonb:='{"expired":[],"days_0_7":[],"days_8_15":[],"days_16_30":[],"days_31_plus":[],"internal":[],"frozen":[]}';
 bucket text;remaining integer;valid_count integer:=0;internal_count integer:=0;expired_count integer:=0;begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then raise exception 'No tienes permiso para consultar este gimnasio.' using errcode='42501';end if;
 for c in select * from public.clients where gym_id=p_gym_id and active order by id loop
  s:=private.membership_snapshot_json(p_gym_id,c.id);
  if s->>'membership_type'='INTERNAL' then
   bucket:='internal';remaining:=null;
   if (s->>'allowed')::boolean then internal_count:=internal_count+1;end if;
  elsif coalesce((s->>'frozen')::boolean,false) then bucket:='frozen';remaining:=null;
  else
   remaining:=nullif(s->>'membership_end','')::date-private.gym_local_date(p_gym_id);
   if coalesce((s->>'allowed')::boolean,false) then valid_count:=valid_count+1;end if;
   if remaining is null or remaining<0 then bucket:='expired';expired_count:=expired_count+1;
   elsif remaining<=7 then bucket:='days_0_7';elsif remaining<=15 then bucket:='days_8_15';elsif remaining<=30 then bucket:='days_16_30';else bucket:='days_31_plus';end if;
  end if;
  s:=s||jsonb_build_object('id',c.id,'client_id',c.id,'client_name',trim(c.first_name||' '||c.last_name),'days_remaining',remaining,'end_date',s->'membership_end');
  rows:=rows||jsonb_build_array(s);groups:=jsonb_set(groups,array[bucket],(groups->bucket)||jsonb_build_array(s));
 end loop;
 return jsonb_build_object('clients',rows,'groups',groups,'metrics',jsonb_build_object('active_clients',jsonb_array_length(rows)-jsonb_array_length(groups->'internal'),
 'valid_memberships',valid_count,'expired_memberships',expired_count,'internal_memberships',internal_count,
 'staff_checkins_today',(select count(*) from public.checkins ci join public.memberships mi on mi.id=ci.membership_id and mi.gym_id=ci.gym_id where ci.gym_id=p_gym_id and mi.membership_type='INTERNAL' and ci.result='PERMITIDA' and ci.local_date=private.gym_local_date(p_gym_id)),
 'checkins_today',(select count(*) from public.checkins ci where ci.gym_id=p_gym_id and ci.result='PERMITIDA' and ci.local_date=private.gym_local_date(p_gym_id) and not exists(select 1 from public.memberships mi where mi.id=ci.membership_id and mi.gym_id=ci.gym_id and mi.membership_type='INTERNAL')),'income_month',0));
end$$;
revoke all on function public.save_membership_plan(uuid,jsonb,bigint,text),public.membership_population(uuid) from public,anon;
grant execute on function public.save_membership_plan(uuid,jsonb,bigint,text),public.membership_population(uuid) to authenticated;
revoke all on function private.membership_snapshot_json(uuid,bigint),private.validate_plan_behavior(),private.validate_membership_behavior() from public,anon,authenticated;
revoke all on function public.assign_internal_membership(uuid,bigint,bigint,uuid,date,text),public.set_internal_membership_active(uuid,bigint,boolean,text),public.add_membership_accumulating(uuid,bigint,bigint,date,bigint,text,text,text) from public,anon;
grant execute on function public.assign_internal_membership(uuid,bigint,bigint,uuid,date,text),public.set_internal_membership_active(uuid,bigint,boolean,text),public.add_membership_accumulating(uuid,bigint,bigint,date,bigint,text,text,text) to authenticated;
notify pgrst,'reload schema';
-- FIN FUENTE internal_plans.sql

-- INICIO FUENTE early_resume.sql
-- Seven days is a ceiling. New freezes extend dates only when closed.
-- Old events retain their original fields and pre-applied extension semantics.
set local lock_timeout='8s';
set local statement_timeout='90s';
alter table public.membership_freezes
 add column if not exists calculation_version text not null default 'LEGACY_PREAPPLIED',
 add column if not exists freeze_max_days integer,
 add column if not exists freeze_used_days integer,
 add column if not exists resumed_at timestamptz,
 add column if not exists resumed_by uuid,
 add column if not exists completion_kind text,
 add column if not exists resume_reason text;
update public.membership_freezes set freeze_max_days=days_added where freeze_max_days is null;
-- Populate new descriptive fields without altering a historical event or its dates.
update public.membership_freezes set freeze_used_days=days_added-days_reversed,
 resumed_at=coalesce(cancelled_at,completed_at),resumed_by=cancelled_by,
 completion_kind=case when status='CANCELLED' then 'MANUAL' else 'AUTOMATIC' end
 where calculation_version='LEGACY_PREAPPLIED' and freeze_used_days is null and status in ('COMPLETED','CANCELLED');
alter table public.membership_freezes drop constraint if exists membership_freezes_days_added_check;
alter table public.membership_freezes drop constraint if exists membership_freezes_check1;
alter table public.membership_freezes drop constraint if exists membership_freezes_status_check;
alter table public.membership_freezes drop constraint if exists freeze_actual_duration_valid;
alter table public.membership_freezes add constraint freeze_actual_duration_valid check(
 calculation_version in ('LEGACY_PREAPPLIED','ACTUAL_DURATION_V1') and days_added between 0 and 365
 and freeze_max_days between 1 and 365 and (freeze_used_days is null or freeze_used_days between 0 and freeze_max_days)
 and status in ('SCHEDULED','ACTIVE','COMPLETED','CANCELLED','RESUMED')
 and (calculation_version='LEGACY_PREAPPLIED' or freeze_max_days<=7));
alter table public.membership_freezes alter column calculation_version set default 'ACTUAL_DURATION_V1';
-- Existing nonstandard historical events keep their agreed ceiling; new policies cannot exceed seven.
update public.membership_freeze_policies set duration_days=least(duration_days,7);
alter table public.membership_freeze_policies drop constraint if exists membership_freeze_policies_duration_days_check;
alter table public.membership_freeze_policies drop constraint if exists freeze_policy_seven_day_ceiling;
alter table public.membership_freeze_policies add constraint freeze_policy_seven_day_ceiling check(duration_days between 1 and 7);
update public.membership_freeze_policies set max_per_membership=1 where max_per_membership<>1;
alter table public.membership_freeze_policies drop constraint if exists membership_freeze_policies_max_per_membership_check;
alter table public.membership_freeze_policies drop constraint if exists freeze_policy_one_per_membership;
alter table public.membership_freeze_policies add constraint freeze_policy_one_per_membership check(max_per_membership=1);

-- Freeze dates are membership adjustments, not corrections to a monetary payment.
create table if not exists private.freeze_adjustment_context(transaction_id bigint primary key,gym_id uuid not null);
alter table private.freeze_adjustment_context enable row level security;
revoke all on private.freeze_adjustment_context from public,anon,authenticated;
do $$declare def text;begin
 def:=pg_get_functiondef('private.audit_membership_payment()'::regprocedure);
 if position('FREEZE_NONFINANCIAL_AUDIT' in def)=0 then
  def:=regexp_replace(def,E'(?i)\\mbegin\\M',$x$begin
  -- FREEZE_NONFINANCIAL_AUDIT: the closing helper writes its own complete event history.
  if tg_op='UPDATE' and exists(select 1 from private.freeze_adjustment_context where transaction_id=txid_current() and gym_id=new.gym_id)
   and (new.amount,new.amount_paid,new.payment_status,new.payment_revision) is not distinct from (old.amount,old.amount_paid,old.payment_status,old.payment_revision) then return new;end if;
  $x$);execute def;
 end if;
 def:=pg_get_functiondef('public.membership_save_freeze_policy(uuid,boolean,integer,integer,bigint)'::regprocedure);
 def:=replace(def,'not private.user_has_gym_role(p_gym_id,array[''admin''])','not private.membership_manage_allowed(p_gym_id)');execute def;
end$$;

create or replace function private.freeze_used_days(p_freeze public.membership_freezes,p_at timestamptz) returns integer
language sql stable set search_path='' as $$
 select least(p_freeze.freeze_max_days,greatest(0,floor(extract(epoch from
 (least(p_at,p_freeze.ends_at)-p_freeze.starts_at))/86400)::integer))
$$;
create or replace function private.freeze_event_json(p_freeze public.membership_freezes,p_at timestamptz) returns jsonb
language sql stable set search_path='' as $$
 select to_jsonb(p_freeze)||jsonb_build_object('freeze_started_at',p_freeze.starts_at,'freeze_resumed_at',p_freeze.resumed_at,
  'freeze_used_days',coalesce(p_freeze.freeze_used_days,private.freeze_used_days(p_freeze,p_at)),
  'freeze_remaining_days',greatest(0,p_freeze.freeze_max_days-coalesce(p_freeze.freeze_used_days,private.freeze_used_days(p_freeze,p_at))),
  'server_now',p_at)
$$;
create or replace function private.freeze_active(p_gym_id uuid,p_client_id bigint) returns jsonb
language sql stable security definer set search_path='' as $$
 select private.freeze_event_json(f,private.gym_server_now()) from public.membership_freezes f
 where gym_id=p_gym_id and client_id=p_client_id and status in ('SCHEDULED','ACTIVE')
 and private.gym_server_now()>=starts_at and private.gym_server_now()<ends_at order by starts_at,id limit 1
$$;
create or replace function private.freeze_invalidate_messages(p_gym_id uuid,p_client_id bigint) returns void
language sql security definer set search_path='' as $$
 update public.marketing_messages set status='SKIPPED',error_message='MEMBERSHIP_CHANGED',updated_at=private.gym_server_now()
 where gym_id=p_gym_id and client_id=p_client_id and status='QUEUED'
 and automation_type in ('MEMBERSHIP_BEFORE','MEMBERSHIP_TODAY','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','TICKET_EXPIRING','TICKET_REMAINING','INACTIVITY')
$$;
create or replace function private.freeze_close(p_gym_id uuid,p_freeze_id uuid,p_kind text,p_reason text default '') returns jsonb
language plpgsql security definer set search_path='' as $$
declare f public.membership_freezes;m public.memberships;at_time timestamptz;used integer;delta integer;actor uuid;begin
 select * into f from public.membership_freezes where id=p_freeze_id and gym_id=p_gym_id;
 if not found then raise exception 'Congelación no encontrada.';end if;
 perform pg_advisory_xact_lock(f.client_id);
 select * into f from public.membership_freezes where id=p_freeze_id and gym_id=p_gym_id for update;
 if f.status not in ('ACTIVE','SCHEDULED') then
  return private.freeze_event_json(f,private.gym_server_now())||jsonb_build_object('duplicate',true,'new_end_date',f.extended_end_date);end if;
 if p_kind not in ('MANUAL','AUTOMATIC') then raise exception 'Modo de reanudación inválido.';end if;
 if p_kind='AUTOMATIC' and private.gym_server_now()<f.ends_at then raise exception 'No se ha alcanzado el máximo de congelación.';end if;
 at_time:=least(private.gym_server_now(),f.ends_at);
 used:=private.freeze_used_days(f,at_time);
 -- Completion is capped at the deadline, even if the scheduler runs days late.
 if private.gym_server_now()>=f.ends_at then p_kind:='AUTOMATIC';used:=f.freeze_max_days;at_time:=f.ends_at;end if;
 actor:=case when p_kind='MANUAL' then auth.uid() end;
 select * into m from public.memberships where gym_id=p_gym_id and id=f.membership_id for update;
 if not m.has_expiration or m.membership_type='INTERNAL' then raise exception 'Esta membresía no admite congelación.';end if;
 delta:=case when f.calculation_version='LEGACY_PREAPPLIED' then used-(f.days_added-f.days_reversed) else used end;
 insert into private.freeze_adjustment_context values(txid_current(),p_gym_id) on conflict do nothing;
 -- Shift already purchased future commercial cycles by the actual extension, once.
 update public.memberships set start_date=start_date+delta,end_date=end_date+delta
 where gym_id=p_gym_id and client_id=f.client_id and id<>m.id and payment_status='posted' and has_expiration and start_date>m.end_date;
 update public.memberships set end_date=end_date+delta where gym_id=p_gym_id and id=m.id;
 delete from private.freeze_adjustment_context where transaction_id=txid_current() and gym_id=p_gym_id;
 update public.membership_freezes set status=case when p_kind='MANUAL' then 'RESUMED' else 'COMPLETED' end,
  freeze_used_days=used,resumed_at=at_time,resumed_by=actor,completion_kind=p_kind,resume_reason=trim(coalesce(p_reason,'')),
  days_added=case when calculation_version='ACTUAL_DURATION_V1' then used else days_added end,
  days_reversed=case when calculation_version='LEGACY_PREAPPLIED' then days_added-used else 0 end,
  extended_end_date=m.end_date+delta,completed_at=case when p_kind='AUTOMATIC' then private.gym_server_now() else completed_at end
 where gym_id=p_gym_id and id=f.id returning * into f;
 perform private.freeze_invalidate_messages(p_gym_id,f.client_id);
 insert into public.audit_logs(gym_id,actor_user_id,action,entity_type,entity_id,summary,details)
 values(p_gym_id,actor,case when p_kind='MANUAL' then 'MEMBERSHIP_FREEZE_RESUMED' else 'MEMBERSHIP_FREEZE_COMPLETED' end,
 'memberships',m.id::text,'Membresía reanudada · '||used||' días utilizados',private.freeze_event_json(f,private.gym_server_now()));
 return private.freeze_event_json(f,private.gym_server_now())||jsonb_build_object('duplicate',false,'new_end_date',f.extended_end_date);
end$$;
create or replace function private.freeze_complete_due(p_gym_id uuid default null,p_client_id bigint default null) returns integer
language plpgsql security definer set search_path='' as $$declare f record;r jsonb;n integer:=0;begin
 for f in select id,gym_id,client_id from public.membership_freezes where status in ('ACTIVE','SCHEDULED')
 and (p_gym_id is null or gym_id=p_gym_id) and (p_client_id is null or client_id=p_client_id)
 and ends_at<=private.gym_server_now() order by client_id,id loop
  r:=private.freeze_close(f.gym_id,f.id,'AUTOMATIC');
  if not (r->>'duplicate')::boolean then n:=n+1;end if;
 end loop;return n;
end$$;

create or replace function public.membership_freeze(p_gym_id uuid,p_membership_id bigint,p_request_id uuid,
 p_reason text default '',p_override boolean default false) returns jsonb
language plpgsql security definer set search_path='' as $$
declare m public.memberships;f public.membership_freezes;s jsonb;policy jsonb;days integer;used integer;at_time timestamptz;zone text;begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) and not private.membership_manage_allowed(p_gym_id)
 or p_override and not private.membership_manage_allowed(p_gym_id) then
  raise exception 'No tienes permiso para congelar esta membresía.' using errcode='42501';end if;
 if p_request_id is null or length(coalesce(p_reason,''))>500 or p_override and length(trim(coalesce(p_reason,'')))<3 then
  raise exception 'La excepción administrativa requiere un motivo y una referencia válida.';end if;
 select * into m from public.memberships where gym_id=p_gym_id and id=p_membership_id;
 if not found then raise exception 'La membresía no pertenece al gimnasio.';end if;
 perform pg_advisory_xact_lock(m.client_id);
 perform private.freeze_complete_due(p_gym_id,m.client_id);
 select * into m from public.memberships where gym_id=p_gym_id and id=p_membership_id for update;
 select * into f from public.membership_freezes where gym_id=p_gym_id and request_id=p_request_id;
 if found then
  if f.membership_id<>m.id then raise exception 'La referencia corresponde a otra membresía.';end if;
  return private.freeze_event_json(f,private.gym_server_now())||jsonb_build_object('duplicate',true,'new_end_date',m.end_date);end if;
 if not m.has_expiration or m.membership_type='INTERNAL' then raise exception 'Los planes internos o indefinidos no utilizan congelación.';end if;
 s:=private.membership_snapshot_json(p_gym_id,m.client_id);
 if coalesce((s->>'frozen')::boolean,false) then raise exception 'El cliente ya tiene una congelación activa.';end if;
 if m.payment_status<>'posted' or not coalesce((s->>'allowed')::boolean,false)
 or (s->>'membership_id')::bigint is distinct from m.id then raise exception 'Solo se puede congelar una membresía activa con tiempo y saldo disponibles.';end if;
 policy:=private.freeze_policy(p_gym_id,m.plan_id);days:=least(7,(policy->>'duration_days')::integer);
 select count(*) into used from public.membership_freezes where gym_id=p_gym_id and membership_id=m.id;
 if not p_override and (not (policy->>'enabled')::boolean or used>=(policy->>'max_per_membership')::integer) then
  raise exception 'Esta membresía alcanzó el máximo de congelaciones o su plan no lo permite.';end if;
 at_time:=private.gym_server_now();zone:=private.gym_timezone(p_gym_id);
 insert into public.membership_freezes(gym_id,client_id,membership_id,start_date,resume_date,timezone,starts_at,ends_at,
  days_added,original_end_date,extended_end_date,status,reason,created_by,created_at,request_id,administrative_override,freeze_max_days,calculation_version)
 values(p_gym_id,m.client_id,m.id,(at_time at time zone zone)::date,((at_time+days*interval '24 hours') at time zone zone)::date,zone,
  at_time,at_time+days*interval '24 hours',0,m.end_date,m.end_date,'ACTIVE',trim(coalesce(p_reason,'')),auth.uid(),at_time,p_request_id,p_override,days,'ACTUAL_DURATION_V1') returning * into f;
 perform private.freeze_invalidate_messages(p_gym_id,m.client_id);
 insert into public.audit_logs(gym_id,actor_user_id,action,entity_type,entity_id,summary,details)
 values(p_gym_id,auth.uid(),'MEMBERSHIP_FROZEN','memberships',m.id::text,'Membresía congelada · máximo '||days||' días',to_jsonb(f));
 return private.freeze_event_json(f,at_time)||jsonb_build_object('duplicate',false,'new_end_date',m.end_date);
end$$;

create or replace function public.membership_resume_preview(p_gym_id uuid,p_freeze_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$declare f public.membership_freezes;used integer;begin
 if not private.membership_manage_allowed(p_gym_id) then raise exception 'No tienes permiso para reanudar esta membresía.' using errcode='42501';end if;
 select * into f from public.membership_freezes where gym_id=p_gym_id and id=p_freeze_id;
 if not found then raise exception 'Congelación no encontrada.';end if;
 used:=coalesce(f.freeze_used_days,private.freeze_used_days(f,private.gym_server_now()));
 return private.freeze_event_json(f,private.gym_server_now())||jsonb_build_object('extension_days',used,
 'new_end_date',f.original_end_date+used,'can_resume',f.status in ('ACTIVE','SCHEDULED'));
end$$;
create or replace function public.membership_resume_freeze(p_gym_id uuid,p_freeze_id uuid,p_expected_days integer,p_reason text default '') returns jsonb
language plpgsql security definer set search_path='' as $$declare f public.membership_freezes;used integer;begin
 if not private.membership_manage_allowed(p_gym_id) then raise exception 'No tienes permiso para reanudar esta membresía.' using errcode='42501';end if;
 select * into f from public.membership_freezes where gym_id=p_gym_id and id=p_freeze_id;
 if not found then raise exception 'Congelación no encontrada.';end if;
 perform pg_advisory_xact_lock(f.client_id);
 select * into f from public.membership_freezes where gym_id=p_gym_id and id=p_freeze_id for update;
 used:=coalesce(f.freeze_used_days,private.freeze_used_days(f,private.gym_server_now()));
 if f.status in ('ACTIVE','SCHEDULED') and used is distinct from p_expected_days then
  raise exception 'La duración cambió. Actualiza la confirmación antes de reanudar.' using errcode='40001';end if;
 return private.freeze_close(p_gym_id,p_freeze_id,'MANUAL',p_reason);
end$$;
-- Compatibility endpoint: old clients may still request cancellation, using the same closing operation.
create or replace function public.membership_cancel_freeze(p_gym_id uuid,p_freeze_id uuid,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$declare preview jsonb;begin
 if length(trim(coalesce(p_reason,''))) not between 3 and 500 then raise exception 'Indica el motivo de reanudación.';end if;
 preview:=public.membership_resume_preview(p_gym_id,p_freeze_id);
 return public.membership_resume_freeze(p_gym_id,p_freeze_id,(preview->>'extension_days')::integer,p_reason);
end$$;

-- The internal wrapper delegates commercial access to this updated freeze wrapper.
create or replace function private.membership_snapshot_before_internal(p_gym_id uuid,p_client_id bigint) returns jsonb
language plpgsql security definer set search_path='' as $$
declare s jsonb;f jsonb;m public.memberships;policy jsonb;used integer;eligible boolean;begin
 perform private.freeze_complete_due(p_gym_id,p_client_id);
 s:=private.membership_snapshot_before_freezes(p_gym_id,p_client_id);f:=private.freeze_active(p_gym_id,p_client_id);
 if f is not null then
  select * into m from public.memberships where gym_id=p_gym_id and id=(f->>'membership_id')::bigint;
  return s||jsonb_build_object('status','FROZEN','frozen',true,'allowed',false,'freeze',f,'membership_state','FROZEN',
  'membership_id',m.id,'membership_end',m.end_date,'end_date',m.end_date,'plan_id',m.plan_id,
  'freeze_last_date',(f->>'resume_date')::date-1,'resume_date',f->>'resume_date','can_freeze',false,
  'freeze_policy',private.freeze_policy(p_gym_id,m.plan_id),'denial_code','CHECK_IN_DENIED_MEMBERSHIP_FROZEN',
  'denial_message','Membresía congelada. Reanudación máxima: '||to_char((f->>'ends_at')::timestamptz at time zone (f->>'timezone'),'DD/MM/YYYY HH24:MI')||'.');
 end if;
 select * into m from public.memberships where gym_id=p_gym_id and id=(s->>'membership_id')::bigint;
 policy:=private.freeze_policy(p_gym_id,m.plan_id);
 select count(*) into used from public.membership_freezes where gym_id=p_gym_id and membership_id=m.id;
 eligible:=coalesce((s->>'allowed')::boolean,false) and coalesce((policy->>'enabled')::boolean,false)
 and used<(policy->>'max_per_membership')::integer and m.payment_status='posted' and m.has_expiration and m.membership_type='COMMERCIAL';
 return s||jsonb_build_object('frozen',false,'end_date',s->>'membership_end','start_date',s->>'membership_start',
 'plan_id',m.plan_id,'can_freeze',coalesce(eligible,false),'freeze_policy',policy,'freeze_count',used);
end$$;
create or replace function public.membership_freeze_info(p_gym_id uuid,p_client_id bigint) returns jsonb
language plpgsql security definer set search_path='' as $$declare s jsonb;begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) and not private.membership_manage_allowed(p_gym_id) then
  raise exception 'No tienes permiso para consultar este cliente.' using errcode='42501';end if;
 perform private.freeze_complete_due(p_gym_id,p_client_id);s:=private.membership_snapshot_json(p_gym_id,p_client_id);
 return jsonb_build_object('membership',s,'policy',coalesce(s->'freeze_policy',private.freeze_policy(p_gym_id,null)),
 'permissions',jsonb_build_object('can_resume',private.membership_manage_allowed(p_gym_id),'can_manage_internal',private.membership_manage_allowed(p_gym_id)),
 'history',(select coalesce(jsonb_agg(private.freeze_event_json(f,private.gym_server_now()) order by created_at desc),'[]') from public.membership_freezes f where gym_id=p_gym_id and client_id=p_client_id));
end$$;
-- A deactivated internal membership cannot be bypassed by a manual-access override or stale client.
create or replace function private.freeze_checkin_guard() returns trigger
language plpgsql security definer set search_path='' as $$declare s jsonb;begin
 if exists(select 1 from private.ticket_import_context where transaction_id=txid_current() and gym_id=new.gym_id) then return new;end if;
 perform pg_advisory_xact_lock(new.client_id);perform private.freeze_complete_due(new.gym_id,new.client_id);
 s:=private.membership_snapshot_json(new.gym_id,new.client_id);
 if coalesce((s->>'frozen')::boolean,false) then new.membership_id:=(s->>'membership_id')::bigint;new.result:='DENEGADA';new.notes:='CHECK_IN_DENIED_MEMBERSHIP_FROZEN';
 elsif s->>'membership_type'='INTERNAL' then new.membership_id:=(s->>'membership_id')::bigint; if not coalesce((s->>'allowed')::boolean,false) then new.result:='DENEGADA';new.notes:='INTERNAL_MEMBERSHIP_INACTIVE';end if;end if;
 return new;
end$$;
-- Preserve the new and legacy event fields when restoring an authorized backup.
create or replace function private.restore_freeze_archive() returns trigger
language plpgsql security definer set search_path='' as $$declare x jsonb;f public.membership_freezes;begin
 if new.freeze_archive is null then return new;end if;
 if jsonb_typeof(new.freeze_archive)<>'array' or jsonb_array_length(new.freeze_archive)>100 then raise exception 'Historial de congelaciones no válido.';end if;
 for x in select value from jsonb_array_elements(new.freeze_archive) loop
  f:=jsonb_populate_record(null::public.membership_freezes,x);
  f.id:=gen_random_uuid();f.gym_id:=new.gym_id;f.client_id:=new.client_id;f.membership_id:=new.id;
  f.calculation_version:=coalesce(f.calculation_version,'LEGACY_PREAPPLIED');
  f.freeze_max_days:=coalesce(f.freeze_max_days,f.days_added);
  f.days_reversed:=coalesce(f.days_reversed,0);f.reason:=coalesce(f.reason,'');f.administrative_override:=coalesce(f.administrative_override,false);
  if f.freeze_used_days is null and f.status in ('COMPLETED','CANCELLED','RESUMED') then f.freeze_used_days:=f.days_added-f.days_reversed;end if;
  insert into public.membership_freezes select (f).*;
 end loop;return new;
end$$;
revoke all on function private.freeze_used_days(public.membership_freezes,timestamptz),private.freeze_event_json(public.membership_freezes,timestamptz),
 private.freeze_close(uuid,uuid,text,text),private.freeze_invalidate_messages(uuid,bigint) from public,anon,authenticated;
revoke all on function public.membership_resume_preview(uuid,uuid),public.membership_resume_freeze(uuid,uuid,integer,text) from public,anon;
grant execute on function public.membership_resume_preview(uuid,uuid),public.membership_resume_freeze(uuid,uuid,integer,text) to authenticated;
notify pgrst,'reload schema';
-- FIN FUENTE early_resume.sql

commit;
