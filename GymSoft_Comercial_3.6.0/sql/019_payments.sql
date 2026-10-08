-- GymSoft 2.0: corregir o anular registros de pagos sin borrar su historia.
-- Ejecutar completo en Supabase / SQL Editor, con ambas aplicaciones cerradas.
begin;

alter table public.memberships
    add column if not exists payment_status text not null default 'posted',
    add column if not exists payment_revision bigint not null default 0,
    add column if not exists payment_changed_at timestamptz,
    add column if not exists payment_changed_by uuid,
    add column if not exists payment_change_reason text;

do $migration$
begin
    if not exists (
        select 1 from pg_catalog.pg_constraint
        where conrelid = 'public.memberships'::regclass
          and conname = 'gymsoft_payment_status_valid'
    ) then
        alter table public.memberships add constraint gymsoft_payment_status_valid
            check (payment_status in ('posted', 'void') and payment_revision >= 0);
    end if;
end;
$migration$;

-- Se conserva el cuerpo actual de estas funciones, incluidos otros arreglos.
-- Si la instalación tiene una estructura diferente, se cancela TODA la migración.
do $migration$
declare
    signature text;
    function_id regprocedure;
    definition text;
    patched text;
    pattern text := '(where[[:space:]]+m[.]gym_id[[:space:]]*=[[:space:]]*p_gym_id)';
begin
    foreach signature in array array[
        'public.get_finance_dashboard(uuid,date,date)',
        'private.membership_snapshot_json(uuid,bigint)',
        'public.add_membership_accumulating(uuid,bigint,bigint,date,bigint,text,text,text)',
        'public.reception_list_memberships(uuid,bigint,integer)'
    ] loop
        function_id := pg_catalog.to_regprocedure(signature);
        if function_id is null then
            raise exception 'Falta la función %. Ningún cambio fue aplicado.', signature;
        end if;
        definition := pg_catalog.pg_get_functiondef(function_id);
        if position('GymSoft_PAYMENT_VOID_FILTER_V1' in definition) > 0 then
            continue;
        end if;
        if (select count(*) from pg_catalog.regexp_matches(definition, pattern, 'gi')) <> 1 then
            raise exception 'La función % tiene otra versión. Ningún cambio fue aplicado.', signature;
        end if;
        patched := pg_catalog.regexp_replace(
            definition, pattern,
            E'\\1 AND m.payment_status = ''posted'' /* GymSoft_PAYMENT_VOID_FILTER_V1 */', 'gi'
        );
        execute patched;
    end loop;
end;
$migration$;

-- Auditoría del movimiento: un evento por cambio, con antes/después.
-- La política de lectura administrativa existente de audit_logs permanece vigente.
create or replace function private.audit_membership_payment()
returns trigger
language plpgsql security definer set search_path = ''
as $function$
declare
    before_row jsonb;
    after_row jsonb;
    row_data jsonb;
    actor uuid := auth.uid();
    actor_mail text;
    actor_role text;
    action_name text;
    message text;
begin
    if tg_op <> 'INSERT' then before_row := to_jsonb(old); end if;
    if tg_op <> 'DELETE' then after_row := to_jsonb(new); end if;
    row_data := coalesce(after_row, before_row);
    if tg_op = 'UPDATE' and
       (before_row - 'recorded_by' - 'updated_at') =
       (after_row - 'recorded_by' - 'updated_at') then
        return new;
    end if;
    select u.email into actor_mail from auth.users u where u.id = actor;
    select gu.role into actor_role from public.gym_users gu
        where gu.gym_id = (row_data->>'gym_id')::uuid and gu.user_id = actor;
    action_name := case
        when tg_op = 'INSERT' then 'PAGO_REGISTRADO'
        when tg_op = 'DELETE' then 'PAGO_ELIMINADO'
        when new.payment_status = 'void' and old.payment_status <> 'void'
            then 'PAGO_ANULADO'
        else 'PAGO_EDITADO'
    end;
    message := case action_name
        when 'PAGO_REGISTRADO' then 'Pago registrado'
        when 'PAGO_ELIMINADO' then 'Pago retirado de datos operativos'
        when 'PAGO_ANULADO' then 'Pago anulado'
        else 'Pago corregido'
    end || ' · cliente #' || (row_data->>'client_id') || ' · $' ||
        coalesce(row_data->>'amount', row_data->>'amount_paid', '0');
    if tg_op = 'UPDATE' then
        message := message || ' · anterior $' ||
            coalesce(before_row->>'amount', before_row->>'amount_paid', '0') ||
            ' · ' || coalesce(after_row->>'payment_change_reason', 'Actualización administrativa');
    end if;
    insert into public.audit_logs (
        gym_id, actor_user_id, actor_email, actor_role, action,
        entity_type, entity_id, summary, details
    ) values (
        (row_data->>'gym_id')::uuid, actor,
        coalesce(actor_mail, 'Sistema'), coalesce(actor_role, 'system'), action_name,
        'memberships', row_data->>'id', message,
        jsonb_build_object('before', before_row, 'after', after_row,
            'reason', case when tg_op = 'UPDATE' then after_row->>'payment_change_reason' end,
            'client_id', row_data->>'client_id', 'payment_revision', row_data->'payment_revision')
    );
    if tg_op = 'DELETE' then return old; end if;
    return new;
