-- Exact previous function body verified read-only in both projects 2026-11-26.
-- Recheck definition/owner/ACL drift before a future authorized deployment.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '8s';
CREATE OR REPLACE FUNCTION private.marketing_cron_tick() RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $body$
DECLARE endpoint text; token text; request_id bigint;
BEGIN
 SELECT project_url INTO endpoint FROM private.marketing_scheduler_config WHERE singleton;
 IF endpoint IS NULL THEN RETURN NULL; END IF;
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
COMMIT;
