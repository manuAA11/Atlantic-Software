-- El gimnasio de una relación debe coincidir en los dos extremos.
-- Un filtro de interfaz o una FK de solo client_id no bastan.
do $$
declare r record; col text; delete_rule text;
begin
 for r in select t.oid::regclass as tbl from pg_class t join pg_namespace n on n.oid=t.relnamespace
 where n.nspname='public' and t.relkind='r'
 and exists(select 1 from pg_attribute a where a.attrelid=t.oid and a.attname='gym_id')
 and exists(select 1 from pg_attribute a where a.attrelid=t.oid and a.attname='id') loop
  execute format('alter table %s add unique(gym_id,id)',r.tbl);
 end loop;
 for r in select c.*,c.conrelid::regclass as child,c.confrelid::regclass as parent
 from pg_constraint c join pg_class t on t.oid=c.conrelid join pg_namespace n on n.oid=t.relnamespace
 where c.contype='f' and n.nspname='public' and array_length(c.conkey,1)=1
 and exists(select 1 from pg_attribute a where a.attrelid=c.conrelid and a.attname='gym_id')
 and exists(select 1 from pg_attribute a where a.attrelid=c.confrelid and a.attname='gym_id') loop
  select attname into col from pg_attribute where attrelid=r.conrelid and attnum=r.conkey[1];
  delete_rule:=case r.confdeltype when 'c' then ' ON DELETE CASCADE' when 'n' then format(' ON DELETE SET NULL (%I)',col) else '' end;
  execute format('alter table %s drop constraint %I',r.child,r.conname);
  execute format('alter table %s add constraint %I foreign key(gym_id,%I) references %s(gym_id,id)%s',r.child,r.conname,col,r.parent,delete_rule);
 end loop;
end $$;

-- Ni el administrador de un gimnasio puede asignarse otro gimnasio,
-- cambiar su rol, habilitarse de nuevo ni aumentar sus límites.
do $$ declare p record; begin
 for p in select tablename,policyname from pg_policies where schemaname='public' and tablename in ('gyms','gym_users') loop
  execute format('drop policy %I on public.%I',p.policyname,p.tablename);
 end loop;
end $$;
revoke all on public.gyms,public.gym_users from public,anon,authenticated;
grant select on public.gyms,public.gym_users to authenticated;
grant update(name) on public.gyms to authenticated;
create policy user_self on public.gym_users for select to authenticated using(user_id=auth.uid());
create policy gym_self on public.gyms for select to authenticated
 using(exists(select 1 from public.gym_users u where u.gym_id=gyms.id and u.user_id=auth.uid()));
create policy gym_rename on public.gyms for update to authenticated
 using(private.user_has_gym_role(id,array['admin'])) with check(private.user_has_gym_role(id,array['admin']));

-- Una política restrictiva añade el candado comercial a TODOS los registros
-- operativos, incluidas auditoría, eventos y futuras políticas permisivas.
do $$ declare r record; begin
 for r in select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace
 where n.nspname='public' and c.relkind='r' and c.relname<>'gym_users'
 and exists(select 1 from pg_attribute a where a.attrelid=c.oid and a.attname='gym_id') loop
  execute format('alter table public.%I enable row level security',r.relname);
  execute format('revoke all on public.%I from public,anon',r.relname);
  execute format('create policy commercial_guard on public.%I as restrictive for all to authenticated using(private.current_access(gym_id)) with check(private.current_access(gym_id))',r.relname);
 end loop;
end $$;

-- Los RPC heredados SECURITY DEFINER también validan la sesión y suscripción.
-- Sus implementaciones pasan a un esquema que no expone la API.
do $$
declare r record; args text; ident text; result_type text; call_args text; body text;
begin
 for r in select p.* from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='public' and p.prokind='f' and p.prorettype<>'trigger'::regtype
 and p.proname not like 'owner_%' and p.proname not like 'commercial_%'
 and p.proname not in ('reception_account_context','redeem_reception_invite') loop
  ident:=pg_get_function_identity_arguments(r.oid);
  execute format('revoke all on function public.%I(%s) from public,anon,authenticated',r.proname,ident);
  if r.proname like '%_internal' then continue; end if;
  args:=pg_get_function_arguments(r.oid); result_type:=pg_get_function_result(r.oid);
  select coalesce(string_agg('$'||i,','),'') into call_args from generate_series(1,r.pronargs) i;
  execute format('alter function public.%I(%s) set schema private',r.proname,ident);
  body:='BEGIN PERFORM private.require_current_access(); ';
  if r.proretset then body:=body||format('RETURN QUERY SELECT * FROM private.%I(%s);',r.proname,call_args);
  elsif r.prorettype='void'::regtype then body:=body||format('PERFORM private.%I(%s); RETURN;',r.proname,call_args);
  else body:=body||format('RETURN private.%I(%s);',r.proname,call_args); end if;
  body:=body||' END';
  execute format('create function public.%I(%s) returns %s language plpgsql security definer set search_path='''' as %L',r.proname,args,result_type,body);
 end loop;
end $$;

revoke all on all functions in schema public from public,anon,authenticated;
revoke all on all functions in schema private from public,anon,authenticated;
grant execute on function private.user_has_gym_role(uuid,text[]),private.current_access(uuid) to authenticated;
do $$ declare r record; begin
 for r in select p.oid,p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname='public' and p.prokind='f' and p.prorettype<>'trigger'::regtype and p.proname not like '%_internal' loop
  execute format('grant execute on function %s to authenticated',r.oid::regprocedure);
 end loop;
end $$;
grant execute on function public.commercial_system_info() to anon,authenticated;
-- Los pagos se corrigen por RPC con revisión y motivo; no por PATCH directo.
revoke update,delete on public.memberships from authenticated;
-- Evita que los clientes escriban movimientos de auditoría o eventos falsos.
revoke insert,update,delete on public.audit_logs,public.gym_events from authenticated;
grant execute on function public.commercial_system_info() to anon;
notify pgrst,'reload schema';
