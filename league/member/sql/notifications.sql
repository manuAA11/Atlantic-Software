-- League-owned notification state only. Never triggers writes from Gym source tables.
begin;
create table league_member_private.observed_state(
 athlete_id uuid not null,gym_id uuid not null,source_key text not null,fingerprint text not null,
 primary key(athlete_id,gym_id,source_key)
);
create table league_member_private.push_outbox(
 id uuid primary key default gen_random_uuid(),notice_id uuid not null references public.league_member_notifications(id),
 athlete_id uuid not null,gym_id uuid not null,endpoint text not null,
 status text not null default 'PENDING' check(status in ('PENDING','SENDING','SENT','FAILED')),
 attempts integer not null default 0,available_at timestamptz not null default now(),lease_until timestamptz,
 unique(notice_id,endpoint)
);
alter table league_member_private.observed_state enable row level security;
alter table league_member_private.push_outbox enable row level security;
revoke all on league_member_private.observed_state,league_member_private.push_outbox from public,anon,authenticated;
grant all on league_member_private.observed_state,league_member_private.push_outbox to service_role;
create function league_member_private.enqueue_notice() returns trigger language plpgsql security invoker set search_path='' as $$
begin
 insert into league_member_private.push_outbox(notice_id,athlete_id,gym_id,endpoint)
 select new.id,new.athlete_id,new.gym_id,endpoint from league_member_private.push_subscriptions
 where athlete_id=new.athlete_id and gym_id=new.gym_id on conflict do nothing;
 return new;
end $$;
revoke all on function league_member_private.enqueue_notice() from public,anon,authenticated;
create trigger league_member_notice_push after insert on public.league_member_notifications for each row execute function league_member_private.enqueue_notice();
create function league_member_private.emit(a uuid,g uuid,k text,t text,b text,route text) returns void
language sql security invoker set search_path='' as $$
 insert into public.league_member_notifications(athlete_id,gym_id,source_key,title,body,target)
 values(a,g,k,t,b,route) on conflict(athlete_id,gym_id,source_key) do nothing
$$;
create function league_member_private.observe(a uuid,g uuid,k text,fp text) returns boolean
language plpgsql security invoker set search_path='' as $$
declare previous text;
begin
 select fingerprint into previous from league_member_private.observed_state where athlete_id=a and gym_id=g and source_key=k for update;
 insert into league_member_private.observed_state values(a,g,k,fp) on conflict(athlete_id,gym_id,source_key) do update set fingerprint=excluded.fingerprint;
 return previous is not null and previous<>fp;
