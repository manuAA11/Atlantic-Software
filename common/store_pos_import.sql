begin;

create or replace function private.store_pos_import_authorize(p_gym_id uuid) returns void
language plpgsql security definer set search_path='' as $$
declare owner_allowed boolean:=false;
begin
 if auth.uid() is not null and private.user_has_gym_role(p_gym_id,array['admin']) then return;end if;
 if auth.uid() is not null and to_regclass('private.software_owners') is not null then
  execute 'select exists(select 1 from private.software_owners where user_id=$1)' using auth.uid() into owner_allowed;
 end if;
 if not owner_allowed then raise exception 'Restauración POS no autorizada.' using errcode='42501';end if;
end $$;

-- The existing full-gym importer keeps its membership/ticket/freeze behavior.
-- These private hooks extend its single transaction to the new immutable POS.
create or replace function public.store_pos_backup_settings(p_gym_id uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare settings jsonb;
begin
 perform private.store_pos_authorize(p_gym_id,true,false);
 select to_jsonb(s) into settings from public.gym_store_settings s where gym_id=p_gym_id;
 settings:=coalesce(settings,jsonb_build_object('gym_id',p_gym_id,'enabled',true,'last_sale_number',
  coalesce((select max(sale_number) from public.store_orders where gym_id=p_gym_id),0)));
 return jsonb_build_array(settings||jsonb_build_object('inventory_request_archive',
  (select coalesce(jsonb_agg(jsonb_build_object('request_id',r.request_id,'payload',r.payload,'result',r.result)
   order by r.request_id),'[]') from private.store_pos_requests r where r.gym_id=p_gym_id)));
end $$;
revoke all on function public.store_pos_backup_settings(uuid) from public,anon,authenticated;
grant execute on function public.store_pos_backup_settings(uuid) to authenticated;

create or replace function public.store_pos_backup_table(p_gym_id uuid,p_table text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare result jsonb;
begin
 perform private.store_pos_authorize(p_gym_id,true,false);
 if p_table='gym_store_settings' then return public.store_pos_backup_settings(p_gym_id);end if;
 if p_table<>all(array['store_orders','store_payments','store_inventory_movements']) then raise exception 'Tabla de respaldo POS no permitida.';end if;
 execute format('select coalesce(jsonb_agg(to_jsonb(t) order by id),''[]'') from public.%I t where gym_id=$1',p_table)
 using p_gym_id into result;
 return result;
end $$;
revoke all on function public.store_pos_backup_table(uuid,text) from public,anon,authenticated;
grant execute on function public.store_pos_backup_table(uuid,text) to authenticated;

-- One MVCC snapshot prevents a checkout on another PC from producing a
-- backup with old product balances and newer payments/movements.
create or replace function public.store_pos_backup(p_gym_id uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare result jsonb:='{}';table_name text;rows jsonb;
begin
 perform private.store_pos_authorize(p_gym_id,true,false);
 foreach table_name in array array['store_products','store_sales','store_orders','store_payments','store_inventory_movements'] loop
  execute format('select coalesce(jsonb_agg(to_jsonb(t) order by id),''[]'') from public.%I t where gym_id=$1',table_name)
  using p_gym_id into rows;
  result:=result||jsonb_build_object(table_name,rows);
 end loop;
 return result||jsonb_build_object('gym_store_settings',public.store_pos_backup_settings(p_gym_id));
end $$;
revoke all on function public.store_pos_backup(uuid) from public,anon,authenticated;
grant execute on function public.store_pos_backup(uuid) to authenticated;

create or replace function private.store_pos_import_begin(p_gym_id uuid,p_tables jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare table_name text; supplied integer:=0; prior_counter bigint;
begin
 perform private.store_pos_import_authorize(p_gym_id);
 for table_name in select unnest(array['store_orders','store_payments','store_inventory_movements','gym_store_settings']) loop
  if p_tables ? table_name then
   supplied:=supplied+1;
   if jsonb_typeof(p_tables->table_name) is distinct from 'array' then raise exception 'Historial POS de importación inválido: %.',table_name;end if;
  end if;
 end loop;
 if supplied not in (0,4) then raise exception 'Faltan hojas del historial POS. Exporta nuevamente un respaldo completo antes de importar.';end if;
 if supplied=0 and (exists(select 1 from public.store_orders where gym_id=p_gym_id)
  or exists(select 1 from public.store_inventory_movements where gym_id=p_gym_id and movement_type<>'INITIAL_STOCK')) then
  raise exception 'Este archivo antiguo no contiene el historial POS existente. No se modificó información. Exporta un respaldo completo actual antes de importar.';
 end if;
 if supplied=4 and jsonb_array_length(p_tables->'gym_store_settings')>1 then raise exception 'La configuración de tienda debe corresponder a un solo gimnasio.';end if;
 select greatest(coalesce((select last_sale_number from public.gym_store_settings where gym_id=p_gym_id),0),
  coalesce((select max(sale_number) from public.store_orders where gym_id=p_gym_id),0)) into prior_counter;
 create temporary table store_pos_import_archive(tables jsonb not null,old_counter bigint not null) on commit drop;
 insert into pg_temp.store_pos_import_archive values(p_tables,prior_counter);
 create temporary table store_pos_import_order_ids(old_id text primary key,new_id uuid not null) on commit drop;
 create temporary table store_pos_import_movement_ids(old_id text primary key,new_id bigint not null) on commit drop;
 insert into private.store_pos_context(transaction_id,movement_type,reason)
 values(txid_current(),'ADJUSTMENT','Restauración completa autorizada');
 -- Dependent rows are removed only after the complete-file guard above; any
 -- subsequent validation failure rolls this entire transaction back.
 delete from public.store_inventory_movements where gym_id=p_gym_id;
 delete from public.store_payments where gym_id=p_gym_id;
 delete from public.store_sales where gym_id=p_gym_id;
 delete from public.store_orders where gym_id=p_gym_id;
 delete from private.store_pos_requests where gym_id=p_gym_id;
 return jsonb_set(p_tables,'{store_sales}',coalesce((select jsonb_agg(row-'order_id')
  from jsonb_array_elements(coalesce(p_tables->'store_sales','[]')) row),'[]'));
end $$;

create or replace function private.store_pos_import_record(p_table text,p_gym_id uuid,p_row jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare columns text;values_sql text;result jsonb;
begin
 if p_table<>all(array['store_orders','store_payments','store_inventory_movements']) then raise exception 'Tabla POS no permitida.';end if;
 if not exists(select 1 from private.store_pos_context where transaction_id=txid_current()) then raise exception 'Restauración POS no autorizada.' using errcode='42501';end if;
 p_row:=p_row||jsonb_build_object('gym_id',p_gym_id);
 select string_agg(format('%I',a.attname),',' order by a.attnum),
  string_agg(format('r.%I',a.attname),',' order by a.attnum) into columns,values_sql
 from pg_catalog.pg_attribute a where a.attrelid=format('public.%I',p_table)::regclass
  and a.attnum>0 and not a.attisdropped and a.attgenerated='' and p_row ? a.attname;
 execute format('insert into public.%1$I(%2$s) select %3$s from jsonb_populate_record(null::public.%1$I,$1) r returning to_jsonb(%1$I)',p_table,columns,values_sql)
 using p_row into result;
 return result;
end $$;

create or replace function private.store_pos_import_map(p_entity text,p_old_id text,p_required boolean default true) returns bigint
language plpgsql security definer set search_path='' as $$
declare result bigint;
begin
 if nullif(p_old_id,'') is null and not p_required then return null;end if;
 select new_id into result from pg_temp.gymsoft_import_ids where entity=p_entity and old_id=p_old_id;
 if result is null then raise exception 'El historial POS contiene una relación inválida con %.',p_entity;end if;
 return result;
end $$;

create or replace function private.store_pos_import_payload(p_payload jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare item jsonb;items jsonb:='[]';result jsonb:=p_payload;
begin
 if result ? 'client_id' and result->>'client_id' is not null then
  result:=jsonb_set(result,'{client_id}',to_jsonb(private.store_pos_import_map('clients',result->>'client_id')));
 end if;
 if result ? 'product_id' then result:=jsonb_set(result,'{product_id}',to_jsonb(private.store_pos_import_map('store_products',result->>'product_id')));end if;
 if result ? 'items' then
  for item in select value from jsonb_array_elements(result->'items') loop
   items:=items||jsonb_build_array(jsonb_set(item,'{product_id}',to_jsonb(private.store_pos_import_map('store_products',item->>'product_id'))));
  end loop;
  result:=jsonb_set(result,'{items}',items);
 end if;
 return result;
end $$;

create or replace function private.store_pos_import_finish(p_gym_id uuid) returns void
language plpgsql security definer set search_path='' as $$
declare tables jsonb;row jsonb;settings jsonb;result jsonb;old_id text;restored_order_uuid uuid;payment_id uuid;product_id bigint;client_id bigint;sale_id bigint;movement_id bigint;counter bigint;prior_counter bigint;
begin
 perform private.store_pos_import_authorize(p_gym_id);
 select a.tables,a.old_counter into tables,prior_counter from pg_temp.store_pos_import_archive a;
 if tables ? 'store_orders' then
  for row in select value from jsonb_array_elements(tables->'store_orders') loop
   old_id:=row->>'id'; restored_order_uuid:=old_id::uuid;
   if exists(select 1 from public.store_orders where id=restored_order_uuid) then restored_order_uuid:=gen_random_uuid();end if;
   client_id:=private.store_pos_import_map('clients',row->>'client_id',false);
   row:=(row-'client_id')||jsonb_build_object('id',restored_order_uuid,'request_payload',private.store_pos_import_payload(row->'request_payload'));
   if client_id is not null then row:=row||jsonb_build_object('client_id',client_id);end if;
   perform private.store_pos_import_record('store_orders',p_gym_id,row);
   insert into pg_temp.store_pos_import_order_ids values(old_id,restored_order_uuid);
  end loop;
  for row in select value from jsonb_array_elements(coalesce(tables->'store_sales','[]')) where value->>'order_id' is not null loop
   select m.new_id into restored_order_uuid from pg_temp.store_pos_import_order_ids m where m.old_id=row->>'order_id';
   sale_id:=private.store_pos_import_map('store_sales',row->>'id');
   if restored_order_uuid is null then raise exception 'Una línea de venta POS no tiene cabecera válida.';end if;
   update public.store_sales set order_id=restored_order_uuid where id=sale_id and gym_id=p_gym_id;
  end loop;
  for row in select value from jsonb_array_elements(tables->'store_payments') loop
   select m.new_id into restored_order_uuid from pg_temp.store_pos_import_order_ids m where m.old_id=row->>'order_id';
   if restored_order_uuid is null then raise exception 'Un pago POS no tiene venta válida.';end if;
   payment_id:=(row->>'id')::uuid;
   if exists(select 1 from public.store_payments where id=payment_id) then payment_id:=gen_random_uuid();end if;
   perform private.store_pos_import_record('store_payments',p_gym_id,row||jsonb_build_object('id',payment_id,'order_id',restored_order_uuid));
  end loop;
  -- Product INSERT triggers established temporary opening balances. Replace
  -- those with the actual archived movements, retaining their real instants.
  delete from public.store_inventory_movements where gym_id=p_gym_id;
  for row in select value from jsonb_array_elements(tables->'store_inventory_movements') loop
   old_id:=row->>'id'; product_id:=private.store_pos_import_map('store_products',row->>'product_id');restored_order_uuid:=null;
   if row->>'order_id' is not null then
    select m.new_id into restored_order_uuid from pg_temp.store_pos_import_order_ids m where m.old_id=row->>'order_id';
    if restored_order_uuid is null then raise exception 'Un movimiento POS no tiene venta válida.';end if;
   end if;
   row:=(row-'id'-'order_id')||jsonb_build_object('product_id',product_id);
   if restored_order_uuid is not null then row:=row||jsonb_build_object('order_id',restored_order_uuid);end if;
   result:=private.store_pos_import_record('store_inventory_movements',p_gym_id,row);
   if old_id is not null then insert into pg_temp.store_pos_import_movement_ids values(old_id,(result->>'id')::bigint);end if;
  end loop;
  if exists(select 1 from public.store_orders o left join public.store_payments p on p.gym_id=o.gym_id and p.order_id=o.id
   where o.gym_id=p_gym_id and (p.id is null or p.amount<>o.total_amount or p.status<>o.status
    or o.total_amount<>(select coalesce(sum(s.total_amount),0) from public.store_sales s where s.gym_id=o.gym_id and s.order_id=o.id)
    or not exists(select 1 from public.store_sales s where s.gym_id=o.gym_id and s.order_id=o.id)
    or exists(select 1 from public.store_sales s where s.gym_id=o.gym_id and s.order_id=o.id and s.status<>o.status))) then
   raise exception 'El respaldo POS tiene ventas, pagos o líneas inconsistentes.';
  end if;
  if exists(select 1 from public.store_products p where p.gym_id=p_gym_id and
    p.stock_quantity is distinct from (select m.stock_after from public.store_inventory_movements m
      where m.gym_id=p_gym_id and m.product_id=p.id order by m.id desc limit 1)) then
   raise exception 'El saldo de productos no coincide con el historial POS de inventario.';
  end if;
  settings:=coalesce(tables->'gym_store_settings'->0,'{}');
  for row in select value from jsonb_array_elements(coalesce(settings->'inventory_request_archive','[]')) loop
   result:=row->'result';product_id:=private.store_pos_import_map('store_products',result->>'product_id');
   result:=result||jsonb_build_object('product_id',product_id);
   if result->'movement' is not null then
    select m.new_id into movement_id from pg_temp.store_pos_import_movement_ids m where m.old_id=result->'movement'->>'id';
    if movement_id is null then raise exception 'Una solicitud de inventario no tiene movimiento válido.';end if;
    result:=jsonb_set(result,'{movement}',(result->'movement')||jsonb_build_object('id',movement_id,'gym_id',p_gym_id,'product_id',product_id));
   end if;
   insert into private.store_pos_requests(gym_id,request_id,payload,result)
   values(p_gym_id,(row->>'request_id')::uuid,private.store_pos_import_payload(row->'payload'),result);
  end loop;
 else
  settings:='{}';
 end if;
 select greatest(prior_counter,coalesce((settings->>'last_sale_number')::bigint,0),
  coalesce((select max(sale_number) from public.store_orders where gym_id=p_gym_id),0)) into counter;
 insert into public.gym_store_settings(gym_id,enabled,last_sale_number,updated_by,updated_at)
 values(p_gym_id,coalesce((settings->>'enabled')::boolean,true),counter,auth.uid(),private.gym_server_now())
 on conflict(gym_id) do update set enabled=excluded.enabled,last_sale_number=excluded.last_sale_number,updated_by=excluded.updated_by,updated_at=excluded.updated_at;
 perform private.insert_store_audit(p_gym_id,auth.uid(),'STORE_BACKUP_RESTORED','gym_store_settings',p_gym_id::text,'Restauración transaccional de tienda',jsonb_build_object('last_sale_number',counter));
 delete from private.store_pos_context where transaction_id=txid_current();
end $$;

-- Owner restores use the existing owner's relationship map and the same
-- ledger restorer. They do not create a second sales/inventory implementation.
create or replace function private.store_pos_restore_ledger(p_gym_id uuid,p_tables jsonb,p_mappings jsonb) returns void
language plpgsql security definer set search_path='' as $$
declare row jsonb;mapping record;old_id text;new_id bigint;product_id bigint;counter bigint;
begin
 perform private.store_pos_import_authorize(p_gym_id);
 if not p_tables ? 'store_orders' then return;end if;
 if not (p_tables ? 'store_payments' and p_tables ? 'store_inventory_movements' and p_tables ? 'gym_store_settings') then
  raise exception 'Faltan tablas del historial POS en el respaldo del propietario.';
 end if;
 select greatest(coalesce((select last_sale_number from public.gym_store_settings where gym_id=p_gym_id),0),
  coalesce((p_tables->'gym_store_settings'->0->>'last_sale_number')::bigint,0)) into counter;
 create temporary table store_pos_import_archive(tables jsonb not null,old_counter bigint not null) on commit drop;
 insert into pg_temp.store_pos_import_archive values(p_tables,counter);
 create temporary table store_pos_import_order_ids(old_id text primary key,new_id uuid not null) on commit drop;
 create temporary table store_pos_import_movement_ids(old_id text primary key,new_id bigint not null) on commit drop;
 create temporary table gymsoft_import_ids(entity text,old_id text,new_id bigint,primary key(entity,old_id)) on commit drop;
 for mapping in select key,value from jsonb_each_text(p_mappings) loop
  insert into pg_temp.gymsoft_import_ids values(split_part(mapping.key,':',1),substring(mapping.key from position(':' in mapping.key)+1),mapping.value::bigint);
 end loop;
 insert into private.store_pos_context(transaction_id,movement_type,reason) values(txid_current(),'ADJUSTMENT','Restauración por el propietario');
 for row in select value from jsonb_array_elements(coalesce(p_tables->'store_sales','[]')) where value->>'order_id' is not null loop
  old_id:=row->>'id';product_id:=private.store_pos_import_map('store_products',row->>'product_id');
  row:=(row-'order_id')||jsonb_build_object('product_id',product_id);
  new_id:=private.gymsoft_import_insert('store_sales',p_gym_id,row);
  insert into pg_temp.gymsoft_import_ids values('store_sales',old_id,new_id);
 end loop;
 perform private.store_pos_import_finish(p_gym_id);
end $$;

-- Fail closed if the original importer changed rather than partially patching it.
do $patch$
declare definition text;original text;anchor text;target regprocedure;insert_helper text;
begin
 -- Comercial keeps its licensed public wrapper; extend the private body.
 target:=coalesce(to_regprocedure('private.admin_replace_gym_from_excel(jsonb)'),
                  to_regprocedure('public.admin_replace_gym_from_excel(jsonb)'));
 if target is null then raise exception 'Falta instalar el importador Excel original antes de POS.';end if;
 select pg_get_functiondef(target) into definition;
 if position('private.store_pos_import_begin' in definition)>0 then return;end if;
 definition:=replace(definition,E'\r\n',E'\n');
 -- ZTATTUZ uses the same importer with its historical prefix/format. Keep
 -- the public format and insertion helper, sharing only the temporary map.
 definition:=replace(definition,'ztattuz_import_ids','gymsoft_import_ids');
 insert_helper:=case when position('private.ztattuz_import_insert' in definition)>0 then 'ztattuz_import_insert' else 'gymsoft_import_insert' end;
 original:=definition;
 anchor:=E'    create temporary table gymsoft_import_ids (';
 if position(anchor in definition)=0 then raise exception 'Revisar ancla inicial del importador Excel antes de extender POS.';end if;
 definition:=replace(definition,anchor,E'    v_tables := private.store_pos_import_begin(v_gym_id, v_tables);\n\n'||anchor);
 anchor:=E'        perform private.'||insert_helper||E'(\n            ''store_sales'', v_gym_id, v_row\n        );';
 if position(anchor in definition)=0 then raise exception 'Revisar ancla de líneas de venta del importador Excel.';end if;
 definition:=replace(definition,anchor,E'        v_old_id := v_row->>''id'';\n        v_new_id := private.'||insert_helper||E'(\n            ''store_sales'', v_gym_id, v_row\n        );\n        insert into gymsoft_import_ids values (''store_sales'', v_old_id, v_new_id);');
 anchor:=E'    v_total :=';
 if position(anchor in definition)=0 then raise exception 'Revisar ancla final del importador Excel antes de extender POS.';end if;
 definition:=replace(definition,anchor,E'    perform private.store_pos_import_finish(v_gym_id);\n\n'||anchor);
 execute definition;
end $patch$;

revoke all on function private.store_pos_import_begin(uuid,jsonb),private.store_pos_import_record(text,uuid,jsonb),
 private.store_pos_import_map(text,text,boolean),private.store_pos_import_payload(jsonb),private.store_pos_import_finish(uuid)
 from public,anon,authenticated;
revoke all on function private.store_pos_import_authorize(uuid),private.store_pos_restore_ledger(uuid,jsonb,jsonb) from public,anon,authenticated;
notify pgrst,'reload schema';
commit;