end;
$function$;
revoke all on function private.audit_membership_payment() from public, anon, authenticated;
do $migration$
begin
    if exists (
        select 1 from pg_catalog.pg_trigger t
        where t.tgrelid = 'public.memberships'::regclass
          and t.tgname = 'gymsoft_audit_memberships'
          and t.tgfoid <> 'private.audit_membership_payment()'::regprocedure
          and t.tgfoid is distinct from pg_catalog.to_regprocedure('private.write_audit_log()')
    ) then
        raise exception 'La auditoría de pagos tiene otra versión. Ningún cambio fue aplicado.';
    end if;
end;
$migration$;
drop trigger if exists gymsoft_audit_memberships on public.memberships;
create trigger gymsoft_audit_memberships
    after insert or update or delete on public.memberships
    for each row execute function private.audit_membership_payment();

create or replace function public.gymsoft_change_payment(
    p_gym_id uuid,
    p_membership_id bigint,
    p_expected_revision bigint,
    p_action text,
    p_reason text,
    p_amount bigint default null,
    p_payment_method text default null,
    p_payment_reference text default null
)
returns jsonb
language plpgsql security definer set search_path = ''
as $function$
declare
    payment public.memberships%rowtype;
    client_key bigint;
begin
    if not private.user_has_gym_role(p_gym_id, array['admin','receptionist']::text[]) then
        raise exception 'No tienes permiso para modificar pagos de este gimnasio.' using errcode='42501';
    end if;
    if p_action is null or p_action not in ('correct', 'void') then
        raise exception 'Acción no válida.' using errcode='22023';
    end if;
    if length(trim(coalesce(p_reason, ''))) not between 3 and 500 then
        raise exception 'Escribe un motivo de 3 a 500 caracteres.' using errcode='22023';
    end if;
    select m.client_id into client_key from public.memberships m
        where m.id=p_membership_id and m.gym_id=p_gym_id;
    if not found then
        raise exception 'El pago no existe en este gimnasio.' using errcode='P0002';
    end if;
    -- Mismo bloqueo usado al acumular planes nuevos. Después, bloqueo de la fila.
    perform pg_catalog.pg_advisory_xact_lock(client_key);
    select * into payment from public.memberships m
        where m.id=p_membership_id and m.gym_id=p_gym_id for update;
    if not found then
        raise exception 'El pago ya no está disponible. Actualiza la lista.' using errcode='P0002';
    end if;
    if payment.payment_status = 'void' then
        if p_action = 'void' then return to_jsonb(payment); end if;
        raise exception 'Este pago está anulado y no se puede corregir.' using errcode='22023';
    end if;
    if p_expected_revision is distinct from payment.payment_revision then
        raise exception 'Otra persona modificó este pago. Actualiza la lista antes de continuar.' using errcode='40001';
    end if;
    if p_action='correct' then
        if p_amount is null or p_amount < 0 or p_amount > 1000000000000 then
            raise exception 'El valor debe ser un número entero entre 0 y 1000000000000.' using errcode='22023';
        end if;
        if length(trim(coalesce(p_payment_method,''))) not between 1 and 60 or
           length(coalesce(p_payment_reference,'')) > 120 then
            raise exception 'Revisa el método de pago y la referencia (máximo 120 caracteres).' using errcode='22023';
        end if;
        if payment.amount is not distinct from p_amount and
           payment.amount_paid is not distinct from p_amount and
           coalesce(payment.payment_method,'') = trim(p_payment_method) and
           coalesce(payment.payment_reference,'') = trim(coalesce(p_payment_reference,'')) then
            raise exception 'No hay cambios en el valor, método o referencia.' using errcode='22023';
        end if;
    end if;
    update public.memberships m set
        amount = case when p_action='correct' then p_amount else m.amount end,
        amount_paid = case when p_action='correct' then p_amount else m.amount_paid end,
        payment_method = case when p_action='correct' then trim(p_payment_method) else m.payment_method end,
        payment_reference = case when p_action='correct' then trim(coalesce(p_payment_reference,'')) else m.payment_reference end,
        payment_status = case when p_action='void' then 'void' else 'posted' end,
        payment_revision = m.payment_revision + 1,
        payment_changed_at = clock_timestamp(),
        payment_changed_by = auth.uid(),
        payment_change_reason = trim(p_reason)
    where m.id=p_membership_id and m.gym_id=p_gym_id
    returning * into payment;
    return to_jsonb(payment);
