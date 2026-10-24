-- Independent optional module; does not alter gym licensing, billing or payments.
begin;
create table private.core_league_modules (
 gym_id uuid primary key references private.core_gyms(gym_id),
 enabled boolean not null default false,athlete_code text not null unique,
 updated_by uuid not null,updated_at timestamptz not null default now(),
 check(athlete_code ~ '^[A-Z0-9-]{6,24}$')
);
alter table private.core_league_modules enable row level security;
revoke all on private.core_league_modules from public,anon,authenticated;
create function private.league_owner(p_gym_id uuid,p_enabled boolean) returns jsonb language plpgsql security definer set search_path='' as $$
begin
 perform private.require_owner();
 insert into private.core_league_modules(gym_id,enabled,athlete_code,updated_by)
  values(p_gym_id,p_enabled,'AL-'||upper(substr(replace(gen_random_uuid()::text,'-',''),1,10)),auth.uid())
  on conflict(gym_id) do update set enabled=excluded.enabled,updated_by=auth.uid(),updated_at=now();
 return jsonb_build_object('gym_id',p_gym_id,'enabled',enabled,'athlete_code',athlete_code) from private.core_league_modules where gym_id=p_gym_id;
end $$;
create function private.league_entitlement(p_gym_id uuid) returns jsonb language sql stable security definer set search_path='' as $$
 select jsonb_build_object('gym_id',g.gym_id,'name',g.name,'source_ref',g.source_project_ref,
  'enabled',coalesce(m.enabled,false) and g.status='ACTIVE','athlete_code',m.athlete_code)
 from private.core_gyms g left join private.core_league_modules m using(gym_id) where g.gym_id=p_gym_id
$$;
create function public.core_league_owner(p_gym_id uuid,p_enabled boolean) returns jsonb language sql security invoker set search_path='' as $$
 select private.league_owner(p_gym_id,p_enabled)
$$;
create function public.core_league_entitlement(p_gym_id uuid) returns jsonb language sql stable security invoker set search_path='' as $$
 select private.league_entitlement(p_gym_id)
$$;
create function private.league_search(p_query text) returns jsonb language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(to_jsonb(t)),'[]') from (
  select g.gym_id,g.name,g.source_project_ref as source_ref,m.athlete_code
  from private.core_gyms g join private.core_league_modules m using(gym_id)
  where g.status='ACTIVE' and m.enabled and length(trim(p_query))>=2 and
   (m.athlete_code=upper(trim(p_query)) or g.name ilike '%'||left(trim(p_query),80)||'%')
  order by g.name limit 20)t
$$;
create function public.core_league_search(p_query text) returns jsonb language sql stable security invoker set search_path='' as $$
 select private.league_search(p_query)
$$;
revoke all on function private.league_owner(uuid,boolean),private.league_entitlement(uuid),private.league_search(text),public.core_league_owner(uuid,boolean),public.core_league_entitlement(uuid),public.core_league_search(text) from public,anon,authenticated;
grant usage on schema private to authenticated,service_role;
grant execute on function private.league_owner(uuid,boolean) to authenticated;
grant execute on function private.league_entitlement(uuid) to service_role;
grant execute on function private.league_search(text),public.core_league_search(text) to service_role;
grant execute on function public.core_league_owner(uuid,boolean) to authenticated;
grant execute on function public.core_league_entitlement(uuid) to service_role;
commit;

-- Public opt-in directory metadata only. Never returns billing, roles, member or owner data.
begin;
create schema if not exists league_directory_private;
revoke all on schema league_directory_private from public;
create function league_directory_private.directory(p_gym_id uuid,p_query text) returns jsonb language sql stable security definer set search_path='' as $$
 select coalesce(jsonb_agg(to_jsonb(t)),'[]') from (
  select g.gym_id,g.name,g.source_project_ref as source_ref,m.athlete_code,true as enabled
  from private.core_gyms g join private.core_league_modules m using(gym_id)
  where g.status='ACTIVE' and m.enabled and
   ((p_gym_id is not null and g.gym_id=p_gym_id) or (p_gym_id is null and length(trim(p_query))>=2 and (m.athlete_code=upper(trim(p_query)) or g.name ilike '%'||left(trim(p_query),80)||'%')))
  order by g.name limit 20)t
$$;
create function public.core_league_public_directory(p_gym_id uuid default null,p_query text default null) returns jsonb language sql stable security invoker set search_path='' as $$
 select league_directory_private.directory(p_gym_id,p_query)
$$;
revoke all on function league_directory_private.directory(uuid,text),public.core_league_public_directory(uuid,text) from public;
grant usage on schema league_directory_private to anon,authenticated,service_role;
grant execute on function league_directory_private.directory(uuid,text),public.core_league_public_directory(uuid,text) to anon,authenticated,service_role;
commit;
