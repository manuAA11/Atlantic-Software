-- Gym soft comercial 3.1.0. Actualización ADITIVA sobre la base comercial.
-- No ejecutar INSTALAR_BASE_NUEVA.sql en un proyecto que ya tenga datos.
begin;
do $$ begin
 if to_regclass('private.software_owners') is null or
    to_regprocedure('public.commercial_system_info()') is null then
   raise exception 'Esta actualización requiere la base COMERCIAL de Gym soft.';
 end if;
end $$;

-- Este catálogo limita tanto la lectura como los campos editables. No admite
-- tablas arbitrarias, IDs, gym_id, claves de acceso ni identidades de auditoría.
create or replace function private.owner_editor_fields(p_table text) returns text[]
language plpgsql immutable set search_path='' as $$
begin
 return case p_table
 when 'clients' then array['document','first_name','last_name','phone','email','birth_date','emergency_contact','medical_notes','active']
 when 'plans' then array['name','duration_days','price','entry_limit','active']
 when 'memberships' then array['start_date','end_date','amount','entry_limit','payment_method','payment_reference','notes','payment_status']
 when 'checkins' then array['checkin_at','method','result','notes']
 when 'trainers' then array['name','phone','email','specialty','active','hourly_rate','hire_date','notes']
 when 'staff_shifts' then array['check_in_at','check_out_at','hourly_rate_snapshot','notes']
 when 'routines' then array['name','goal','start_date','notes','active']
 when 'exercises' then array['day_name','name','sets','reps','weight','notes','position']
 when 'classes' then array['name','starts_at','capacity','notes','status']
 when 'reservations' then array['status']
 when 'store_products' then array['name','sku','sale_price','stock_quantity','low_stock_threshold','active']
 when 'store_sales' then array['quantity','unit_price','payment_method','payment_reference','customer_name','notes','sold_at']
 when 'accounting_expenses' then array['expense_date','category','description','vendor','amount','payment_method','payment_reference','receipt_reference','notes']
 when 'marketing_messages' then array[]::text[]
 when 'audit_logs' then array[]::text[]
 else null end;
end $$;

-- Las operaciones destructivas adquieren un bloqueo exclusivo por gimnasio.
-- Las escrituras normales participan con un bloqueo compartido; nunca se
-- bloquea toda la base ni se deshabilitan RLS/FK/triggers durante una importación.
create or replace function private.owner_editor_write_guard() returns trigger
language plpgsql security definer set search_path='' as $$
declare g uuid;
begin
 g:=(case when tg_op='DELETE' then to_jsonb(old) else to_jsonb(new) end ->>
     case when tg_table_name='gyms' then 'id' else 'gym_id' end)::uuid;
 if g is not null then
  perform pg_catalog.pg_advisory_xact_lock_shared(pg_catalog.hashtextextended('gymsoft-owner-editor:'||g::text,0));
  if private.owner_editor_fields(tg_table_name) is not null and
     tg_table_name not in ('audit_logs','marketing_messages') and auth.uid() is not null and
     not exists(select 1 from private.software_owners where user_id=auth.uid()) and
     not private.current_access(g) then
    raise exception 'Acceso no autorizado: el gimnasio ya no tiene acceso activo. Actualiza la aplicación.' using errcode='42501';
  end if;
 end if;
 if tg_op='DELETE' then return old; else return new; end if;
end $$;
do $$ declare t record; begin
 for t in select n.nspname,c.relname from pg_catalog.pg_class c
 join pg_catalog.pg_namespace n on n.oid=c.relnamespace
 where n.nspname in ('public','private') and c.relkind='r' and
 (c.relname='gyms' or exists(select 1 from pg_catalog.pg_attribute a where a.attrelid=c.oid and a.attname='gym_id')) loop
  execute format('drop trigger if exists owner_editor_guard on %I.%I',t.nspname,t.relname);
  execute format('create trigger owner_editor_guard before insert or update or delete on %I.%I for each row execute function private.owner_editor_write_guard()',t.nspname,t.relname);
 end loop;
end $$;

create or replace function private.owner_editor_lock(p_gym_id uuid,p_reason text default null) returns void
language plpgsql security definer set search_path='' as $$
begin
 perform private.require_owner();
 if p_reason is not null and length(trim(p_reason)) not between 3 and 500 then
  raise exception 'Escribe un motivo de 3 a 500 caracteres.';
 end if;
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('gymsoft-owner-editor:'||p_gym_id::text,0));
 if not exists(select 1 from public.gyms where id=p_gym_id) then raise exception 'El gimnasio ya no existe.'; end if;
