-- DRAFT: local QA only. Not applied to any hosted project.
-- Use the Supabase CLI to generate the migration after review and local validation.
-- Depends on existing League links/directory; never updates Gym tables or Auth.
begin;
create schema if not exists league_member_private;
revoke all on schema league_member_private from public,anon,authenticated;
create table league_member_private.identities(
 gym_id uuid not null,client_id bigint not null,auth_user_id uuid not null unique,
 previous_athlete_id uuid,created_at timestamptz not null default now(),primary key(gym_id,client_id)
);
alter table league_member_private.identities enable row level security;
revoke all on league_member_private.identities from public,anon,authenticated;
grant all on league_member_private.identities to service_role;
-- A member alias uses the original approved source link; it never transfers that link.
create function league_member_private.connection(p_actor uuid,p_gym uuid) returns jsonb
language sql security invoker set search_path='' as $$
 select jsonb_build_object('gym_id',l.gym_id,'name',g.name,'source_ref',g.source_ref,
  'source_profile_id',l.source_profile_id,'client_id',cp.client_id::text)
 from public.league_links l join public.league_gym_directory g using(gym_id)
 join public.league_client_profiles cp on cp.gym_id=l.gym_id and cp.profile_id=l.source_profile_id
 left join league_member_private.identities i on i.gym_id=cp.gym_id and i.client_id=cp.client_id and i.auth_user_id=p_actor
 where l.gym_id=p_gym and l.status='APPROVED' and g.enabled and (l.athlete_id=p_actor or i.auth_user_id=p_actor)
 limit 1
$$;
revoke all on function league_member_private.connection(uuid,uuid) from public,anon,authenticated;
grant execute on function league_member_private.connection(uuid,uuid) to service_role;
create table public.league_member_renewals(
 id uuid primary key default gen_random_uuid(),
 athlete_id uuid not null references public.league_profiles(id),
 gym_id uuid not null references public.league_gym_directory(gym_id),
 period_key text not null check(length(period_key) between 1 and 100),
 request_key uuid not null,
 status text not null default 'PENDING' check(status in ('PENDING','REVIEW','APPROVED','REJECTED','CANCELLED')),
 created_at timestamptz not null default now(),updated_at timestamptz not null default now(),
 unique(athlete_id,request_key)
);
create unique index league_member_one_open_renewal on public.league_member_renewals(athlete_id,gym_id,period_key) where status in ('PENDING','REVIEW');
create index league_member_renewal_history on public.league_member_renewals(athlete_id,gym_id,created_at desc);
create table public.league_member_notifications(
 id uuid primary key default gen_random_uuid(),
 athlete_id uuid not null references public.league_profiles(id),
 gym_id uuid not null references public.league_gym_directory(gym_id),
 source_key text not null check(length(source_key) between 1 and 200),
 title text not null check(length(title) between 1 and 120),
 body text not null check(length(body)<=1000),
 target text not null check(target in ('/','/agenda','/rutinas','/perfil')),
 read_at timestamptz,created_at timestamptz not null default now(),
 unique(athlete_id,gym_id,source_key)
);
create index league_member_notification_history on public.league_member_notifications(athlete_id,gym_id,created_at desc);
create table league_member_private.push_subscriptions(
 athlete_id uuid not null references public.league_profiles(id),
 gym_id uuid not null references public.league_gym_directory(gym_id),
 endpoint text not null check(length(endpoint)<=4096),p256dh text not null,auth text not null,
 updated_at timestamptz not null default now(),primary key(athlete_id,gym_id,endpoint)
);
alter table public.league_member_renewals enable row level security;
alter table public.league_member_notifications enable row level security;
alter table league_member_private.push_subscriptions enable row level security;
revoke all on public.league_member_renewals,public.league_member_notifications,league_member_private.push_subscriptions from public,anon,authenticated;
grant select on public.league_member_renewals,public.league_member_notifications to authenticated;
-- Current pilot shares the existing Gym database. Read only an approved source profile.
-- The original authoritative snapshot is projected; document, contact, biometric and medical
-- fields are never returned. No Gym function, trigger, table or routine is replaced.
create function league_member_private.membership(p_actor uuid,p_gym uuid)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare source_client bigint;s jsonb;
begin
 source_client:=(league_member_private.connection(p_actor,p_gym)->>'client_id')::bigint;
 if source_client is null then raise exception 'Perfil no disponible.' using errcode='42501';end if;
 s:=private.membership_snapshot_json(p_gym,source_client);
 return jsonb_build_object('membership_id',nullif(s->>'membership_id',''),'plan_name',nullif(s->>'plan_name',''),
  'active',coalesce((s->>'allowed')::boolean,false),'frozen',coalesce((s->>'frozen')::boolean,false),
  'starts_at',nullif(s->>'membership_start',''),'ends_at',case when coalesce((s->>'has_expiration')::boolean,true) then nullif(s->>'membership_end','') else null end,
  'status',case when coalesce((s->>'frozen')::boolean,false) then 'FROZEN' when nullif(s->>'membership_id','') is null then 'NO_PLAN' else coalesce(s->>'status',s->>'membership_state','INACTIVE') end,
  'remaining_days',case when not coalesce((s->>'frozen')::boolean,false) and coalesce((s->>'has_expiration')::boolean,true) and nullif(s->>'membership_end','') is not null then greatest(0,nullif(s->>'membership_end','')::date-private.gym_local_date(p_gym)) else null end,
  'has_expiration',coalesce((s->>'has_expiration')::boolean,true),
  'entry_limit',s->'entry_limit','entries_used',s->'entries_used','entries_remaining',s->'entries_remaining',
  'already_consumed_today',coalesce((s->>'already_consumed_today')::boolean,false),
  'renewable',coalesce(s->>'membership_type','COMMERCIAL')<>'INTERNAL');
