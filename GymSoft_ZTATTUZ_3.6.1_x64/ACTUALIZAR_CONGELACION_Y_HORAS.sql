-- Calendar freezes use [start_date, resume_date); access is date-driven, never PC-driven.
begin;
set local lock_timeout='8s';
set local statement_timeout='90s';
create table if not exists public.membership_freeze_policies (
 id uuid primary key default gen_random_uuid(),
 gym_id uuid not null references public.gyms(id) on delete cascade,
 plan_id bigint references public.plans(id) on delete cascade,
 enabled boolean not null default true,
 duration_days integer not null default 7 check(duration_days between 1 and 365),
 max_per_membership integer not null default 1 check(max_per_membership between 1 and 10),
 updated_by uuid,updated_at timestamptz not null default now()
);
create unique index if not exists freeze_gym_policy on public.membership_freeze_policies(gym_id) where plan_id is null;
create unique index if not exists freeze_plan_policy on public.membership_freeze_policies(gym_id,plan_id) where plan_id is not null;
insert into public.membership_freeze_policies(gym_id) select id from public.gyms on conflict do nothing;
create table if not exists public.membership_freezes (
 id uuid primary key default gen_random_uuid(),
 gym_id uuid not null references public.gyms(id) on delete cascade,
 client_id bigint not null references public.clients(id) on delete cascade,
 membership_id bigint not null references public.memberships(id) on delete cascade,
 start_date date not null,resume_date date not null,timezone text not null,
 starts_at timestamptz not null,ends_at timestamptz not null,
 days_added integer not null check(days_added between 1 and 365),
 days_reversed integer not null default 0 check(days_reversed>=0 and days_reversed<=days_added),
 original_end_date date not null,extended_end_date date not null,
 status text not null check(status in ('SCHEDULED','ACTIVE','COMPLETED','CANCELLED')),
 reason text not null default '',created_by uuid,created_at timestamptz not null default clock_timestamp(),
 completed_at timestamptz,cancelled_at timestamptz,cancelled_by uuid,cancellation_reason text,
 administrative_override boolean not null default false,
 request_id uuid not null,unique(gym_id,request_id),
 check(resume_date=start_date+days_added),check(ends_at>starts_at)
);
create index if not exists freezes_member on public.membership_freezes(gym_id,membership_id);
create index if not exists freezes_client on public.membership_freezes(gym_id,client_id,start_date,resume_date);
create index if not exists freezes_due on public.membership_freezes(ends_at) where status in ('ACTIVE','SCHEDULED');
create unique index if not exists freezes_one_live_client on public.membership_freezes(gym_id,client_id) where status in ('ACTIVE','SCHEDULED');
-- Only the verified RPCs mutate freeze state. Staff can read only their gym.
do $$declare t text;begin
 foreach t in array array['membership_freeze_policies','membership_freezes'] loop
 execute format('alter table public.%I enable row level security',t);
 execute format('revoke all on public.%I from public,anon,authenticated',t);
 execute format('grant select on public.%I to authenticated',t);
 execute format('drop policy if exists freeze_staff_read on public.%I',t);
 execute format('create policy freeze_staff_read on public.%I for select to authenticated using(private.user_has_gym_role(gym_id,array[''admin'',''receptionist'']))',t);
 end loop;
end$$;
-- Changing a gym calendar in the middle of a freeze would change its agreed days.
create or replace function private.validate_gym_timezone() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from pg_catalog.pg_timezone_names where name=new.timezone) then
 raise exception 'Selecciona una zona horaria IANA válida.' using errcode='22023';end if;
 if tg_op='UPDATE' and new.timezone is distinct from old.timezone
 and exists(select 1 from public.membership_freezes where gym_id=new.id and status in ('SCHEDULED','ACTIVE') and ends_at>private.gym_server_now()) then
 raise exception 'Finaliza las congelaciones vigentes antes de cambiar la zona horaria del gimnasio.';end if;
 return new;
