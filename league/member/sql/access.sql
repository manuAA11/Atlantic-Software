-- DRAFT / local QA only. Does not change clients, memberships, desktop or staff passwords.
-- Apply AFTER schema.sql in an isolated environment. No production activation has occurred.
begin;
create table league_member_private.access_attempts(
 gym_id uuid not null,bucket text not null,window_started_at timestamptz not null,hits integer not null,
 primary key(gym_id,bucket)
);
alter table league_member_private.access_attempts enable row level security;
alter table league_member_private.identities enable row level security;
revoke all on league_member_private.access_attempts,league_member_private.identities from public,anon,authenticated;
grant all on league_member_private.access_attempts,league_member_private.identities to service_role;
grant select on public.clients,public.league_gym_settings,public.league_gym_directory,public.gym_users to service_role;
grant select,insert,update on public.league_client_profiles,public.league_links,public.league_profiles to service_role;
grant usage on schema league_private to service_role;
grant select,insert on league_private.pilot_accounts to service_role;
create function public.league_member_access(p_action text,p_gym uuid,p_data jsonb)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare c public.clients;profile uuid;old_actor uuid;actor uuid;attempts integer;name text;previous_user uuid;
begin
 if p_action='attempt' then
  if coalesce(p_data->>'bucket','')!~'^[a-f0-9]{64}$' then raise exception 'Acceso no disponible.';end if;
  insert into league_member_private.access_attempts(gym_id,bucket,window_started_at,hits) values(p_gym,p_data->>'bucket',now(),1)
  on conflict(gym_id,bucket) do update set hits=case when access_attempts.window_started_at<now()-interval '15 minutes' then 1 else access_attempts.hits+1 end,
   window_started_at=case when access_attempts.window_started_at<now()-interval '15 minutes' then now() else access_attempts.window_started_at end returning hits into attempts;
  -- Bounded cleanup: no raw identifiers or IP addresses are stored.
  delete from league_member_private.access_attempts where (gym_id,bucket) in
   (select gym_id,bucket from league_member_private.access_attempts where window_started_at<now()-interval '1 day' limit 100);
  return to_jsonb(attempts<=10);
 end if;
 if p_action='resolve' then
  select cl.* into c from public.clients cl join public.league_gym_settings cfg on cfg.gym_id=cl.gym_id
   join public.league_gym_directory g on g.gym_id=cl.gym_id
   where cl.gym_id=p_gym and cl.document=p_data->>'document' and cl.active and cfg.enabled and g.enabled
   and (cfg.allow_all_clients or cl.id=any(cfg.pilot_client_ids));
  if c.id is null then return null;end if;
  return jsonb_build_object('client_id',c.id::text);
 elsif p_action='activate' then
  actor:=(p_data->>'auth_user_id')::uuid;
  select cl.* into c from public.clients cl join public.league_gym_settings cfg on cfg.gym_id=cl.gym_id
   join public.league_gym_directory g on g.gym_id=cl.gym_id
   where cl.gym_id=p_gym and cl.id=(p_data->>'client_id')::bigint and cl.active and cfg.enabled and g.enabled
   and (cfg.allow_all_clients or cl.id=any(cfg.pilot_client_ids));
  if c.id is null or actor is null or exists(select 1 from public.gym_users where user_id=actor) then raise exception 'Acceso no disponible.' using errcode='42501';end if;
  perform pg_advisory_xact_lock(hashtextextended('league-member:'||p_gym::text||':'||c.id::text,0));
  select auth_user_id into previous_user from league_member_private.identities where gym_id=p_gym and client_id=c.id;
  if previous_user is not null and previous_user<>actor then raise exception 'Identidad no disponible.' using errcode='42501';end if;
  insert into public.league_client_profiles(gym_id,client_id) values(p_gym,c.id) on conflict(gym_id,client_id) do nothing;
  select profile_id into profile from public.league_client_profiles where gym_id=p_gym and client_id=c.id;
  name:=left(coalesce(nullif(trim(coalesce(c.first_name,'')||' '||coalesce(c.last_name,'')),''),nullif(c.full_name,''),'Socio'),60);
  insert into public.league_profiles(id,alias) values(actor,name) on conflict(id) do nothing;
  select athlete_id into old_actor from public.league_links where gym_id=p_gym and source_profile_id=profile for update;
  -- Preserve existing routine sessions and links. Never transfer a legacy identity silently.
  if old_actor is null then
   insert into public.league_links(athlete_id,gym_id,source_profile_id,status,approved_by)
    values(actor,p_gym,profile,'APPROVED',coalesce(c.created_by,actor));
  end if;
  -- A revoked link is not silently reactivated by knowing a document.
  if not exists(select 1 from public.league_links where source_profile_id=profile and gym_id=p_gym and status='APPROVED') then
   raise exception 'Vinculación no disponible.' using errcode='42501';
  end if;
  insert into league_member_private.identities(gym_id,client_id,auth_user_id,previous_athlete_id)
   values(p_gym,c.id,actor,case when old_actor<>actor then old_actor end) on conflict(gym_id,client_id) do nothing;
  -- Only clients already allowed by the existing source pilot settings can reach here.
  insert into league_private.pilot_accounts(user_id) values(actor) on conflict do nothing;
  return jsonb_build_object('activated',true);
 end if;
 raise exception 'Acción no disponible.' using errcode='22023';
end $$;
revoke all on function public.league_member_access(text,uuid,jsonb) from public,anon,authenticated;
grant execute on function public.league_member_access(text,uuid,jsonb) to service_role;
commit;
