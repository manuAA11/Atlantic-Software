-- Additive source adapter for either existing Gym provider. Apply to isolated QA first.
begin;
create schema if not exists league_source_private;
revoke all on schema league_source_private from public,anon;
create table public.league_gym_settings (
 gym_id uuid primary key references public.gyms(id),enabled boolean not null default false,
 pilot_client_ids bigint[] not null default '{}',allow_all_clients boolean not null default false
);
create table public.league_client_profiles (
 profile_id uuid primary key default gen_random_uuid(),gym_id uuid not null references public.gyms(id),
 client_id bigint not null references public.clients(id),created_at timestamptz not null default now(),
 unique(gym_id,client_id)
);
create table public.league_coaches (
 gym_id uuid not null references public.gyms(id),user_id uuid not null references auth.users(id),
 granted_by uuid not null,created_at timestamptz not null default now(),primary key(gym_id,user_id)
);
create table public.league_machines (
 id uuid primary key default gen_random_uuid(),gym_id uuid not null references public.gyms(id),
 name text not null check(length(name) between 2 and 120),notes text not null default '',active boolean not null default true,
 unique(gym_id,id)
);
alter table public.exercises add column league_catalog_id uuid;
alter table public.exercises add column league_machine_id uuid;
alter table public.exercises add column league_rest_seconds integer check(league_rest_seconds between 0 and 600);
alter table public.exercises add constraint league_machine_same_gym foreign key(gym_id,league_machine_id) references public.league_machines(gym_id,id);
create index league_source_profiles_client on public.league_client_profiles(client_id);
create index league_source_machines_gym on public.league_machines(gym_id,active);
alter table public.league_gym_settings enable row level security;
alter table public.league_client_profiles enable row level security;
alter table public.league_coaches enable row level security;
alter table public.league_machines enable row level security;
revoke all on public.league_gym_settings,public.league_client_profiles,public.league_coaches,public.league_machines from public,anon,authenticated;

create function league_source_private.staff_role(g uuid) returns text language plpgsql stable security definer set search_path='' as $$
declare r text;
begin
 if auth.uid() is null or not exists(select 1 from auth.users where id=auth.uid() and email_confirmed_at is not null) then raise exception 'Inicia sesión y confirma tu correo.' using errcode='42501';end if;
 select case when u.role='admin' then 'admin' when exists(select 1 from public.league_coaches c where c.gym_id=g and c.user_id=u.user_id) then 'coach' end into r
  from public.gym_users u where u.gym_id=g and u.user_id=auth.uid() and coalesce((to_jsonb(u)->>'enabled')::boolean,true);
 if r is null then raise exception 'No tienes permiso para gestionar League.' using errcode='42501';end if;
 return r;
end $$;
create function league_source_private.enabled(g uuid,c bigint default null) returns void language plpgsql stable security definer set search_path='' as $$
begin
 if not exists(select 1 from public.league_gym_settings where gym_id=g and enabled and
  (c is null or allow_all_clients or c=any(pilot_client_ids))) then
  raise exception 'League no está habilitado para este cliente del piloto.' using errcode='42501';end if;
end $$;
create function league_source_private.provision_client() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if exists(select 1 from public.league_gym_settings where gym_id=new.gym_id and enabled and (allow_all_clients or new.id=any(pilot_client_ids))) then
  insert into public.league_client_profiles(gym_id,client_id) values(new.gym_id,new.id) on conflict do nothing;
 end if;return new;
end $$;
create trigger league_prepare_profile after insert on public.clients for each row execute function league_source_private.provision_client();

create function league_source_private.reserve_guard() returns trigger language plpgsql security definer set search_path='' as $$
declare c public.classes;used integer;
begin
 -- The guard covers desktop and mobile writers to the same existing table.
 if new.status<>'RESERVADA' then return new;end if;
 if tg_op='UPDATE' and old.status='RESERVADA' and old.gym_id=new.gym_id and old.class_id=new.class_id and old.client_id=new.client_id then return new;end if;
 select * into c from public.classes where id=new.class_id and gym_id=new.gym_id for update;
 if not found or c.status<>'PROGRAMADA' or c.starts_at<=now() then raise exception 'La clase no está disponible.';end if;
 if not exists(select 1 from public.clients where id=new.client_id and gym_id=new.gym_id and active) then raise exception 'Cliente no disponible.' using errcode='42501';end if;
 select count(*) into used from public.reservations where gym_id=new.gym_id and class_id=new.class_id and status='RESERVADA' and id is distinct from new.id;
 if used>=c.capacity then raise exception 'La clase ya no tiene cupos disponibles.' using errcode='23514';end if;
 return new;