end$$;
create or replace function private.freeze_policy(p_gym_id uuid,p_plan_id bigint) returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce((select to_jsonb(p) from public.membership_freeze_policies p
 where gym_id=p_gym_id and (plan_id=p_plan_id or plan_id is null)
 order by plan_id nulls last limit 1),' {"enabled":true,"duration_days":7,"max_per_membership":1}'::jsonb)
$$;
create or replace function public.membership_freeze_policy(p_gym_id uuid,p_plan_id bigint default null) returns jsonb
language plpgsql stable security definer set search_path='' as $$
begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
 raise exception 'No tienes permiso para consultar congelaciones.' using errcode='42501';end if;
 if p_plan_id is not null and not exists(select 1 from public.plans where id=p_plan_id and gym_id=p_gym_id) then
 raise exception 'El plan no pertenece al gimnasio.';end if;
 return private.freeze_policy(p_gym_id,p_plan_id);
end$$;
create or replace function public.membership_save_freeze_policy(p_gym_id uuid,p_enabled boolean,
 p_duration_days integer,p_max_per_membership integer,p_plan_id bigint default null) returns jsonb
language plpgsql security definer set search_path='' as $$
declare r public.membership_freeze_policies;begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin']) then
 raise exception 'La política de congelación es exclusiva de Administración.' using errcode='42501';end if;
 if p_plan_id is not null and not exists(select 1 from public.plans where id=p_plan_id and gym_id=p_gym_id) then
 raise exception 'El plan no pertenece al gimnasio.';end if;
 perform pg_advisory_xact_lock(hashtextextended(p_gym_id::text||'/freeze-policy',0));
 select * into r from public.membership_freeze_policies where gym_id=p_gym_id and plan_id is not distinct from p_plan_id for update;
 if found then update public.membership_freeze_policies set enabled=p_enabled,duration_days=p_duration_days,
 max_per_membership=p_max_per_membership,updated_by=auth.uid(),updated_at=clock_timestamp() where id=r.id returning * into r;
 else insert into public.membership_freeze_policies(gym_id,plan_id,enabled,duration_days,max_per_membership,updated_by)
 values(p_gym_id,p_plan_id,p_enabled,p_duration_days,p_max_per_membership,auth.uid()) returning * into r;end if;
 insert into public.audit_logs(gym_id,action,entity_type,entity_id,summary,details)
 values(p_gym_id,'MEMBERSHIP_FREEZE_POLICY_CHANGED','plans',coalesce(p_plan_id::text,'gym'),
 'Política de congelación actualizada',to_jsonb(r));return to_jsonb(r);
end$$;
create or replace function private.freeze_active(p_gym_id uuid,p_client_id bigint) returns jsonb
language sql stable security definer set search_path='' as $$
 select to_jsonb(f) from public.membership_freezes f
 where gym_id=p_gym_id and client_id=p_client_id and status in ('SCHEDULED','ACTIVE')
 and private.gym_local_date(p_gym_id)>=start_date and private.gym_local_date(p_gym_id)<resume_date
 order by start_date,id limit 1
$$;
-- Keep the existing ticket/monthly snapshot as the sole membership engine.
do $$begin
 if to_regprocedure('private.membership_snapshot_before_freezes(uuid,bigint)') is null then
 alter function private.membership_snapshot_json(uuid,bigint) rename to membership_snapshot_before_freezes;end if;
