-- Solo lectura. No registra pagos, entradas ni cambios.
select public.commercial_system_info() as version_instalada;
-- ticket_features_version debe indicar 3.3.0.
select table_name,column_name,data_type from information_schema.columns
where table_schema='public' and ((table_name='plans' and column_name='duration_months') or
(table_name='memberships' and column_name in ('initial_entries_used','carryover_key')));
-- Tres endpoints: invoker/autenticado=true, anonimo=false.
select p.proname as funcion,not p.prosecdef as invoker,
has_function_privilege('authenticated',p.oid,'execute') as autenticado,
has_function_privilege('anon',p.oid,'execute') as anonimo
from pg_proc p join pg_namespace n on n.oid=p.pronamespace
where n.nspname='public' and p.proname in ('ticket_followup','session_followup','register_ticket_carryover');
