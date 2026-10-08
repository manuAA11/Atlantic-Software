create or replace function private.daily_register_checkin(p_gym_id uuid,p_client_id bigint,p_method text,p_override boolean default false)
returns jsonb language plpgsql security definer set search_path='' as $$
declare s jsonb; ch public.checkins; allowed boolean;
begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist'])
 or (p_override and not private.user_has_gym_role(p_gym_id,array['admin'])) then
  raise exception 'No tienes permiso para registrar esta entrada.' using errcode='42501';
 end if;
 perform pg_catalog.pg_advisory_xact_lock(p_client_id);
 perform 1 from public.clients where gym_id=p_gym_id and id=p_client_id for update;
 s:=private.membership_snapshot_json(p_gym_id,p_client_id);
 allowed:=coalesce((s->>'allowed')::boolean,false);
 insert into public.checkins(gym_id,client_id,membership_id,checkin_at,method,result,notes,recorded_by)
 values(p_gym_id,p_client_id,nullif(s->>'membership_id','')::bigint,private.gym_server_now(),
 left(trim(coalesce(p_method,'MANUAL')),80),case when allowed or p_override then 'PERMITIDA' else 'DENEGADA' end,
 case when p_override and not allowed then 'Autorización manual del administrador' else '' end,auth.uid()) returning * into ch;
 if ch.ticket_consumed then
  s:=s||jsonb_build_object('entries_used',(s->>'entries_used')::bigint+1,
    'entries_remaining',greatest((s->>'entries_remaining')::bigint-1,0));
 end if;
 return s||jsonb_build_object('result',ch.result,'checkin_id',ch.id,'checkin_at',ch.checkin_at,
 'override',p_override and not allowed,'ticket_consumed',ch.ticket_consumed,
 'already_consumed_today',ch.already_consumed_today,'local_date',ch.local_date);
end $$;
revoke all on function private.daily_register_checkin(uuid,bigint,text,boolean) from public,anon,authenticated;
grant execute on function private.daily_register_checkin(uuid,bigint,text,boolean) to authenticated;
create or replace function public.reception_register_checkin(p_gym_id uuid,p_client_id bigint,p_method text default 'RECEPCIÓN')
returns jsonb language sql security invoker set search_path='' as $$
 select private.daily_register_checkin(p_gym_id,p_client_id,p_method,false)
$$;
create or replace function public.admin_register_checkin(p_gym_id uuid,p_client_id bigint,p_method text,p_override boolean default false)
returns jsonb language plpgsql security invoker set search_path='' as $$
begin
 if not private.user_has_gym_role(p_gym_id,array['admin']) then raise exception 'Acceso exclusivo de Administración.' using errcode='42501'; end if;
 return private.daily_register_checkin(p_gym_id,p_client_id,p_method,p_override);
end $$;
revoke all on function public.reception_register_checkin(uuid,bigint,text),public.admin_register_checkin(uuid,bigint,text,boolean) from public,anon,authenticated;
grant execute on function public.reception_register_checkin(uuid,bigint,text),public.admin_register_checkin(uuid,bigint,text,boolean) to authenticated;
create or replace function private.ticket_backup_memberships(p_gym_id uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(to_jsonb(m)||jsonb_build_object('ticket_consumption_archive',
 (select coalesce(jsonb_agg(jsonb_build_object('local_date',d.local_date,'units',d.units,'legacy',d.legacy,'created_at',d.created_at) order by d.local_date),'[]')
 from public.ticket_daily_consumptions d where d.gym_id=m.gym_id and d.membership_id=m.id)) order by m.id),'[]')
 from public.memberships m where m.gym_id=p_gym_id
$$;
create or replace function public.ticket_backup_memberships(p_gym_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin']) then
  raise exception 'Solo Administración puede exportar membresías.' using errcode='42501'; end if;
 return private.ticket_backup_memberships(p_gym_id);
end $$;
revoke all on function public.ticket_backup_memberships(uuid) from public,anon,authenticated;
grant execute on function public.ticket_backup_memberships(uuid) to authenticated;
create or replace function public.gym_local_clock(p_gym_id uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
  raise exception 'Acceso no autorizado.' using errcode='42501'; end if;
 return jsonb_build_object('now',private.gym_server_now(),'today',private.gym_local_date(p_gym_id),'timezone',private.gym_timezone(p_gym_id));
end $$;
revoke all on function public.gym_local_clock(uuid) from public,anon,authenticated;
grant execute on function public.gym_local_clock(uuid) to authenticated;
-- Existing per-gym reports/renewals must use the same clock and consumption ledger.
do $patch$
declare f record; definition text; updated text;
begin
 for f in select p.oid,n.nspname,p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in ('public','private') and p.prokind='f' and 'p_gym_id'=any(p.proargnames)
 and p.proname not in ('gym_timezone','gym_server_now','gym_local_date') loop
  definition:=pg_get_functiondef(f.oid); updated:=definition;
  updated:=replace(updated,'public.ztattuz_today()','private.gym_local_date(p_gym_id)');
  updated:=replace(updated,'public.gymsoft_today()','private.gym_local_date(p_gym_id)');
  updated:=replace(updated,'private.current_timezone()','private.gym_timezone(p_gym_id)');
  updated:=replace(updated,'AT TIME ZONE ''America/Bogota''','AT TIME ZONE private.gym_timezone(p_gym_id)');
  updated:=replace(updated,'at time zone ''America/Bogota''','at time zone private.gym_timezone(p_gym_id)');
  if f.proname in ('ztattuz_add_membership','add_membership_accumulating_internal') then
   updated:=regexp_replace(updated,'select count\(\*\) \+ m.initial_entries_used\s+from public.checkins ch\s+where ch.gym_id = p_gym_id\s+and ch.client_id = p_client_id\s+and ch.membership_id = m.id\s+and ch.result = ''PERMITIDA''',
    'select private.ticket_consumption_units(p_gym_id,m.id) + m.initial_entries_used','g');
   if position('from public.checkins' in lower(updated))>0 then raise exception 'Revisar función de renovación: %',f.proname; end if;
  end if;
  if f.proname='ticket_followup' then
   updated:=regexp_replace(updated,'select count\(\*\) as used from public.checkins ch\s+where ch.gym_id=p_gym_id and ch.membership_id=m.id and ch.result=''PERMITIDA''',
    'select private.ticket_consumption_units(p_gym_id,m.id) as used','g');
  end if;
  if f.proname in ('owner_editor_snapshot','owner_backup_gym') then
   updated:=replace(updated,'tables:=tables||jsonb_build_object(t,rows);',
    'if t=''memberships'' then rows:=private.ticket_backup_memberships(p_gym_id); end if; tables:=tables||jsonb_build_object(t,rows);');
  end if;
  if updated<>definition then execute updated; end if;
 end loop;
end $patch$;
-- Private helpers are not APIs. Explicitly revoke default PUBLIC execution.
do $$ declare f record; begin
 for f in select p.oid::regprocedure as signature from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='private' and p.proname=any(array['validate_gym_timezone','gym_timezone','gym_server_now','gym_local_date',
 'ticket_consumption_units','ticket_consumed_on','consume_daily_ticket','preserve_ticket_history','restore_ticket_archive','ticket_backup_memberships']) loop
  execute format('revoke all on function %s from public,anon,authenticated',f.signature);
 end loop;
end $$;
commit;
