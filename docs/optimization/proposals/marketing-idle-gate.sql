-- REVIEW CANDIDATE ONLY. Not an installed migration.
-- Requires a recoverable backup and verification before production.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '8s';
CREATE OR REPLACE FUNCTION private.marketing_cron_tick() RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $body$
DECLARE endpoint text; token text; request_id bigint;
BEGIN
 SELECT project_url INTO endpoint FROM private.marketing_scheduler_config WHERE singleton;
 IF endpoint IS NULL THEN RETURN NULL; END IF;

 -- Conservative: any enabled feature/rule or in-flight/queued message wakes
 -- the original worker, including future jobs and ambiguous stale claims.
 -- Do not change schedules, claims, retry policy, or membership calculations.
 IF NOT EXISTS (
   SELECT 1 FROM public.marketing_settings
   WHERE whatsapp_enabled OR chatbot_enabled OR marketing_automation_enabled OR online_payments_enabled
 ) AND NOT EXISTS (
   SELECT 1 FROM public.marketing_automations WHERE enabled AND deleted_at IS NULL
 ) AND NOT EXISTS (
   SELECT 1 FROM public.marketing_messages WHERE status IN ('QUEUED','PROCESSING')
 ) AND EXISTS (
   -- Skip the duplicate freeze pass only while the dedicated minute job
   -- is present and enabled with the known command in this database.
   SELECT 1 FROM cron.job
   WHERE jobname = 'gymsoft-freeze-completion' AND active
     AND schedule = '* * * * *'
     AND database = current_database()
     AND btrim(command) IN ('select private.freeze_complete_due()', 'select private.freeze_complete_due();')
 ) THEN
   RETURN NULL;
 END IF;

 SELECT v.decrypted_secret INTO token FROM vault.decrypted_secrets v
 JOIN private.marketing_platform p ON p.scheduler_secret_id = v.id WHERE p.singleton;
 IF token IS NULL THEN RAISE EXCEPTION 'Scheduler no configurado.'; END IF;
 SELECT net.http_post(url := endpoint || '/functions/v1/marketing/jobs',
   headers := jsonb_build_object('Content-Type','application/json','x-marketing-scheduler',token),
   body := '{}'::jsonb, timeout_milliseconds := 55000) INTO request_id;
 UPDATE private.marketing_scheduler_config
 SET last_requested_at = clock_timestamp(), last_request_id = request_id WHERE singleton;
 RETURN request_id;
END
$body$;
-- CREATE OR REPLACE preserves existing owner, privileges and signature.
-- No new public RPC; no table/role/grant/schedule changes.
COMMIT;
