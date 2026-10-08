begin;

create schema if not exists private;

create or replace function private.gymsoft_import_insert(
    p_table text,
    p_gym_id uuid,
    p_row jsonb
)
returns bigint
language plpgsql
security definer
set search_path = public, private, pg_temp
as $$
declare
    v_row jsonb;
    v_columns text;
    v_values text;
    v_new_id bigint;
begin
    if p_table <> all(array[
        'clients',
        'plans',
        'memberships',
        'checkins',
        'store_products',
        'store_sales',
        'accounting_expenses',
        'trainers',
        'staff_shifts',
        'routines',
        'exercises',
        'classes',
        'reservations',
        'marketing_messages'
    ]) then
        raise exception 'Tabla de importación no permitida: %', p_table;
    end if;

    v_row := (coalesce(p_row, '{}'::jsonb) - 'id' - '__excel_row')
        || jsonb_build_object('gym_id', p_gym_id);

    select
        string_agg(format('%I', attribute.attname), ', ' order by attribute.attnum),
        string_agg(format('record.%I', attribute.attname), ', ' order by attribute.attnum)
    into v_columns, v_values
    from pg_attribute attribute
    where attribute.attrelid = format('public.%I', p_table)::regclass
      and attribute.attnum > 0
      and not attribute.attisdropped
      and attribute.attname <> 'id'
      and attribute.attgenerated = ''
      and attribute.attidentity = ''
      and v_row ? attribute.attname;

    if v_columns is null then
        raise exception 'La fila de % no contiene columnas válidas.', p_table;
    end if;

    execute format(
        'insert into public.%1$I (%2$s) '
        'select %3$s '
        'from jsonb_populate_record(null::public.%1$I, $1) as record '
        'returning id',
        p_table,
        v_columns,
        v_values
    )
    using v_row
    into v_new_id;

    return v_new_id;
end;
$$;

revoke all on function private.gymsoft_import_insert(text, uuid, jsonb)
from public, anon, authenticated;