end $$;
create trigger league_reservation_capacity before insert or update on public.reservations for each row execute function league_source_private.reserve_guard();

create function league_source_private.staff(g uuid,a text,d jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare role_name text:=league_source_private.staff_role(g);c bigint;rid bigint;profile uuid;e jsonb;item jsonb;result jsonb:='[]';trainer bigint;
begin
 perform league_source_private.enabled(g);
 if a='context' then return jsonb_build_object('gym_id',g,'actor_id',auth.uid(),'role',role_name);end if;
 if a='clients' then
  return coalesce(jsonb_agg(jsonb_build_object('client_id',cl.id::text,'name',trim(cl.first_name||' '||cl.last_name),'profile_id',p.profile_id)),'[]')
   from public.clients cl join public.league_gym_settings cfg on cfg.gym_id=cl.gym_id left join public.league_client_profiles p on p.client_id=cl.id and p.gym_id=cl.gym_id
   where cl.gym_id=g and cl.active and (cfg.allow_all_clients or cl.id=any(cfg.pilot_client_ids));
 elsif a='provision' then
  if role_name<>'admin' then raise exception 'Permiso de administración requerido.' using errcode='42501';end if;
  c:=(d->>'client_id')::bigint;perform league_source_private.enabled(g,c);
  if not exists(select 1 from public.clients where id=c and gym_id=g and active) then raise exception 'Cliente no disponible.';end if;
  insert into public.league_client_profiles(gym_id,client_id) values(g,c) on conflict do nothing;
  return jsonb_build_object('profile_id',profile_id) from public.league_client_profiles where gym_id=g and client_id=c;
 elsif a='machines' then
  return coalesce(jsonb_agg(to_jsonb(m) order by name),'[]') from public.league_machines m where gym_id=g and active;
 elsif a='machine.create' then
  insert into public.league_machines(gym_id,name,notes) values(g,trim(d->>'name'),left(coalesce(d->>'notes',''),2000)) returning to_jsonb(league_machines.*) into result;return result;
 elsif a='routine.assign' then
  if coalesce(jsonb_array_length(d->'profiles'),0) not between 1 and 50 or coalesce(jsonb_array_length(d->'exercises'),0) not between 1 and 100 then raise exception 'Selecciona clientes y ejercicios.';end if;
  if coalesce(length(trim(d->>'name')),0) not between 2 and 120 then raise exception 'Escribe el nombre de la rutina.';end if;
  trainer:=nullif(d->>'trainer_id','')::bigint;
  if trainer is not null and not exists(select 1 from public.trainers where gym_id=g and id=trainer and active) then raise exception 'Entrenador no disponible.';end if;
  for item in select value from jsonb_array_elements(d->'profiles') loop
   select client_id into c from public.league_client_profiles where gym_id=g and profile_id=(item#>>'{}')::uuid;
   if c is null then raise exception 'Perfil no disponible.' using errcode='42501';end if;
   perform league_source_private.enabled(g,c);
   insert into public.routines(gym_id,client_id,trainer_id,name,goal,start_date,notes,active)
    values(g,c,trainer,trim(d->>'name'),coalesce(d->>'goal',''),private.gym_local_date(g),coalesce(d->>'notes',''),true) returning id into rid;
   for e in select value from jsonb_array_elements(d->'exercises') loop
    if coalesce((e->>'sets')::integer,0) not between 1 and 20 or coalesce((e->>'reps')::integer,0) not between 1 and 100 or coalesce((e->>'rest_seconds')::integer,-1) not between 0 and 600 or
     coalesce((e->>'weight_kg')::numeric,-1) not between 0 and 1000 or e->>'catalog_id' is null or coalesce(length(trim(e->>'name')),0) not between 2 and 120 then raise exception 'Revisa los ejercicios, series, repeticiones y descanso.';end if;
    if e->>'machine_id' is not null and not exists(select 1 from public.league_machines where gym_id=g and id=(e->>'machine_id')::uuid and active) then raise exception 'Máquina no disponible.';end if;
    insert into public.exercises(gym_id,routine_id,day_name,name,sets,reps,weight,notes,position,league_catalog_id,league_machine_id,league_rest_seconds)
     values(g,rid,coalesce(e->>'day','Día 1'),e->>'name',e->>'sets',e->>'reps',coalesce(e->>'weight_kg','0'),coalesce(e->>'notes',''),coalesce((e->>'position')::integer,0),
      (e->>'catalog_id')::uuid,nullif(e->>'machine_id','')::uuid,(e->>'rest_seconds')::integer);
   end loop;
   result:=result||jsonb_build_array(jsonb_build_object('routine_id',rid::text));
  end loop;return result;
 elsif a='event.create' then
  trainer:=nullif(d->>'trainer_id','')::bigint;
  if trainer is not null and not exists(select 1 from public.trainers where gym_id=g and id=trainer and active) then raise exception 'Entrenador no disponible.';end if;
  if d->>'starts_at' is null or (d->>'starts_at')::timestamptz<=now() or coalesce((d->>'capacity')::integer,0) not between 1 and 5000 or coalesce(length(trim(d->>'name')),0) not between 2 and 120 then raise exception 'Revisa el nombre, la fecha futura y los cupos de la clase.';end if;
  insert into public.classes(gym_id,trainer_id,name,starts_at,capacity,notes,status)
   values(g,trainer,trim(d->>'name'),(d->>'starts_at')::timestamptz,(d->>'capacity')::integer,coalesce(d->>'description',''),'PROGRAMADA') returning id into rid;
  return jsonb_build_object('class_id',rid::text);
 elsif a='events' then
  return coalesce(jsonb_agg(t order by t.starts_at),'[]') from (
   select cl.id::text as id,cl.name,cl.starts_at,cl.capacity,cl.status,
    (select coalesce(jsonb_agg(jsonb_build_object('id',r.id::text,'client',trim(c.first_name||' '||c.last_name),'status',r.status)),'[]') from public.reservations r join public.clients c on c.id=r.client_id and c.gym_id=r.gym_id where r.gym_id=g and r.class_id=cl.id) as reservations
   from public.classes cl where cl.gym_id=g and cl.starts_at>now()-interval '7 days' order by cl.starts_at limit 100)t;
 elsif a='event.cancel' then
  update public.classes set status='CANCELADA' where gym_id=g and id=(d->>'class_id')::bigint;
  return jsonb_build_object('cancelled',true);
 elsif a='reservation.cancel' then
  select class_id into rid from public.reservations where gym_id=g and id=(d->>'reservation_id')::bigint;
  perform 1 from public.classes where gym_id=g and id=rid for update;
  update public.reservations set status='CANCELADA' where gym_id=g and id=(d->>'reservation_id')::bigint;
  return jsonb_build_object('cancelled',true);
 elsif a='coach.grant' and role_name='admin' then
  if not exists(select 1 from public.gym_users where gym_id=g and user_id=(d->>'user_id')::uuid) then raise exception 'La cuenta debe pertenecer al gimnasio.';end if;
  insert into public.league_coaches(gym_id,user_id,granted_by) values(g,(d->>'user_id')::uuid,auth.uid()) on conflict do nothing;
  return jsonb_build_object('granted',true);
 end if;
 raise exception 'Operación no disponible.' using errcode='22023';
end $$;
create function public.league_staff(p_gym_id uuid,p_action text,p_data jsonb default '{}') returns jsonb language sql security invoker set search_path='' as $$
 select league_source_private.staff(p_gym_id,p_action,p_data)
$$;

create function league_source_private.athlete(g uuid,p uuid,a text,d jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare c bigint;rid bigint;result jsonb;snapshot jsonb;
begin
 select client_id into c from public.league_client_profiles where profile_id=p and gym_id=g;
 if c is null then raise exception 'Perfil no disponible.' using errcode='42501';end if;
 perform league_source_private.enabled(g,c);
 if a='routines' then
  return coalesce(jsonb_agg(jsonb_build_object('id',r.id::text,'name',r.name,'goal',r.goal,'notes',r.notes,
   'exercises',(select coalesce(jsonb_agg(jsonb_build_object('id',e.id::text,'catalog_id',e.league_catalog_id,'name',e.name,'day',e.day_name,'sets',e.sets,'reps',e.reps,'weight_kg',e.weight,'rest_seconds',e.league_rest_seconds) order by e.day_name,e.position,e.id),'[]') from public.exercises e where e.gym_id=g and e.routine_id=r.id)) order by r.id desc),'[]') from public.routines r where r.gym_id=g and r.client_id=c and r.active;
 elsif a='routine.snapshot' then
  rid:=(d->>'routine_id')::bigint;
  return jsonb_build_object('id',r.id::text,'name',r.name,'goal',r.goal,'captured_at',now(),
   'exercises',(select coalesce(jsonb_agg(jsonb_build_object('id',e.id::text,'catalog_id',e.league_catalog_id,'name',e.name,'day',e.day_name,'sets',e.sets,'reps',e.reps,'weight_kg',e.weight,'rest_seconds',e.league_rest_seconds) order by e.day_name,e.position,e.id),'[]') from public.exercises e where e.gym_id=g and e.routine_id=r.id))
   from public.routines r where r.id=rid and r.gym_id=g and r.client_id=c and r.active;
 elsif a='membership' then
  snapshot:=private.membership_snapshot_json(g,c);
  return jsonb_build_object('active',coalesce((snapshot->>'allowed')::boolean,false),'frozen',coalesce((snapshot->>'frozen')::boolean,false),'ends_at',snapshot->'membership_end');
 elsif a='calendar' then
  return coalesce(jsonb_agg(t order by t.starts_at),'[]') from (
   select cl.id::text as id,cl.name,cl.starts_at,cl.capacity,cl.notes as description,
    (select name from public.trainers where id=cl.trainer_id and gym_id=g) as trainer,
    (select count(*) from public.reservations where gym_id=g and class_id=cl.id and status='RESERVADA') as reserved,
    exists(select 1 from public.reservations where gym_id=g and class_id=cl.id and client_id=c and status='RESERVADA') as mine
   from public.classes cl where cl.gym_id=g and cl.status='PROGRAMADA' and cl.starts_at>now() and cl.starts_at<now()+interval '90 days' order by cl.starts_at limit 100)t;
 elsif a='reserve' then
  snapshot:=private.membership_snapshot_json(g,c);
  if not coalesce((snapshot->>'allowed')::boolean,false) then raise exception 'Necesitas una membresía activa para reservar.' using errcode='42501';end if;
  rid:=(d->>'class_id')::bigint;
  -- Shared class lock precedes inspection, insert, reactivation and cancellation.
  perform 1 from public.classes where id=rid and gym_id=g for update;
  if not found then raise exception 'Clase no disponible.';end if;
  if exists(select 1 from public.reservations where gym_id=g and class_id=rid and client_id=c and status='RESERVADA') then return jsonb_build_object('reserved',true);end if;
  update public.reservations set status='RESERVADA' where gym_id=g and class_id=rid and client_id=c;
  if not found then insert into public.reservations(gym_id,class_id,client_id,status) values(g,rid,c,'RESERVADA');end if;
  return jsonb_build_object('reserved',true);
 elsif a='cancel' then
  rid:=(d->>'class_id')::bigint;
  perform 1 from public.classes where id=rid and gym_id=g for update;
  update public.reservations set status='CANCELADA' where gym_id=g and class_id=rid and client_id=c;
  return jsonb_build_object('cancelled',true);
 elsif a='attendance' then
  return coalesce(jsonb_agg(t),'[]') from (select distinct local_date from public.checkins where gym_id=g and client_id=c and result='PERMITIDA' and local_date>=current_date-30 and local_date<=current_date+1)t;
 end if;
 raise exception 'Operación no disponible.' using errcode='22023';
end $$;
create function public.league_source(p_gym_id uuid,p_profile_id uuid,p_action text,p_data jsonb default '{}') returns jsonb language sql security invoker set search_path='' as $$
 select league_source_private.athlete(p_gym_id,p_profile_id,p_action,p_data)
$$;
revoke all on all functions in schema league_source_private from public,anon,authenticated;
grant usage on schema league_source_private to authenticated,service_role;
grant execute on function league_source_private.staff(uuid,text,jsonb) to authenticated;
grant execute on function league_source_private.athlete(uuid,uuid,text,jsonb) to service_role;
revoke all on function public.league_staff(uuid,text,jsonb),public.league_source(uuid,uuid,text,jsonb) from public,anon,authenticated;
grant execute on function public.league_staff(uuid,text,jsonb) to authenticated;
grant execute on function public.league_source(uuid,uuid,text,jsonb) to service_role;
commit;
