-- Gym soft para ZTATTUZ 3.4.5. Actualización aditiva del proyecto original.
-- No ejecuta altas, importaciones ni borrados de registros de gimnasios.
begin;
set local lock_timeout='8s';
set local statement_timeout='60s';
do $$ begin
 if to_regprocedure('public.ztattuz_today()') is null or
    to_regprocedure('public.ztattuz_change_payment(uuid,bigint,bigint,text,text,bigint,text,text)') is null then
  raise exception 'Este archivo requiere la base original ZTATTUZ con la corrección de pagos instalada.';
 end if;
 if to_regprocedure('public.commercial_system_info()') is not null then
  raise exception 'Este archivo es exclusivo de ZTATTUZ; no lo ejecutes en Gym soft Comercial.';
 end if;
end $$;
create or replace function private.current_timezone() returns text
language sql stable set search_path='' as $$ select 'America/Bogota'::text $$;
revoke all on function private.current_timezone() from public,anon,authenticated;
alter table public.plans add column if not exists duration_months integer;
alter table public.memberships add column if not exists initial_entries_used bigint not null default 0;
alter table public.memberships add column if not exists carryover_key uuid;
do $$ begin
 if not exists(select 1 from pg_constraint where conrelid='public.plans'::regclass and conname='ticket_months_valid') then
  alter table public.plans add constraint ticket_months_valid check(duration_months is null or (entry_limit is not null and duration_months between 1 and 120));
 end if;
 if not exists(select 1 from pg_constraint where conrelid='public.memberships'::regclass and conname='ticket_initial_used_valid') then
  alter table public.memberships add constraint ticket_initial_used_valid check(initial_entries_used>=0 and
   ((entry_limit is null and initial_entries_used=0) or (entry_limit is not null and initial_entries_used<=entry_limit)));
 end if;
end $$;
create unique index if not exists membership_carryover_key on public.memberships(gym_id,carryover_key) where carryover_key is not null;
create index if not exists checkins_ticket_consumption on public.checkins(gym_id,membership_id) where result='PERMITIDA';
create or replace function private.ticket_end_date(p_start date,p_days integer,p_months integer)
returns date language sql immutable set search_path='' as $$
 select case when p_months is null then p_start+p_days-1
 else (p_start+pg_catalog.make_interval(months=>p_months))::date-1 end
$$;
revoke all on function private.ticket_end_date(date,integer,integer) from public,anon,authenticated;
CREATE OR REPLACE FUNCTION private.ztattuz_add_membership(p_gym_id uuid, p_client_id bigint, p_plan_id bigint, p_requested_start date, p_amount bigint, p_payment_method text, p_payment_reference text, p_notes text)
 RETURNS TABLE(membership_id bigint, start_date date, end_date date)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
    v_user_id uuid := (select auth.uid());
    v_today date := public.ztattuz_today();
    v_requested_start date;
    v_duration_days integer;
    v_duration_months integer;
    v_entry_limit bigint;
    v_last_end_date date;
    v_start_date date;
    v_end_date date;
    v_membership_id bigint;
