-- Seven days is a ceiling. New freezes extend dates only when closed.
-- Old events retain their original fields and pre-applied extension semantics.
begin;
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
commit;
