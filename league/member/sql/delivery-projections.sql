-- Update only League member read projections.
begin;
create or replace function league_member_private.membership(p_actor uuid,p_gym uuid)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare source_client bigint;s jsonb;
begin
 source_client:=(league_member_private.connection(p_actor,p_gym)->>'client_id')::bigint;
 if source_client is null then raise exception 'Perfil no disponible.' using errcode='42501';end if;
 s:=private.membership_snapshot_json(p_gym,source_client);
 return jsonb_build_object('membership_id',nullif(s->>'membership_id',''),'plan_name',nullif(s->>'plan_name',''),
  'active',coalesce((s->>'allowed')::boolean,false),'frozen',coalesce((s->>'frozen')::boolean,false),
  'starts_at',nullif(s->>'membership_start',''),'ends_at',case when coalesce((s->>'has_expiration')::boolean,true) then nullif(s->>'membership_end','') else null end,
  'status',case when coalesce((s->>'frozen')::boolean,false) then 'FROZEN' when nullif(s->>'membership_id','') is null then 'NO_PLAN' else coalesce(s->>'status',s->>'membership_state','INACTIVE') end,
  'remaining_days',case when not coalesce((s->>'frozen')::boolean,false) and coalesce((s->>'has_expiration')::boolean,true) and nullif(s->>'membership_end','') is not null then greatest(0,nullif(s->>'membership_end','')::date-private.gym_local_date(p_gym)) else null end,
  'has_expiration',coalesce((s->>'has_expiration')::boolean,true),
  'entry_limit',s->'entry_limit','entries_used',s->'entries_used','entries_remaining',s->'entries_remaining',
  'already_consumed_today',coalesce((s->>'already_consumed_today')::boolean,false),
  'renewal_whatsapp_url',(select nullif(to_jsonb(g)->>'renewal_whatsapp_url','') from public.league_gym_settings g where g.gym_id=p_gym),
  'renewable',coalesce(s->>'membership_type','COMMERCIAL')<>'INTERNAL');
end $$;
revoke all on function league_member_private.membership(uuid,uuid) from public,anon,authenticated;
grant execute on function league_member_private.membership(uuid,uuid) to service_role;
create or replace function public.league_member_content(p_actor uuid,p_gym uuid,p_action text) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare conn jsonb;client bigint;
begin
 conn:=league_member_private.connection(p_actor,p_gym);client:=(conn->>'client_id')::bigint;
 if conn is null then raise exception 'Vinculación no disponible.' using errcode='42501';end if;
 if p_action='calendar' then
  return coalesce(jsonb_agg(to_jsonb(t) order by t.starts_at),'[]') from(
   select k.id::text id,k.name,k.starts_at,k.capacity,k.notes description,k.status,'CLASS'::text kind,
    tr.name trainer,k.duration_minutes,k.conditions,k.requires_membership,g.timezone,
    (select count(*) from public.reservations r where r.gym_id=p_gym and r.class_id=k.id and r.status='RESERVADA') reserved,
    exists(select 1 from public.reservations r where r.gym_id=p_gym and r.class_id=k.id and r.client_id=client and r.status='RESERVADA') mine,
    (select r.status from public.reservations r where r.gym_id=p_gym and r.class_id=k.id and r.client_id=client limit 1) reservation_status,
    null::text location,null::text image_url
   from public.classes k join public.gyms g on g.id=k.gym_id
   left join public.trainers tr on tr.id=k.trainer_id and tr.gym_id=k.gym_id
   where k.gym_id=p_gym and k.starts_at between now()-interval '180 days' and now()+interval '180 days'
   and (k.status='PROGRAMADA' or exists(select 1 from public.reservations r where r.gym_id=p_gym and r.class_id=k.id and r.client_id=client))
   union all
   select e.id::text,e.title,e.starts_at,0,e.description,e.status,'EVENT',e.organizer,null,null,false,g.timezone,0,false,null,e.location,e.image_url
   from public.league_member_events e join public.gyms g on g.id=e.gym_id
   where e.gym_id=p_gym and to_jsonb(e)->>'deleted_at' is null and e.status in ('PUBLISHED','CANCELLED') and e.starts_at between now()-interval '180 days' and now()+interval '180 days'
  )t;
 elsif p_action='catalog' then
  return coalesce(jsonb_agg(jsonb_build_object('id',id,'name',name,'muscle',muscle,'equipment',equipment,'instructions',instructions) order by name),'[]')
  from public.league_exercise_catalog c where coalesce((to_jsonb(c)->>'active')::boolean,true) and ((c.owner_id is null and (c.gym_id=p_gym or (c.gym_id is null and coalesce((select (to_jsonb(s)->>'show_shared_catalog')::boolean from public.league_gym_settings s where s.gym_id=p_gym),true)))) or c.owner_id=p_actor);
 elsif p_action='templates' then
  return coalesce(jsonb_agg(jsonb_build_object('id',id,'name',name,'goal',goal,'notes',notes,'exercises',exercises) order by name),'[]')
  from public.gym_routine_templates where gym_id=p_gym and active;
 elsif p_action='profile' then
  return jsonb_build_object('name',coalesce(nullif(trim(coalesce(c.first_name,'')||' '||coalesce(c.last_name,'')),''),c.full_name),
   'phone',c.phone,'email',c.email,'document_hint',right(c.document,4),
   'attendance',coalesce((select jsonb_agg(t.local_date order by t.local_date desc) from(select distinct local_date from public.checkins where gym_id=p_gym and client_id=client and result='PERMITIDA' order by local_date desc limit 100)t),'[]'))
   from public.clients c where c.id=client and c.gym_id=p_gym;
 end if;
 raise exception 'Acción no disponible.';
end $$;
commit;

