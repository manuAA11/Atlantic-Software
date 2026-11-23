-- Additive member delivery tools. Existing Gym access and billing rules are unchanged.
begin;
set local lock_timeout='5s';
alter table public.league_gym_settings add column if not exists renewal_whatsapp_url text not null default '';
alter table public.league_gym_settings add column if not exists show_shared_catalog boolean not null default true;
alter table public.league_member_events add column if not exists deleted_at timestamptz;
create index if not exists league_member_events_visible on public.league_member_events(gym_id,starts_at) where deleted_at is null;

create or replace function league_source_private.member_admin(p_gym_id uuid,p_action text,p_data jsonb default '{}')
returns jsonb language plpgsql security definer set search_path='' as $$
declare
 role_name text:=league_source_private.training_role(p_gym_id);
 result jsonb; old_request league_source_private.training_requests;
 request uuid; record_key text; resource uuid; expected integer; contact text;
begin
 if p_data is null or jsonb_typeof(p_data)<>'object' or octet_length(p_data::text)>100000 then raise exception 'Solicitud no válida.';end if;
 if p_action in ('event.save','event.archive','event.restore') and role_name<>'admin' then
  raise exception 'Sólo Administración puede gestionar los eventos del gimnasio.' using errcode='42501';
 end if;
 if p_action='settings.get' then
  return jsonb_build_object('role',role_name,'renewal_whatsapp_url',coalesce((select renewal_whatsapp_url from public.league_gym_settings where gym_id=p_gym_id),''),
   'show_shared_catalog',coalesce((select show_shared_catalog from public.league_gym_settings where gym_id=p_gym_id),true));
 elsif p_action='events.list' then
  return coalesce(jsonb_agg(to_jsonb(e) order by e.starts_at,e.id),'[]') from (
   select event.* from public.league_member_events event where event.gym_id=p_gym_id
    and (coalesce((p_data->>'include_deleted')::boolean,false) or event.deleted_at is null)
    and (coalesce(p_data->>'query','')='' or event.title ilike '%'||left(p_data->>'query',100)||'%')
    and (nullif(p_data->>'status','') is null or event.status=p_data->>'status')
   order by event.starts_at,event.id limit least(100,greatest(1,coalesce((p_data->>'limit')::int,50))) offset greatest(0,coalesce((p_data->>'offset')::int,0))
  ) e;
 end if;
 if p_action not in ('settings.save','event.save','event.archive','event.restore','routine.archive','template.archive','catalog.archive') then
  raise exception 'Operación no disponible.';
 end if;
 request:=(p_data->>'request_id')::uuid;
 if request is null then raise exception 'La operación necesita una referencia para guardarse.';end if;
 perform pg_advisory_xact_lock(hashtextextended(p_gym_id::text||request::text,0));
 select * into old_request from league_source_private.training_requests where gym_id=p_gym_id and request_id=request;
 if found then
  if old_request.actor_id<>auth.uid() or old_request.payload<>jsonb_build_object('member_action',p_action,'data',p_data) then
   raise exception 'La referencia ya corresponde a otra operación.';
  end if;
  return old_request.result;
 end if;
 if p_action='settings.save' then
  if role_name<>'admin' then raise exception 'Sólo Administración puede cambiar el contacto del gimnasio.' using errcode='42501';end if;
  contact:=trim(coalesce(p_data->>'renewal_whatsapp_url',''));
  if contact<>'' and contact !~ '^https://(wa[.]me/[1-9][0-9]{6,14}/?|(www[.])?whatsapp[.]com/channel/[A-Za-z0-9_-]{8,128}/?)$' then
   raise exception 'Usa un enlace oficial de WhatsApp: https://wa.me/indicativoynumero o https://whatsapp.com/channel/identificador.';
  end if;
  contact:=rtrim(contact,'/');
  insert into public.league_gym_settings(gym_id,enabled,allow_all_clients,pilot_client_ids,renewal_whatsapp_url,show_shared_catalog)
   values(p_gym_id,false,false,'{}',contact,coalesce((p_data->>'show_shared_catalog')::boolean,false))
   on conflict(gym_id) do update set renewal_whatsapp_url=excluded.renewal_whatsapp_url,show_shared_catalog=excluded.show_shared_catalog;
  result:=jsonb_build_object('renewal_whatsapp_url',contact,'show_shared_catalog',coalesce((p_data->>'show_shared_catalog')::boolean,false));
  record_key:=p_gym_id::text;
 elsif p_action='event.save' then
  if coalesce(length(trim(p_data->>'title')),0) not between 1 and 150 or length(coalesce(p_data->>'description',''))>6000
    or length(coalesce(p_data->>'location',''))>250 or length(coalesce(p_data->>'organizer',''))>150 then raise exception 'Revisa el título y la descripción del evento.';end if;
  if coalesce(p_data->>'status','') not in ('DRAFT','PUBLISHED','CANCELLED') then raise exception 'Estado del evento no válido.';end if;
  if coalesce(p_data->>'starts_at','') !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' then raise exception 'El horario necesita la zona horaria del gimnasio.';end if;
  if nullif(p_data->>'id','') is null then
   insert into public.league_member_events(gym_id,title,description,starts_at,location,organizer,status)
    values(p_gym_id,trim(p_data->>'title'),coalesce(p_data->>'description',''),(p_data->>'starts_at')::timestamptz,
      nullif(trim(p_data->>'location'),''),nullif(trim(p_data->>'organizer'),''),p_data->>'status') returning to_jsonb(league_member_events.*) into result;
  else
   resource:=(p_data->>'id')::uuid;expected:=(p_data->>'version')::integer;
   update public.league_member_events e set title=trim(p_data->>'title'),description=coalesce(p_data->>'description',''),starts_at=(p_data->>'starts_at')::timestamptz,
    location=nullif(trim(p_data->>'location'),''),organizer=nullif(trim(p_data->>'organizer'),''),status=p_data->>'status',
    version=e.version+1,updated_at=now()
    where e.gym_id=p_gym_id and e.id=resource and e.version=expected and e.deleted_at is null returning to_jsonb(e.*) into result;
   if result is null then raise exception 'El evento cambió o ya fue eliminado. Actualiza la lista antes de editar.' using errcode='40001';end if;
  end if;
  record_key:=result->>'id';
 elsif p_action in ('event.archive','event.restore') then
  resource:=(p_data->>'id')::uuid;expected:=(p_data->>'version')::integer;
  update public.league_member_events e set deleted_at=case when p_action='event.archive' then now() else null end,version=e.version+1,updated_at=now()
   where e.gym_id=p_gym_id and e.id=resource and e.version=expected
    and ((p_action='event.archive' and e.deleted_at is null) or (p_action='event.restore' and e.deleted_at is not null)) returning to_jsonb(e.*) into result;
  if result is null then raise exception 'El evento cambió. Actualiza la lista antes de continuar.' using errcode='40001';end if;
  record_key:=resource::text;
 elsif p_action='routine.archive' then
  update public.routines set active=false where gym_id=p_gym_id and id=(p_data->>'id')::bigint and active returning jsonb_build_object('id',id,'active',active) into result;
  if result is null then raise exception 'La rutina ya fue archivada o no está disponible.';end if;
  record_key:=result->>'id';
 elsif p_action='template.archive' then
  update public.gym_routine_templates set active=false,updated_at=now() where gym_id=p_gym_id and id=(p_data->>'id')::uuid and active returning jsonb_build_object('id',id,'active',active) into result;
  if result is null then raise exception 'Sólo puedes archivar plantillas propias del gimnasio.' using errcode='42501';end if;
  record_key:=result->>'id';
 elsif p_action='catalog.archive' then
  update public.league_exercise_catalog set active=false where gym_id=p_gym_id and owner_id is null and id=(p_data->>'id')::uuid and active returning jsonb_build_object('id',id,'active',active) into result;
  if result is null then raise exception 'Sólo puedes archivar ejercicios propios del gimnasio.' using errcode='42501';end if;
  record_key:=result->>'id';
 end if;
 insert into league_source_private.training_requests(gym_id,request_id,actor_id,payload,result)
  values(p_gym_id,request,auth.uid(),jsonb_build_object('member_action',p_action,'data',p_data),result);
 insert into league_source_private.training_audit(gym_id,actor_id,action,record_id) values(p_gym_id,auth.uid(),'member.'||p_action,record_key);
 return result;