end $$;
revoke all on function league_member_private.emit(uuid,uuid,text,text,text,text),league_member_private.observe(uuid,uuid,text,text) from public,anon,authenticated;
create function public.league_member_jobs(p_action text,p_data jsonb default '{}') returns jsonb
language plpgsql security invoker set search_path='' as $$
declare a uuid;g uuid;client bigint;conn jsonb;m jsonb;fp text;item record;period text;changed boolean;result jsonb;
begin
 if p_action='targets' then
  return coalesce(jsonb_agg(jsonb_build_object('actor',auth_user_id,'gym',gym_id)),'[]') from league_member_private.identities;
 elsif p_action='reconcile' then
  a:=(p_data->>'actor')::uuid;g:=(p_data->>'gym')::uuid;conn:=league_member_private.connection(a,g);
  if conn is null then return jsonb_build_object('skipped',true);end if;
  client:=(conn->>'client_id')::bigint;m:=league_member_private.membership(a,g);
  period:=coalesce(m->>'membership_id','NO_PLAN')||':'||coalesce(m->>'ends_at','NO_PERIOD');
  fp:=md5(jsonb_build_array(m->>'status',m->>'ends_at',m->>'membership_id')::text);
  changed:=league_member_private.observe(a,g,'membership',fp);
  if changed then perform league_member_private.emit(a,g,'membership:'||fp,'Tu membresía cambió','Consulta el estado y vencimiento actualizados de tu plan.','/');end if;
  if coalesce((m->>'renewable')::boolean,false) and not coalesce((m->>'frozen')::boolean,false) and m->>'remaining_days' is not null then
   if (m->>'remaining_days')::int in (0,1,3,7) then
    perform league_member_private.emit(a,g,'expiry:'||period||':'||(m->>'remaining_days')||':'||(m->>'status'),case when m->>'status'='EXPIRED' then 'Membresía vencida' when (m->>'remaining_days')::int=0 then 'Tu membresía vence hoy' else 'Tu membresía está por vencer' end,'Consulta el vencimiento y las opciones de renovación en la aplicación.','/');
   end if;
  end if;
  -- Only the original server-confirmed membership change can approve a renewal request.
  if coalesce((m->>'active')::boolean,false) and coalesce((m->>'renewable')::boolean,false) then
   for item in update public.league_member_renewals set status='APPROVED',updated_at=now()
    where athlete_id=a and gym_id=g and status in ('PENDING','REVIEW') and split_part(period_key,':',1) is distinct from m->>'membership_id'
    and exists(select 1 from public.memberships paid where paid.gym_id=g and paid.client_id=client and paid.id=(m->>'membership_id')::bigint and paid.payment_status='posted') returning id loop
    perform league_member_private.emit(a,g,'renewal:'||item.id||':approved','Membresía actualizada','El gimnasio registró un nuevo periodo activo para tu membresía.','/');
   end loop;
  end if;
  for item in select k.id,k.name,k.starts_at,k.status,k.version,r.status reservation_status from public.reservations r
   join public.classes k on k.id=r.class_id and k.gym_id=r.gym_id where r.gym_id=g and r.client_id=client and k.starts_at>now()-interval '7 days' loop
   fp:=md5(jsonb_build_array(item.starts_at,item.status,item.version,item.reservation_status)::text);
   if league_member_private.observe(a,g,'class:'||item.id,fp) then
    perform league_member_private.emit(a,g,'class:'||item.id||':'||fp,'Tu clase o reserva cambió','Consulta la fecha y el estado actual de tu reserva.','/agenda');
   end if;
   if item.reservation_status='RESERVADA' and item.status='PROGRAMADA' then
    if item.starts_at between now()+interval '23 hours 55 minutes' and now()+interval '24 hours' then
     perform league_member_private.emit(a,g,'class-reminder:'||item.id||':'||item.starts_at||':24h','Tienes una clase mañana','Consulta los detalles de tu próxima clase.','/agenda');
    elsif item.starts_at between now()+interval '55 minutes' and now()+interval '1 hour' then
     perform league_member_private.emit(a,g,'class-reminder:'||item.id||':'||item.starts_at||':1h','Tu clase está próxima','Consulta los detalles de tu próxima clase.','/agenda');
    end if;
   end if;
  end loop;
  for item in select id,name,goal,notes from public.routines where gym_id=g and client_id=client and active loop
   fp:=md5(to_jsonb(item)::text||coalesce((select jsonb_agg(to_jsonb(e) order by e.id)::text from public.exercises e where e.gym_id=g and e.routine_id=item.id),''));
   if league_member_private.observe(a,g,'routine:'||item.id,fp) then
    perform league_member_private.emit(a,g,'routine:'||item.id||':'||fp,'Tu rutina cambió','Tu entrenador actualizó un plan asignado.','/rutinas');
   end if;
  end loop;
  for item in select id,title,starts_at,status,version from public.league_member_events where gym_id=g and status<>'DRAFT' and starts_at>now()-interval '1 day' loop
   fp:=md5(to_jsonb(item)::text);
   if not exists(select 1 from league_member_private.observed_state where athlete_id=a and gym_id=g and source_key='event:'||item.id) then
    perform league_member_private.emit(a,g,'event:'||item.id||':'||fp,'Nuevo evento del gimnasio','Consulta los próximos eventos de tu gimnasio.','/agenda');
   elsif league_member_private.observe(a,g,'event:'||item.id,fp) then
    perform league_member_private.emit(a,g,'event:'||item.id||':'||fp,'Un evento cambió','Consulta la información actualizada del evento.','/agenda');
   end if;
   perform league_member_private.observe(a,g,'event:'||item.id,fp);
  end loop;
  return jsonb_build_object('reconciled',true);
 elsif p_action='claim' then
  update league_member_private.push_outbox o set status='FAILED' where status in ('PENDING','SENDING') and not exists(select 1 from league_member_private.push_subscriptions s where s.athlete_id=o.athlete_id and s.gym_id=o.gym_id and s.endpoint=o.endpoint);
  with picked as(select o.id from league_member_private.push_outbox o
    where (o.status='PENDING' and o.available_at<=now() or o.status='SENDING' and o.lease_until<now()) and o.attempts<8
    order by o.available_at for update skip locked limit 50),claimed as(
    update league_member_private.push_outbox o set status='SENDING',attempts=attempts+1,lease_until=now()+interval '5 minutes'
    from picked where o.id=picked.id returning o.*)
   select coalesce(jsonb_agg(to_jsonb(t)),'[]') into result from (select c.id,c.athlete_id,c.gym_id,c.endpoint,c.attempts,s.p256dh,s.auth from claimed c
   join league_member_private.push_subscriptions s on s.athlete_id=c.athlete_id and s.gym_id=c.gym_id and s.endpoint=c.endpoint)t;
  return result;
 elsif p_action='validate_delivery' then
  select o.*,n.source_key into item from league_member_private.push_outbox o join public.league_member_notifications n on n.id=o.notice_id where o.id=(p_data->>'id')::uuid;
  if not found or league_member_private.connection(item.athlete_id,item.gym_id) is null then return 'false'::jsonb;end if;
  if item.source_key like 'expiry:%' then
   m:=league_member_private.membership(item.athlete_id,item.gym_id);
   period:=coalesce(m->>'membership_id','NO_PLAN')||':'||coalesce(m->>'ends_at','NO_PERIOD');
   return to_jsonb(not coalesce((m->>'frozen')::boolean,false) and coalesce((m->>'renewable')::boolean,false)
    and item.source_key='expiry:'||period||':'||coalesce(m->>'remaining_days','unknown')||':'||coalesce(m->>'status','unknown'));
  elsif item.source_key like 'class-reminder:%' then
   conn:=league_member_private.connection(item.athlete_id,item.gym_id);
   return to_jsonb(exists(select 1 from public.classes k join public.reservations r on r.class_id=k.id and r.gym_id=k.gym_id
    where k.gym_id=item.gym_id and k.id=split_part(item.source_key,':',2)::bigint
    and r.client_id=(conn->>'client_id')::bigint and r.status='RESERVADA' and k.status='PROGRAMADA' and k.starts_at>now()
    and item.source_key like 'class-reminder:'||k.id||':'||k.starts_at||':%'));
  end if;
  return 'true'::jsonb;
 elsif p_action='finish' then
  update league_member_private.push_outbox set status=case when p_data->>'outcome'='SENT' then 'SENT' when attempts>=8 or p_data->>'outcome' in ('GONE','OBSOLETE') then 'FAILED' else 'PENDING' end,
   available_at=now()+interval '5 minutes'*least(attempts,12),lease_until=null where id=(p_data->>'id')::uuid and status='SENDING';
  if p_data->>'outcome'='GONE' then
   delete from league_member_private.push_subscriptions s using league_member_private.push_outbox o
   where o.id=(p_data->>'id')::uuid and s.athlete_id=o.athlete_id and s.gym_id=o.gym_id and s.endpoint=o.endpoint;
  end if;
  return jsonb_build_object('updated',true);
 end if;
 raise exception 'Acción no disponible.';
end $$;
revoke all on function public.league_member_jobs(text,jsonb) from public,anon,authenticated;
grant execute on function public.league_member_jobs(text,jsonb) to service_role;
grant execute on function league_member_private.emit(uuid,uuid,text,text,text,text),league_member_private.observe(uuid,uuid,text,text) to service_role;
grant select on public.routines,public.exercises to service_role;
commit;