create or replace function public.admin_replace_gym_from_excel(
    p_data jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, private, pg_temp
as $$
declare
    v_gym_id uuid;
    v_tables jsonb;
    v_row jsonb;
    v_old_id text;
    v_new_id bigint;
    v_client_id bigint;
    v_plan_id bigint;
    v_membership_id bigint;
    v_product_id bigint;
    v_trainer_id bigint;
    v_routine_id bigint;
    v_class_id bigint;
    v_image jsonb;
    v_total integer := 0;
begin
    if coalesce(p_data->>'format', '') <> 'GymSoft-EXCEL-REPLACE-2' then
        raise exception 'El formato de importación no es válido.';
    end if;

    select gym_user.gym_id
    into v_gym_id
    from public.gym_users gym_user
    where gym_user.user_id = auth.uid()
      and lower(coalesce(gym_user.role::text, '')) = 'admin'
    limit 1;

    if v_gym_id is null then
        raise exception 'Solo un administrador puede reemplazar la información.'
            using errcode = '42501';
    end if;

    v_tables := coalesce(p_data->'tables', '{}'::jsonb);

    perform pg_advisory_xact_lock(
        hashtextextended('gymsoft-import-' || v_gym_id::text, 0)
    );

    create temporary table gymsoft_import_ids (
        entity text not null,
        old_id text not null,
        new_id bigint not null,
        primary key (entity, old_id)
    ) on commit drop;

    create temporary table gymsoft_product_images (
        sku text primary key,
        image_data jsonb not null
    ) on commit drop;

    insert into gymsoft_product_images (sku, image_data)
    select
        lower(trim(product.sku)),
        to_jsonb(product.image_data)
    from public.store_products product
    where product.gym_id = v_gym_id
      and nullif(trim(product.sku), '') is not null
      and product.image_data is not null
    on conflict (sku) do nothing;

    delete from public.marketing_messages where gym_id = v_gym_id;
    delete from public.staff_shifts where gym_id = v_gym_id;
    delete from public.store_sales where gym_id = v_gym_id;
    delete from public.accounting_expenses where gym_id = v_gym_id;
    delete from public.reservations where gym_id = v_gym_id;
    delete from public.exercises where gym_id = v_gym_id;
    delete from public.checkins where gym_id = v_gym_id;
    delete from public.classes where gym_id = v_gym_id;
    delete from public.routines where gym_id = v_gym_id;
    delete from public.memberships where gym_id = v_gym_id;
    delete from public.trainers where gym_id = v_gym_id;
    delete from public.clients where gym_id = v_gym_id;
    delete from public.store_products where gym_id = v_gym_id;
    delete from public.plans where gym_id = v_gym_id;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'plans', '[]'::jsonb)
        )
    loop
        v_old_id := nullif(v_row->>'id', '');
        if v_old_id is null then
            raise exception 'Un plan no tiene ID interno.';
        end if;
        v_new_id := private.gymsoft_import_insert(
            'plans', v_gym_id, v_row
        );
        insert into gymsoft_import_ids values (
            'plans', v_old_id, v_new_id
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'clients', '[]'::jsonb)
        )
    loop
        v_old_id := nullif(v_row->>'id', '');
        if v_old_id is null then
            raise exception 'Un cliente no tiene ID interno.';
        end if;
        v_new_id := private.gymsoft_import_insert(
            'clients', v_gym_id, v_row
        );
        insert into gymsoft_import_ids values (
            'clients', v_old_id, v_new_id
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'store_products', '[]'::jsonb)
        )
    loop
        v_old_id := nullif(v_row->>'id', '');
        if v_old_id is null then
            raise exception 'Un producto no tiene ID interno.';
        end if;

        if not (v_row ? 'image_data') then
            select saved.image_data
            into v_image
            from gymsoft_product_images saved
            where saved.sku = lower(trim(v_row->>'sku'));

            if v_image is not null then
                v_row := v_row || jsonb_build_object(
                    'image_data', v_image
                );
            end if;
        end if;

        v_new_id := private.gymsoft_import_insert(
            'store_products', v_gym_id, v_row
        );
        insert into gymsoft_import_ids values (
            'store_products', v_old_id, v_new_id
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'trainers', '[]'::jsonb)
        )
    loop
        v_old_id := nullif(v_row->>'id', '');
        if v_old_id is null then
            raise exception 'Un trabajador no tiene ID interno.';
        end if;
        v_new_id := private.gymsoft_import_insert(
            'trainers', v_gym_id, v_row
        );
        insert into gymsoft_import_ids values (
            'trainers', v_old_id, v_new_id
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'accounting_expenses', '[]'::jsonb)
        )
    loop
        perform private.gymsoft_import_insert(
            'accounting_expenses', v_gym_id, v_row
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'memberships', '[]'::jsonb)
        )
    loop
        select new_id into v_client_id
        from gymsoft_import_ids
        where entity = 'clients'
          and old_id = v_row->>'client_id';

        select new_id into v_plan_id
        from gymsoft_import_ids
        where entity = 'plans'
          and old_id = v_row->>'plan_id';

        if v_client_id is null or v_plan_id is null then
            raise exception 'Una membresía tiene relaciones inválidas.';
        end if;

        v_old_id := nullif(v_row->>'id', '');
        v_row := v_row || jsonb_build_object(
            'client_id', v_client_id,
            'plan_id', v_plan_id
        );
        v_new_id := private.gymsoft_import_insert(
            'memberships', v_gym_id, v_row
        );
        insert into gymsoft_import_ids values (
            'memberships', v_old_id, v_new_id
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'routines', '[]'::jsonb)
        )
    loop
        select new_id into v_client_id
        from gymsoft_import_ids
        where entity = 'clients'
          and old_id = v_row->>'client_id';

        v_trainer_id := null;
        if nullif(v_row->>'trainer_id', '') is not null then
            select new_id into v_trainer_id
            from gymsoft_import_ids
            where entity = 'trainers'
              and old_id = v_row->>'trainer_id';
        end if;

        if v_client_id is null then
            raise exception 'Una rutina tiene un cliente inválido.';
        end if;

        v_old_id := nullif(v_row->>'id', '');
        v_row := v_row || jsonb_build_object(
            'client_id', v_client_id
        );
        if v_trainer_id is null then
            v_row := v_row - 'trainer_id';
        else
            v_row := v_row || jsonb_build_object(
                'trainer_id', v_trainer_id
            );
        end if;

        v_new_id := private.gymsoft_import_insert(
            'routines', v_gym_id, v_row
        );
        insert into gymsoft_import_ids values (
            'routines', v_old_id, v_new_id
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'classes', '[]'::jsonb)
        )
    loop
        v_trainer_id := null;
        if nullif(v_row->>'trainer_id', '') is not null then
            select new_id into v_trainer_id
            from gymsoft_import_ids
            where entity = 'trainers'
              and old_id = v_row->>'trainer_id';
        end if;

        v_old_id := nullif(v_row->>'id', '');
        if v_trainer_id is null then
            v_row := v_row - 'trainer_id';
        else
            v_row := v_row || jsonb_build_object(
                'trainer_id', v_trainer_id
            );
        end if;

        v_new_id := private.gymsoft_import_insert(
            'classes', v_gym_id, v_row
        );
        insert into gymsoft_import_ids values (
            'classes', v_old_id, v_new_id
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'checkins', '[]'::jsonb)
        )
    loop
        select new_id into v_client_id
        from gymsoft_import_ids
        where entity = 'clients'
          and old_id = v_row->>'client_id';

        v_membership_id := null;
        if nullif(v_row->>'membership_id', '') is not null then
            select new_id into v_membership_id
            from gymsoft_import_ids
            where entity = 'memberships'
              and old_id = v_row->>'membership_id';
        end if;

        if v_client_id is null then
            raise exception 'Una entrada tiene un cliente inválido.';
        end if;

        v_row := v_row || jsonb_build_object(
            'client_id', v_client_id
        );
        if v_membership_id is null then
            v_row := v_row - 'membership_id';
        else
            v_row := v_row || jsonb_build_object(
                'membership_id', v_membership_id
            );
        end if;

        perform private.gymsoft_import_insert(
            'checkins', v_gym_id, v_row
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'exercises', '[]'::jsonb)
        )
    loop
        select new_id into v_routine_id
        from gymsoft_import_ids
        where entity = 'routines'
          and old_id = v_row->>'routine_id';

        if v_routine_id is null then
            raise exception 'Un ejercicio tiene una rutina inválida.';
        end if;

        v_row := v_row || jsonb_build_object(
            'routine_id', v_routine_id
        );
        perform private.gymsoft_import_insert(
            'exercises', v_gym_id, v_row
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'reservations', '[]'::jsonb)
        )
    loop
        select new_id into v_class_id
        from gymsoft_import_ids
        where entity = 'classes'
          and old_id = v_row->>'class_id';

        select new_id into v_client_id
        from gymsoft_import_ids
        where entity = 'clients'
          and old_id = v_row->>'client_id';

        if v_class_id is null or v_client_id is null then
            raise exception 'Una reserva tiene relaciones inválidas.';
        end if;

        v_row := v_row || jsonb_build_object(
            'class_id', v_class_id,
            'client_id', v_client_id
        );
        perform private.gymsoft_import_insert(
            'reservations', v_gym_id, v_row
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'store_sales', '[]'::jsonb)
        )
    loop
        select new_id into v_product_id
        from gymsoft_import_ids
        where entity = 'store_products'
          and old_id = v_row->>'product_id';

        if v_product_id is null then
            raise exception 'Una venta tiene un producto inválido.';
        end if;

        v_row := v_row || jsonb_build_object(
            'product_id', v_product_id
        );
        perform private.gymsoft_import_insert(
            'store_sales', v_gym_id, v_row
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'staff_shifts', '[]'::jsonb)
        )
    loop
        select new_id into v_trainer_id
        from gymsoft_import_ids
        where entity = 'trainers'
          and old_id = v_row->>'trainer_id';

        if v_trainer_id is null then
            raise exception 'Una jornada tiene un trabajador inválido.';
        end if;

        v_row := v_row || jsonb_build_object(
            'trainer_id', v_trainer_id
        );
        perform private.gymsoft_import_insert(
            'staff_shifts', v_gym_id, v_row
        );
    end loop;

    for v_row in
        select value
        from jsonb_array_elements(
            coalesce(v_tables->'marketing_messages', '[]'::jsonb)
        )
    loop
        v_client_id := null;
        if nullif(v_row->>'client_id', '') is not null then
            select new_id into v_client_id
            from gymsoft_import_ids
            where entity = 'clients'
              and old_id = v_row->>'client_id';
        end if;

        if v_client_id is null then
            v_row := v_row - 'client_id';
        else
            v_row := v_row || jsonb_build_object(
                'client_id', v_client_id
            );
        end if;

        perform private.gymsoft_import_insert(
            'marketing_messages', v_gym_id, v_row
        );
    end loop;

    v_total :=
        jsonb_array_length(coalesce(v_tables->'clients', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'plans', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'memberships', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'checkins', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'store_products', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'store_sales', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'accounting_expenses', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'trainers', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'staff_shifts', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'routines', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'exercises', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'classes', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'reservations', '[]'::jsonb))
        + jsonb_array_length(coalesce(v_tables->'marketing_messages', '[]'::jsonb));

    return jsonb_build_object(
        'status', 'ok',
        'gym_id', v_gym_id,
        'total_rows', v_total,
        'counts', jsonb_build_object(
            'clients', jsonb_array_length(coalesce(v_tables->'clients', '[]'::jsonb)),
            'plans', jsonb_array_length(coalesce(v_tables->'plans', '[]'::jsonb)),
            'memberships', jsonb_array_length(coalesce(v_tables->'memberships', '[]'::jsonb)),
            'checkins', jsonb_array_length(coalesce(v_tables->'checkins', '[]'::jsonb)),
            'store_products', jsonb_array_length(coalesce(v_tables->'store_products', '[]'::jsonb)),
            'store_sales', jsonb_array_length(coalesce(v_tables->'store_sales', '[]'::jsonb)),
            'accounting_expenses', jsonb_array_length(coalesce(v_tables->'accounting_expenses', '[]'::jsonb)),
            'trainers', jsonb_array_length(coalesce(v_tables->'trainers', '[]'::jsonb)),
            'staff_shifts', jsonb_array_length(coalesce(v_tables->'staff_shifts', '[]'::jsonb)),
            'routines', jsonb_array_length(coalesce(v_tables->'routines', '[]'::jsonb)),
            'exercises', jsonb_array_length(coalesce(v_tables->'exercises', '[]'::jsonb)),
            'classes', jsonb_array_length(coalesce(v_tables->'classes', '[]'::jsonb)),
            'reservations', jsonb_array_length(coalesce(v_tables->'reservations', '[]'::jsonb)),
            'marketing_messages', jsonb_array_length(coalesce(v_tables->'marketing_messages', '[]'::jsonb))
        )
    );
end;
$$;

revoke all on function public.admin_replace_gym_from_excel(jsonb)
from public, anon;
grant execute on function public.admin_replace_gym_from_excel(jsonb)
to authenticated;

notify pgrst, 'reload schema';

commit;

select
    'IMPORTACIÓN EXCEL FINAL 2.0 INSTALADA' as resultado,
    'La operación es transaccional y exclusiva para administradores.' as seguridad;
