begin;

-- Extend the existing Commercial owner tools; ZTATTUZ has no such API.
-- No ordinary product/sale editor gains permission to rewrite POS history.
create or replace function private.store_pos_owner_clear(p_gym_id uuid) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform private.require_owner();
 insert into private.store_pos_context(transaction_id,movement_type,reason)
 values(txid_current(),'ADJUSTMENT','Reemplazo completo confirmado por propietario');
 delete from public.store_inventory_movements where gym_id=p_gym_id;
 delete from public.store_payments where gym_id=p_gym_id;
 delete from public.store_sales where gym_id=p_gym_id and order_id is not null;
 delete from public.store_orders where gym_id=p_gym_id;
 delete from private.store_pos_requests where gym_id=p_gym_id;
 -- Keep the server counter when replacing data. Deleting the entire gym
 -- already cascades gym_store_settings after the confirmed owner operation.
 delete from private.store_pos_context where transaction_id=txid_current();
end $$;
revoke all on function private.store_pos_owner_clear(uuid) from public,anon,authenticated;

do $pos_owner$
declare definition text;anchor text;replacement text;
begin
 if to_regprocedure('private.owner_editor_snapshot(uuid)') is null then return;end if;

 if to_regprocedure('private.owner_editor_fields_before_pos(text)') is null then
  alter function private.owner_editor_fields(text) rename to owner_editor_fields_before_pos;
 end if;
 execute $fields$
 create or replace function private.owner_editor_fields(p_table text) returns text[]
 language sql immutable set search_path='' as $body$
 select case when p_table in ('store_orders','store_payments','store_inventory_movements','gym_store_settings')
  then array[]::text[] else private.owner_editor_fields_before_pos(p_table) end
 $body$;
 $fields$;
 revoke all on function private.owner_editor_fields(text),private.owner_editor_fields_before_pos(text) from public,anon,authenticated;

 definition:=pg_get_functiondef('private.owner_editor_snapshot(uuid)'::regprocedure);
 if position('inventory_request_archive' in definition)=0 then
  anchor:='''audit_logs''] loop';
  if position(anchor in definition)=0 then raise exception 'Revisar tablas del respaldo propietario antes de ampliar POS.';end if;
  definition:=replace(definition,anchor,'''audit_logs'',''store_orders'',''store_payments'',''store_inventory_movements'',''gym_store_settings''] loop');
  anchor:='tables:=tables||jsonb_build_object(t,rows);';
  if position(anchor in definition)=0 then raise exception 'Revisar filas del respaldo propietario antes de ampliar POS.';end if;
  replacement:=$snapshot$
  if t='gym_store_settings' then
   rows:=jsonb_build_array(coalesce((select to_jsonb(s) from public.gym_store_settings s where gym_id=p_gym_id),
    jsonb_build_object('gym_id',p_gym_id,'enabled',true,'last_sale_number',0))||jsonb_build_object('inventory_request_archive',
    (select coalesce(jsonb_agg(jsonb_build_object('request_id',r.request_id,'payload',r.payload,'result',r.result) order by r.request_id),'[]')
     from private.store_pos_requests r where r.gym_id=p_gym_id)));
  end if;
$snapshot$;
  definition:=replace(definition,anchor,replacement||anchor);
  execute definition;
 end if;

 definition:=pg_get_functiondef('private.owner_editor_clear(uuid)'::regprocedure);
 if position('private.store_pos_owner_clear' in definition)=0 then
  anchor:=' perform private.require_owner();';
  if position(anchor in definition)=0 then raise exception 'Revisar limpieza autorizada del propietario antes de ampliar POS.';end if;
  definition:=replace(definition,anchor,anchor||E'\n perform private.store_pos_owner_clear(p_gym_id);');
  execute definition;
 end if;

 definition:=pg_get_functiondef('private.owner_editor_validate_import(jsonb)'::regprocedure);
 if position('inventory_request_archive' in definition)=0 then
  anchor:='if not exists(select 1 from pg_catalog.pg_attribute a where';
  if position(anchor in definition)=0 then raise exception 'Revisar columnas del respaldo propietario antes de ampliar POS.';end if;
  definition:=replace(definition,anchor,'if not (t=''gym_store_settings'' and k=''inventory_request_archive'') and not exists(select 1 from pg_catalog.pg_attribute a where');
  anchor:='if t not in (''marketing_settings'',''gym_branding'') then';
  if position(anchor in definition)=0 then raise exception 'Revisar identificadores del respaldo propietario antes de ampliar POS.';end if;
  definition:=replace(definition,anchor,'if t not in (''marketing_settings'',''gym_branding'',''gym_store_settings'',''store_orders'',''store_payments'') then');
  execute definition;
 end if;

 definition:=pg_get_functiondef('private.owner_editor_import(uuid,jsonb,text,text,text)'::regprocedure);
 if position('private.store_pos_restore_ledger' in definition)=0 then
  anchor:=' tables:=p_data->''tables'';';
  if position(anchor in definition)=0 then raise exception 'Revisar inicio del importador propietario antes de ampliar POS.';end if;
  replacement:=$guard$
 if ((tables?'store_orders')::integer+(tables?'store_payments')::integer+
     (tables?'store_inventory_movements')::integer+(tables?'gym_store_settings')::integer) not in (0,4) then
  raise exception 'El respaldo POS está incompleto. Exporta una copia completa actual.';
 end if;
 if not tables?'store_orders' and (exists(select 1 from public.store_orders where gym_id=p_gym_id)
  or exists(select 1 from public.store_inventory_movements where gym_id=p_gym_id and movement_type<>'INITIAL_STOCK')) then
  raise exception 'El archivo antiguo no contiene el historial POS existente. Exporta una copia completa actual antes de reemplazar datos.';
 end if;
$guard$;
  definition:=replace(definition,anchor,anchor||replacement);
  anchor:='   old_id:=row_data->>''id'';';
  if position(anchor in definition)=0 then raise exception 'Revisar líneas del importador propietario antes de ampliar POS.';end if;
  definition:=replace(definition,anchor,E'   if t=''store_sales'' and row_data->>''order_id'' is not null then continue;end if;\n'||anchor);
  anchor:=' insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),''database_imported'',';
  if position(anchor in definition)=0 then raise exception 'Revisar final del importador propietario antes de ampliar POS.';end if;
  definition:=replace(definition,anchor,E' perform private.store_pos_restore_ledger(p_gym_id,tables,mappings);\n'||anchor);
  execute definition;
 end if;

 -- All new rows participate in the existing shared/exclusive owner lock:
 -- a confirmed full restore/delete cannot race normal POS writes.
 foreach anchor in array array['store_orders','store_payments','store_inventory_movements','gym_store_settings'] loop
  execute format('drop trigger if exists owner_editor_guard on public.%I',anchor);
  execute format('create trigger owner_editor_guard before insert or update or delete on public.%I for each row execute function private.owner_editor_write_guard()',anchor);
 end loop;
end $pos_owner$;
commit;