end$$;
create or replace function private.membership_snapshot_json(p_gym_id uuid,p_client_id bigint) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare s jsonb;f jsonb;m public.memberships;policy jsonb;eligible boolean;used integer;begin
 s:=private.membership_snapshot_before_freezes(p_gym_id,p_client_id);
 f:=private.freeze_active(p_gym_id,p_client_id);
 if f is not null then
 select * into m from public.memberships where gym_id=p_gym_id and id=(f->>'membership_id')::bigint;
 return s||jsonb_build_object('status','FROZEN','frozen',true,'allowed',false,'freeze',f,
 'freeze_last_date',((f->>'resume_date')::date-1),'resume_date',f->>'resume_date',
 'end_date',m.end_date,'membership_end',m.end_date,'can_freeze',false,'plan_id',m.plan_id,'freeze_policy',private.freeze_policy(p_gym_id,m.plan_id),
 'denial_code','CHECK_IN_DENIED_MEMBERSHIP_FROZEN',
 'denial_message','Membresía congelada hasta el '||to_char((f->>'resume_date')::date,'DD/MM/YYYY')||'.');
 end if;
 select * into m from public.memberships where gym_id=p_gym_id and id=(s->>'membership_id')::bigint;
 policy:=private.freeze_policy(p_gym_id,m.plan_id);
 select count(*) into used from public.membership_freezes where gym_id=p_gym_id and membership_id=m.id;
 eligible:=coalesce((s->>'allowed')::boolean,false) and coalesce((policy->>'enabled')::boolean,false)
 and used<(policy->>'max_per_membership')::integer and m.payment_status='posted'
 and (s->>'entry_limit' is null or (s->>'entries_remaining')::bigint>0);
 return s||jsonb_build_object('frozen',false,'end_date',s->>'membership_end','start_date',s->>'membership_start',
 'plan_id',m.plan_id,'can_freeze',coalesce(eligible,false),'freeze_policy',policy,'freeze_count',used);
end$$;
create or replace function private.freeze_complete_due(p_gym_id uuid default null,p_client_id bigint default null) returns integer
language plpgsql security definer set search_path='' as $$
declare f record;n integer:=0;begin
 for f in select id,gym_id,client_id from public.membership_freezes
 where status in ('ACTIVE','SCHEDULED') and (p_gym_id is null or gym_id=p_gym_id)
 and (p_client_id is null or client_id=p_client_id)
 and private.gym_local_date(gym_id)>=resume_date order by client_id,id loop
 perform pg_advisory_xact_lock(f.client_id);
 with finished as(update public.membership_freezes set status='COMPLETED',completed_at=private.gym_server_now()
 where id=f.id and status in ('ACTIVE','SCHEDULED') returning *)
 insert into public.audit_logs(gym_id,action,entity_type,entity_id,summary,details)
 select gym_id,'MEMBERSHIP_FREEZE_COMPLETED','memberships',membership_id::text,
 'Congelación completada · cliente #'||client_id,to_jsonb(finished) from finished;
 if found then n:=n+1;end if;
 end loop;return n;
end$$;
create or replace function public.membership_freeze(p_gym_id uuid,p_membership_id bigint,p_request_id uuid,
 p_reason text default '',p_override boolean default false) returns jsonb