end $$;

create or replace function private.owner_editor_snapshot(p_gym_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare t text; rows jsonb; tables jsonb:='{}'; result jsonb; counts jsonb:='{}';
begin
 perform private.require_owner();
 if not exists(select 1 from public.gyms where id=p_gym_id) then raise exception 'El gimnasio ya no existe.'; end if;
 foreach t in array array['clients','plans','memberships','checkins','trainers','staff_shifts','routines','exercises','classes','reservations',
 'store_products','store_sales','accounting_expenses','marketing_settings','marketing_messages','gym_branding','audit_logs'] loop
  execute format('select coalesce(jsonb_agg(to_jsonb(r) order by to_jsonb(r)->>''id''),''[]''::jsonb) from public.%I r where gym_id=$1',t) into rows using p_gym_id;
  tables:=tables||jsonb_build_object(t,rows); counts:=counts||jsonb_build_object(t,jsonb_array_length(rows));
 end loop;
 result:=jsonb_build_object('format','GymSoft-CLOUD-2','gym_id',p_gym_id,
  'gym',(select to_jsonb(g)-'join_code' from public.gyms g where id=p_gym_id),
  'contract',(select to_jsonb(s) from private.subscriptions s where gym_id=p_gym_id),
  'users',coalesce((select jsonb_agg(to_jsonb(u)||jsonb_build_object('email',a.email) order by u.user_id) from public.gym_users u join auth.users a on a.id=u.user_id where u.gym_id=p_gym_id),'[]'),
  'devices',coalesce((select jsonb_agg(to_jsonb(d)-'device_hash'-'last_seen' order by id) from private.license_devices d where gym_id=p_gym_id),'[]'),
  'payments',coalesce((select jsonb_agg(to_jsonb(p) order by id) from private.subscription_payments p where gym_id=p_gym_id),'[]'),
  'invitations',coalesce((select jsonb_agg(jsonb_build_object('email',i.email,'role',i.role,'expires_at',i.expires_at,'used_at',i.used_at) order by i.email,i.expires_at) from private.activation_invites i where gym_id=p_gym_id),'[]'),
  'tables',tables,'counts',counts);
 -- La huella ignora conexiones y eventos de lectura. Sí detecta cambios de
 -- datos, contrato, usuarios, equipos autorizados e invitaciones.
 result:=result||jsonb_build_object('fingerprint',encode(sha256(convert_to(result::text,'UTF8')),'hex'));
 return result||jsonb_build_object('created_at',now(),'owner_history',
 coalesce((select jsonb_agg(to_jsonb(e) order by id) from private.owner_events e where gym_id=p_gym_id),'[]'));
end $$;

create or replace function private.owner_editor_backup(p_gym_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare snapshot jsonb;
begin
 perform private.owner_editor_lock(p_gym_id);
 snapshot:=private.owner_editor_snapshot(p_gym_id);
 insert into private.owner_events(gym_id,actor,action) values(p_gym_id,auth.uid(),'backup_exported');
 return snapshot;
end $$;

create or replace function private.owner_editor_profile(p_gym_id uuid,p_name text,p_email text,p_timezone text,p_plan text,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare before_row jsonb;
begin
 perform private.owner_editor_lock(p_gym_id,coalesce(p_reason,''));
 if length(trim(coalesce(p_name,''))) not between 1 and 120 or
    length(trim(coalesce(p_plan,''))) not between 1 and 80 or
    coalesce(p_email,'') !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' or length(p_email)>254 then
  raise exception 'Revisa el nombre, correo de contacto y plan comercial.';
 end if;
 if not exists(select 1 from pg_catalog.pg_timezone_names where name=p_timezone) then raise exception 'Zona horaria inválida.'; end if;
 select jsonb_build_object('name',g.name,'timezone',g.timezone,'email',s.contact_email,'plan',s.plan)
 into before_row from public.gyms g join private.subscriptions s on s.gym_id=g.id where g.id=p_gym_id;
 update public.gyms set name=trim(p_name),timezone=p_timezone where id=p_gym_id;
 update public.marketing_settings set timezone=p_timezone,updated_by=auth.uid(),updated_at=now() where gym_id=p_gym_id;
 update private.subscriptions set contact_email=lower(trim(p_email)),plan=trim(p_plan) where gym_id=p_gym_id;
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),'gym_profile_edited',
 jsonb_build_object('before',before_row,'after',jsonb_build_object('name',trim(p_name),'email',lower(trim(p_email)),'timezone',p_timezone,'plan',trim(p_plan)),'reason',trim(p_reason)));
 return jsonb_build_object('gym_id',p_gym_id,'name',trim(p_name));
end $$;

create or replace function private.owner_editor_access(p_gym_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 perform private.require_owner();
 return jsonb_build_object(
 'users',coalesce((select jsonb_agg(jsonb_build_object('email',a.email,'role',u.role,'enabled',u.enabled) order by a.email)
  from public.gym_users u join auth.users a on a.id=u.user_id where u.gym_id=p_gym_id),'[]'),
 'invitations',coalesce((select jsonb_agg(jsonb_build_object('email',i.email,'role',i.role,'expires_at',i.expires_at,'expired',i.expires_at<=now()) order by i.email,i.expires_at)
  from private.activation_invites i where gym_id=p_gym_id and used_at is null),'[]'));
end $$;

create or replace function private.owner_editor_revoke_invite(p_gym_id uuid,p_email text,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare n integer;
begin
 perform private.owner_editor_lock(p_gym_id,coalesce(p_reason,''));
 delete from private.activation_invites where gym_id=p_gym_id and lower(email)=lower(trim(p_email)) and used_at is null;
 get diagnostics n=row_count;
 if n=0 then raise exception 'No hay invitación pendiente. Actualiza la lista: puede haberse utilizado.'; end if;
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),'invitation_revoked',jsonb_build_object('email',lower(trim(p_email)),'reason',trim(p_reason)));
 return jsonb_build_object('revoked',n);
end $$;

-- Asigna una cuenta confirmada sin crear contraseñas. Una cuenta de otro
-- gimnasio o del propietario nunca se traslada. Si no existe, genera código.
create or replace function private.owner_editor_email(p_gym_id uuid,p_email text,p_role text,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare u auth.users%rowtype; member public.gym_users%rowtype; code text; cap integer;
begin
 perform private.owner_editor_lock(p_gym_id,coalesce(p_reason,''));
 p_email:=lower(trim(p_email));
 if coalesce(p_email,'') !~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' or length(p_email)>254 or coalesce(p_role,'') not in ('admin','receptionist') then
  raise exception 'Escribe un correo válido y elige Administración o Recepción.';
 end if;
 perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('gymsoft-owner-email:'||p_email,0));
 select * into u from auth.users where lower(email)=p_email;
 if u.id is not null then
  if exists(select 1 from private.software_owners where user_id=u.id) then raise exception 'La cuenta propietaria no puede asignarse a un gimnasio.'; end if;
  select * into member from public.gym_users where user_id=u.id for update;
  if member.gym_id is not null and member.gym_id<>p_gym_id then raise exception 'Ese correo pertenece a otro gimnasio. No se trasladó la cuenta.'; end if;
 end if;
 if u.id is null or u.email_confirmed_at is null then
  -- Reemplazar invitaciones pendientes del mismo correo evita roles antiguos.
  delete from private.activation_invites where gym_id=p_gym_id and email=p_email and used_at is null;
  code:=public.owner_invite_user(p_gym_id,p_email,p_role);
  return jsonb_build_object('state','invited','email',p_email,'role',p_role,'activation_code',code);
 end if;
 select max_users into cap from private.subscriptions where gym_id=p_gym_id for update;
 if not coalesce(member.enabled,false) and (select count(*) from public.gym_users where gym_id=p_gym_id and enabled)>=cap then
  raise exception 'Se alcanzó el límite de usuarios. Amplía el contrato antes de agregar otra cuenta.';
 end if;
 insert into public.gym_users(gym_id,user_id,role,enabled) values(p_gym_id,u.id,p_role,true)
 on conflict(user_id) do update set role=excluded.role,enabled=true
 where gym_users.gym_id=excluded.gym_id;
 if not found then raise exception 'Ese correo acaba de ser asignado a otro gimnasio. Actualiza la lista.'; end if;
 delete from private.license_sessions where user_id=u.id;
 delete from private.activation_invites where gym_id=p_gym_id and email=p_email and used_at is null;
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),'email_assigned',
 jsonb_build_object('email',p_email,'user_id',u.id,'before_role',member.role,'role',p_role,'reason',trim(p_reason)));
 return jsonb_build_object('state','assigned','email',p_email,'role',p_role);
