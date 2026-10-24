-- Read-only metadata. No client, membership, biometric, Auth or Storage rows.
with required_tables(name) as (values
 ('public.gyms'),('public.gym_users'),('public.clients'),('public.trainers'),
 ('public.routines'),('public.exercises'),('public.classes'),('public.reservations'),
 ('public.league_exercise_catalog'),('public.league_coaches'),
 ('public.league_client_profiles'),('public.league_gym_directory')),
required_functions(signature) as (values
 ('league_source_private.staff_role(uuid)'),('league_source_private.enabled(uuid,bigint)'),
 ('league_source_private.athlete(uuid,uuid,text,jsonb)'),
 ('league_private.app(text,jsonb)'),('league_private.service(text,jsonb)'),
 ('private.membership_snapshot_json(uuid,bigint)'),('private.gym_local_date(uuid)'),
 ('public.league_source(uuid,uuid,text,jsonb)')),
required_columns(relation,name) as (values
 ('public.gyms','timezone'),('public.gym_users','role'),('public.clients','active'),
 ('public.routines','client_id'),('public.routines','active'),('public.exercises','notes'),
 ('public.exercises','league_catalog_id'),('public.exercises','league_rest_seconds'),
 ('public.classes','starts_at'),('public.classes','capacity'),('public.classes','status'),
 ('public.reservations','gym_id'),('public.reservations','client_id'),('public.reservations','status')),
new_tables(name) as (values
 ('public.gym_routine_templates'),('league_source_private.training_requests'),
 ('league_source_private.reservation_history'),('league_source_private.training_audit')),
new_functions(signature) as (values
 ('public.gym_training(uuid,text,jsonb)'),('league_source_private.training(uuid,text,jsonb)'),
 ('league_source_private.training_reserve(uuid,bigint,bigint)'),
 ('league_source_private.athlete_before_training(uuid,uuid,text,jsonb)')),
new_columns(relation,name) as (values
 ('public.league_exercise_catalog','active'),('public.league_exercise_catalog','image_url'),
 ('public.league_exercise_catalog','video_url'),('public.league_exercise_catalog','sort_order'),
 ('public.routines','assigned_at'),('public.routines','assigned_by'),('public.routines','previous_routine_id'),
 ('public.classes','conditions'),('public.classes','requires_membership'),('public.classes','duration_minutes'),
 ('public.classes','recurrence_id'),('public.classes','version')),
rpc as (select p.* from pg_proc p where p.oid=to_regprocedure('public.gym_training(uuid,text,jsonb)'))
select jsonb_build_object(
 'format','atlantic.training.preflight.v1','server_version_num',current_setting('server_version_num')::int,
 'required_tables',(select jsonb_object_agg(name,to_regclass(name) is not null) from required_tables),
 'required_functions',(select jsonb_object_agg(signature,to_regprocedure(signature) is not null) from required_functions),
 'required_columns',(select jsonb_object_agg(relation||'.'||name,exists(select 1 from pg_attribute a where a.attrelid=to_regclass(relation) and a.attname=c.name and not a.attisdropped)) from required_columns c),
 'capacity_guard',exists(select 1 from pg_trigger t where t.tgrelid=to_regclass('public.reservations') and not t.tgisinternal
   and t.tgfoid=to_regprocedure('league_source_private.reserve_guard()') and t.tgenabled in ('O','A') and (t.tgtype::int & 23)=23),
 'reservation_unique',exists(select 1 from pg_index i where i.indrelid=to_regclass('public.reservations')
   and i.indisunique and i.indisvalid and i.indimmediate and i.indpred is null and i.indexprs is null
   and (select array_agg(a.attname::text order by a.attname) from unnest(i.indkey) with ordinality k(attnum,n)
        join pg_attribute a on a.attrelid=i.indrelid and a.attnum=k.attnum where k.n<=i.indnkeyatts)=array['class_id','client_id']),
 'new_tables',(select jsonb_object_agg(name,jsonb_build_object('exists',c.oid is not null,'rls',coalesce(c.relrowsecurity,false),
   'client_grants',coalesce(has_table_privilege('anon',c.oid,'SELECT,INSERT,UPDATE,DELETE') or has_table_privilege('authenticated',c.oid,'SELECT,INSERT,UPDATE,DELETE'),false)))
   from new_tables t left join pg_class c on c.oid=to_regclass(t.name)),
 'new_functions',(select jsonb_object_agg(signature,to_regprocedure(signature) is not null) from new_functions),
 'new_columns',(select jsonb_object_agg(relation||'.'||name,exists(select 1 from pg_attribute a where a.attrelid=to_regclass(relation) and a.attname=c.name and not a.attisdropped)) from new_columns c),
 'rpc',(select jsonb_build_object('definer',prosecdef,'anon_execute',has_function_privilege('anon',oid,'EXECUTE'),'authenticated_execute',has_function_privilege('authenticated',oid,'EXECUTE')) from rpc),
 'source_api',(select jsonb_build_object('definer',prosecdef,'anon_execute',has_function_privilege('anon',oid,'EXECUTE'),
   'authenticated_execute',has_function_privilege('authenticated',oid,'EXECUTE'),'service_execute',has_function_privilege('service_role',oid,'EXECUTE'))
   from pg_proc where oid=to_regprocedure('public.league_source(uuid,uuid,text,jsonb)'))
) as preflight;
