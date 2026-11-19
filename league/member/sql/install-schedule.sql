-- Apply after the member jobs Edge Function has initialized project_url and VAPID.
-- Existing pg_cron and pg_net are required; no extension is installed by this script.
do $$
begin
 if not exists(select 1 from pg_extension where extname='pg_cron') or not exists(select 1 from pg_extension where extname='pg_net') then raise exception 'Existing pg_cron and pg_net are required.';end if;
 if not exists(select 1 from league_member_private.settings where project_url is not null and vapid_public is not null) then raise exception 'Initialize the member jobs function before scheduling.';end if;
 perform cron.schedule('atlantic-league-member-notices','*/5 * * * *',$job$
  select net.http_post(
   url:=(select project_url from league_member_private.settings where singleton)||'/functions/v1/atlantic-league-member-jobs',
   headers:=jsonb_build_object('Content-Type','application/json','Authorization','Bearer '||(select job_key from league_member_private.settings where singleton)),
   body:='{}'::jsonb,timeout_milliseconds:=60000
  );
 $job$);
end $$;
