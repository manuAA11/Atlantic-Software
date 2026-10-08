-- Hosted scheduler. Provider flags stay OFF; no credentials leave Vault.
begin;
set local lock_timeout='8s';
do $extensions$begin
 if exists(select 1 from pg_available_extensions where name='pg_cron') then
 execute 'create extension if not exists pg_cron';end if;
 if exists(select 1 from pg_available_extensions where name='pg_net') then
 execute 'create extension if not exists pg_net';end if;
end$extensions$;
create table if not exists private.marketing_scheduler_config (
 singleton boolean primary key default true check(singleton),
 project_url text not null check(project_url ~ '^https://[a-z0-9]+[.]supabase[.]co$'),
 installed_at timestamptz not null default now(),last_requested_at timestamptz,last_request_id bigint);
alter table private.marketing_scheduler_config enable row level security;
revoke all on private.marketing_scheduler_config from public,anon,authenticated,service_role;
create or replace function private.marketing_cron_tick() returns bigint
language plpgsql security definer set search_path='' as $body$
declare endpoint text;token text;request_id bigint;begin
 select project_url into endpoint from private.marketing_scheduler_config where singleton;
 if endpoint is null then return null;end if;
 select v.decrypted_secret into token from vault.decrypted_secrets v
 join private.marketing_platform p on p.scheduler_secret_id=v.id where p.singleton;
 if token is null then raise exception 'Scheduler no configurado.';end if;
 select net.http_post(url:=endpoint||'/functions/v1/marketing/jobs',
 headers:=jsonb_build_object('Content-Type','application/json','x-marketing-scheduler',token),
 body:='{}'::jsonb,timeout_milliseconds:=55000) into request_id;
 update private.marketing_scheduler_config set last_requested_at=clock_timestamp(),last_request_id=request_id where singleton;
 return request_id;
end$body$;
create or replace function public.marketing_service_install_scheduler(p_project_url text) returns jsonb
language plpgsql security definer set search_path='' as $body$
declare sid uuid;begin
 if p_project_url !~ '^https://[a-z0-9]+[.]supabase[.]co$' then raise exception 'URL del proyecto no válida.';end if;
 if not exists(select 1 from pg_extension where extname='pg_cron') or not exists(select 1 from pg_extension where extname='pg_net') then
 raise exception 'Activa pg_cron y pg_net en el servidor.';end if;
 perform pg_advisory_xact_lock(hashtextextended('gymsoft/marketing-scheduler',0));
 select scheduler_secret_id into sid from private.marketing_platform where singleton for update;
 if sid is null then
 select vault.create_secret(encode(extensions.gen_random_bytes(32),'hex'),'gymsoft_scheduler_token','Private scheduler authentication') into sid;
 update private.marketing_platform set scheduler_secret_id=sid where singleton;end if;
 insert into private.marketing_scheduler_config(singleton,project_url) values(true,p_project_url)
 on conflict(singleton) do update set project_url=excluded.project_url;
 perform cron.schedule('gymsoft-marketing-minute','* * * * *','select private.marketing_cron_tick()');
 perform cron.schedule('gymsoft-freeze-completion','* * * * *','select private.freeze_complete_due()');
 return jsonb_build_object('installed',true,'interval','1 minute');
end$body$;
revoke all on function private.marketing_cron_tick() from public,anon,authenticated,service_role;
revoke all on function public.marketing_service_install_scheduler(text) from public,anon,authenticated,service_role;
grant execute on function public.marketing_service_install_scheduler(text) to service_role;
create or replace function public.marketing_service_health() returns jsonb
language plpgsql security definer set search_path='' as $body$
declare installed boolean:=false;begin
 if exists(select 1 from pg_extension where extname='pg_cron')
 and exists(select 1 from pg_extension where extname='pg_net')
 and exists(select 1 from private.marketing_scheduler_config where singleton)
 and exists(select 1 from private.marketing_platform where singleton and scheduler_secret_id is not null) then
 execute 'select count(*)=2 from cron.job where jobname in (''gymsoft-marketing-minute'',''gymsoft-freeze-completion'') and active' into installed;
 end if;
 return jsonb_build_object('database',true,'server_now',private.gym_server_now(),'scheduler_installed',installed);
end$body$;
revoke all on function public.marketing_service_health() from public,anon,authenticated,service_role;
grant execute on function public.marketing_service_health() to service_role;
commit;