end $$;
revoke all on function league_source_private.member_admin(uuid,text,jsonb) from public,anon;
grant execute on function league_source_private.member_admin(uuid,text,jsonb) to authenticated;
create or replace function public.gym_member_admin(p_gym_id uuid,p_action text,p_data jsonb default '{}')
returns jsonb language sql security invoker set search_path='' as $$
 select league_source_private.member_admin(p_gym_id,p_action,p_data);
$$;
revoke all on function public.gym_member_admin(uuid,text,jsonb) from public,anon;
grant execute on function public.gym_member_admin(uuid,text,jsonb) to authenticated;

-- Keep the original validated training engine; only filter the optional shared examples.
create or replace function public.gym_training(p_gym_id uuid,p_action text,p_data jsonb default '{}')
returns jsonb language plpgsql security invoker set search_path='' as $$
declare result jsonb;settings jsonb;
begin
 result:=league_source_private.training(p_gym_id,p_action,p_data);
 if p_action in ('catalog','templates') then
  settings:=public.gym_member_admin(p_gym_id,'settings.get','{}');
  if not (settings->>'show_shared_catalog')::boolean then
   select coalesce(jsonb_agg(value),'[]') into result from jsonb_array_elements(result) where value->>'gym_id'=p_gym_id::text;
  end if;
 end if;
 return result;
end $$;
notify pgrst,'reload schema';
commit;


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

