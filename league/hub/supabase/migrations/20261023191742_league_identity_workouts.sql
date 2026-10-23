-- Atlantic League athlete hub. STAGING ONLY until the controlled pilot is approved.
-- No dependency on, copy of, or changes to Gym's business/member/payment tables.
begin;
create schema if not exists league_private;
revoke all on schema league_private from public,anon;
create table public.league_profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 alias text not null check(length(alias) between 2 and 60),
 timezone text not null default 'America/Bogota', leaderboard_opt_in boolean not null default false,
 created_at timestamptz not null default now()
);
-- Routing directory only. Operational gyms remain owned by their source projects/Core.
create table public.league_gym_directory (
 gym_id uuid primary key, source_ref text not null check(source_ref ~ '^[a-z0-9]{20}$'),
 name text not null check(length(name) between 1 and 150),
 athlete_code text not null unique check(athlete_code ~ '^[A-Z0-9-]{6,24}$'),
 enabled boolean not null default false, entitlement_until timestamptz not null default '-infinity'
);
create table public.league_links (
 id uuid primary key default gen_random_uuid(), athlete_id uuid not null references public.league_profiles(id) on delete cascade,
 gym_id uuid not null references public.league_gym_directory(gym_id), source_profile_id uuid not null,
 status text not null default 'APPROVED' check(status in ('APPROVED','REVOKED')),
 approved_by uuid not null, approved_at timestamptz not null default now(),
 unique(athlete_id,gym_id),unique(gym_id,source_profile_id)
);
create table public.league_join_requests (
 id uuid primary key default gen_random_uuid(),athlete_id uuid not null references public.league_profiles(id) on delete cascade,
 gym_id uuid not null references public.league_gym_directory(gym_id),
 status text not null default 'PENDING' check(status in ('PENDING','APPROVED','REJECTED')),
 created_at timestamptz not null default now(), reviewed_at timestamptz,reviewed_by uuid,
 unique(athlete_id,gym_id)
);
create table league_private.invites (
 id uuid primary key default gen_random_uuid(),gym_id uuid not null references public.league_gym_directory(gym_id),
 source_profile_id uuid not null,email text not null,token_hash text not null unique,
 expires_at timestamptz not null,used_at timestamptz,used_by uuid,created_by uuid not null,
 created_at timestamptz not null default now()
);
create table public.league_exercise_catalog (
 id uuid primary key default gen_random_uuid(),gym_id uuid references public.league_gym_directory(gym_id),
 owner_id uuid references public.league_profiles(id) on delete cascade,name text not null check(length(name) between 2 and 120),
 muscle text not null default '',equipment text not null default 'Sin equipamiento',
 instructions text not null default '' check(length(instructions)<=4000),standard_key text unique,
 check(gym_id is null or owner_id is null)
);
-- Server-created snapshots freeze assigned routines before the first recorded set.
create table public.league_workout_drafts (
 id uuid primary key default gen_random_uuid(),athlete_id uuid not null references public.league_profiles(id) on delete cascade,
 gym_id uuid not null references public.league_gym_directory(gym_id),routine_snapshot jsonb not null,
 created_at timestamptz not null default now()
);
alter table public.league_workout_drafts enable row level security;
revoke all on public.league_workout_drafts from public,anon,authenticated;
grant select on public.league_workout_drafts to authenticated;
create policy league_draft_self on public.league_workout_drafts for select to authenticated using(athlete_id=(select auth.uid()));
create table public.league_workouts (
 id uuid primary key,athlete_id uuid not null references public.league_profiles(id) on delete cascade,
 name text not null check(length(name) between 1 and 120),started_at timestamptz not null,
 finished_at timestamptz not null default now(),gym_id uuid references public.league_gym_directory(gym_id),
 routine_snapshot jsonb,sets jsonb not null check(jsonb_typeof(sets)='array' and jsonb_array_length(sets) between 1 and 100),
 payload jsonb not null,created_at timestamptz not null default now()
);
create table public.league_xp_events (
 id uuid primary key default gen_random_uuid(),athlete_id uuid not null references public.league_profiles(id) on delete cascade,
 kind text not null check(kind in ('WORKOUT','ATTENDANCE','STREAK')),source_key text not null,
 points integer not null check(points between 1 and 200),official boolean not null default false,
 gym_id uuid references public.league_gym_directory(gym_id),created_at timestamptz not null default now(),
 unique(athlete_id,kind,source_key),check(not official or gym_id is not null)
);
create table public.league_strength_requests (
 id uuid primary key default gen_random_uuid(),athlete_id uuid not null references public.league_profiles(id) on delete cascade,
 gym_id uuid not null references public.league_gym_directory(gym_id),exercise_id uuid not null references public.league_exercise_catalog(id),
 weight_kg numeric(8,2) not null check(weight_kg>0 and weight_kg<=1000),reps integer not null check(reps between 1 and 12),
 division text not null check(division in ('OPEN','WOMEN','MEN')),
 weight_class text not null check(weight_class in ('OPEN','LE60','60-75','75-90','GT90')),
 evidence_path text,status text not null default 'PENDING' check(status in ('PENDING','APPROVED','REJECTED')),
 request_key uuid not null,created_at timestamptz not null default now(),reviewed_at timestamptz,reviewed_by uuid,
 unique(athlete_id,request_key)
);
create table league_private.verification_history (
 id uuid primary key default gen_random_uuid(),request_id uuid not null references public.league_strength_requests(id) on delete cascade,
 gym_id uuid not null,actor_id uuid not null,decision text not null check(decision in ('APPROVED','REJECTED')),
 reason text not null,created_at timestamptz not null default now()
);
create table league_private.audit (
 id bigint generated always as identity primary key,gym_id uuid,actor_id uuid not null,
 action text not null,record_id uuid,created_at timestamptz not null default now()
);
create index league_links_athlete on public.league_links(athlete_id,status);
create index league_links_gym on public.league_links(gym_id,status);
create index league_pending_join on public.league_join_requests(gym_id,created_at) where status='PENDING';
create index league_workouts_athlete on public.league_workouts(athlete_id,finished_at desc);
create index league_xp_owner on public.league_xp_events(athlete_id,official);
create index league_strength_pending on public.league_strength_requests(gym_id,created_at) where status='PENDING';
create index league_strength_ranking on public.league_strength_requests(exercise_id,division,weight_class,weight_kg desc) where status='APPROVED';
create index league_catalog_gym on public.league_exercise_catalog(gym_id);
create index league_catalog_owner on public.league_exercise_catalog(owner_id);

