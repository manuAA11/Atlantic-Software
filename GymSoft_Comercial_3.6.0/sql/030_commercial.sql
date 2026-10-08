-- Control central. Ninguna clave de servicio se entrega a los clientes.
create table private.software_owners (
 user_id uuid primary key references auth.users(id), created_at timestamptz not null default now()
);
create table private.subscriptions (
 gym_id uuid primary key references public.gyms(id),
 contact_email text not null, plan text not null default 'Standard',
 monthly_price numeric(12,2) not null default 0 check(monthly_price>=0),
 currency text not null default 'COP' check(currency ~ '^[A-Z]{3}$'),
 status text not null default 'trial' check(status in ('trial','active','suspended','cancelled')),
 expires_at timestamptz not null, grace_until timestamptz,
 max_devices integer not null default 2 check(max_devices between 1 and 100),
 max_users integer not null default 10 check(max_users between 1 and 1000),
 notes text not null default '', created_at timestamptz not null default now()
);
create table private.license_devices (
 id uuid primary key default gen_random_uuid(), gym_id uuid not null references public.gyms(id),
 device_hash text not null check(device_hash ~ '^[a-f0-9]{64}$'), name text not null,
 blocked boolean not null default false, approved boolean not null default false, first_seen timestamptz not null default now(),
 last_seen timestamptz not null default now(), unique(gym_id,device_hash)
);
create table private.license_sessions (
 session_id uuid primary key, gym_id uuid not null references public.gyms(id),
 user_id uuid not null references auth.users(id), device_id uuid not null references private.license_devices(id),
 last_seen timestamptz not null default now()
);
create table private.activation_invites (
 code_hash text primary key, gym_id uuid not null references public.gyms(id),
 email text not null, role text not null check(role in ('admin','receptionist')),
 expires_at timestamptz not null default (now()+interval '7 days'), used_at timestamptz,
 created_by uuid references auth.users(id), created_at timestamptz not null default now()
);
create table private.subscription_payments (
 id uuid primary key default gen_random_uuid(), gym_id uuid not null references public.gyms(id),
 amount numeric(12,2) not null check(amount>=0), currency text not null check(currency ~ '^[A-Z]{3}$'),
 months integer not null check(months between 1 and 120), reference text not null,
 period_from timestamptz not null, period_until timestamptz not null,
 idempotency_key uuid not null, recorded_by uuid not null references auth.users(id),
 created_at timestamptz not null default now(), unique(gym_id,idempotency_key)
);
create table private.owner_events (
 id bigint generated always as identity primary key, gym_id uuid references public.gyms(id),
 actor uuid references auth.users(id), action text not null, detail jsonb not null default '{}',
 created_at timestamptz not null default now()
);
create index on private.owner_events(gym_id,created_at desc);
create index on private.license_sessions(gym_id,user_id);
create index on private.subscription_payments(gym_id,created_at desc);

create function private.require_owner() returns void
language plpgsql stable security definer set search_path='' as $$
begin
 if not exists(select 1 from private.software_owners where user_id=auth.uid()) then
  raise exception 'Acceso exclusivo del propietario de Gym soft.' using errcode='42501';
 end if;
end $$;
create function private.code_hash(p_code text) returns text
language sql immutable set search_path='' as $$
 select encode(sha256(convert_to(lower(trim(p_code)),'UTF8')),'hex')
$$;
create function private.subscription_open(p_gym_id uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from private.subscriptions s where s.gym_id=p_gym_id
  and s.status in ('active','trial') and now()<greatest(s.expires_at,coalesce(s.grace_until,s.expires_at)))