end;
$function$;
revoke all on function public.gymsoft_change_payment(uuid,bigint,bigint,text,text,bigint,text,text)
    from public, anon, authenticated;
grant execute on function public.gymsoft_change_payment(uuid,bigint,bigint,text,text,bigint,text,text)
    to authenticated;

create or replace function public.gymsoft_client_payments(
    p_gym_id uuid, p_client_id bigint, p_include_void boolean default false,
    p_offset integer default 0, p_limit integer default 50
)
returns jsonb
language plpgsql stable security definer set search_path = ''
as $function$
declare
    result jsonb;
    page_size integer := least(greatest(coalesce(p_limit,50),1),100);
begin
    if not private.user_has_gym_role(p_gym_id, array['admin','receptionist']::text[]) then
        raise exception 'No tienes permiso para consultar estos pagos.' using errcode='42501';
    end if;
    if not private.client_belongs_to_gym(p_client_id,p_gym_id) then
        raise exception 'El cliente no existe en este gimnasio.' using errcode='P0002';
    end if;
    with selected as (
        select m.id, m.client_id, m.plan_id, coalesce(p.name,'Sin plan') as plan_name,
            m.start_date, m.end_date, coalesce(m.amount,m.amount_paid,0) as amount,
            m.payment_method, m.payment_reference, m.paid_at,
            m.payment_status, m.payment_revision, m.payment_changed_at,
            m.payment_change_reason
        from public.memberships m
        left join public.plans p on p.id=m.plan_id and p.gym_id=m.gym_id
        where m.gym_id=p_gym_id and m.client_id=p_client_id
          and (coalesce(p_include_void,false) or m.payment_status='posted')
        order by m.paid_at desc, m.id desc
        offset greatest(coalesce(p_offset,0),0) limit page_size+1
    ), page as (select * from selected limit page_size)
    select jsonb_build_object(
        'rows',coalesce((select jsonb_agg(to_jsonb(p) order by p.paid_at desc,p.id desc) from page p),'[]'::jsonb),
        'has_more',(select count(*) > page_size from selected)
    ) into result;
    return result;
end;
$function$;
revoke all on function public.gymsoft_client_payments(uuid,bigint,boolean,integer,integer) from public,anon,authenticated;
grant execute on function public.gymsoft_client_payments(uuid,bigint,boolean,integer,integer) to authenticated;

create or replace function public.gymsoft_payment_history(p_gym_id uuid,p_membership_id bigint)
returns jsonb
language plpgsql stable security definer set search_path = ''
as $function$
declare result jsonb;
begin
    if not private.user_has_gym_role(p_gym_id,array['admin','receptionist']::text[]) then
        raise exception 'No tienes permiso para consultar este historial.' using errcode='42501';
    end if;
    if not exists(select 1 from public.memberships where id=p_membership_id and gym_id=p_gym_id) then
        raise exception 'El pago no existe en este gimnasio.' using errcode='P0002';
    end if;
    select coalesce(jsonb_agg(to_jsonb(a) order by a.created_at desc,a.id desc),'[]'::jsonb) into result
    from (
        select id,created_at,actor_email,actor_role,action,summary,details
        from public.audit_logs
        where gym_id=p_gym_id and entity_type='memberships' and entity_id=p_membership_id::text
        order by created_at desc,id desc limit 200
    ) a;
    return result;
end;
$function$;
revoke all on function public.gymsoft_payment_history(uuid,bigint) from public,anon,authenticated;
grant execute on function public.gymsoft_payment_history(uuid,bigint) to authenticated;

notify pgrst, 'reload schema';
commit;
select 'CORRECCIÓN Y ANULACIÓN DE PAGOS INSTALADAS' as resultado;
