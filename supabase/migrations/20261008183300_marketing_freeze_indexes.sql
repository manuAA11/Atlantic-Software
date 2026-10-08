-- Cover integration foreign keys without duplicating an existing usable index.
begin;
set local lock_timeout='8s';
do $indexes$
declare fk record;begin
 for fk in
 select c.oid,c.conname,c.conrelid,c.conkey,n.nspname,t.relname
 from pg_constraint c join pg_class t on t.oid=c.conrelid
 join pg_namespace n on n.oid=t.relnamespace
 where c.contype='f' and (
  (n.nspname='private' and t.relname in ('marketing_events','marketing_oauth_states','marketing_sandbox_clients'))
  or (n.nspname='public' and t.relname in ('automation_runs','chatbot_link_requests','marketing_messages','membership_freezes','payment_requests','ticket_daily_consumptions','whatsapp_conversations')))
 loop
  if not exists(
   select 1 from pg_index i join pg_class ix on ix.oid=i.indexrelid
   join pg_am am on am.oid=ix.relam
   where i.indrelid=fk.conrelid and i.indisvalid and i.indisready
    and i.indpred is null and am.amname='btree'
    and not exists(select 1 from unnest(fk.conkey) with ordinality k(attnum,position)
     where i.indkey[(k.position-1)::integer] is distinct from k.attnum)
  ) then
   execute format('create index if not exists %I on %I.%I (%s)',fk.conname||'_idx',fk.nspname,fk.relname,
    (select string_agg(quote_ident(a.attname),',' order by k.position)
     from unnest(fk.conkey) with ordinality k(attnum,position)
     join pg_attribute a on a.attrelid=fk.conrelid and a.attnum=k.attnum));
  end if;
 end loop;
end$indexes$;
commit;
