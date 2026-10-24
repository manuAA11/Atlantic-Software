-- Co-located Gym + League catalog. No seed/customer changes in this migration.
-- Prerequisites: existing Gym schema + League hub + source adapter in same DB.
begin;
set local lock_timeout='5s';
do $$ begin
 if to_regclass('public.league_exercise_catalog') is null or to_regclass('public.league_coaches') is null then
  raise exception 'Instala primero el catálogo League y el adaptador Gym en este mismo proyecto.';
 end if;
end $$;
alter table public.league_exercise_catalog add column if not exists active boolean not null default true;
alter table public.league_exercise_catalog add column if not exists image_url text not null default '';
alter table public.league_exercise_catalog add column if not exists video_url text not null default '';
alter table public.league_exercise_catalog add column if not exists sort_order integer not null default 0;
alter table public.routines add column if not exists previous_routine_id bigint references public.routines(id);
alter table public.routines add column if not exists assigned_by uuid;
alter table public.routines add column if not exists assigned_at timestamptz;
alter table public.classes add column if not exists duration_minutes integer check(duration_minutes between 5 and 600);
alter table public.classes add column if not exists conditions text not null default '';
-- Preserve legacy desktop enrollment rules. New editor explicitly chooses a condition.
alter table public.classes add column if not exists requires_membership boolean not null default false;
alter table public.classes add column if not exists recurrence_id uuid;
alter table public.classes add column if not exists version integer not null default 1;
create table if not exists public.gym_routine_templates(
 id uuid primary key default gen_random_uuid(),gym_id uuid references public.gyms(id),
 name text not null check(length(name) between 2 and 120),goal text not null default '',
 notes text not null default '',exercises jsonb not null check(jsonb_typeof(exercises)='array'),
 active boolean not null default true,seed_key text unique,created_by uuid,updated_at timestamptz not null default now()
);
create table if not exists league_source_private.training_requests(
 gym_id uuid not null,request_id uuid not null,actor_id uuid not null,payload jsonb not null,result jsonb not null,
 created_at timestamptz not null default now(),primary key(gym_id,request_id)
);
create table if not exists league_source_private.reservation_history(
 id bigint generated always as identity primary key,gym_id uuid not null,reservation_id bigint not null,
 class_id bigint not null,client_id bigint not null,previous_status text,status text not null,
 actor_id uuid,created_at timestamptz not null default now()
);
create table if not exists league_source_private.training_audit(
 id bigint generated always as identity primary key,gym_id uuid not null,actor_id uuid not null,
 action text not null,record_id text,created_at timestamptz not null default now()
);
create index if not exists gym_training_clients on public.routines(gym_id,client_id,active);
create index if not exists gym_training_exercises on public.exercises(gym_id,routine_id,position);
create index if not exists gym_training_classes on public.classes(gym_id,starts_at,status);
create index if not exists gym_training_reservations on public.reservations(gym_id,class_id,status);
create index if not exists gym_training_history on league_source_private.reservation_history(gym_id,class_id,created_at desc);
alter table public.gym_routine_templates enable row level security;
alter table league_source_private.training_requests enable row level security;
alter table league_source_private.reservation_history enable row level security;
alter table league_source_private.training_audit enable row level security;
revoke all on public.gym_routine_templates from public,anon,authenticated;
revoke all on league_source_private.training_requests,league_source_private.reservation_history,league_source_private.training_audit from public,anon,authenticated;

create or replace function league_source_private.training_role(g uuid) returns text language plpgsql stable security definer set search_path='' as $$
declare r text;
begin
 r:=league_source_private.staff_role(g);
 if to_regprocedure('private.current_access(uuid)') is not null then
  if not private.current_access(g) then raise exception 'La cuenta o el equipo no tiene acceso al gimnasio.' using errcode='42501';end if;
 end if;
 return r;
