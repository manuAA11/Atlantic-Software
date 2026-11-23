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