end $$;
revoke all on function league_member_private.membership(uuid,uuid) from public,anon,authenticated;
grant execute on function league_member_private.membership(uuid,uuid) to service_role;
create policy league_member_renewals_self on public.league_member_renewals for select to authenticated using(
 athlete_id=(select auth.uid()) and exists(select 1 from public.league_links l where l.athlete_id=(select auth.uid()) and l.gym_id=league_member_renewals.gym_id and l.status='APPROVED')
);
create policy league_member_notices_self on public.league_member_notifications for select to authenticated using(
 athlete_id=(select auth.uid()) and exists(select 1 from public.league_links l where l.athlete_id=(select auth.uid()) and l.gym_id=league_member_notifications.gym_id and l.status='APPROVED')
);
-- No client writes. The gateway verifies JWT + pilot + current entitlement + source link first.
-- SECURITY INVOKER: this function is exclusively executable by the server's service role.
create function public.league_member_gateway(p_actor uuid,p_gym uuid,p_action text,p_data jsonb default '{}')
returns jsonb language plpgsql security invoker set search_path='' as $$
declare item public.league_member_renewals;rid uuid;result jsonb;period text;details jsonb;
begin
 if p_action='snapshot' then
  return jsonb_build_object('profile',(select jsonb_build_object('id',id,'alias',alias) from public.league_profiles where id=p_actor),
   'links',coalesce((select jsonb_agg(jsonb_build_object('gym_id',g.gym_id,'name',g.name,'status','APPROVED')) from public.league_gym_directory g where league_member_private.connection(p_actor,g.gym_id) is not null),'[]'::jsonb));
 end if;
 if p_actor is null or league_member_private.connection(p_actor,p_gym) is null then
  raise exception 'Vinculación no disponible.' using errcode='42501';
 end if;
 if p_action='connection' then return league_member_private.connection(p_actor,p_gym);end if;
 if p_action='membership.details' then
  return league_member_private.membership(p_actor,p_gym);
 elsif p_action='renewals.list' then
  return coalesce(jsonb_agg(to_jsonb(t)),'[]') from(select id,status,created_at,period_key from public.league_member_renewals where athlete_id=p_actor and gym_id=p_gym order by created_at desc limit 50)t;
 elsif p_action='renewals.create' then
  details:=league_member_private.membership(p_actor,p_gym);
  if not coalesce((details->>'renewable')::boolean,false) then raise exception 'Este plan no requiere renovación.' using errcode='42501';end if;
  period:=coalesce(details->>'membership_id','NO_PLAN')||':'||coalesce(details->>'ends_at','NO_PERIOD');
  -- Serialize concurrent requests for this exact member/gym/period, independent of device key.
  perform pg_advisory_xact_lock(hashtextextended(p_actor::text||':'||p_gym::text||':'||period,0));
  select * into item from public.league_member_renewals where athlete_id=p_actor and request_key=(p_data->>'request_key')::uuid;
  if found then
   if item.gym_id<>p_gym then raise exception 'Identificador ya utilizado.' using errcode='22023';end if;
   return jsonb_build_object('id',item.id,'status',item.status);
  end if;
  select * into item from public.league_member_renewals where athlete_id=p_actor and gym_id=p_gym and period_key=period and status in ('PENDING','REVIEW');
  if not found then
   insert into public.league_member_renewals(athlete_id,gym_id,period_key,request_key)
   values(p_actor,p_gym,period,(p_data->>'request_key')::uuid) returning * into item;
   insert into public.league_member_notifications(athlete_id,gym_id,source_key,title,body,target)
   values(p_actor,p_gym,'renewal:'||item.id||':requested','Renovación solicitada','Tu gimnasio revisará la solicitud. Tu vencimiento y tus pagos no han cambiado.','/') on conflict do nothing;
  end if;
  return jsonb_build_object('id',item.id,'status',item.status);
 elsif p_action='renewals.cancel' then
  update public.league_member_renewals set status='CANCELLED',updated_at=now() where id=(p_data->>'id')::uuid and athlete_id=p_actor and gym_id=p_gym and status in ('PENDING','REVIEW') returning id into rid;
  if rid is not null then
   insert into public.league_member_notifications(athlete_id,gym_id,source_key,title,body,target)
   values(p_actor,p_gym,'renewal:'||rid||':cancelled','Solicitud cancelada','Cancelaste tu solicitud de renovación.','/') on conflict do nothing;
  elsif not exists(select 1 from public.league_member_renewals where id=(p_data->>'id')::uuid and athlete_id=p_actor and gym_id=p_gym and status='CANCELLED') then
   raise exception 'Solicitud no disponible.' using errcode='42501';
  end if;
  return jsonb_build_object('cancelled',true);
 elsif p_action='notifications.list' then
  return coalesce(jsonb_agg(to_jsonb(t)),'[]') from(select id,title,body,target,read_at,created_at from public.league_member_notifications where athlete_id=p_actor and gym_id=p_gym order by created_at desc limit 100)t;
 elsif p_action='notifications.read' then
  update public.league_member_notifications set read_at=coalesce(read_at,now()) where id=(p_data->>'id')::uuid and athlete_id=p_actor and gym_id=p_gym returning id into rid;
  if rid is null then raise exception 'Aviso no disponible.' using errcode='42501';end if;
  return jsonb_build_object('read',true);
 elsif p_action='push.subscribe' then
  insert into league_member_private.push_subscriptions(athlete_id,gym_id,endpoint,p256dh,auth)
  values(p_actor,p_gym,p_data->>'endpoint',p_data->>'p256dh',p_data->>'auth')
  on conflict(athlete_id,gym_id,endpoint) do update set p256dh=excluded.p256dh,auth=excluded.auth,updated_at=now();
  return jsonb_build_object('registered',true);
 elsif p_action='push.unsubscribe' then
  delete from league_member_private.push_subscriptions where athlete_id=p_actor and gym_id=p_gym and endpoint=p_data->>'endpoint';
  return jsonb_build_object('removed',true);
 end if;
 raise exception 'Acción no disponible.' using errcode='22023';
end $$;
revoke all on function public.league_member_gateway(uuid,uuid,text,jsonb) from public,anon,authenticated;
grant usage on schema league_member_private to service_role;
grant usage on schema private to service_role;
grant execute on function private.membership_snapshot_json(uuid,bigint),private.gym_local_date(uuid) to service_role;
grant select on public.league_client_profiles,public.league_links,public.league_gym_directory to service_role;
grant all on public.league_member_renewals,public.league_member_notifications,league_member_private.push_subscriptions to service_role;
grant execute on function public.league_member_gateway(uuid,uuid,text,jsonb) to service_role;
commit;