begin
    if not private.user_has_gym_role(
        p_gym_id,
        array['admin', 'receptionist']::text[]
    ) then
        raise exception 'No tienes permiso para registrar pagos.'
            using errcode = '42501';
    end if;

    if not private.client_belongs_to_gym(
        p_client_id,
        p_gym_id
    ) then
        raise exception 'El cliente no pertenece al gimnasio.'
            using errcode = '23503';
    end if;

    select
        greatest(p.duration_days, 1),
        p.entry_limit, p.duration_months
    into
        v_duration_days,
        v_entry_limit, v_duration_months
    from public.plans p
    where p.id = p_plan_id
      and p.gym_id = p_gym_id
      and p.active = true;

    if not found then
        raise exception 'El plan no existe o está desactivado.'
            using errcode = '23503';
    end if;

    if coalesce(p_amount, 0) < 0 then
        raise exception 'El valor pagado no puede ser negativo.'
            using errcode = '22023';
    end if;

    -- Impide que dos pagos simultáneos creen fechas superpuestas.
    perform pg_catalog.pg_advisory_xact_lock(p_client_id);

    v_requested_start := coalesce(
        p_requested_start,
        v_today
    );

    select max(m.end_date)
    into v_last_end_date
    from public.memberships m
    left join public.plans current_plan
      on current_plan.id = m.plan_id
     and current_plan.gym_id = m.gym_id
    where m.gym_id = p_gym_id AND m.payment_status = 'posted'
      and m.client_id = p_client_id
      and m.end_date >= v_today
      and (
          coalesce(
              m.entry_limit,
              current_plan.entry_limit
          ) is null
          or (
              select count(*) + m.initial_entries_used
              from public.checkins ch
              where ch.gym_id = p_gym_id
                and ch.client_id = p_client_id
                and ch.membership_id = m.id
                and ch.result = 'PERMITIDA'
          ) < coalesce(
              m.entry_limit,
              current_plan.entry_limit
          )
      );

    v_start_date := case
        when v_last_end_date is null then v_requested_start
        else greatest(
            v_requested_start,
            v_last_end_date + 1
        )
    end;

    v_end_date := private.ticket_end_date(v_start_date, v_duration_days, v_duration_months);

    insert into public.memberships(
        gym_id,
        client_id,
        plan_id,
        start_date,
        end_date,
        entry_limit,
        amount,
        amount_paid,
        payment_method,
        payment_reference,
        notes,
        recorded_by
    )
    values (
        p_gym_id,
        p_client_id,
        p_plan_id,
        v_start_date,
        v_end_date,
        v_entry_limit,
        p_amount,
        p_amount,
        coalesce(
            nullif(trim(p_payment_method), ''),
            'Efectivo'
        ),
        trim(coalesce(p_payment_reference, '')),
        trim(coalesce(p_notes, '')),
        v_user_id
    )
    returning id into v_membership_id;

    return query
    select
        v_membership_id,
        v_start_date,
        v_end_date;
end;
$function$

