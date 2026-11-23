-- Additive read models for member-facing content. No source schema or routine changes.
begin;
create table public.league_member_events(
 id uuid primary key default gen_random_uuid(),gym_id uuid not null references public.league_gym_directory(gym_id),
 title text not null check(length(title) between 1 and 150),description text not null default '',
 starts_at timestamptz not null,location text,organizer text,image_url text,
 status text not null default 'PUBLISHED' check(status in ('DRAFT','PUBLISHED','CANCELLED')),
 version integer not null default 1,updated_at timestamptz not null default now()
);
alter table public.league_member_events enable row level security;
revoke all on public.league_member_events from public,anon,authenticated;
grant all on public.league_member_events to service_role;
create function public.league_member_content(p_actor uuid,p_gym uuid,p_action text) returns jsonb
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
revoke all on function public.league_member_content(uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.league_member_content(uuid,uuid,text) to service_role;
grant select on public.classes,public.gyms,public.trainers,public.reservations,public.league_exercise_catalog,public.gym_routine_templates,public.clients,public.checkins to service_role;
commit;