alter table public.league_profiles enable row level security;
alter table public.league_gym_directory enable row level security;
alter table public.league_links enable row level security;
alter table public.league_join_requests enable row level security;
alter table public.league_exercise_catalog enable row level security;
alter table public.league_workouts enable row level security;
alter table public.league_xp_events enable row level security;
alter table public.league_strength_requests enable row level security;
alter table league_private.invites enable row level security;
alter table league_private.audit enable row level security;
alter table league_private.verification_history enable row level security;
revoke all on public.league_profiles,public.league_gym_directory,public.league_links,public.league_join_requests,
 public.league_exercise_catalog,public.league_workouts,public.league_xp_events,public.league_strength_requests from public,anon,authenticated;
grant select on public.league_gym_directory to service_role;
grant select on public.league_profiles,public.league_links,public.league_join_requests,public.league_exercise_catalog,
 public.league_workouts,public.league_xp_events,public.league_strength_requests to authenticated;
create policy league_profile_self on public.league_profiles for select to authenticated using(id=(select auth.uid()));
create policy league_links_self on public.league_links for select to authenticated using(athlete_id=(select auth.uid()));
create policy league_join_self on public.league_join_requests for select to authenticated using(athlete_id=(select auth.uid()));
create policy league_workout_self on public.league_workouts for select to authenticated using(athlete_id=(select auth.uid()));
create policy league_xp_self on public.league_xp_events for select to authenticated using(athlete_id=(select auth.uid()));
create policy league_strength_self on public.league_strength_requests for select to authenticated using(athlete_id=(select auth.uid()));
create policy league_catalog_read on public.league_exercise_catalog for select to authenticated using(
 (gym_id is null and owner_id is null) or owner_id=(select auth.uid()) or exists(
 select 1 from public.league_links l where l.athlete_id=(select auth.uid()) and l.gym_id=league_exercise_catalog.gym_id and l.status='APPROVED'));

