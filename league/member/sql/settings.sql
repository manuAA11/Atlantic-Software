-- Private server configuration. No secrets are returned to authenticated/anonymous clients.
begin;
create table league_member_private.settings(
 singleton boolean primary key default true check(singleton),
 access_pepper text not null default (gen_random_uuid()::text||gen_random_uuid()::text),
 job_key text not null default (gen_random_uuid()::text||gen_random_uuid()::text),
 vapid_public text,vapid_private text,project_url text
);
alter table league_member_private.settings enable row level security;
revoke all on league_member_private.settings from public,anon,authenticated;
grant all on league_member_private.settings to service_role;
insert into league_member_private.settings(singleton) values(true);
create function public.league_member_settings(p_action text,p_data jsonb default '{}') returns jsonb
language plpgsql security invoker set search_path='' as $$
begin
 if p_action='project.initialize' then
  if coalesce(p_data->>'url','')!~'^https://[a-z0-9]{20}[.]supabase[.]co$' then raise exception 'Invalid project URL';end if;
  update league_member_private.settings set project_url=p_data->>'url' where singleton and project_url is null;
 elsif p_action='vapid.initialize' then
  if coalesce(p_data->>'public','')!~'^[A-Za-z0-9_-]{80,120}$' or coalesce(p_data->>'private','')!~'^[A-Za-z0-9_-]{40,60}$' then raise exception 'Invalid VAPID key';end if;
  update league_member_private.settings set vapid_public=p_data->>'public',vapid_private=p_data->>'private' where singleton and vapid_public is null;
 elsif p_action<>'get' then raise exception 'Invalid action';end if;
 return (select jsonb_build_object('access_pepper',access_pepper,'job_key',job_key,'vapid_public',vapid_public,'vapid_private',vapid_private) from league_member_private.settings where singleton);
end $$;
revoke all on function public.league_member_settings(text,jsonb) from public,anon,authenticated;
grant execute on function public.league_member_settings(text,jsonb) to service_role;
commit;