end $$;

create or replace function private.owner_editor_rows(p_gym_id uuid,p_table text,p_search text default '',p_offset integer default 0,p_limit integer default 50) returns jsonb
language plpgsql security definer set search_path='' as $$
declare fields text[]; cols jsonb; items jsonb; total bigint;
begin
 perform private.require_owner();
 fields:=private.owner_editor_fields(p_table);
 if fields is null then raise exception 'Tabla no disponible en el editor.'; end if;
 if p_offset is null or p_offset<0 or p_limit is null or p_limit not between 1 and 100 or length(coalesce(p_search,''))>120 then raise exception 'Paginación o búsqueda inválida.'; end if;
 select jsonb_agg(jsonb_build_object('name',a.attname,'type',format_type(a.atttypid,a.atttypmod),'nullable',not a.attnotnull,'editable',a.attname=any(fields)) order by a.attnum)
 into cols from pg_catalog.pg_attribute a where a.attrelid=format('public.%I',p_table)::regclass and a.attnum>0 and not a.attisdropped;
 execute format('select count(*) from public.%I r where gym_id=$1 and ($2='''' or strpos(lower(to_jsonb(r)::text),lower($2))>0)',p_table)
 into total using p_gym_id,coalesce(p_search,'');
 execute format('select coalesce(jsonb_agg(jsonb_build_object(''data'',to_jsonb(r),''version'',md5(to_jsonb(r)::text)) order by r.id desc),''[]'') from (select * from public.%I x where gym_id=$1 and ($2='''' or strpos(lower(to_jsonb(x)::text),lower($2))>0) order by id desc offset $3 limit $4) r',p_table)
 into items using p_gym_id,coalesce(p_search,''),p_offset,p_limit;
 return jsonb_build_object('table',p_table,'columns',cols,'rows',items,'total',total);