create function league_private.require_user() returns uuid language plpgsql stable security definer set search_path='' as $$
declare u uuid:=auth.uid();
begin
 if u is null or not exists(select 1 from auth.users where id=u and email_confirmed_at is not null) then
  raise exception 'Confirma tu cuenta e inicia sesión.' using errcode='42501';end if;
 return u;
end $$;
create function league_private.require_module(g uuid) returns void language plpgsql stable security definer set search_path='' as $$
begin
 if not exists(select 1 from public.league_gym_directory where gym_id=g and enabled and entitlement_until>now()) then
  raise exception 'El módulo del gimnasio no está disponible.' using errcode='42501';end if;
end $$;
create function league_private.app(a text,d jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare u uuid:=league_private.require_user();g uuid;w uuid;row_data record;item jsonb;result jsonb;token text;plan jsonb;
begin
 if octet_length(d::text)>100000 then raise exception 'Solicitud demasiado grande.';end if;
 if a='profile.ensure' then
  insert into public.league_profiles(id,alias) values(u,left(coalesce(nullif(trim(d->>'alias'),''),'Deportista'),60)) on conflict(id) do nothing;
  return to_jsonb(p) from public.league_profiles p where id=u;
 end if;
 if not exists(select 1 from public.league_profiles where id=u) then raise exception 'Completa tu perfil.';end if;
 if a='profile.update' then
  if coalesce(length(trim(d->>'alias')),0) not between 2 and 60 then raise exception 'Escribe un nombre de 2 a 60 caracteres.';end if;
  update public.league_profiles set alias=trim(d->>'alias'),leaderboard_opt_in=coalesce((d->>'leaderboard_opt_in')::boolean,false),
   weekly_goal=coalesce((d->>'weekly_goal')::integer,weekly_goal) where id=u;
  return to_jsonb(p) from public.league_profiles p where id=u;
 elsif a='snapshot' then
  return jsonb_build_object('profile',(select to_jsonb(p) from public.league_profiles p where id=u),
   'xp',(select coalesce(sum(points),0) from public.league_xp_events where athlete_id=u),
   'official_xp',(select coalesce(sum(points),0) from public.league_xp_events where athlete_id=u and official),
   'weekly_days',(select count(distinct (finished_at at time zone 'UTC')::date) from public.league_workouts where athlete_id=u
    and finished_at at time zone 'UTC'>=date_trunc('week',now() at time zone 'UTC')),
   'workouts',(select coalesce(jsonb_agg(t order by t.finished_at desc),'[]') from (select id,name,finished_at,sets,routine_snapshot from public.league_workouts where athlete_id=u order by finished_at desc limit 50)t),
   'links',(select coalesce(jsonb_agg(jsonb_build_object('gym_id',l.gym_id,'name',g.name,'status',l.status)),'[]') from public.league_links l join public.league_gym_directory g using(gym_id) where l.athlete_id=u),
   'requests',(select coalesce(jsonb_agg(to_jsonb(t)),'[]') from public.league_join_requests t where athlete_id=u),
   'records',(select coalesce(jsonb_agg(t order by t.created_at desc),'[]') from (select s.*,e.name as exercise_name from public.league_strength_requests s join public.league_exercise_catalog e on e.id=s.exercise_id where athlete_id=u order by created_at desc limit 50)t));
 elsif a='catalog' then
  return coalesce(jsonb_agg(to_jsonb(e) order by e.name),'[]') from public.league_exercise_catalog e where
   (gym_id is null and owner_id is null) or owner_id=u or exists(select 1 from public.league_links where athlete_id=u and gym_id=e.gym_id and status='APPROVED');
 elsif a='exercise.personal' then
  insert into public.league_exercise_catalog(owner_id,name,muscle,equipment,instructions)
   values(u,trim(d->>'name'),left(coalesce(d->>'muscle',''),80),left(coalesce(d->>'equipment','Sin equipamiento'),120),coalesce(d->>'instructions','')) returning to_jsonb(league_exercise_catalog.*) into result;
  return result;
 elsif a='workout.save' then
  w:=(d->>'id')::uuid;
  select * into row_data from public.league_workouts where id=w;
  if found then
   if row_data.athlete_id<>u or row_data.payload<>d then raise exception 'Ese registro ya tiene otro contenido.' using errcode='23505';end if;
   return jsonb_build_object('id',w,'saved',true);
  end if;
  if w is null or coalesce(jsonb_typeof(d->'sets'),'')<>'array' or coalesce(jsonb_array_length(d->'sets'),0) not between 1 and 100 then raise exception 'Registra al menos una serie.';end if;
  if coalesce(length(trim(d->>'name')),0) not between 1 and 120 or d->>'started_at' is null then raise exception 'Revisa el nombre y la fecha del entrenamiento.';end if;
  for item in select value from jsonb_array_elements(d->'sets') loop
   if (item->>'weight_kg')::numeric not between 0 and 1000 or (item->>'reps')::integer not between 1 and 100 then raise exception 'Revisa peso y repeticiones.';end if;
   if item->>'weight_kg' is null or item->>'reps' is null or not exists(select 1 from public.league_exercise_catalog e where id=(item->>'exercise_id')::uuid and
    ((e.gym_id is null and e.owner_id is null) or e.owner_id=u or exists(select 1 from public.league_links where athlete_id=u and gym_id=e.gym_id and status='APPROVED'))) then raise exception 'Ejercicio no disponible.' using errcode='42501';end if;
  end loop;
  -- Official routine snapshots are inserted only by the verified gateway, never supplied by an athlete.
  if d ? 'routine_snapshot' or d ? 'gym_id' then raise exception 'La rutina oficial requiere confirmación del servidor.' using errcode='42501';end if;
  if d ? 'draft_id' then
   select gym_id,routine_snapshot into g,plan from public.league_workout_drafts where id=(d->>'draft_id')::uuid and athlete_id=u;
   if not found then raise exception 'Entrenamiento no disponible.' using errcode='42501';end if;
  end if;
  insert into public.league_workouts(id,athlete_id,name,started_at,sets,payload,gym_id,routine_snapshot)
   values(w,u,trim(d->>'name'),greatest(now()-interval '7 days',least(now(),(d->>'started_at')::timestamptz)),d->'sets',d,g,plan);
  insert into public.league_xp_events(athlete_id,kind,source_key,points)
   values(u,'WORKOUT',to_char(now() at time zone 'UTC','YYYY-MM-DD'),20) on conflict do nothing;
  -- Independent workouts never generate official XP or an approved strength record.
  return jsonb_build_object('id',w,'saved',true);
 elsif a='gym.search' then
  return coalesce(jsonb_agg(jsonb_build_object('gym_id',gym_id,'name',name)),'[]') from
   (select gym_id,name from public.league_gym_directory where enabled and entitlement_until>now() and
    (athlete_code=upper(trim(d->>'query')) or name ilike '%'||left(coalesce(d->>'query',''),80)||'%') order by name limit 20)t;
 elsif a='gym.request' then
  select gym_id into g from public.league_gym_directory where athlete_code=upper(trim(d->>'code'));
  perform league_private.require_module(g);
  if exists(select 1 from public.league_links where athlete_id=u and gym_id=g and status='APPROVED') then raise exception 'Ya estás vinculado a este gimnasio.';end if;
  insert into public.league_join_requests(athlete_id,gym_id) values(u,g) on conflict(athlete_id,gym_id)
   do update set status='PENDING',created_at=now(),reviewed_at=null,reviewed_by=null where league_join_requests.status='REJECTED'
   returning id into w;
  return jsonb_build_object('status','PENDING');
 elsif a='gym.connection' then
  g:=(d->>'gym_id')::uuid;perform league_private.require_module(g);
  return jsonb_build_object('gym_id',l.gym_id,'source_ref',dir.source_ref,'source_profile_id',l.source_profile_id)
   from public.league_links l join public.league_gym_directory dir using(gym_id) where l.gym_id=g and athlete_id=u and status='APPROVED';
 elsif a='invitation.accept' then
  token:=d->>'token';if token !~ '^[a-f0-9]{64}$' then raise exception 'Invitación no disponible.' using errcode='42501';end if;
  select * into row_data from league_private.invites where token_hash=encode(sha256(convert_to(token,'UTF8')),'hex') for update;
  if not found or row_data.expires_at<=now() or row_data.used_at is not null or
   not exists(select 1 from auth.users where id=u and lower(email)=lower(row_data.email) and email_confirmed_at is not null) then
   raise exception 'Invitación no disponible.' using errcode='42501';end if;
  perform league_private.require_module(row_data.gym_id);
  insert into public.league_links(athlete_id,gym_id,source_profile_id,approved_by)
   values(u,row_data.gym_id,row_data.source_profile_id,row_data.created_by);
  update league_private.invites set used_at=now(),used_by=u where id=row_data.id;
  return jsonb_build_object('status','APPROVED');
 elsif a='record.submit' then
  g:=(d->>'gym_id')::uuid;perform league_private.require_module(g);
  if not exists(select 1 from public.league_links where athlete_id=u and gym_id=g and status='APPROVED') then raise exception 'Solicita la vinculación al gimnasio.' using errcode='42501';end if;
  if not exists(select 1 from public.league_exercise_catalog where id=(d->>'exercise_id')::uuid and owner_id is null and (gym_id is null or gym_id=g)) then raise exception 'Ejercicio no verificable.';end if;
  if nullif(d->>'evidence_path','') is not null and d->>'evidence_path' !~ ('^'||u::text||'/[a-f0-9-]{36}[.](jpg|png|webp)$') then raise exception 'Evidencia no autorizada.' using errcode='42501';end if;
  select * into row_data from public.league_strength_requests where athlete_id=u and request_key=(d->>'request_key')::uuid;
  if found then
   if row_data.gym_id<>g or row_data.exercise_id<>(d->>'exercise_id')::uuid or row_data.weight_kg<>(d->>'weight_kg')::numeric or row_data.reps<>(d->>'reps')::integer or
    row_data.division is distinct from d->>'division' or row_data.weight_class is distinct from d->>'weight_class' or row_data.evidence_path is distinct from nullif(d->>'evidence_path','') then
    raise exception 'Ese registro ya tiene otro contenido.' using errcode='23505';end if;
   return jsonb_build_object('status',row_data.status);
  end if;
  insert into public.league_strength_requests(athlete_id,gym_id,exercise_id,weight_kg,reps,division,weight_class,evidence_path,request_key)
   values(u,g,(d->>'exercise_id')::uuid,(d->>'weight_kg')::numeric,(d->>'reps')::integer,d->>'division',d->>'weight_class',nullif(d->>'evidence_path',''),(d->>'request_key')::uuid)
   on conflict(athlete_id,request_key) do nothing;
  return jsonb_build_object('status','PENDING');
 elsif a='leaderboard' then
  -- Only aliases explicitly opted in. Pending/private records cannot influence ranking.
  if d->>'kind'='XP' then
   return coalesce(jsonb_agg(to_jsonb(t)),'[]') from (
    select p.alias,sum(x.points)::bigint as score from public.league_xp_events x join public.league_profiles p on p.id=x.athlete_id
    join public.league_gym_directory g on g.gym_id=x.gym_id where x.official and p.leaderboard_opt_in and g.enabled and g.entitlement_until>now()
     and (nullif(d->>'gym_id','') is null or x.gym_id=(d->>'gym_id')::uuid)
    group by p.id,p.alias order by sum(x.points) desc,p.alias limit 100)t;
  end if;
  return coalesce(jsonb_agg(to_jsonb(t)),'[]') from (
   select p.alias,max(round(s.weight_kg*(1+s.reps/30.0),2)) as score from public.league_strength_requests s
   join public.league_profiles p on p.id=s.athlete_id join public.league_gym_directory g using(gym_id)
   where s.status='APPROVED' and p.leaderboard_opt_in and g.enabled and g.entitlement_until>now()
    and s.exercise_id=(d->>'exercise_id')::uuid and s.division=d->>'division' and s.weight_class=d->>'weight_class'
    and (nullif(d->>'gym_id','') is null or s.gym_id=(d->>'gym_id')::uuid)
   group by p.id,p.alias order by score desc,p.alias limit 100)t;
 end if;
 raise exception 'Operación no disponible.' using errcode='22023';
end $$;
create function public.league_app(p_action text,p_data jsonb default '{}') returns jsonb language sql security invoker set search_path='' as $$
 select league_private.app(p_action,p_data)
$$;
revoke all on function public.league_app(text,jsonb) from public,anon;
grant execute on function public.league_app(text,jsonb) to authenticated;
revoke all on all functions in schema league_private from public,anon,authenticated;
grant usage on schema league_private to authenticated,service_role;
grant execute on function league_private.app(text,jsonb) to authenticated;
-- The definer is unexposed and always checks the authenticated owner itself.

insert into public.league_exercise_catalog(id,name,muscle,equipment,instructions,standard_key) values
 ('10000000-0000-4000-8000-000000000001','Sentadilla con barra','Piernas','Barra','Registra las series realizadas con la técnica indicada por tu entrenador.','barbell-squat'),
 ('10000000-0000-4000-8000-000000000002','Press de banca','Pecho','Banco y barra','Usa las indicaciones y la supervisión de tu entrenador.','bench-press'),
 ('10000000-0000-4000-8000-000000000003','Peso muerto','Cadena posterior','Barra','Registra el peso total de la barra y los discos.','deadlift'),
 ('10000000-0000-4000-8000-000000000004','Remo con mancuerna','Espalda','Mancuerna','Registra el peso utilizado en cada lado.','dumbbell-row'),
 ('10000000-0000-4000-8000-000000000005','Flexiones','Pecho','Sin equipamiento','Registra las repeticiones completadas.','push-up');
-- Service-only gateway commands. Source staff identity/role and Core module are
-- verified by the gateway before invoking this function. No browser grants.
create function league_private.service(a text,d jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare g uuid:=(d->>'gym_id')::uuid;actor uuid:=(d->>'actor_id')::uuid;r record;v uuid;result jsonb;
begin
 if a='directory.sync' then
  if exists(select 1 from public.league_gym_directory where gym_id=g and source_ref<>d->>'source_ref') then raise exception 'Origen del gimnasio no coincide.';end if;
  insert into public.league_gym_directory(gym_id,source_ref,name,athlete_code,enabled,entitlement_until)
   values(g,d->>'source_ref',d->>'name',upper(d->>'athlete_code'),(d->>'enabled')::boolean,now()+interval '60 seconds')
   on conflict(gym_id) do update set name=excluded.name,enabled=excluded.enabled,entitlement_until=excluded.entitlement_until;
  return jsonb_build_object('gym_id',g);
 end if;
 perform league_private.require_module(g);
 if a='draft.open' then
  if not exists(select 1 from public.league_links where athlete_id=(d->>'athlete_id')::uuid and gym_id=g and status='APPROVED') then raise exception 'Vinculación no disponible.' using errcode='42501';end if;
  insert into public.league_workout_drafts(athlete_id,gym_id,routine_snapshot) values((d->>'athlete_id')::uuid,g,d->'routine_snapshot') returning id into v;
  return jsonb_build_object('draft_id',v,'routine_snapshot',d->'routine_snapshot');
 elsif a='attendance.credit' then
  if not exists(select 1 from public.league_links where athlete_id=(d->>'athlete_id')::uuid and gym_id=g and status='APPROVED') then raise exception 'Vinculación no disponible.' using errcode='42501';end if;
  if (d->>'local_date')::date>current_date+1 or (d->>'local_date')::date<current_date-30 then raise exception 'Fecha de asistencia fuera del período.';end if;
  insert into public.league_xp_events(athlete_id,kind,source_key,points,official,gym_id)
   values((d->>'athlete_id')::uuid,'ATTENDANCE',g::text||':'||(d->>'local_date'),25,true,g) on conflict do nothing;
  return jsonb_build_object('credited',true);
 end if;
 if actor is null or d->>'actor_role' not in ('admin','coach') then raise exception 'Permiso de entrenador requerido.' using errcode='42501';end if;
 if a='staff.evidence' then
  return jsonb_build_object('path',evidence_path) from public.league_strength_requests where id=(d->>'request_id')::uuid and gym_id=g;
 elsif a in ('staff.pending','staff.catalog') then
  if a='staff.catalog' then return coalesce(jsonb_agg(to_jsonb(e) order by name),'[]') from public.league_exercise_catalog e where owner_id is null and (gym_id is null or gym_id=g);end if;
  return jsonb_build_object('requests',(select coalesce(jsonb_agg(jsonb_build_object('id',j.id,'athlete_alias',p.alias,'created_at',j.created_at)),'[]') from public.league_join_requests j join public.league_profiles p on p.id=j.athlete_id where j.gym_id=g and j.status='PENDING'),
   'links',(select coalesce(jsonb_agg(jsonb_build_object('id',l.id,'athlete_alias',p.alias,'source_profile_id',l.source_profile_id,'status',l.status)),'[]') from public.league_links l join public.league_profiles p on p.id=l.athlete_id where l.gym_id=g),
   'verifications',(select coalesce(jsonb_agg(jsonb_build_object('id',s.id,'athlete_alias',p.alias,'exercise',e.name,'weight_kg',s.weight_kg,'reps',s.reps,'division',s.division,'weight_class',s.weight_class,'evidence_path',s.evidence_path)),'[]') from public.league_strength_requests s join public.league_profiles p on p.id=s.athlete_id join public.league_exercise_catalog e on e.id=s.exercise_id where s.gym_id=g and s.status='PENDING'));
 elsif a='staff.catalog_create' then
  insert into public.league_exercise_catalog(gym_id,name,muscle,equipment,instructions)
   values(g,trim(d->>'name'),left(coalesce(d->>'muscle',''),80),left(coalesce(d->>'equipment','Sin equipamiento'),120),coalesce(d->>'instructions','')) returning to_jsonb(league_exercise_catalog.*) into result;
  return result;
 elsif a='staff.verify' then
  select * into r from public.league_strength_requests where id=(d->>'request_id')::uuid and gym_id=g for update;
  if not found then raise exception 'Marca no disponible.' using errcode='42501';end if;
  if exists(select 1 from auth.users where id=r.athlete_id and lower(email)=lower(d->>'actor_email')) then raise exception 'Otra persona autorizada debe verificar tu marca.' using errcode='42501';end if;
  if coalesce(d->>'decision','') not in ('APPROVED','REJECTED') or coalesce(length(trim(d->>'reason')),0) not between 3 and 1000 then raise exception 'Indica la decisión y el motivo.';end if;
  if r.status<>'PENDING' then
   if r.status=d->>'decision' then return jsonb_build_object('status',r.status);end if;
   raise exception 'Esta solicitud ya fue revisada.';
  end if;
  update public.league_strength_requests set status=d->>'decision',reviewed_at=now(),reviewed_by=actor where id=r.id;
  insert into league_private.verification_history(request_id,gym_id,actor_id,decision,reason) values(r.id,g,actor,d->>'decision',trim(d->>'reason'));
  return jsonb_build_object('status',d->>'decision');
 end if;
 if d->>'actor_role'<>'admin' then raise exception 'Permiso de administración requerido.' using errcode='42501';end if;
 if a='staff.approve_join' then
  select * into r from public.league_join_requests where id=(d->>'request_id')::uuid and gym_id=g for update;
  if not found or r.status<>'PENDING' then raise exception 'Solicitud no disponible.' using errcode='42501';end if;
  insert into public.league_links(athlete_id,gym_id,source_profile_id,approved_by) values(r.athlete_id,g,(d->>'source_profile_id')::uuid,actor);
  update public.league_join_requests set status='APPROVED',reviewed_at=now(),reviewed_by=actor where id=r.id;
  insert into league_private.audit(gym_id,actor_id,action,record_id) values(g,actor,a,r.id);
  return jsonb_build_object('status','APPROVED');
 elsif a='staff.reject_join' then
  update public.league_join_requests set status='REJECTED',reviewed_at=now(),reviewed_by=actor where id=(d->>'request_id')::uuid and gym_id=g and status='PENDING';
  return jsonb_build_object('status','REJECTED');
 elsif a='staff.invite' then
  if d->>'token_hash' !~ '^[a-f0-9]{64}$' or length(d->>'email') not between 3 and 254 then raise exception 'Revisa la invitación.';end if;
  insert into league_private.invites(gym_id,source_profile_id,email,token_hash,expires_at,created_by)
   values(g,(d->>'source_profile_id')::uuid,lower(trim(d->>'email')),d->>'token_hash',now()+interval '24 hours',actor);
  return jsonb_build_object('created',true);
 end if;
 raise exception 'Operación no disponible.' using errcode='22023';
end $$;
create function public.league_gateway(p_action text,p_data jsonb) returns jsonb language sql security invoker set search_path='' as $$
 select league_private.service(p_action,p_data)
$$;
revoke all on function league_private.service(text,jsonb) from public,anon,authenticated;
revoke all on function public.league_gateway(text,jsonb) from public,anon,authenticated;
grant execute on function league_private.service(text,jsonb),public.league_gateway(text,jsonb) to service_role;
commit;
