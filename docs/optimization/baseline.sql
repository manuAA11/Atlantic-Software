-- Run manually in each verified project; metadata only, never reset counters.
BEGIN READ ONLY;
SET LOCAL statement_timeout = '8s';
SELECT jsonb_build_object(
 'captured_at', clock_timestamp(),
 'database', current_database(),
 'database_bytes', pg_database_size(current_database()),
 'server_started_at', pg_postmaster_start_time(),
 'database_stats', (SELECT to_jsonb(d) FROM (
   SELECT stats_reset,numbackends,xact_commit,xact_rollback,deadlocks,temp_bytes
   FROM pg_stat_database WHERE datname=current_database()
 ) d),
 'statement_reset', (SELECT to_jsonb(s) FROM pg_stat_statements_info s),
 'statements', (SELECT jsonb_agg(s) FROM (
   SELECT userid,dbid,toplevel,queryid,calls,rows,total_exec_time,mean_exec_time
   FROM pg_stat_statements ORDER BY calls DESC LIMIT 100
 ) s),
 'tables', (SELECT jsonb_agg(t) FROM (
   SELECT schemaname,relname,n_live_tup,n_dead_tup,seq_scan,seq_tup_read,idx_scan,
          last_autovacuum,last_autoanalyze
   FROM pg_stat_user_tables WHERE schemaname IN ('public','private')
 ) t),
 'waiting_locks', (SELECT count(*) FROM pg_locks WHERE NOT granted),
 'cron', (SELECT jsonb_agg(j) FROM (
   SELECT jobid,jobname,schedule,active FROM cron.job
 ) j)
) AS baseline;
COMMIT;