end $$;

create or replace function private.owner_editor_record(p_gym_id uuid,p_table text,p_id bigint,p_expected text,p_patch jsonb,p_reason text,p_delete boolean default false) returns jsonb
language plpgsql security definer set search_path='' as $$
declare fields text[]; before_row jsonb; after_row jsonb; merged jsonb; assignments text; k text; parent record; col text; dependent bigint;
 delta integer; available integer;
begin
 perform private.owner_editor_lock(p_gym_id,coalesce(p_reason,''));
 fields:=private.owner_editor_fields(p_table);
 if fields is null or cardinality(fields)=0 then raise exception 'Esta tabla es de consulta; no permite editar ni borrar el historial.'; end if;
 execute format('select to_jsonb(r) from public.%I r where gym_id=$1 and id=$2 for update',p_table) into before_row using p_gym_id,p_id;
 if before_row is null then raise exception 'El registro no existe en el gimnasio seleccionado.'; end if;
 if p_expected is distinct from md5(before_row::text) then raise exception 'El registro cambió. Actualiza la lista antes de guardar.' using errcode='40001'; end if;
 if p_delete then
  -- También se bloquean FK con cascada para no borrar hijos inadvertidamente.
  for parent in select c.*,c.conrelid::regclass as child from pg_catalog.pg_constraint c
   where c.contype='f' and c.confrelid=format('public.%I',p_table)::regclass loop
   select ca.attname into col from unnest(parent.conkey,parent.confkey) as keys(child_col,parent_col)
   join pg_catalog.pg_attribute ca on ca.attrelid=parent.conrelid and ca.attnum=keys.child_col
   join pg_catalog.pg_attribute pa on pa.attrelid=parent.confrelid and pa.attnum=keys.parent_col where pa.attname='id';
   if col is not null then
    execute format('select count(*) from %s where gym_id=$1 and %I=$2',parent.child,col) into dependent using p_gym_id,p_id;
    if dependent>0 then raise exception 'Este registro tiene % registros relacionados en %. Elimina primero esas dependencias o desactiva el registro.',dependent,parent.child; end if;
   end if;
  end loop;
  if p_table='store_sales' then
   update public.store_products set stock_quantity=stock_quantity+(before_row->>'quantity')::integer,updated_by=auth.uid(),updated_at=now()
   where gym_id=p_gym_id and id=(before_row->>'product_id')::bigint;
  end if;
  execute format('delete from public.%I where gym_id=$1 and id=$2',p_table) using p_gym_id,p_id;
 else
  if jsonb_typeof(p_patch) is distinct from 'object' or p_patch='{}'::jsonb or octet_length(p_patch::text)>100000 then raise exception 'Envía los campos que deseas cambiar.'; end if;
  for k in select jsonb_object_keys(p_patch) loop
   if not k=any(fields) then raise exception 'No se permite modificar el campo %.',k; end if;
  end loop;
  merged:=before_row||p_patch;
  if p_table='classes' then
   if coalesce(merged->>'status','') not in ('PROGRAMADA','CANCELADA','COMPLETADA') then raise exception 'Estado de clase inválido.'; end if;
   if (merged->>'capacity')::integer<(select count(*) from public.reservations where gym_id=p_gym_id and class_id=p_id and status='RESERVADA') then
    raise exception 'El cupo no puede ser menor al número de reservas activas.';
   end if;
  elsif p_table='reservations' then
   if coalesce(merged->>'status','') not in ('RESERVADA','CANCELADA') then raise exception 'Estado de reserva inválido.'; end if;
   if merged->>'status'='RESERVADA' and before_row->>'status'<>'RESERVADA' and
    (select count(*) from public.reservations where gym_id=p_gym_id and class_id=(before_row->>'class_id')::bigint and status='RESERVADA') >=
    (select capacity from public.classes where gym_id=p_gym_id and id=(before_row->>'class_id')::bigint) then raise exception 'La clase no tiene cupos disponibles.'; end if;
  end if;
  if p_table='clients' then
   merged:=merged||jsonb_build_object('full_name',trim(coalesce(merged->>'first_name','')||' '||coalesce(merged->>'last_name','')),'birthdate',merged->'birth_date','updated_at',now());
   fields:=fields||array['full_name','birthdate','updated_at'];
   if length(trim(coalesce(merged->>'document','')))=0 or length(trim(coalesce(merged->>'first_name','')))=0 then raise exception 'Documento y nombre son obligatorios.'; end if;
  elsif p_table='trainers' then merged:=merged||jsonb_build_object('full_name',merged->>'name'); fields:=fields||array['full_name'];
  elsif p_table='memberships' then
   merged:=merged||jsonb_build_object('amount_paid',case when merged->>'payment_status'='void' then 0 else (merged->>'amount')::bigint end,
     'payment_revision',(before_row->>'payment_revision')::bigint+1,'payment_changed_at',now(),'payment_changed_by',auth.uid(),'payment_change_reason',trim(p_reason));
   fields:=fields||array['amount_paid','payment_revision','payment_changed_at','payment_changed_by','payment_change_reason'];
  elsif p_table='store_sales' then
   delta:=(merged->>'quantity')::integer-(before_row->>'quantity')::integer;
   select stock_quantity into available from public.store_products where gym_id=p_gym_id and id=(before_row->>'product_id')::bigint for update;
   if delta>available then raise exception 'No hay existencias suficientes para aumentar esta venta.'; end if;
   update public.store_products set stock_quantity=stock_quantity-delta,updated_by=auth.uid(),updated_at=now() where gym_id=p_gym_id and id=(before_row->>'product_id')::bigint;
   merged:=merged||jsonb_build_object('total_amount',(merged->>'quantity')::bigint*(merged->>'unit_price')::bigint); fields:=fields||array['total_amount'];
  elsif p_table='store_products' then
   merged:=merged||jsonb_build_object('updated_by',auth.uid(),'updated_at',now()); fields:=fields||array['updated_by','updated_at'];
  elsif p_table='accounting_expenses' then merged:=merged||jsonb_build_object('updated_at',now()); fields:=fields||array['updated_at'];
  end if;
  select string_agg(format('%1$I=r.%1$I',f),',') into assignments from unnest(fields) f;
  execute format('update public.%1$I t set %2$s from jsonb_populate_record(null::public.%1$I,$3) r where t.gym_id=$1 and t.id=$2 returning to_jsonb(t)',p_table,assignments)
  into after_row using p_gym_id,p_id,merged;
 end if;
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),case when p_delete then 'record_deleted' else 'record_edited' end,
 jsonb_build_object('table',p_table,'id',p_id,'reason',trim(p_reason),'before',before_row,'after',after_row));
 return jsonb_build_object('deleted',coalesce(p_delete,false),'data',after_row,'version',md5(after_row::text));