language plpgsql security definer set search_path='' as $$
declare m public.memberships;f public.membership_freezes;policy jsonb;today date;zone text;days integer;used integer;s jsonb;begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist'])
 or (p_override and not private.user_has_gym_role(p_gym_id,array['admin'])) then
 raise exception 'No tienes permiso para congelar esta membresía.' using errcode='42501';end if;
 if p_request_id is null or length(coalesce(p_reason,''))>500 or (p_override and length(trim(coalesce(p_reason,'')))<3) then
 raise exception 'La excepción administrativa requiere un motivo y una referencia válida.';end if;
 select * into m from public.memberships where id=p_membership_id and gym_id=p_gym_id;
 if not found then raise exception 'La membresía no pertenece al gimnasio.';end if;
 perform pg_advisory_xact_lock(m.client_id);
 select * into m from public.memberships where id=p_membership_id and gym_id=p_gym_id for update;
 select * into f from public.membership_freezes where gym_id=p_gym_id and request_id=p_request_id;
 if found then
 if f.membership_id<>m.id then raise exception 'La referencia corresponde a otra membresía.';end if;
 return to_jsonb(f)||jsonb_build_object('duplicate',true);end if;
 perform private.freeze_complete_due(p_gym_id,m.client_id);
 today:=private.gym_local_date(p_gym_id);zone:=private.gym_timezone(p_gym_id);policy:=private.freeze_policy(p_gym_id,m.plan_id);
 days:=(policy->>'duration_days')::integer;
 s:=private.membership_snapshot_json(p_gym_id,m.client_id);
 if coalesce((s->>'frozen')::boolean,false) then raise exception 'El cliente ya tiene una congelación activa.';end if;
 if m.payment_status<>'posted' or today not between m.start_date and m.end_date
 or not exists(select 1 from public.clients where gym_id=p_gym_id and id=m.client_id and active)
 or (s->>'membership_id')::bigint is distinct from m.id
 or (s->>'entry_limit' is not null and (s->>'entries_remaining')::bigint<=0) then
 raise exception 'Solo se puede congelar una membresía activa con tiempo y saldo disponibles.';end if;
 select count(*) into used from public.membership_freezes where gym_id=p_gym_id and membership_id=m.id;
 if not p_override and (not (policy->>'enabled')::boolean or used>=(policy->>'max_per_membership')::integer) then
 raise exception 'Esta membresía alcanzó el máximo de congelaciones o su plan no lo permite.';end if;
 insert into public.membership_freezes(gym_id,client_id,membership_id,start_date,resume_date,timezone,starts_at,ends_at,
 days_added,original_end_date,extended_end_date,status,reason,created_by,request_id,administrative_override)
 values(p_gym_id,m.client_id,m.id,today,today+days,zone,today::timestamp at time zone zone,
 (today+days)::timestamp at time zone zone,days,m.end_date,m.end_date+days,'ACTIVE',trim(coalesce(p_reason,'')),auth.uid(),p_request_id,p_override)
 returning * into f;
 -- Already-purchased future cycles move too, preserving duration and avoiding overlaps.
 update public.memberships set start_date=start_date+days,end_date=end_date+days
 where gym_id=p_gym_id and client_id=m.client_id and id<>m.id and payment_status='posted' and start_date>m.end_date;
 update public.memberships set end_date=end_date+days where id=m.id and gym_id=p_gym_id;
 -- A message already in the queue must never announce the obsolete expiry.
 update public.marketing_messages set status='SKIPPED',error_message='MEMBERSHIP_CHANGED',updated_at=clock_timestamp()
 where gym_id=p_gym_id and client_id=m.client_id and status='QUEUED'
 and automation_type in ('MEMBERSHIP_BEFORE','MEMBERSHIP_TODAY','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','TICKET_EXPIRING','TICKET_REMAINING','INACTIVITY');
 insert into public.audit_logs(gym_id,action,entity_type,entity_id,summary,details)
 values(p_gym_id,'MEMBERSHIP_FROZEN','memberships',m.id::text,'Membresía congelada · cliente #'||m.client_id,to_jsonb(f));
 return to_jsonb(f)||jsonb_build_object('duplicate',false,'new_end_date',m.end_date+days);
