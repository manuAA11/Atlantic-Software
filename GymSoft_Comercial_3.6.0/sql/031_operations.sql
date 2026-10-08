-- Compatibilidad biométrica y operaciones atómicas.
create function private.current_timezone() returns text
language sql stable security definer set search_path='' as $$
 select coalesce((select g.timezone from public.gyms g join public.gym_users u on u.gym_id=g.id where u.user_id=auth.uid()),'America/Bogota')
$$;
do $$ declare r record; def text; begin
 for r in select p.oid from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in ('public','private') and p.prokind='f'
 and p.proname not like 'owner_%' and p.proname not like 'commercial_%'
 and p.proname not in ('current_timezone','gymsoft_today') and p.prosrc like '%America/Bogota%' loop
  def:=pg_get_functiondef(r.oid);
  def:=replace(def,'''America/Bogota''','private.current_timezone()');
  execute def;
 end loop;
end $$;

create function public.commercial_system_info() returns jsonb
language sql immutable set search_path='' as $$
 select jsonb_build_object('product','gymsoft-commercial','schema_version','3.0.0')
$$;

do $$ declare def text; begin
 def:=pg_get_functiondef('private.membership_snapshot_json(uuid,bigint)'::regprocedure);
 def:=replace(def,'        c.active','        c.biometric_identifier, c.active');
 def:=replace(def,'''id'', v_client.id,','''id'', v_client.id, ''biometric_identifier'', v_client.biometric_identifier,');
 execute def;
 def:=pg_get_functiondef('public.reception_list_clients(uuid,text)'::regprocedure);
 def:=replace(def,'or c.document ilike','or c.biometric_identifier = trim(p_search) or c.document ilike');
 execute def;
end $$;
create function public.reception_find_client_by_biometric(p_gym_id uuid,p_biometric_identifier text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare cid bigint;
begin
 if not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then raise exception 'Sin permiso.' using errcode='42501'; end if;
 select id into cid from public.clients where gym_id=p_gym_id and biometric_identifier=trim(p_biometric_identifier) limit 1;
 if cid is null then return null; end if;
 return private.membership_snapshot_json(p_gym_id,cid);
end $$;

create function public.reception_save_client(p_gym_id uuid,p_client_id bigint,p_document text,p_first_name text,
 p_last_name text,p_phone text,p_email text,p_birthdate date,p_biometric_identifier text) returns bigint
language plpgsql security definer set search_path='' as $$
declare cid bigint;
begin
 if not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then raise exception 'Sin permiso.' using errcode='42501'; end if;
 cid:=public.reception_save_client(p_gym_id,p_client_id,p_document,p_first_name,p_last_name,p_phone,p_email,p_birthdate);
 update public.clients set biometric_identifier=trim(coalesce(p_biometric_identifier,'')) where gym_id=p_gym_id and id=cid;
 return cid;
end $$;

create function public.admin_register_checkin(p_gym_id uuid,p_client_id bigint,p_method text,p_override boolean default false) returns jsonb
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

-- Una membresía anulada tampoco debe desplazar el inicio de una compra nueva.
do $$ declare def text; begin
 def:=pg_get_functiondef('public.add_membership_accumulating_internal(uuid,bigint,bigint,date,bigint,text,text,text)'::regprocedure);
 def:=replace(def,'where m.gym_id = p_gym_id', 'where m.gym_id = p_gym_id AND m.payment_status = ''posted''');
 execute def;
end $$;

-- Conserva el plazo de las invitaciones de recepción y añade control de cupo.
alter table public.staff_invites alter column expires_at set default (now()+interval '6 months');
create or replace function public.redeem_reception_invite(p_code uuid) returns uuid
language plpgsql security definer set search_path='' as $$
declare inv public.staff_invites%rowtype; s private.subscriptions%rowtype;
begin
 if not exists(select 1 from auth.users where id=auth.uid() and email_confirmed_at is not null)
 or exists(select 1 from public.gym_users where user_id=auth.uid()) then raise exception 'Cuenta no disponible para esta invitación.' using errcode='42501'; end if;
 select * into inv from public.staff_invites where code=p_code and used_at is null and expires_at>now() for update;
 if not found then raise exception 'Invitación inválida o vencida.' using errcode='42501'; end if;
 select * into s from private.subscriptions where gym_id=inv.gym_id for update;
 if not private.subscription_open(inv.gym_id) or (select count(*) from public.gym_users where gym_id=inv.gym_id and enabled)>=s.max_users then
  raise exception 'Suscripción inactiva o límite de usuarios alcanzado.' using errcode='42501';
 end if;
 insert into public.gym_users(gym_id,user_id,role) values(inv.gym_id,auth.uid(),'receptionist');
 update public.staff_invites set used_at=now(),used_by=auth.uid() where id=inv.id;
 insert into private.owner_events(gym_id,actor,action) values(inv.gym_id,auth.uid(),'reception_joined');
 return inv.gym_id;
end $$;
create or replace function public.reception_account_context() returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare ctx jsonb;
begin
 ctx:=public.commercial_context();
 if ctx='{}'::jsonb then raise exception 'La cuenta aún no tiene gimnasio.'; end if;
 return ctx;
end $$;

create function public.commercial_accept_invite(p_code text) returns jsonb
language plpgsql security definer set search_path='' as $$
begin
 if exists(select 1 from private.activation_invites where code_hash=private.code_hash(p_code)) then
  return public.commercial_redeem_invite(p_code);
 end if;
 begin
  perform public.redeem_reception_invite(trim(p_code)::uuid);
 exception when invalid_text_representation then
  raise exception 'Invitación inválida.' using errcode='42501';
 end;
 return public.commercial_context();
end $$;

create function public.owner_backup_gym(p_gym_id uuid) returns jsonb
language plpgsql security definer set search_path='' as $$
declare t text; rows jsonb; tables jsonb:='{}';
begin
 perform private.require_owner();
 if not exists(select 1 from public.gyms where id=p_gym_id) then raise exception 'Gimnasio inexistente.'; end if;
 foreach t in array array['clients','plans','memberships','checkins','trainers','staff_shifts','routines','exercises','classes','reservations',
 'store_products','store_sales','accounting_expenses','marketing_settings','marketing_messages','gym_branding','audit_logs'] loop
  execute format('select coalesce(jsonb_agg(to_jsonb(r)),''[]''::jsonb) from public.%I r where gym_id=$1',t) into rows using p_gym_id;
  tables:=tables||jsonb_build_object(t,rows);
 end loop;
 insert into private.owner_events(gym_id,actor,action) values(p_gym_id,auth.uid(),'backup_exported');
 return jsonb_build_object('format','GymSoft-CLOUD-1','gym_id',p_gym_id,'created_at',now(),'tables',tables);
end $$;