$$;
create function private.current_access(p_gym_id uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select private.subscription_open(p_gym_id) and exists(
  select 1 from private.license_sessions ls join private.license_devices d on d.id=ls.device_id
  join public.gym_users gu on gu.gym_id=ls.gym_id and gu.user_id=ls.user_id
  where ls.session_id=nullif(auth.jwt()->>'session_id','')::uuid
    and ls.user_id=auth.uid() and ls.gym_id=p_gym_id and d.gym_id=p_gym_id
    and gu.enabled and d.approved and not d.blocked)
$$;
create or replace function private.user_has_gym_role(p_gym_id uuid,p_roles text[])
returns boolean language sql stable security definer set search_path='' as $$
 select private.current_access(p_gym_id) and exists(select 1 from public.gym_users gu
  where gu.gym_id=p_gym_id and gu.user_id=auth.uid() and gu.enabled and gu.role=any(p_roles))
$$;
create function private.require_current_access() returns void
language plpgsql stable security definer set search_path='' as $$
declare g uuid;
begin
 select gym_id into g from public.gym_users where user_id=auth.uid() and enabled;
 if g is null or not private.current_access(g) then
  raise exception 'Acceso no autorizado. Revisa tu suscripción, cuenta y equipo con el proveedor.' using errcode='42501';
 end if;
end $$;

create function public.commercial_context() returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare result jsonb;
begin
 if auth.uid() is null then raise exception 'Inicia sesión.' using errcode='42501'; end if;
 select jsonb_build_object('gym_id',g.id,'gym_name',g.name,'role',gu.role,'enabled',gu.enabled,'timezone',g.timezone)
 into result from public.gym_users gu join public.gyms g on g.id=gu.gym_id where gu.user_id=auth.uid();
 return coalesce(result,'{}');
end $$;

create function public.commercial_redeem_invite(p_code text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare inv private.activation_invites%rowtype; mail text; sub private.subscriptions%rowtype;
begin
 select lower(email) into mail from auth.users where id=auth.uid() and email_confirmed_at is not null;
 if mail is null then raise exception 'Confirma tu correo e inicia sesión.' using errcode='42501'; end if;
 if exists(select 1 from public.gym_users where user_id=auth.uid()) then
  raise exception 'Esta cuenta ya está asignada a un gimnasio.' using errcode='42501';
 end if;
 select * into inv from private.activation_invites where code_hash=private.code_hash(p_code) for update;
 if not found or inv.used_at is not null or inv.expires_at<=now() or inv.email<>mail then
  raise exception 'Invitación inválida, vencida o destinada a otro correo.' using errcode='42501';
 end if;
 select * into sub from private.subscriptions where gym_id=inv.gym_id for update;
 if not private.subscription_open(inv.gym_id) then raise exception 'El proveedor debe activar la suscripción.' using errcode='42501'; end if;
 if (select count(*) from public.gym_users where gym_id=inv.gym_id and enabled)>=sub.max_users then
  raise exception 'Se alcanzó el límite de usuarios.' using errcode='42501';
 end if;
 insert into public.gym_users(gym_id,user_id,role) values(inv.gym_id,auth.uid(),inv.role);
 update private.activation_invites set used_at=now() where code_hash=inv.code_hash;
 insert into private.owner_events(gym_id,actor,action,detail) values(inv.gym_id,auth.uid(),'invite_redeemed',jsonb_build_object('role',inv.role));
 return public.commercial_context();
end $$;

create function public.commercial_check_license(p_device_hash text,p_device_name text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare g uuid; sub private.subscriptions%rowtype; dev private.license_devices%rowtype;
 sid uuid := nullif(auth.jwt()->>'session_id','')::uuid; state text; existing_device uuid;
begin
 if auth.uid() is null or sid is null then raise exception 'Sesión inválida. Inicia sesión otra vez.' using errcode='42501'; end if;
 select gym_id into g from public.gym_users where user_id=auth.uid() and enabled;
 if g is null then return jsonb_build_object('allowed',false,'state','account_disabled','message','Cuenta sin gimnasio o desactivada.'); end if;
 select * into sub from private.subscriptions where gym_id=g for update;
 if not found or not private.subscription_open(g) then
  return jsonb_build_object('allowed',false,'state',case when sub.status in ('suspended','cancelled') then sub.status else 'expired' end,
   'message','Suscripción vencida o suspendida. Contacta a tu proveedor.','expires_at',sub.expires_at);
 end if;
 if p_device_hash !~ '^[a-f0-9]{64}$' or p_device_hash is null then raise exception 'Identificador de equipo inválido.'; end if;
 select * into dev from private.license_devices where gym_id=g and device_hash=p_device_hash for update;
 if found and dev.blocked then return jsonb_build_object('allowed',false,'state','device_revoked','message','Este equipo fue desautorizado.'); end if;
 if dev.id is null then
  insert into private.license_devices(gym_id,device_hash,name) values(g,p_device_hash,left(coalesce(nullif(trim(p_device_name),''),'Computador'),120)) returning * into dev;
  insert into private.owner_events(gym_id,actor,action,detail) values(g,auth.uid(),'device_registered',jsonb_build_object('device_id',dev.id,'name',dev.name));
 end if;
 if not dev.approved then
  return jsonb_build_object('allowed',false,'state','device_pending','message','Equipo registrado y pendiente de autorización del proveedor. Después de autorizarlo, vuelve a ingresar.');
 end if;
 select device_id into existing_device from private.license_sessions where session_id=sid;
 if existing_device is not null and existing_device<>dev.id then raise exception 'La sesión pertenece a otro equipo. Inicia sesión nuevamente.' using errcode='42501'; end if;
 insert into private.license_sessions(session_id,gym_id,user_id,device_id) values(sid,g,auth.uid(),dev.id)
 on conflict(session_id) do update set last_seen=now();
 update private.license_devices set last_seen=now() where id=dev.id;
 state:=case when now()>=sub.expires_at then 'grace' else sub.status end;
 return jsonb_build_object('allowed',true,'state',state,'message','Suscripción válida.','gym_id',g,
  'expires_at',sub.expires_at,'grace_until',sub.grace_until,'plan',sub.plan,'server_time',now());
end $$;

create function public.owner_list_gyms() returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare result jsonb;
begin
 perform private.require_owner();
 select coalesce(jsonb_agg(to_jsonb(t) order by t.expires_at),'[]') into result from (
  select g.id,g.name,g.timezone,s.*,
   case when s.status in ('suspended','cancelled') then s.status when now()<s.expires_at then s.status
    when now()<s.grace_until then 'grace' else 'expired' end as effective_status,
   (select count(*) from private.license_devices d where d.gym_id=g.id and d.approved and not d.blocked) as active_devices,
   (select count(*) from private.license_devices d where d.gym_id=g.id and not d.approved and not d.blocked) as pending_devices,
   (select max(d.last_seen) from private.license_devices d where d.gym_id=g.id) as last_seen,
   (select count(*) from public.gym_users gu where gu.gym_id=g.id and gu.enabled) as active_users
  from public.gyms g join private.subscriptions s on s.gym_id=g.id
 ) t;
 return result;
end $$;

create function public.owner_create_gym(p_name text,p_email text,p_monthly_price numeric,p_currency text default 'COP',
 p_max_devices integer default 2,p_trial_days integer default 7,p_timezone text default 'America/Bogota') returns jsonb
language plpgsql security definer set search_path='' as $$
declare g uuid; code text := gen_random_uuid()::text;
begin
 perform private.require_owner();
 if trim(coalesce(p_email,'')) !~ '^[^ @]+@[^ @]+[.][^ @]+$' or p_trial_days not between 1 and 90
 or not exists(select 1 from pg_timezone_names where name=p_timezone) then raise exception 'Correo, días o zona horaria inválidos.'; end if;
 insert into public.gyms(name,timezone) values(trim(p_name),p_timezone) returning id into g;
 insert into private.subscriptions(gym_id,contact_email,monthly_price,currency,max_devices,expires_at)
 values(g,lower(trim(p_email)),p_monthly_price,upper(p_currency),p_max_devices,now()+make_interval(days=>p_trial_days));
 insert into private.activation_invites(code_hash,gym_id,email,role,created_by)
 values(private.code_hash(code),g,lower(trim(p_email)),'admin',auth.uid());
 insert into public.plans(gym_id,name,duration_days,price,entry_limit) values
  (g,'Mensual',30,0,null),(g,'Semanal',7,0,null),(g,'Sesión',1,0,1),(g,'Tiquetera',30,0,15);
 insert into public.marketing_settings(gym_id,timezone) values(g,p_timezone);
 insert into private.owner_events(gym_id,actor,action,detail) values(g,auth.uid(),'gym_created',jsonb_build_object('email',lower(trim(p_email)),'trial_days',p_trial_days));
 return jsonb_build_object('gym_id',g,'activation_code',code,'email',lower(trim(p_email)),'invite_expires_at',now()+interval '7 days');
end $$;

create function public.owner_renew(p_gym_id uuid,p_months integer,p_amount numeric,p_currency text,
 p_reference text,p_idempotency_key uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare s private.subscriptions%rowtype; payment private.subscription_payments%rowtype; start_at timestamptz; end_at timestamptz;
begin
 perform private.require_owner();
 if p_months not between 1 and 120 or p_amount<0 or p_amount is null or length(trim(coalesce(p_reference,'')))<3
 or p_idempotency_key is null then raise exception 'Completa meses, valor, referencia e identificador de operación.'; end if;
 select * into s from private.subscriptions where gym_id=p_gym_id for update;
 if not found then raise exception 'Gimnasio inexistente.'; end if;
 select * into payment from private.subscription_payments where gym_id=p_gym_id and idempotency_key=p_idempotency_key;
 if found then
  if payment.amount<>p_amount or payment.months<>p_months or payment.currency<>upper(p_currency) or payment.reference<>trim(p_reference) then
   raise exception 'La operación ya existe con otros datos.' using errcode='22023';
  end if;
  return to_jsonb(payment);
 end if;
 if upper(p_currency)<>s.currency then raise exception 'La moneda debe coincidir con el contrato.'; end if;
 start_at:=greatest(now(),s.expires_at);
 end_at:=((start_at at time zone (select timezone from public.gyms where id=p_gym_id))+make_interval(months=>p_months))
 at time zone (select timezone from public.gyms where id=p_gym_id);
 insert into private.subscription_payments(gym_id,amount,currency,months,reference,period_from,period_until,idempotency_key,recorded_by)
 values(p_gym_id,p_amount,upper(p_currency),p_months,trim(p_reference),start_at,end_at,p_idempotency_key,auth.uid()) returning * into payment;
 update private.subscriptions set status='active',expires_at=end_at,grace_until=null where gym_id=p_gym_id;
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),'subscription_renewed',to_jsonb(payment));
 return to_jsonb(payment);
end $$;

create function public.owner_set_status(p_gym_id uuid,p_status text,p_reason text) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform private.require_owner();
 if p_status not in ('active','suspended','cancelled') or length(trim(coalesce(p_reason,'')))<3 then raise exception 'Estado o motivo inválido.'; end if;
 update private.subscriptions set status=p_status where gym_id=p_gym_id;
 if not found then raise exception 'Gimnasio inexistente.'; end if;
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),'status_changed',jsonb_build_object('status',p_status,'reason',p_reason));
end $$;
create function public.owner_update_contract(p_gym_id uuid,p_price numeric,p_currency text,p_max_devices integer,
 p_max_users integer,p_notes text) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform private.require_owner();
 perform 1 from private.subscriptions where gym_id=p_gym_id for update;
 if not found then raise exception 'Gimnasio inexistente.'; end if;
 if p_max_devices<(select count(*) from private.license_devices where gym_id=p_gym_id and approved and not blocked)
 or p_max_users<(select count(*) from public.gym_users where gym_id=p_gym_id and enabled) then
  raise exception 'Desactiva primero los equipos o usuarios que superan el nuevo límite.';
 end if;
 update private.subscriptions set monthly_price=p_price,currency=upper(p_currency),max_devices=p_max_devices,max_users=p_max_users,notes=left(p_notes,4000) where gym_id=p_gym_id;
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),'contract_changed',jsonb_build_object('price',p_price,'currency',upper(p_currency),'devices',p_max_devices,'users',p_max_users));
end $$;
create function public.owner_grant_grace(p_gym_id uuid,p_days integer,p_reason text) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform private.require_owner();
 if p_days not between 1 and 30 or length(trim(coalesce(p_reason,'')))<3 then raise exception 'Días o motivo inválido.'; end if;
 update private.subscriptions set grace_until=greatest(now(),expires_at)+make_interval(days=>p_days) where gym_id=p_gym_id;
 if not found then raise exception 'Gimnasio inexistente.'; end if;
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),'grace_granted',jsonb_build_object('days',p_days,'reason',p_reason));
end $$;
create function public.owner_gym_detail(p_gym_id uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
begin
 perform private.require_owner();
 return jsonb_build_object(
 'devices',coalesce((select jsonb_agg(to_jsonb(d) order by d.last_seen desc) from private.license_devices d where gym_id=p_gym_id),'[]'),
 'users',coalesce((select jsonb_agg(jsonb_build_object('user_id',gu.user_id,'email',u.email,'role',gu.role,'enabled',gu.enabled)) from public.gym_users gu join auth.users u on u.id=gu.user_id where gu.gym_id=p_gym_id),'[]'),
 'payments',coalesce((select jsonb_agg(to_jsonb(p) order by p.created_at desc) from private.subscription_payments p where gym_id=p_gym_id),'[]'),
 'events',coalesce((select jsonb_agg(to_jsonb(e) order by e.created_at desc) from (select * from private.owner_events where gym_id=p_gym_id order by created_at desc limit 200) e),'[]'));
end $$;
create function public.owner_set_device(p_device_id uuid,p_blocked boolean,p_reason text) returns void
language plpgsql security definer set search_path='' as $$
declare g uuid; s private.subscriptions%rowtype;
begin
 perform private.require_owner();
 if length(trim(coalesce(p_reason,'')))<3 or p_blocked is null then raise exception 'Indica un motivo.'; end if;
 select gym_id into g from private.license_devices where id=p_device_id;
 if g is null then raise exception 'Equipo inexistente.'; end if;
 select * into s from private.subscriptions where gym_id=g for update;
 if not p_blocked and (select blocked or not approved from private.license_devices where id=p_device_id)
 and (select count(*) from private.license_devices where gym_id=g and approved and not blocked)>=s.max_devices then raise exception 'Límite de equipos alcanzado.'; end if;
 update private.license_devices set blocked=p_blocked,approved=true where id=p_device_id;
 insert into private.owner_events(gym_id,actor,action,detail) values(g,auth.uid(),'device_changed',jsonb_build_object('id',p_device_id,'blocked',p_blocked,'reason',p_reason));
end $$;
create function public.owner_set_user(p_user_id uuid,p_enabled boolean,p_reason text) returns void
language plpgsql security definer set search_path='' as $$
declare g uuid; s private.subscriptions%rowtype;
begin
 perform private.require_owner();
 if length(trim(coalesce(p_reason,'')))<3 or p_enabled is null then raise exception 'Indica un motivo.'; end if;
 select gym_id into g from public.gym_users where user_id=p_user_id;
 if g is null then raise exception 'Usuario inexistente.'; end if;
 select * into s from private.subscriptions where gym_id=g for update;
 if p_enabled and not (select enabled from public.gym_users where user_id=p_user_id)
 and (select count(*) from public.gym_users where gym_id=g and enabled)>=s.max_users then raise exception 'Límite de usuarios alcanzado.'; end if;
 update public.gym_users set enabled=p_enabled where user_id=p_user_id;
 insert into private.owner_events(gym_id,actor,action,detail) values(g,auth.uid(),'user_changed',jsonb_build_object('id',p_user_id,'enabled',p_enabled,'reason',p_reason));
end $$;
create function public.owner_invite_user(p_gym_id uuid,p_email text,p_role text default 'admin') returns text
language plpgsql security definer set search_path='' as $$
declare code text:=gen_random_uuid()::text;
begin
 perform private.require_owner();
 if p_role not in ('admin','receptionist') or lower(trim(coalesce(p_email,''))) !~ '^[^ @]+@[^ @]+[.][^ @]+$' then raise exception 'Correo o rol inválido.'; end if;
 update private.activation_invites set expires_at=now() where gym_id=p_gym_id and email=lower(trim(p_email)) and used_at is null;
 insert into private.activation_invites(code_hash,gym_id,email,role,created_by) values(private.code_hash(code),p_gym_id,lower(trim(p_email)),p_role,auth.uid());
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),'invite_created',jsonb_build_object('email',lower(trim(p_email)),'role',p_role));
 return code;
end $$;

-- Marca propia de cada gimnasio, compartida entre sus equipos.
create table public.gym_branding (
 gym_id uuid primary key references public.gyms(id), logo_data text not null default '' check(length(logo_data)<=1000000),
 updated_at timestamptz not null default now()
);
alter table public.gym_branding enable row level security;
create policy branding_read on public.gym_branding for select to authenticated
 using(private.user_has_gym_role(gym_id,array['admin','receptionist']));
create policy branding_write on public.gym_branding for all to authenticated
 using(private.user_has_gym_role(gym_id,array['admin'])) with check(private.user_has_gym_role(gym_id,array['admin']));
grant select,insert,update on public.gym_branding to authenticated;

-- Todas las tablas privadas quedan cerradas a los roles de aplicaciones.
revoke all on all tables in schema private from public,anon,authenticated;
revoke all on all sequences in schema private from public,anon,authenticated;