end$$;
create or replace function public.membership_cancel_freeze(p_gym_id uuid,p_freeze_id uuid,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare f public.membership_freezes;m public.memberships;unspent integer;begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin']) then
 raise exception 'Solo Administración puede cancelar una congelación.' using errcode='42501';end if;
 if length(trim(coalesce(p_reason,''))) not between 3 and 500 then raise exception 'Indica el motivo de cancelación.';end if;
 select * into f from public.membership_freezes where id=p_freeze_id and gym_id=p_gym_id;
 if not found then raise exception 'Congelación no encontrada.';end if;
 perform pg_advisory_xact_lock(f.client_id);
 select * into f from public.membership_freezes where id=p_freeze_id and gym_id=p_gym_id for update;
 if f.status='CANCELLED' then return to_jsonb(f)||jsonb_build_object('duplicate',true);end if;
 if private.gym_local_date(p_gym_id)>=f.resume_date or f.status='COMPLETED' then
 raise exception 'La congelación ya finalizó y no se puede cancelar.';end if;
 unspent:=f.days_added-greatest(0,private.gym_local_date(p_gym_id)-f.start_date);
 select * into m from public.memberships where id=f.membership_id and gym_id=p_gym_id for update;
 update public.memberships set start_date=start_date-unspent,end_date=end_date-unspent
 where gym_id=p_gym_id and client_id=f.client_id and id<>m.id and payment_status='posted' and start_date>m.end_date;
 update public.memberships set end_date=end_date-unspent where id=m.id and gym_id=p_gym_id;
 update public.membership_freezes set status='CANCELLED',days_reversed=unspent,cancelled_at=private.gym_server_now(),
 cancelled_by=auth.uid(),cancellation_reason=trim(p_reason) where id=f.id returning * into f;
 insert into public.audit_logs(gym_id,action,entity_type,entity_id,summary,details)
 values(p_gym_id,'MEMBERSHIP_FREEZE_CANCELLED','memberships',m.id::text,'Congelación cancelada · cliente #'||f.client_id,to_jsonb(f));
 return to_jsonb(f)||jsonb_build_object('new_end_date',m.end_date-unspent);
end$$;
create or replace function public.membership_freeze_info(p_gym_id uuid,p_client_id bigint) returns jsonb
language plpgsql security definer set search_path='' as $$
declare s jsonb;begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
 raise exception 'No tienes permiso para consultar este cliente.' using errcode='42501';end if;
 perform private.freeze_complete_due(p_gym_id,p_client_id);
 s:=private.membership_snapshot_json(p_gym_id,p_client_id);
 return jsonb_build_object('membership',s,'policy',coalesce(s->'freeze_policy',private.freeze_policy(p_gym_id,null)),
 'history',(select coalesce(jsonb_agg(to_jsonb(f) order by created_at desc),'[]') from public.membership_freezes f
 where gym_id=p_gym_id and client_id=p_client_id));
end$$;
-- Even direct inserts/administrator overrides must deny access while frozen.
create or replace function private.freeze_checkin_guard() returns trigger
language plpgsql security definer set search_path='' as $$
declare f jsonb;begin
 if exists(select 1 from private.ticket_import_context where transaction_id=txid_current() and gym_id=new.gym_id) then return new;end if;
 perform pg_advisory_xact_lock(new.client_id);
 perform private.freeze_complete_due(new.gym_id,new.client_id);
 f:=private.freeze_active(new.gym_id,new.client_id);
 if f is not null then
 new.result:='DENEGADA';new.notes:='CHECK_IN_DENIED_MEMBERSHIP_FROZEN · Membresía congelada hasta el '||to_char((f->>'resume_date')::date,'DD/MM/YYYY')||'.';
 new.membership_id:=(f->>'membership_id')::bigint;
 end if;return new;
end$$;
drop trigger if exists a_freeze_checkin_guard on public.checkins;
create trigger a_freeze_checkin_guard before insert on public.checkins for each row execute function private.freeze_checkin_guard();
create or replace function private.freeze_checkin_audit() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if new.notes like 'CHECK_IN_DENIED_MEMBERSHIP_FROZEN%' then
 insert into public.audit_logs(gym_id,action,entity_type,entity_id,summary,details)
 values(new.gym_id,'CHECK_IN_DENIED_MEMBERSHIP_FROZEN','checkins',new.id::text,
 'Entrada denegada por congelación · cliente #'||new.client_id,to_jsonb(new));end if;return new;
end$$;
drop trigger if exists freeze_checkin_audit on public.checkins;
create trigger freeze_checkin_audit after insert on public.checkins for each row execute function private.freeze_checkin_audit();
-- The snapshot denies the RPC override before any ticket can be consumed.
do $$declare def text;begin
 def:=pg_get_functiondef('private.daily_register_checkin(uuid,bigint,text,boolean)'::regprocedure);
 if position('s->>''frozen''' in def)=0 then
 def:=replace(def,'allowed or p_override','(allowed or p_override) and not coalesce((s->>''frozen'')::boolean,false)');end if;
 def:=replace(def,'''override'',p_override and not allowed','''override'',p_override and not allowed and ch.result=''PERMITIDA''');
 execute def;
end$$;
create or replace function public.membership_service_complete_freezes() returns integer
language sql security definer set search_path='' as $$ select private.freeze_complete_due() $$;
-- Recheck expiry/freeze after queuing and just before the provider call.
alter table public.marketing_messages add column if not exists membership_end_snapshot date;
do $$declare def text;begin
 def:=pg_get_functiondef('public.marketing_service_enqueue(uuid,uuid,bigint,text,text,text,jsonb,uuid)'::regprocedure);
 if position('declare snap jsonb' in def)=0 then
 def:=replace(def,'declare a public.marketing_automations;', 'declare snap jsonb; a public.marketing_automations;');
 def:=replace(def,'insert into public.automation_runs(gym_id,automation_id,client_id,dedupe_key,status,reason)',
 $s$snap:=private.membership_snapshot_json(p_gym_id,p_client_id);
 if a.trigger_type in ('MEMBERSHIP_BEFORE','MEMBERSHIP_TODAY','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','TICKET_EXPIRING','TICKET_REMAINING','INACTIVITY') and coalesce((snap->>'frozen')::boolean,false) then v_status:='SKIPPED';reason:='MEMBERSHIP_FROZEN';end if;
 insert into public.automation_runs(gym_id,automation_id,client_id,dedupe_key,status,reason)$s$);
 def:=replace(def,'update public.marketing_automations set last_run_at=now()',
 $s$update public.marketing_messages set membership_end_snapshot=nullif(snap->>'end_date','')::date where id=mid;
 update public.marketing_automations set last_run_at=now()$s$);
 execute def;end if;
 def:=pg_get_functiondef('public.marketing_service_send_guard(bigint,uuid)'::regprocedure);
 if position('declare snap jsonb' in def)=0 then
 def:=replace(def,'declare m public.marketing_messages;', 'declare snap jsonb; m public.marketing_messages;');
 def:=replace(def,'if m.automation_id is not null then',
 $s$if m.automation_type in ('MEMBERSHIP_BEFORE','MEMBERSHIP_TODAY','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','TICKET_EXPIRING','TICKET_REMAINING','INACTIVITY') then
 snap:=private.membership_snapshot_json(m.gym_id,m.client_id);
 if coalesce((snap->>'frozen')::boolean,false) then return '{"allowed":false,"reason":"MEMBERSHIP_FROZEN"}';end if;
 if nullif(snap->>'end_date','')::date is distinct from m.membership_end_snapshot then return '{"allowed":false,"reason":"MEMBERSHIP_CHANGED"}';end if;end if;
 if m.automation_id is not null then$s$);
 execute def;end if;
end$$;
-- New absolutes are generated by the DB, not the desktop clock. Do not rewrite history.
create or replace function private.gym_event_clock() returns trigger
language plpgsql security definer set search_path='' as $$
declare j jsonb:=to_jsonb(new);k text;begin
 if exists(select 1 from private.ticket_import_context where transaction_id=txid_current() and gym_id=new.gym_id) then return new;end if;
 foreach k in array tg_argv loop
 if tg_op='INSERT' or k='updated_at' then
 -- Privileged historical audit imports retain their explicit timestamp.
 if tg_table_name in ('audit_logs','memberships') and pg_trigger_depth()=1 and auth.uid() is null then continue;end if;
 j:=j||jsonb_build_object(k,private.gym_server_now());end if;
 end loop;new:=jsonb_populate_record(new,j);return new;
end$$;
do $$declare t text;col text;begin
 for t,col in select * from (values('checkins','checkin_at'),('store_sales','sold_at'),('clients','created_at'),
 ('accounting_expenses','created_at'),('audit_logs','created_at'),('memberships','paid_at')) v(t,col) loop
 execute format('drop trigger if exists a_server_event_clock on public.%I',t);
 execute format('create trigger a_server_event_clock before insert on public.%I for each row execute function private.gym_event_clock(%L)',t,col);
 end loop;
end$$;
-- Freeze archival travels with membership backups, preserving local dates and quota.
alter table public.memberships add column if not exists freeze_archive jsonb;
do $$begin
 if to_regprocedure('private.ticket_backup_before_freezes(uuid)') is null then
 alter function private.ticket_backup_memberships(uuid) rename to ticket_backup_before_freezes;end if;
end$$;
create or replace function private.ticket_backup_memberships(p_gym_id uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(item||jsonb_build_object('freeze_archive',(select coalesce(jsonb_agg(to_jsonb(f)),'[]')
 from public.membership_freezes f where f.gym_id=p_gym_id and f.membership_id=(item->>'id')::bigint))),'[]')
 from jsonb_array_elements(private.ticket_backup_before_freezes(p_gym_id)) item
$$;
create or replace function private.restore_freeze_archive() returns trigger
language plpgsql security definer set search_path='' as $$
declare x jsonb;begin
 if new.freeze_archive is null then return new;end if;
 if jsonb_typeof(new.freeze_archive)<>'array' or jsonb_array_length(new.freeze_archive)>100 then raise exception 'Historial de congelaciones no válido.';end if;
 for x in select value from jsonb_array_elements(new.freeze_archive) loop
 insert into public.membership_freezes(gym_id,client_id,membership_id,start_date,resume_date,timezone,starts_at,ends_at,
 days_added,days_reversed,original_end_date,extended_end_date,status,reason,created_by,created_at,completed_at,
 cancelled_at,cancelled_by,cancellation_reason,administrative_override,request_id)
 values(new.gym_id,new.client_id,new.id,(x->>'start_date')::date,(x->>'resume_date')::date,x->>'timezone',
 (x->>'starts_at')::timestamptz,(x->>'ends_at')::timestamptz,(x->>'days_added')::integer,coalesce((x->>'days_reversed')::integer,0),
 (x->>'original_end_date')::date,(x->>'extended_end_date')::date,x->>'status',coalesce(x->>'reason',''),
 (x->>'created_by')::uuid,(x->>'created_at')::timestamptz,(x->>'completed_at')::timestamptz,
 (x->>'cancelled_at')::timestamptz,(x->>'cancelled_by')::uuid,x->>'cancellation_reason',
 coalesce((x->>'administrative_override')::boolean,false),(x->>'request_id')::uuid);
 end loop;return new;
end$$;
drop trigger if exists restore_freeze_archive on public.memberships;
create trigger restore_freeze_archive after insert on public.memberships for each row execute function private.restore_freeze_archive();
-- Restricted helpers / explicit API grants.
-- Owner expiry counters also use the server clock, without granting staff owner access.
do $owner$begin
 if to_regprocedure('public.owner_list_gyms()') is not null then
 if to_regprocedure('private.owner_list_gyms_before_freezes()') is null then
 alter function public.owner_list_gyms() rename to owner_list_gyms_before_freezes;
 alter function public.owner_list_gyms_before_freezes() set schema private;end if;
 execute $sql$create or replace function public.owner_list_gyms() returns jsonb
 language sql stable security definer set search_path='' as $body$
 select coalesce(jsonb_agg(item||jsonb_build_object('server_now',private.gym_server_now())),'[]')
 from jsonb_array_elements(private.owner_list_gyms_before_freezes()) item
 $body$$sql$;
 revoke all on function public.owner_list_gyms() from public,anon,authenticated;
 grant execute on function public.owner_list_gyms() to authenticated;
 end if;
end$owner$;
do $$declare f record;begin
 for f in select p.oid::regprocedure sig,n.nspname,p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in ('private','public') and (p.proname like '%freeze%' or p.proname='gym_event_clock'
 or (n.nspname='private' and p.proname in ('membership_snapshot_json','ticket_backup_memberships','validate_gym_timezone'))) loop
 execute format('revoke all on function %s from public,anon,authenticated,service_role',f.sig);
 if f.nspname='public' then execute format('grant execute on function %s to %I',f.sig,
 case when f.proname='membership_service_complete_freezes' then 'service_role' else 'authenticated' end);end if;
 end loop;
end$$;
-- The cron job runs with all integration flags OFF too. Access resumes even if a cron tick is late.
do $$begin
 if exists(select 1 from pg_extension where extname='pg_cron') then
 perform cron.schedule('gymsoft-freeze-completion','* * * * *','select private.freeze_complete_due()');end if;
end$$;
commit;