end $$;
create or replace function league_source_private.training_items(g uuid,items jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare e jsonb;c public.league_exercise_catalog;out_items jsonb:='[]';n integer:=0;
begin
 if jsonb_typeof(items) is distinct from 'array' or jsonb_array_length(items) not between 1 and 100 then raise exception 'Selecciona entre 1 y 100 ejercicios.';end if;
 for e in select value from jsonb_array_elements(items) loop
  select * into c from public.league_exercise_catalog where id=(e->>'catalog_id')::uuid and active and owner_id is null and (gym_id is null or gym_id=g);
  if not found then raise exception 'Uno de los ejercicios no está disponible.' using errcode='42501';end if;
  if coalesce((e->>'sets')::int,0) not between 1 and 20 or coalesce((e->>'reps')::int,0) not between 1 and 100 or
   coalesce((e->>'weight_kg')::numeric,-1) not between 0 and 1000 or coalesce((e->>'rest_seconds')::int,-1) not between 0 and 600 or
   coalesce(length(trim(e->>'day')),0) not between 1 and 80 or length(coalesce(e->>'notes',''))>2000 then raise exception 'Revisa las series, repeticiones, peso, día y descanso.';end if;
  n:=n+1;
  out_items:=out_items||jsonb_build_array(e||jsonb_build_object('name',c.name,'position',n));
 end loop;
 return out_items;
end $$;

-- Covers all writers, including the existing desktop and mobile paths.
create or replace function league_source_private.reserve_guard() returns trigger language plpgsql security definer set search_path='' as $$
declare c public.classes;used integer;
begin
 if new.status not in ('RESERVADA','ASISTIO') then return new;end if;
 select * into c from public.classes where id=new.class_id and gym_id=new.gym_id for update;
 if not found then raise exception 'Clase no disponible.' using errcode='42501';end if;
 if tg_op='UPDATE' and old.status in ('RESERVADA','ASISTIO') and old.gym_id=new.gym_id and old.class_id=new.class_id and old.client_id=new.client_id then
  return new;
 end if;
 if new.status='ASISTIO' then raise exception 'Registra primero la reserva.';end if;
 if c.status<>'PROGRAMADA' or c.starts_at<=now() then raise exception 'La clase no está disponible para reservas.';end if;
 if not exists(select 1 from public.clients where id=new.client_id and gym_id=new.gym_id and active) then raise exception 'Cliente no disponible.' using errcode='42501';end if;
 if c.requires_membership and not coalesce((private.membership_snapshot_json(new.gym_id,new.client_id)->>'allowed')::boolean,false) then raise exception 'La inscripción requiere una membresía vigente y habilitada.';end if;
 select count(*) into used from public.reservations where gym_id=new.gym_id and class_id=new.class_id and status in ('RESERVADA','ASISTIO') and id is distinct from new.id;
 if used>=c.capacity then raise exception 'La clase ya no tiene cupos disponibles.' using errcode='23514';end if;
 return new;
end $$;
create or replace function league_source_private.training_class_guard() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if new.trainer_id is not null and not exists(select 1 from public.trainers where id=new.trainer_id and gym_id=new.gym_id) then raise exception 'Entrenador no disponible.' using errcode='42501';end if;
 if tg_op='UPDATE' then
  if new.gym_id<>old.gym_id then raise exception 'No se puede mover una clase a otro gimnasio.';end if;
  if new.capacity<(select count(*) from public.reservations where gym_id=new.gym_id and class_id=new.id and status in ('RESERVADA','ASISTIO')) then raise exception 'Los cupos no pueden ser menores que las inscripciones.';end if;
  new.version:=old.version+1;
 end if;
 return new;
end $$;
drop trigger if exists gym_training_class_guard on public.classes;
create trigger gym_training_class_guard before insert or update on public.classes for each row execute function league_source_private.training_class_guard();
create or replace function league_source_private.training_class_cancel() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if new.status='CANCELADA' and old.status is distinct from new.status then
  update public.reservations set status='CANCELADA' where gym_id=new.gym_id and class_id=new.id and status='RESERVADA';
 end if;return new;
end $$;
drop trigger if exists gym_training_class_cancel on public.classes;
create trigger gym_training_class_cancel after update on public.classes for each row execute function league_source_private.training_class_cancel();
create or replace function league_source_private.training_reservation_history() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if tg_op='INSERT' or old.status is distinct from new.status then
  insert into league_source_private.reservation_history(gym_id,reservation_id,class_id,client_id,previous_status,status,actor_id)
   values(new.gym_id,new.id,new.class_id,new.client_id,case when tg_op='UPDATE' then old.status end,new.status,auth.uid());
 end if;return new;
end $$;
drop trigger if exists gym_training_reservation_history on public.reservations;
create trigger gym_training_reservation_history after insert or update on public.reservations for each row execute function league_source_private.training_reservation_history();

create or replace function league_source_private.training(g uuid,a text,d jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare role_name text:=league_source_private.training_role(g);result jsonb;items jsonb;picked jsonb;
 rid bigint;cid bigint;tid bigint;old_routine public.routines;cl public.classes;request uuid;
 old_request league_source_private.training_requests;recur uuid;stamp timestamptz;wall timestamp;next_stamp timestamptz;zone_name text;count_classes int;off int:=greatest(0,coalesce((d->>'offset')::int,0));lim int:=least(100,greatest(1,coalesce((d->>'limit')::int,100)));q text:=left(coalesce(d->>'query',''),100);
begin
 if octet_length(d::text)>150000 then raise exception 'Reduce el tamaño de la solicitud.';end if;
 if a='context' then return jsonb_build_object('role',role_name,'gym_id',g,'schema','training-1','today',private.gym_local_date(g));end if;
 if a='trainers' then
  return coalesce(jsonb_agg(jsonb_build_object('id',t.id,'name',t.name) order by t.name),'[]') from public.trainers t where t.gym_id=g and t.active;
 elsif a='staff' then
  if role_name<>'admin' then raise exception 'Permiso de administración requerido.' using errcode='42501';end if;
  return coalesce(jsonb_agg(jsonb_build_object('id',u.user_id,'name',a.email,'role',u.role,'coach',exists(select 1 from public.league_coaches c where c.gym_id=g and c.user_id=u.user_id)) order by a.email),'[]')
   from public.gym_users u join auth.users a on a.id=u.user_id where u.gym_id=g and coalesce((to_jsonb(u)->>'enabled')::boolean,true);
 elsif a='catalog' then
  return coalesce(jsonb_agg(to_jsonb(c) order by c.sort_order,c.name),'[]') from public.league_exercise_catalog c
   where c.owner_id is null and (c.gym_id is null or c.gym_id=g) and (c.active or coalesce((d->>'include_inactive')::boolean,false));
 elsif a='templates' then
  return coalesce(jsonb_agg(to_jsonb(t) order by t.name),'[]') from public.gym_routine_templates t where t.active and (t.gym_id is null or t.gym_id=g);
 elsif a='clients' then
  return coalesce(jsonb_agg(t order by t.name,t.id),'[]') from (
   select c.id,trim(c.first_name||' '||c.last_name) as name,coalesce(to_jsonb(c)->>'document','') as document,
    exists(select 1 from public.routines r where r.gym_id=g and r.client_id=c.id and r.active) as has_routine
   from public.clients c where c.gym_id=g and c.active and
    (trim(c.first_name||' '||c.last_name) ilike '%'||q||'%' or coalesce(to_jsonb(c)->>'document','') ilike '%'||q||'%')
    and (not coalesce((d->>'unassigned')::boolean,false) or not exists(select 1 from public.routines r where r.gym_id=g and r.client_id=c.id and r.active))
   order by c.first_name,c.last_name,c.id limit lim offset off)t;
 elsif a='routines' then
  return coalesce(jsonb_agg(t order by t.id desc),'[]') from (
   select r.*,trim(c.first_name||' '||c.last_name) as client_name,coalesce(t.name,'Sin asignar') as trainer_name,
    (select count(*) from public.exercises e where e.gym_id=g and e.routine_id=r.id) as exercise_count
   from public.routines r join public.clients c on c.id=r.client_id and c.gym_id=g left join public.trainers t on t.id=r.trainer_id and t.gym_id=g
   where r.gym_id=g and (d->>'client_id' is null or r.client_id=(d->>'client_id')::bigint)
    and (d->>'status' is null or r.active=(d->>'status'='ACTIVA'))
    and (r.name||' '||c.first_name||' '||c.last_name||' '||coalesce(t.name,'')) ilike '%'||q||'%'
   order by r.id desc limit lim offset off)t;
 elsif a='routine.detail' then
  return to_jsonb(r)||jsonb_build_object('exercises',(select coalesce(jsonb_agg(to_jsonb(e)||jsonb_build_object('catalog_id',e.league_catalog_id,'day',e.day_name,'weight_kg',e.weight,'rest_seconds',coalesce(e.league_rest_seconds,90)) order by e.position,e.id),'[]') from public.exercises e where e.gym_id=g and e.routine_id=r.id))
   from public.routines r where r.gym_id=g and r.id=(d->>'id')::bigint;
 elsif a='class.calendar' then
  if d->>'date_from' is null or d->>'date_to' is null or (d->>'date_to')::date-(d->>'date_from')::date not between 0 and 62 then raise exception 'Selecciona un período de hasta dos meses.';end if;
  return coalesce(jsonb_agg(to_jsonb(t) order by t.day),'[]') from (
   select (c.starts_at at time zone (select timezone from public.gyms where id=g))::date as day,count(*) as classes
   from public.classes c where c.gym_id=g and c.name ilike '%'||q||'%'
    and (d->>'trainer_id' is null or c.trainer_id=(d->>'trainer_id')::bigint)
    and (d->>'status' is null or c.status=d->>'status')
    and c.starts_at>=((d->>'date_from')::date::timestamp at time zone (select timezone from public.gyms where id=g))
    and c.starts_at<(((d->>'date_to')::date+1)::timestamp at time zone (select timezone from public.gyms where id=g))
   group by 1)t;
 elsif a='classes' then
  return coalesce(jsonb_agg(t order by t.starts_at,t.id),'[]') from (
   select c.*,coalesce(t.name,'Sin asignar') as trainer_name,
    (select count(*) from public.reservations r where r.gym_id=g and r.class_id=c.id and r.status in ('RESERVADA','ASISTIO')) as reserved
   from public.classes c left join public.trainers t on t.id=c.trainer_id and t.gym_id=g where c.gym_id=g and c.name ilike '%'||q||'%'
    and (d->>'trainer_id' is null or c.trainer_id=(d->>'trainer_id')::bigint)
    and (d->>'status' is null or c.status=d->>'status')
    and (d->>'date_from' is null or c.starts_at>=((d->>'date_from')::date::timestamp at time zone (select timezone from public.gyms where id=g)))
    and (d->>'date_to' is null or c.starts_at<(((d->>'date_to')::date+1)::timestamp at time zone (select timezone from public.gyms where id=g)))
   order by c.starts_at,c.id limit lim offset off)t;
 elsif a='reservations' then
  return coalesce(jsonb_agg(t order by t.starts_at desc,t.id),'[]') from (
   select r.*,c.name as class_name,c.starts_at,c.capacity,trim(p.first_name||' '||p.last_name) as client_name,coalesce(to_jsonb(p)->>'document','') as document
   from public.reservations r join public.classes c on c.gym_id=g and c.id=r.class_id join public.clients p on p.gym_id=g and p.id=r.client_id
   where r.gym_id=g and (d->>'class_id' is null or r.class_id=(d->>'class_id')::bigint)
    and (trim(p.first_name||' '||p.last_name)||' '||coalesce(to_jsonb(p)->>'document','')||' '||c.name) ilike '%'||q||'%'
    and (d->>'status' is null or r.status=d->>'status')
    and (d->>'date_from' is null or c.starts_at>=((d->>'date_from')::date::timestamp at time zone (select timezone from public.gyms where id=g)))
    and (d->>'date_to' is null or c.starts_at<(((d->>'date_to')::date+1)::timestamp at time zone (select timezone from public.gyms where id=g)))
   order by c.starts_at desc,r.id limit lim offset off)t;
 elsif a='reservation.history' then
  return coalesce(jsonb_agg(to_jsonb(h) order by h.id desc),'[]') from league_source_private.reservation_history h
   where h.gym_id=g and h.reservation_id=(d->>'id')::bigint;
 end if;
 -- Every mutation is idempotent, scoped to gym and actor, and atomic.
 request:=(d->>'request_id')::uuid;
 if request is null then raise exception 'La operación necesita una referencia para guardarse.';end if;
 perform pg_advisory_xact_lock(hashtextextended(g::text||request::text,0));
 select * into old_request from league_source_private.training_requests where gym_id=g and request_id=request;
 if found then
  if old_request.actor_id<>auth.uid() or old_request.payload<>jsonb_build_object('action',a,'data',d) then raise exception 'La referencia ya corresponde a otra operación.';end if;
  return old_request.result;
 end if;
 if a='coach.grant' then
  if role_name<>'admin' then raise exception 'Permiso de administración requerido.' using errcode='42501';end if;
  if not exists(select 1 from public.gym_users where gym_id=g and user_id=(d->>'user_id')::uuid and coalesce((to_jsonb(gym_users)->>'enabled')::boolean,true)) then raise exception 'La cuenta no pertenece al gimnasio.' using errcode='42501';end if;
  if coalesce((d->>'enabled')::boolean,false) then
   insert into public.league_coaches(gym_id,user_id,granted_by) values(g,(d->>'user_id')::uuid,auth.uid()) on conflict do nothing;
  else
   delete from public.league_coaches where gym_id=g and user_id=(d->>'user_id')::uuid;
  end if;
  result:=jsonb_build_object('enabled',coalesce((d->>'enabled')::boolean,false));
 elsif a='catalog.save' then
  if coalesce(length(trim(d->>'name')),0) not between 2 and 120 or length(coalesce(d->>'instructions',''))>4000 then raise exception 'Revisa el nombre y las indicaciones.';end if;
  if (coalesce(d->>'image_url','')<>'' and d->>'image_url' !~ '^https://[^[:space:]]+$') or (coalesce(d->>'video_url','')<>'' and d->>'video_url' !~ '^https://[^[:space:]]+$') then raise exception 'Usa enlaces HTTPS para las imágenes y videos.';end if;
  if d->>'id' is null then
   if not exists(select 1 from public.league_gym_directory where gym_id=g) then
    if coalesce(d->>'source_ref','') !~ '^[a-z0-9]{20}$' then raise exception 'Revisa la configuración del proyecto.';end if;
    -- Routing metadata only. Core remains the sole authority for activation.
    insert into public.league_gym_directory(gym_id,source_ref,name,athlete_code,enabled)
     select g,d->>'source_ref',name,'GYM-'||upper(substr(replace(g::text,'-',''),1,20)),false from public.gyms where id=g on conflict(gym_id) do nothing;
   end if;
   insert into public.league_exercise_catalog(gym_id,name,muscle,equipment,instructions,image_url,video_url,sort_order)
    values(g,trim(d->>'name'),left(coalesce(d->>'muscle',''),80),left(coalesce(d->>'equipment',''),120),coalesce(d->>'instructions',''),coalesce(d->>'image_url',''),coalesce(d->>'video_url',''),coalesce((d->>'sort_order')::int,0)) returning to_jsonb(league_exercise_catalog.*) into result;
  else
   update public.league_exercise_catalog set name=trim(d->>'name'),muscle=left(coalesce(d->>'muscle',''),80),equipment=left(coalesce(d->>'equipment',''),120),instructions=coalesce(d->>'instructions',''),
    active=coalesce((d->>'active')::boolean,true),image_url=coalesce(d->>'image_url',''),video_url=coalesce(d->>'video_url',''),sort_order=coalesce((d->>'sort_order')::int,0)
    where id=(d->>'id')::uuid and gym_id=g and owner_id is null returning to_jsonb(league_exercise_catalog.*) into result;
   if result is null then raise exception 'Los ejercicios globales se adaptan creando una variante del gimnasio.' using errcode='42501';end if;
  end if;
 elsif a='template.save' then
  items:=league_source_private.training_items(g,d->'exercises');
  if coalesce(length(trim(d->>'name')),0) not between 2 and 120 then raise exception 'Escribe el nombre de la plantilla.';end if;
  if d->>'id' is null then
   insert into public.gym_routine_templates(gym_id,name,goal,notes,exercises,created_by) values(g,trim(d->>'name'),coalesce(d->>'goal',''),coalesce(d->>'notes',''),items,auth.uid()) returning to_jsonb(gym_routine_templates.*) into result;
  else
   update public.gym_routine_templates set name=trim(d->>'name'),goal=coalesce(d->>'goal',''),notes=coalesce(d->>'notes',''),exercises=items,active=coalesce((d->>'active')::boolean,true),updated_at=now()
    where id=(d->>'id')::uuid and gym_id=g returning to_jsonb(gym_routine_templates.*) into result;
   if result is null then raise exception 'Duplica la plantilla global para adaptarla al gimnasio.' using errcode='42501';end if;
  end if;
 elsif a='routine.assign' then
  items:=league_source_private.training_items(g,d->'exercises');
  if coalesce(length(trim(d->>'name')),0) not between 2 and 120 or jsonb_typeof(d->'clients') is distinct from 'array' or jsonb_array_length(d->'clients') not between 1 and 50 then raise exception 'Selecciona de 1 a 50 clientes y escribe el nombre del plan.';end if;
  if (select count(distinct value) from jsonb_array_elements(d->'clients'))<>jsonb_array_length(d->'clients') then raise exception 'No repitas clientes en la asignación.';end if;
  tid:=nullif(d->>'trainer_id','')::bigint;
  if tid is not null and not exists(select 1 from public.trainers where gym_id=g and id=tid and active) then raise exception 'Entrenador no disponible.' using errcode='42501';end if;
  if d->>'previous_id' is not null then
   select * into old_routine from public.routines where id=(d->>'previous_id')::bigint and gym_id=g for update;
   if not found or not old_routine.active or jsonb_array_length(d->'clients')<>1 or (d->'clients'->>0)::bigint<>old_routine.client_id then raise exception 'El plan cambió. Actualiza la lista antes de editarlo.';end if;
   update public.routines set active=false where id=old_routine.id and gym_id=g;
  end if;
  result:='[]';
  for picked in select value from jsonb_array_elements(d->'clients') loop
   cid:=(picked#>>'{}')::bigint;
   if not exists(select 1 from public.clients where id=cid and gym_id=g and active) then raise exception 'Cliente no disponible.' using errcode='42501';end if;
   insert into public.routines(gym_id,client_id,trainer_id,name,goal,start_date,notes,active,previous_routine_id,assigned_by,assigned_at)
    values(g,cid,tid,trim(d->>'name'),coalesce(d->>'goal',''),coalesce((d->>'start_date')::date,private.gym_local_date(g)),coalesce(d->>'notes',''),true,old_routine.id,auth.uid(),now()) returning id into rid;
   insert into public.exercises(gym_id,routine_id,day_name,name,sets,reps,weight,notes,position,league_catalog_id,league_rest_seconds)
    select g,rid,value->>'day',value->>'name',value->>'sets',value->>'reps',value->>'weight_kg',coalesce(value->>'notes',''),(value->>'position')::int,(value->>'catalog_id')::uuid,(value->>'rest_seconds')::int from jsonb_array_elements(items);
   result:=result||jsonb_build_array(jsonb_build_object('routine_id',rid,'client_id',cid));
  end loop;
 elsif a='class.save' then
  tid:=nullif(d->>'trainer_id','')::bigint;
  if tid is not null and not exists(select 1 from public.trainers where gym_id=g and id=tid and active) then raise exception 'Entrenador no disponible.' using errcode='42501';end if;
  if coalesce(d->>'starts_at','') !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' then raise exception 'Indica la fecha, la hora y la zona horaria.';end if;
  stamp:=(d->>'starts_at')::timestamptz;
  if coalesce(length(trim(d->>'name')),0) not between 2 and 120 or stamp is null or coalesce((d->>'capacity')::int,0) not between 1 and 5000 or coalesce((d->>'duration_minutes')::int,0) not between 5 and 600 then raise exception 'Revisa el nombre, el horario, la duración y los cupos.';end if;
  if coalesce(d->>'status','PROGRAMADA') not in ('PROGRAMADA','CANCELADA','FINALIZADA') then raise exception 'Estado de clase no válido.';end if;
  if d->>'id' is not null then
   select * into cl from public.classes where id=(d->>'id')::bigint and gym_id=g for update;
   if not found then raise exception 'Clase no disponible.' using errcode='42501';end if;
   if cl.version<>coalesce((d->>'version')::int,0) then raise exception 'La clase cambió. Actualiza antes de guardar.';end if;
   update public.classes set name=trim(d->>'name'),trainer_id=tid,starts_at=stamp,capacity=(d->>'capacity')::int,notes=coalesce(d->>'notes',''),duration_minutes=(d->>'duration_minutes')::int,
    conditions=coalesce(d->>'conditions',''),requires_membership=coalesce((d->>'requires_membership')::boolean,false),status=coalesce(d->>'status','PROGRAMADA') where id=cl.id and gym_id=g;
   result:=jsonb_build_array(jsonb_build_object('class_id',cl.id));
  else
   if stamp<=now() then raise exception 'Selecciona una fecha futura.';end if;
   count_classes:=coalesce((d->>'repeat_count')::int,1);
   if count_classes not between 1 and 26 or coalesce((d->>'interval_weeks')::int,1) not between 1 and 12 then raise exception 'Revisa la repetición: máximo 26 fechas.';end if;
   recur:=case when count_classes>1 then gen_random_uuid() end;result:='[]';
   zone_name:=(select timezone from public.gyms where id=g);
   for cid in 0..count_classes-1 loop
    wall:=(stamp at time zone zone_name)+make_interval(weeks=>cid::int*coalesce((d->>'interval_weeks')::int,1));
    next_stamp:=case when cid=0 then stamp else wall at time zone zone_name end;
    if cid>0 and ((next_stamp at time zone zone_name)<>wall or exists(
     select 1 from generate_series(-180,180,15) as offsets(minutes) where minutes<>0 and
      ((next_stamp+make_interval(mins=>minutes)) at time zone zone_name)=wall)) then
     raise exception 'Una fecha repetida coincide con un cambio de hora. Programa esa fecha por separado con su zona horaria.';
    end if;
    -- Keep the first explicit instant and preserve local time on later dates.
    insert into public.classes(gym_id,name,trainer_id,starts_at,capacity,notes,status,duration_minutes,conditions,requires_membership,recurrence_id)
     values(g,trim(d->>'name'),tid,next_stamp,
      (d->>'capacity')::int,coalesce(d->>'notes',''),'PROGRAMADA',(d->>'duration_minutes')::int,coalesce(d->>'conditions',''),coalesce((d->>'requires_membership')::boolean,false),recur) returning id into rid;
    result:=result||jsonb_build_array(jsonb_build_object('class_id',rid));
   end loop;
  end if;
 elsif a in ('reservation.reserve','reservation.cancel','reservation.attend') then
  if a='reservation.reserve' then
   select * into cl from public.classes where gym_id=g and id=(d->>'class_id')::bigint for update;
   if not found then raise exception 'Clase no disponible.' using errcode='42501';end if;
   cid:=(d->>'client_id')::bigint;
   select id into rid from public.reservations where gym_id=g and class_id=cl.id and client_id=cid;
   if rid is null then
    insert into public.reservations(gym_id,class_id,client_id,status) values(g,cl.id,cid,'RESERVADA') returning id into rid;
   else
    update public.reservations set status=case when status='ASISTIO' then 'ASISTIO' else 'RESERVADA' end where gym_id=g and id=rid;
   end if;
  else
   -- Lock order: class before reservation, same as mobile and enrollment.
   select * into cl from public.classes where gym_id=g and id=(select class_id from public.reservations where gym_id=g and id=(d->>'id')::bigint) for update;
   if not found then raise exception 'Reserva no disponible.' using errcode='42501';end if;
   if a='reservation.attend' and cl.status='CANCELADA' then raise exception 'La clase está cancelada.';end if;
   if a='reservation.attend' and cl.starts_at>now() then raise exception 'Registra la asistencia cuando comience la clase.';end if;
   update public.reservations set status=case when a='reservation.cancel' then 'CANCELADA' else 'ASISTIO' end
    where gym_id=g and id=(d->>'id')::bigint and (a='reservation.cancel' or status in ('RESERVADA','ASISTIO')) returning id into rid;
   if rid is null then raise exception 'La reserva no está confirmada.';end if;
  end if;
  result:=jsonb_build_object('reservation_id',rid);
 else raise exception 'Acción no disponible.';
 end if;
 insert into league_source_private.training_requests values(g,request,auth.uid(),jsonb_build_object('action',a,'data',d),result,now());
 insert into league_source_private.training_audit(gym_id,actor_id,action,record_id) values(g,auth.uid(),a,coalesce(d->>'id',request::text));
 return result;
end $$;
revoke all on function league_source_private.training_role(uuid),league_source_private.training_items(uuid,jsonb),league_source_private.training(uuid,text,jsonb),
 league_source_private.training_class_guard(),league_source_private.training_class_cancel(),league_source_private.training_reservation_history() from public,anon,authenticated;
grant execute on function league_source_private.training(uuid,text,jsonb) to authenticated;
create or replace function public.gym_training(p_gym_id uuid,p_action text,p_data jsonb default '{}') returns jsonb language sql security invoker set search_path='' as $$ select league_source_private.training(p_gym_id,p_action,p_data) $$;
revoke all on function public.gym_training(uuid,text,jsonb) from public,anon;
grant execute on function public.gym_training(uuid,text,jsonb) to authenticated;
-- Reuse the existing staff-only realtime event stream; no personal data in events.
do $$ declare relation text;begin
 if to_regclass('public.gym_events') is not null and to_regprocedure('private.notify_gym_change()') is not null then
  foreach relation in array array['routines','exercises','classes','reservations'] loop
   execute format('drop trigger if exists %I on public.%I','gym_training_signal_'||relation,relation);
   execute format('create trigger %I after insert or update or delete on public.%I for each row execute function private.notify_gym_change()','gym_training_signal_'||relation,relation);
  end loop;
 end if;
end $$;

-- Keep the existing athlete/gateway checks; hide deactivated exercises in catalogs.
do $$ begin
 if to_regprocedure('league_private.app_before_training(text,jsonb)') is null then
  alter function league_private.app(text,jsonb) rename to app_before_training;
  alter function league_private.service(text,jsonb) rename to service_before_training;
 end if;
end $$;
create or replace function league_private.app(a text,d jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 result:=league_private.app_before_training(a,d);
 if a='catalog' then
  select coalesce(jsonb_agg(value),'[]') into result from jsonb_array_elements(result) where coalesce((value->>'active')::boolean,true);
 end if;return result;
end $$;
create or replace function league_private.service(a text,d jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare result jsonb;
begin
 result:=league_private.service_before_training(a,d);
 if a='staff.catalog' then
  select coalesce(jsonb_agg(value),'[]') into result from jsonb_array_elements(result) where coalesce((value->>'active')::boolean,true);
 elsif a='directory.sync' then
  -- Core's verified code replaces the disabled local routing placeholder.
  update public.league_gym_directory set athlete_code=upper(d->>'athlete_code') where gym_id=(d->>'gym_id')::uuid;
 end if;return result;
end $$;
revoke all on function league_private.app_before_training(text,jsonb),league_private.service_before_training(text,jsonb),league_private.app(text,jsonb),league_private.service(text,jsonb) from public,anon,authenticated;
grant execute on function league_private.app(text,jsonb) to authenticated;
grant execute on function league_private.service(text,jsonb) to service_role;
notify pgrst,'reload schema';
commit;