end $$;

-- Borrar en orden de dependencias, con los disparadores y la auditoría activos.
create or replace function private.owner_editor_clear(p_gym_id uuid) returns void
language plpgsql security definer set search_path='' as $$
declare t text;
begin
 perform private.require_owner();
 foreach t in array array['marketing_messages','reservations','checkins','exercises','staff_shifts','store_sales','accounting_expenses','memberships','routines','classes','store_products','trainers','plans','clients','marketing_settings','gym_branding'] loop
  execute format('delete from public.%I where gym_id=$1',t) using p_gym_id;
 end loop;
end $$;

create or replace function private.owner_editor_confirm(p_gym_id uuid,p_name text,p_expected text,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare snapshot jsonb;
begin
 perform private.owner_editor_lock(p_gym_id,coalesce(p_reason,''));
 if (select name from public.gyms where id=p_gym_id) is distinct from p_name then raise exception 'Escribe exactamente el nombre del gimnasio de destino.'; end if;
 if (select status from private.subscriptions where gym_id=p_gym_id) not in ('suspended','cancelled') then
  raise exception 'Suspende o cancela primero este gimnasio para detener las escrituras de sus equipos.';
 end if;
 snapshot:=private.owner_editor_snapshot(p_gym_id);
 if snapshot->>'fingerprint' is distinct from p_expected then raise exception 'Los datos cambiaron desde el respaldo. Descarga una copia nueva y revisa otra vez.' using errcode='40001'; end if;
 return snapshot;
end $$;

create or replace function private.owner_editor_delete_gym(p_gym_id uuid,p_name text,p_expected text,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare snapshot jsonb; t text;
begin
 snapshot:=private.owner_editor_confirm(p_gym_id,p_name,p_expected,p_reason);
 perform private.owner_editor_clear(p_gym_id);
 delete from private.license_sessions where gym_id=p_gym_id;
 delete from private.license_devices where gym_id=p_gym_id;
 delete from private.activation_invites where gym_id=p_gym_id;
 delete from private.subscription_payments where gym_id=p_gym_id;
 delete from private.subscriptions where gym_id=p_gym_id;
 delete from public.staff_invites where gym_id=p_gym_id;
 delete from public.gym_users where gym_id=p_gym_id;
 -- Quita también el historial y los eventos que produjeron los DELETE.
 delete from private.owner_events where gym_id=p_gym_id;
 delete from public.audit_logs where gym_id=p_gym_id;
 delete from public.gym_events where gym_id=p_gym_id;
 delete from public.gyms where id=p_gym_id;
 -- Auth es identidad global: sus cuentas quedan sin gimnasio ni permiso.
 -- No se borran identidades globales ni información de otros gimnasios.
 return jsonb_build_object('deleted',true,'gym_id',p_gym_id,'counts',snapshot->'counts');
end $$;

-- La importación acepta respaldos de Gym soft, NO SQL ejecutable. Los IDs
-- originales sólo se usan para reconstruir relaciones dentro del destino.
create or replace function private.owner_editor_validate_import(p_data jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare tables jsonb; t text; row_data jsonb; k text; src uuid; total integer:=0; counts jsonb:='{}'; ids jsonb:='{}';
begin
 perform private.require_owner();
 if coalesce(p_data->>'format','') not in ('GymSoft-CLOUD-1','GymSoft-CLOUD-2') or jsonb_typeof(p_data->'tables') is distinct from 'object' then
  raise exception 'Selecciona un respaldo JSON GymSoft-CLOUD-1 o GymSoft-CLOUD-2.';
 end if;
 if octet_length(p_data::text)>20971520 then raise exception 'Esta importación admite hasta 20 MB. Divide o migra los respaldos mayores con soporte.'; end if;
 src:=(p_data->>'gym_id')::uuid;
 if src is null then raise exception 'El respaldo no identifica su gimnasio de origen.'; end if;
 tables:=p_data->'tables';
 foreach t in array array['clients','plans','memberships','checkins','trainers','staff_shifts','routines','exercises','classes','reservations','store_products','store_sales','accounting_expenses','marketing_messages'] loop
  if not tables ? t then raise exception 'El respaldo está incompleto: falta la tabla %.',t; end if;
 end loop;
 for t in select jsonb_object_keys(tables) loop
  if private.owner_editor_fields(t) is null and t not in ('marketing_settings','gym_branding') then raise exception 'Tabla desconocida en el respaldo: %.',t; end if;
  if jsonb_typeof(tables->t) is distinct from 'array' then raise exception 'La tabla % debe ser una lista.',t; end if;
  counts:=counts||jsonb_build_object(t,jsonb_array_length(tables->t)); total:=total+jsonb_array_length(tables->t);
  if t in ('marketing_settings','gym_branding') and jsonb_array_length(tables->t)>1 then raise exception 'Configuración duplicada en %.',t; end if;
  for row_data in select value from jsonb_array_elements(tables->t) loop
   if jsonb_typeof(row_data) is distinct from 'object' or row_data->>'gym_id' is distinct from src::text then raise exception 'El respaldo mezcla gimnasios o tiene filas inválidas en %.',t; end if;
   for k in select jsonb_object_keys(row_data) loop
    if not exists(select 1 from pg_catalog.pg_attribute a where a.attrelid=format('public.%I',t)::regclass and a.attnum>0 and not a.attisdropped and a.attname=k) then raise exception 'Columna desconocida %.%.',t,k; end if;
   end loop;
   if t not in ('marketing_settings','gym_branding') then
    if coalesce(row_data->>'id','') !~ '^[1-9][0-9]*$' or ids ? (t||':'||(row_data->>'id')) then raise exception 'ID inválido o duplicado en %.',t; end if;
    ids:=ids||jsonb_build_object(t||':'||(row_data->>'id'),true);
   end if;
  end loop;
 end loop;
 if total>25000 then raise exception 'Esta importación admite hasta 25.000 filas por operación.'; end if;
 return jsonb_build_object('source_gym_id',src,'source_name',coalesce(p_data#>>'{gym,name}','Copia anterior'),'counts',counts,'total',total);
end $$;

create or replace function private.owner_editor_import(p_gym_id uuid,p_data jsonb,p_name text,p_expected text,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare snapshot jsonb; preview jsonb; tables jsonb; t text; row_data jsonb; old_id text; new_id bigint;
 mappings jsonb:='{}'; rel record; col text; ref_id text; new_ref text; cols text; vals text; changed integer:=0;
begin
 preview:=private.owner_editor_validate_import(p_data);
 snapshot:=private.owner_editor_confirm(p_gym_id,p_name,p_expected,p_reason);
 tables:=p_data->'tables';
 perform private.owner_editor_clear(p_gym_id);
 foreach t in array array['clients','plans','trainers','store_products','memberships','classes','routines','checkins','staff_shifts','store_sales','exercises','reservations','accounting_expenses','marketing_messages'] loop
  for row_data in select value from jsonb_array_elements(tables->t) loop
   old_id:=row_data->>'id';
   for rel in select c.*,ct.relname as parent from pg_catalog.pg_constraint c
    join pg_catalog.pg_class ct on ct.oid=c.confrelid
    where c.contype='f' and c.conrelid=format('public.%I',t)::regclass and
    exists(select 1 from pg_catalog.pg_attribute a where a.attrelid=c.confrelid and a.attname='gym_id') loop
    select ca.attname into col from unnest(rel.conkey,rel.confkey) as keys(child_col,parent_col)
    join pg_catalog.pg_attribute ca on ca.attrelid=rel.conrelid and ca.attnum=keys.child_col
    join pg_catalog.pg_attribute pa on pa.attrelid=rel.confrelid and pa.attnum=keys.parent_col where pa.attname='id';
    ref_id:=row_data->>col;
    if ref_id is not null then
     new_ref:=mappings->>(rel.parent||':'||ref_id);
     if new_ref is null then raise exception 'Relación incompleta: %.% referencia % inexistente.',t,col,ref_id; end if;
     row_data:=row_data||jsonb_build_object(col,new_ref::bigint);
    end if;
   end loop;
   row_data:=(row_data-'id'-'gym_id');
   -- La identidad del autor procede de la sesión, nunca de un archivo.
   for col in select a.attname from pg_catalog.pg_attribute a where a.attrelid=format('public.%I',t)::regclass
    and a.attname in ('recorded_by','created_by','updated_by','sold_by','payment_changed_by','whatsapp_opt_in_by') loop
    row_data:=row_data||jsonb_build_object(col,auth.uid());
   end loop;
   if t='marketing_messages' and row_data->>'status' in ('PENDING','PROCESSING','FAILED') then
    row_data:=row_data||jsonb_build_object('status','SKIPPED','error_message','Importado: no reenviar automáticamente.');
   end if;
   new_id:=private.gymsoft_import_insert(t,p_gym_id,row_data);
   mappings:=mappings||jsonb_build_object(t||':'||old_id,new_id); changed:=changed+1;
  end loop;
 end loop;
 foreach t in array array['marketing_settings','gym_branding'] loop
  for row_data in select value from jsonb_array_elements(coalesce(tables->t,'[]')) loop
   row_data:=(row_data-'gym_id')||jsonb_build_object('gym_id',p_gym_id,'updated_at',now());
   if t='marketing_settings' then
    row_data:=row_data||jsonb_build_object('whatsapp_enabled',false,'updated_by',auth.uid(),'last_worker_at',null,'last_error','');
    if p_data->>'gym_id'<>p_gym_id::text then row_data:=row_data||jsonb_build_object('waba_id','','phone_number_id',''); end if;
   end if;
   select string_agg(format('%I',a.attname),','),string_agg(format('r.%I',a.attname),',') into cols,vals
   from pg_catalog.pg_attribute a where a.attrelid=format('public.%I',t)::regclass and a.attnum>0 and not a.attisdropped and row_data?a.attname;
   execute format('insert into public.%1$I(%2$s) select %3$s from jsonb_populate_record(null::public.%1$I,$1) r',t,cols,vals) using row_data;
  end loop;
 end loop;
 insert into private.owner_events(gym_id,actor,action,detail) values(p_gym_id,auth.uid(),'database_imported',
 jsonb_build_object('source_gym_id',p_data->>'gym_id','rows',changed,'reason',trim(p_reason),'before_counts',snapshot->'counts','import_counts',preview->'counts'));
 return jsonb_build_object('imported',changed,'gym_id',p_gym_id,'marketing_paused',true);
end $$;

-- Implementación privilegiada privada, API pública de alcance explícito.
create or replace function public.commercial_system_info() returns jsonb
language sql stable set search_path='' as $$
 select jsonb_build_object('product','gymsoft-commercial','schema_version','3.0.0','owner_editor_version','3.1.0')
$$;
do $$ declare r record; args text; ident text; call_args text; begin
 for r in select p.* from pg_catalog.pg_proc p join pg_catalog.pg_namespace n on n.oid=p.pronamespace
 where n.nspname='private' and p.proname in ('owner_editor_backup','owner_editor_profile','owner_editor_email','owner_editor_access','owner_editor_revoke_invite','owner_editor_rows','owner_editor_record','owner_editor_delete_gym','owner_editor_validate_import','owner_editor_import') loop
  args:=pg_get_function_arguments(r.oid); ident:=pg_get_function_identity_arguments(r.oid);
  select string_agg('$'||i,',') into call_args from generate_series(1,r.pronargs) i;
  execute format('create or replace function public.%I(%s) returns jsonb language sql security invoker set search_path='''' as %L',r.proname,args,format('select private.%I(%s)',r.proname,call_args));
  execute format('revoke all on function public.%I(%s) from public,anon,authenticated',r.proname,ident);
  execute format('grant execute on function public.%I(%s) to authenticated',r.proname,ident);
 end loop;
 -- Revocar también helpers que no deben invocarse fuera de estos RPC.
 for r in select p.oid from pg_catalog.pg_proc p join pg_catalog.pg_namespace n on n.oid=p.pronamespace where n.nspname='private' and p.proname like 'owner_editor_%' loop
  execute format('revoke all on function %s from public,anon,authenticated',r.oid::regprocedure);
 end loop;
 for r in select p.oid from pg_catalog.pg_proc p join pg_catalog.pg_namespace n on n.oid=p.pronamespace where n.nspname='private' and p.proname in ('owner_editor_backup','owner_editor_profile','owner_editor_email','owner_editor_access','owner_editor_revoke_invite','owner_editor_rows','owner_editor_record','owner_editor_delete_gym','owner_editor_validate_import','owner_editor_import') loop
  execute format('grant execute on function %s to authenticated',r.oid::regprocedure);
 end loop;
end $$;
notify pgrst,'reload schema';
commit;
