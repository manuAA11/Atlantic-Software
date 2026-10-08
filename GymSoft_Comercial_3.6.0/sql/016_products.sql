begin;

alter table public.store_products
    add column if not exists image_data text not null default '';

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname = 'store_products_image_size_check'
          and conrelid = 'public.store_products'::regclass
    ) then
        alter table public.store_products
            add constraint store_products_image_size_check
            check (octet_length(image_data) <= 1000000);
    end if;
end;
$$;


create or replace function public.admin_list_store_products(
    p_gym_id uuid,
    p_search text default '',
    p_include_inactive boolean default true
)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    v_search text := trim(coalesce(p_search, ''));
    v_result jsonb;
begin
    if not private.user_has_gym_role(
        p_gym_id,
        array['admin']::text[]
    ) then
        raise exception 'La tienda administrativa es exclusiva del administrador.'
            using errcode = '42501';
    end if;

    select coalesce(
        jsonb_agg(
            jsonb_build_object(
                'id', p.id,
                'name', p.name,
                'sku', p.sku,
                'sale_price', p.sale_price,
                'stock_quantity', p.stock_quantity,
                'low_stock_threshold', p.low_stock_threshold,
                'active', p.active,
                'image_data', coalesce(p.image_data, ''),
                'stock_status', case
                    when not p.active then 'INACTIVO'
                    when p.stock_quantity = 0 then 'AGOTADO'
                    when p.stock_quantity <= p.low_stock_threshold
                        then 'POCAS UNIDADES'
                    else 'DISPONIBLE'
                end,
                'created_at', p.created_at,
                'updated_at', p.updated_at
            )
            order by p.active desc, p.name
        ),
        '[]'::jsonb
    )
    into v_result
    from public.store_products p
    where p.gym_id = p_gym_id
      and (p_include_inactive or p.active)
      and (
          v_search = ''
          or p.name ilike '%' || v_search || '%'
          or p.sku ilike '%' || v_search || '%'
      );

    return v_result;
end;
$$;

revoke all on function public.admin_list_store_products(
    uuid, text, boolean
) from public, anon, authenticated;
grant execute on function public.admin_list_store_products(
    uuid, text, boolean
) to authenticated;


drop function if exists public.admin_save_store_product(
    uuid, bigint, text, text, bigint, integer, integer, boolean
);

create or replace function public.admin_save_store_product(
    p_gym_id uuid,
    p_product_id bigint,
    p_name text,
    p_sku text,
    p_sale_price bigint,
    p_stock_quantity integer,
    p_low_stock_threshold integer,
    p_active boolean,
    p_image_data text default ''
)
returns bigint
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_product_id bigint;
    v_user_id uuid := (select auth.uid());
    v_image_data text := coalesce(p_image_data, '');
begin
    if not private.user_has_gym_role(
        p_gym_id,
        array['admin']::text[]
    ) then
        raise exception 'Solo el administrador puede modificar productos.'
            using errcode = '42501';
    end if;

    if trim(coalesce(p_name, '')) = ''
       or coalesce(p_sale_price, -1) < 0
       or coalesce(p_stock_quantity, -1) < 0
       or coalesce(p_low_stock_threshold, -1) < 0 then
        raise exception 'Revisa el nombre, precio y cantidades del producto.'
            using errcode = '22023';
    end if;

    if octet_length(v_image_data) > 1000000 then
        raise exception 'La foto del producto supera el tamaño permitido.'
            using errcode = '22023';
    end if;

    if v_image_data <> ''
       and v_image_data not like 'data:image/%;base64,%' then
        raise exception 'La foto del producto no tiene un formato válido.'
            using errcode = '22023';
    end if;

    if p_product_id is null then
        insert into public.store_products(
            gym_id,
            name,
            sku,
            sale_price,
            stock_quantity,
            low_stock_threshold,
            active,
            image_data,
            created_by,
            updated_by
        )
        values (
            p_gym_id,
            trim(p_name),
            upper(trim(coalesce(p_sku, ''))),
            p_sale_price,
            p_stock_quantity,
            p_low_stock_threshold,
            coalesce(p_active, true),
            v_image_data,
            v_user_id,
            v_user_id
        )
        returning id into v_product_id;
    else
        update public.store_products
        set
            name = trim(p_name),
            sku = upper(trim(coalesce(p_sku, ''))),
            sale_price = p_sale_price,
            stock_quantity = p_stock_quantity,
            low_stock_threshold = p_low_stock_threshold,
            active = coalesce(p_active, true),
            image_data = v_image_data,
            updated_by = v_user_id,
            updated_at = now()
        where id = p_product_id
          and gym_id = p_gym_id
        returning id into v_product_id;

        if v_product_id is null then
            raise exception 'Producto no encontrado.'
                using errcode = 'P0002';
        end if;
    end if;

    return v_product_id;
end;
$$;

revoke all on function public.admin_save_store_product(
    uuid, bigint, text, text, bigint, integer, integer, boolean, text
) from public, anon, authenticated;
grant execute on function public.admin_save_store_product(
    uuid, bigint, text, text, bigint, integer, integer, boolean, text
) to authenticated;


create or replace function public.reception_list_store_products(
    p_gym_id uuid,
    p_search text default ''
)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
    v_search text := trim(coalesce(p_search, ''));
    v_result jsonb;
begin
    if not private.user_has_gym_role(
        p_gym_id,
        array['admin', 'receptionist']::text[]
    ) then
        raise exception 'No tienes permiso para consultar la tienda.'
            using errcode = '42501';
    end if;

    select coalesce(
        jsonb_agg(
            jsonb_build_object(
                'id', p.id,
                'name', p.name,
                'sku', p.sku,
                'sale_price', p.sale_price,
                'stock_quantity', p.stock_quantity,
                'low_stock_threshold', p.low_stock_threshold,
                'image_data', coalesce(p.image_data, ''),
                'available', p.stock_quantity > 0
            )
            order by (p.stock_quantity > 0) desc, p.name
        ),
        '[]'::jsonb
    )
    into v_result
    from public.store_products p
    where p.gym_id = p_gym_id
      and p.active = true
      and (
          v_search = ''
          or p.name ilike '%' || v_search || '%'
          or p.sku ilike '%' || v_search || '%'
      );

    return v_result;
end;
$$;

revoke all on function public.reception_list_store_products(
    uuid, text
) from public, anon, authenticated;
grant execute on function public.reception_list_store_products(
    uuid, text
) to authenticated;

commit;

select
    'TIENDA VISUAL 1.5 INSTALADA' as resultado,
    count(*) as productos_actuales
from public.store_products;
