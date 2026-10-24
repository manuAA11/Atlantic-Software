// Compose a bounded, atomic deployment from the versioned migration.
// No connection, credentials, customer export, or production writes here.
export function guardedTrainingMigration(sql){
 if(!sql.includes('\nbegin;')||!sql.trimEnd().endsWith('commit;'))throw Error('Expected atomic training migration');
 const body=sql.replace('\nbegin;','\n').replace(/commit;\s*$/,'');
 const prefix=String.raw`begin;
set local lock_timeout='5s';
set local statement_timeout='20s';
create temporary table atlantic_training_before(object text primary key, payload jsonb) on commit drop;
create function pg_temp.training_snapshot() returns table(object text,payload jsonb) language plpgsql as $guard$
declare relation text; value jsonb;
begin
 foreach relation in array array['league_exercise_catalog','routines','exercises','classes','reservations'] loop
  execute format('select coalesce(jsonb_agg(d order by d::text),''[]''::jsonb) from (select to_jsonb(t)-$1 as d from public.%I t) x',relation)
   into value using array['active','image_url','video_url','sort_order','previous_routine_id','assigned_by','assigned_at','duration_minutes','conditions','requires_membership','recurrence_id','version'];
  -- Preserve existing active flags too; remove it only from the catalog.
  if relation<>'league_exercise_catalog' then
   execute format('select coalesce(jsonb_agg(d order by d::text),''[]''::jsonb) from (select to_jsonb(t)-$1 as d from public.%I t) x',relation)
    into value using array['image_url','video_url','sort_order','previous_routine_id','assigned_by','assigned_at','duration_minutes','conditions','requires_membership','recurrence_id','version'];
  end if;
  object:=relation;payload:=value;return next;
 end loop;
 select coalesce(jsonb_object_agg(p.oid::regprocedure::text,md5(pg_get_functiondef(p.oid))||coalesce(p.proacl::text,'')),'{}'::jsonb) into value
  from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prokind='f' and p.proname not in ('league_source','gym_training');
 object:='legacy_public_rpc';payload:=value;return next;
 select coalesce(jsonb_agg(to_jsonb(u) order by to_jsonb(u)::text),'[]'::jsonb) into value from public.gym_users u;
 object:='gym_users';payload:=value;return next;
end $guard$;
insert into atlantic_training_before select * from pg_temp.training_snapshot();
`;
 const suffix=String.raw`
do $guard$ begin
 if exists(select 1 from atlantic_training_before b full join pg_temp.training_snapshot() a using(object) where b.payload is distinct from a.payload) then
  raise exception 'Training deployment rejected: existing records, accounts or legacy RPCs changed';
 end if;
 if (select prosecdef from pg_proc where oid='public.gym_training(uuid,text,jsonb)'::regprocedure)
  or not has_function_privilege('authenticated','public.gym_training(uuid,text,jsonb)','EXECUTE')
  or has_function_privilege('anon','public.gym_training(uuid,text,jsonb)','EXECUTE') then
  raise exception 'Training deployment rejected: new RPC permissions';
 end if;
 if has_function_privilege('authenticated','public.league_source(uuid,uuid,text,jsonb)','EXECUTE')
  or has_function_privilege('anon','public.league_source(uuid,uuid,text,jsonb)','EXECUTE')
  or not has_function_privilege('service_role','public.league_source(uuid,uuid,text,jsonb)','EXECUTE') then
  raise exception 'Training deployment rejected: source service permissions';
 end if;
end $guard$;
drop function pg_temp.training_snapshot();
commit;
`;
 return prefix+body+suffix;
}

