-- Supabase pgcrypto resides in extensions; SECURITY DEFINER uses an empty search_path.
-- Additive correction: retain the previously applied scheduler migration unchanged.
begin;
set local lock_timeout='8s';
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
commit;
