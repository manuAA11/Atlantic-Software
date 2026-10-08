begin;

-- Todos los planes se colocan en una sola fila de tiempo por cliente.
-- Si hay una membresía vigente o futura, el plan nuevo comienza al día
-- siguiente de la última. Una sesión ya consumida deja de bloquear la fila.
create or replace function public.add_membership_accumulating(
    p_gym_id uuid,
    p_client_id bigint,
    p_plan_id bigint,
    p_requested_start date,
    p_amount bigint,
    p_payment_method text,
    p_payment_reference text,
    p_notes text
)
returns table(
    membership_id bigint,
    start_date date,
    end_date date
)
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_user_id uuid := (select auth.uid());
    v_today date := public.gymsoft_today();
    v_requested_start date;
    v_duration_days integer;
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
        p.entry_limit
    into
        v_duration_days,
        v_entry_limit
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
    where m.gym_id = p_gym_id
      and m.client_id = p_client_id
      and m.end_date >= v_today
      and (
          coalesce(
              m.entry_limit,
              current_plan.entry_limit
          ) is null
          or (
              select count(*)
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

    v_end_date := (
        v_start_date + (v_duration_days - 1)
    );

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
$$;

revoke all on function public.add_membership_accumulating(
    uuid, bigint, bigint, date, bigint, text, text, text
) from public, anon, authenticated;

grant execute on function public.add_membership_accumulating(
    uuid, bigint, bigint, date, bigint, text, text, text
) to authenticated;

commit;

select
    'ACUMULACIÓN DE PLANES INSTALADA' as resultado,
    'Sesión, semanal, tiquetera y mensual se acumulan sin superponerse.'
        as detalle;
