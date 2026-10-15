-- Additive upgrade. Historical sales stay commercial; internal assignments are not payments.
begin;
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
commit;