;
CREATE OR REPLACE FUNCTION private.membership_snapshot_json(p_gym_id uuid, p_client_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
    v_client record;
    v_membership_id bigint;
    v_start_date date;
    v_end_date date;
    v_entry_limit bigint;
    v_entries_used bigint := 0;
    v_plan_name text := 'Sin plan';
    v_today date := public.ztattuz_today();
    v_allowed boolean := false;
    v_status text := 'VENCIDO';
begin
    select
        c.id,
        c.document,
        c.first_name,
        c.last_name,
        c.phone,
        c.email,
        coalesce(c.birthdate, c.birth_date) as birthdate,
        c.biometric_identifier, c.active
    into v_client
    from public.clients c
    where c.id = p_client_id
      and c.gym_id = p_gym_id;

    if not found then
        raise exception 'Cliente no encontrado.' using errcode = 'P0002';
    end if;

    select
        m.id,
        m.start_date,
        m.end_date,
        coalesce(m.entry_limit, p.entry_limit),
        coalesce(p.name, 'Sin plan')
    into
        v_membership_id,
        v_start_date,
        v_end_date,
        v_entry_limit,
        v_plan_name
    from public.memberships m
    left join public.plans p
      on p.id = m.plan_id
     and p.gym_id = m.gym_id
    where m.gym_id = p_gym_id AND m.payment_status = 'posted' /* ZTATTUZ_PAYMENT_VOID_FILTER_V1 */
      and m.client_id = p_client_id
    order by
        case
            when v_today between m.start_date and m.end_date then 0
            else 1
        end,
        m.end_date desc,
        m.id desc
    limit 1;

    if v_membership_id is not null and v_entry_limit is not null then
        select count(*) + (select m.initial_entries_used from public.memberships m where m.gym_id = p_gym_id and m.id = v_membership_id)
        into v_entries_used
        from public.checkins ch
        where ch.gym_id = p_gym_id
          and ch.membership_id = v_membership_id
          and ch.result = 'PERMITIDA';
    end if;

    if not coalesce(v_client.active, true) then
        v_status := 'INACTIVO';
    elsif v_membership_id is null then
        v_status := 'VENCIDO';
    elsif not (v_today between v_start_date and v_end_date) then
        v_status := 'VENCIDO';
    elsif v_entry_limit is not null
          and v_entries_used >= v_entry_limit then
        v_status := 'SIN ENTRADAS';
    else
        v_status := 'AL DÍA';
        v_allowed := true;
    end if;

    return jsonb_build_object(
        'id', v_client.id, 'biometric_identifier', v_client.biometric_identifier,
        'document', v_client.document,
        'first_name', v_client.first_name,
        'last_name', v_client.last_name,
        'client_name', trim(
            concat_ws(' ', v_client.first_name, v_client.last_name)
        ),
        'phone', coalesce(v_client.phone, ''),
        'email', coalesce(v_client.email, ''),
        'birthdate', coalesce(v_client.birthdate::text, ''),
        'active', coalesce(v_client.active, true),
        'status', v_status,
        'allowed', v_allowed,
        'membership_id', v_membership_id,
        'membership_start', coalesce(v_start_date::text, ''),
        'membership_end', coalesce(v_end_date::text, ''),
        'plan_name', v_plan_name,
        'entry_limit', v_entry_limit,
        'entries_used', v_entries_used,
        'entries_remaining', case
            when v_entry_limit is null then null
            else greatest(v_entry_limit - v_entries_used, 0)
        end
    );
end;
$function$

;

-- Saldo inicial: no crea asistencias ni ingresos. El cupo queda fotografiado.
create or replace function private.register_ticket_carryover(p_gym_id uuid,p_client_id bigint,p_plan_id bigint,
 p_start date,p_entries_used bigint,p_notes text,p_request_id uuid)
returns table(membership_id bigint,start_date date,end_date date)
language plpgsql security definer set search_path='' as $$
declare p public.plans%rowtype; m public.memberships%rowtype; ending date; mid bigint;
begin
 if not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
  raise exception 'No tienes permiso para registrar una tiquetera.' using errcode='42501'; end if;
 if not private.client_belongs_to_gym(p_client_id,p_gym_id) then
  raise exception 'El cliente no pertenece al gimnasio.' using errcode='23503'; end if;
 if p_request_id is null or p_start is null or p_start>public.ztattuz_today() or p_entries_used is null then
  raise exception 'Revisa la fecha de inicio y las entradas utilizadas.' using errcode='22023'; end if;
 perform pg_catalog.pg_advisory_xact_lock(p_client_id);
 select * into m from public.memberships where gym_id=p_gym_id and carryover_key=p_request_id;
 if found then
  if m.client_id<>p_client_id or m.plan_id<>p_plan_id or m.start_date<>p_start or m.initial_entries_used<>p_entries_used or m.payment_status<>'posted' then
   raise exception 'Esta solicitud ya corresponde a otra operación. Actualiza la ficha.' using errcode='22023'; end if;
  return query select m.id,m.start_date,m.end_date; return;
 end if;
 select * into p from public.plans where gym_id=p_gym_id and id=p_plan_id and active for share;
 if not found or p.entry_limit is null then
  raise exception 'Selecciona una tiquetera activa.' using errcode='22023'; end if;
 if p_entries_used<0 or p_entries_used>p.entry_limit then
  raise exception 'Las entradas utilizadas exceden el cupo de la tiquetera.' using errcode='22023'; end if;
 ending:=private.ticket_end_date(p_start,p.duration_days,p.duration_months);
 if exists(select 1 from public.memberships x where x.gym_id=p_gym_id and x.client_id=p_client_id
  and x.payment_status='posted' and x.start_date<=ending and x.end_date>=p_start) then
  raise exception 'Ya existe una membresía en esas fechas. Revisa los registros del cliente antes de trasladar esta tiquetera.' using errcode='22023'; end if;
 insert into public.memberships(gym_id,client_id,plan_id,start_date,end_date,entry_limit,initial_entries_used,
  amount,amount_paid,payment_method,payment_reference,notes,recorded_by,carryover_key,paid_at)
 values(p_gym_id,p_client_id,p_plan_id,p_start,ending,p.entry_limit,p_entries_used,0,0,'Saldo inicial','',
  'Tiquetera trasladada sin nuevo cobro. '||trim(coalesce(p_notes,'')),auth.uid(),p_request_id,
  p_start::timestamp at time zone private.current_timezone()) returning id into mid;
 return query select mid,p_start,ending;
end $$;
revoke all on function private.register_ticket_carryover(uuid,bigint,bigint,date,bigint,text,uuid) from public,anon,authenticated;
grant execute on function private.register_ticket_carryover(uuid,bigint,bigint,date,bigint,text,uuid) to authenticated;
create or replace function public.register_ticket_carryover(p_gym_id uuid,p_client_id bigint,p_plan_id bigint,
 p_start date,p_entries_used bigint,p_notes text,p_request_id uuid)
returns table(membership_id bigint,start_date date,end_date date)
language sql security invoker set search_path='' as $$
 select * from private.register_ticket_carryover(p_gym_id,p_client_id,p_plan_id,p_start,p_entries_used,p_notes,p_request_id)
$$;
revoke all on function public.register_ticket_carryover(uuid,bigint,bigint,date,bigint,text,uuid) from public,anon,authenticated;
grant execute on function public.register_ticket_carryover(uuid,bigint,bigint,date,bigint,text,uuid) to authenticated;

-- Una sola lista por gimnasio evita consultas individuales desde el Dashboard.
create or replace function private.ticket_followup(p_gym_id uuid)
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare result jsonb; today date:=public.ztattuz_today();
begin
 if not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
  raise exception 'No tienes permiso para consultar las tiqueteras.' using errcode='42501'; end if;
 with latest as (
  select distinct on (m.client_id) m.*, coalesce(m.entry_limit,p.entry_limit) as allowance,p.name as plan_name
  from public.memberships m join public.plans p on p.gym_id=m.gym_id and p.id=m.plan_id
  where m.gym_id=p_gym_id and m.payment_status='posted'
  order by m.client_id,case when today between m.start_date and m.end_date then 0 else 1 end,m.end_date desc,m.id desc
 ), remaining as (
  select c.id as client_id,c.document,concat_ws(' ',c.first_name,c.last_name) as client_name,c.phone,c.email,
   m.id as membership_id,m.plan_name,m.start_date,m.end_date,m.allowance as entry_limit,
   m.initial_entries_used+u.used as entries_used,greatest(m.allowance-m.initial_entries_used-u.used,0) as entries_remaining
  from latest m join public.clients c on c.gym_id=m.gym_id and c.id=m.client_id
  cross join lateral (select count(*) as used from public.checkins ch
   where ch.gym_id=p_gym_id and ch.membership_id=m.id and ch.result='PERMITIDA') u
  where c.active and m.allowance>1 and today between m.start_date and m.end_date
 ) select coalesce(jsonb_agg(to_jsonb(r) order by r.entries_remaining,r.client_name,r.client_id),'[]') into result from remaining r;
 return result;
end $$;
revoke all on function private.ticket_followup(uuid) from public,anon,authenticated;
grant execute on function private.ticket_followup(uuid) to authenticated;
create or replace function public.ticket_followup(p_gym_id uuid) returns jsonb
language sql security invoker set search_path='' as $$ select private.ticket_followup(p_gym_id) $$;
revoke all on function public.ticket_followup(uuid) from public,anon,authenticated;
grant execute on function public.ticket_followup(uuid) to authenticated;

-- Solo visitas reales permitidas. Los saldos trasladados no cuentan como visitas.
create or replace function private.session_followup(p_gym_id uuid,p_days integer default 7)
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare result jsonb; today date:=public.ztattuz_today(); zone text:=private.current_timezone();
begin
 if not private.user_has_gym_role(p_gym_id,array['admin']) then
  raise exception 'Esta consulta requiere acceso de Administración.' using errcode='42501'; end if;
 if p_days is null or p_days not in (7,14,30) then raise exception 'Selecciona 7, 14 o 30 días.' using errcode='22023'; end if;
 with visits as (
  select ch.client_id,ch.checkin_at,
   coalesce(coalesce(m.entry_limit,p.entry_limit)=1 or
    (coalesce(m.entry_limit,p.entry_limit) is null and p.duration_days=1),false) as is_session
  from public.checkins ch
  left join public.memberships m on m.gym_id=ch.gym_id and m.id=ch.membership_id and m.payment_status='posted'
  left join public.plans p on p.gym_id=m.gym_id and p.id=m.plan_id
  where ch.gym_id=p_gym_id and ch.result='PERMITIDA'
   and ch.checkin_at>=((today-(p_days-1))::timestamp at time zone zone)
   and ch.checkin_at<((today+1)::timestamp at time zone zone)
 ), grouped as (
  select client_id,count(*) as entries,max(checkin_at) as last_visit_at
  from visits group by client_id having bool_and(is_session)
 ), people as (
  select c.id as client_id,c.document,concat_ws(' ',c.first_name,c.last_name) as client_name,c.phone,c.email,c.active,
   g.entries,g.last_visit_at,(g.last_visit_at at time zone zone)::date as last_visit,
   s.data->>'plan_name' as current_plan,s.data->>'status' as current_status
  from grouped g join public.clients c on c.gym_id=p_gym_id and c.id=g.client_id
  cross join lateral (select private.membership_snapshot_json(p_gym_id,c.id) as data) s
 ) select coalesce(jsonb_agg(to_jsonb(p) order by p.last_visit_at desc,p.client_name,p.client_id),'[]') into result from people p;
 return result;
end $$;
revoke all on function private.session_followup(uuid,integer) from public,anon,authenticated;
grant execute on function private.session_followup(uuid,integer) to authenticated;
create or replace function public.session_followup(p_gym_id uuid,p_days integer default 7) returns jsonb
language sql security invoker set search_path='' as $$ select private.session_followup(p_gym_id,p_days) $$;
revoke all on function public.session_followup(uuid,integer) from public,anon,authenticated;
grant execute on function public.session_followup(uuid,integer) to authenticated;


revoke all on function private.ztattuz_add_membership(uuid,bigint,bigint,date,bigint,text,text,text) from public,anon,authenticated;
grant execute on function private.ztattuz_add_membership(uuid,bigint,bigint,date,bigint,text,text,text) to authenticated;
create or replace function public.add_membership_accumulating(p_gym_id uuid,p_client_id bigint,p_plan_id bigint,p_requested_start date,p_amount bigint,p_payment_method text,p_payment_reference text default '',p_notes text default '')
returns table(membership_id bigint,start_date date,end_date date)
language sql security invoker set search_path='' as $$
 select * from private.ztattuz_add_membership(p_gym_id,p_client_id,p_plan_id,p_requested_start,p_amount,p_payment_method,p_payment_reference,p_notes)
$$;
revoke all on function public.add_membership_accumulating(uuid,bigint,bigint,date,bigint,text,text,text) from public,anon,authenticated;
grant execute on function public.add_membership_accumulating(uuid,bigint,bigint,date,bigint,text,text,text) to authenticated;
create or replace function private.admin_register_checkin(p_gym_id uuid,p_client_id bigint,p_method text,p_override boolean default false) returns jsonb
language plpgsql security definer set search_path='' as $$
declare snap jsonb; ts timestamptz:=now();
begin
 if not private.user_has_gym_role(p_gym_id,array['admin']) then raise exception 'Sin permiso.' using errcode='42501'; end if;
 perform pg_advisory_xact_lock(p_client_id);
 if not p_override then return public.reception_register_checkin(p_gym_id,p_client_id,p_method); end if;
 snap:=private.membership_snapshot_json(p_gym_id,p_client_id);
 if coalesce((snap->>'allowed')::boolean,false) then return public.reception_register_checkin(p_gym_id,p_client_id,p_method); end if;
 insert into public.checkins(gym_id,client_id,membership_id,checkin_at,method,result,notes,recorded_by)
 values(p_gym_id,p_client_id,nullif(snap->>'membership_id','')::bigint,ts,left(p_method,80),'PERMITIDA','Autorización manual del administrador',auth.uid());
 return snap||jsonb_build_object('result','PERMITIDA','checkin_at',ts,'override',true);
end $$;


revoke all on function private.admin_register_checkin(uuid,bigint,text,boolean) from public,anon,authenticated;
grant execute on function private.admin_register_checkin(uuid,bigint,text,boolean) to authenticated;
create or replace function public.admin_register_checkin(p_gym_id uuid,p_client_id bigint,p_method text,p_override boolean default false)
returns jsonb language sql security invoker set search_path='' as $$
 select private.admin_register_checkin(p_gym_id,p_client_id,p_method,p_override)
$$;
revoke all on function public.admin_register_checkin(uuid,bigint,text,boolean) from public,anon,authenticated;
grant execute on function public.admin_register_checkin(uuid,bigint,text,boolean) to authenticated;

-- El tipo de un plan utilizado conserva el significado de las compras anteriores.
create or replace function private.ztattuz_validate_plan() returns trigger
language plpgsql security invoker set search_path='' as $$ begin
 if (new.entry_limit is null)<>(old.entry_limit is null) and exists(
  select 1 from public.memberships where gym_id=old.gym_id and plan_id=old.id) then
  raise exception 'Este plan ya tiene compras. Crea otro para cambiar entre días y entradas.' using errcode='22023';
 end if;
 return new;
end $$;
revoke all on function private.ztattuz_validate_plan() from public,anon,authenticated;
drop trigger if exists ztattuz_plan_type_guard on public.plans;
create trigger ztattuz_plan_type_guard before update on public.plans
for each row execute function private.ztattuz_validate_plan();

-- Logotipo compartido entre Administración y Recepción, con permisos del gimnasio.
create table if not exists public.gym_branding(
 gym_id uuid primary key references public.gyms(id) on delete cascade,
 logo_data text not null default '' check(octet_length(logo_data)<=1048576),
 updated_at timestamptz not null default now()
);
alter table public.gym_branding enable row level security;
revoke all on public.gym_branding from public,anon,authenticated;
grant select,insert,update,delete on public.gym_branding to authenticated;
drop policy if exists ztattuz_branding_read on public.gym_branding;
create policy ztattuz_branding_read on public.gym_branding for select to authenticated
 using(private.user_has_gym_role(gym_id,array['admin','receptionist']));
drop policy if exists ztattuz_branding_write on public.gym_branding;
create policy ztattuz_branding_write on public.gym_branding for all to authenticated
 using(private.user_has_gym_role(gym_id,array['admin']))
 with check(private.user_has_gym_role(gym_id,array['admin']));

create or replace function public.ztattuz_system_info() returns jsonb
language sql stable set search_path='' as $$ select jsonb_build_object(
 'product','gymsoft-ztattuz','schema_version','3.4.5','ticket_features_version','3.3.0') $$;
revoke all on function public.ztattuz_system_info() from public,anon,authenticated;
grant execute on function public.ztattuz_system_info() to authenticated;
notify pgrst,'reload schema';
commit;
