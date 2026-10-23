-- Keep distinct installer variants even when product/version/architecture match.
begin;
alter table private.core_gyms add column if not exists product_variant text not null default 'commercial' check(product_variant in ('ztattuz','commercial'));
alter table private.core_releases add column if not exists product_variant text not null default 'commercial' check(product_variant in ('ztattuz','commercial'));
update private.core_gyms g set product_variant=case when s.context_rpc='reception_account_context' then 'ztattuz' else 'commercial' end
from private.core_sources s where s.project_ref=g.source_project_ref and g.product_variant is distinct from case when s.context_rpc='reception_account_context' then 'ztattuz' else 'commercial' end;
drop index if exists private.core_release_global;
drop index if exists private.core_release_gym;
create unique index core_release_global on private.core_releases(product,product_variant,version,architecture,channel) where gym_id is null;
create unique index core_release_gym on private.core_releases(gym_id,product,product_variant,version,architecture,channel) where gym_id is not null;
create or replace function public.core_owner(p_action text,p_data jsonb default '{}') returns jsonb
language plpgsql security definer set search_path='' as $$
declare g uuid; result jsonb; sub private.core_subscriptions%rowtype; payment private.core_payments%rowtype;
 start_day date; end_day date; idempotency uuid; cfg jsonb; item jsonb;
begin
 perform private.require_owner();
 if octet_length(p_data::text)>50000 then raise exception 'Solicitud demasiado grande.'; end if;
 g:=nullif(p_data->>'gym_id','')::uuid;
 if g is not null and p_action<>'register_gym' and not exists(select 1 from private.core_gyms where gym_id=g) then raise exception 'Gimnasio no registrado.'; end if;
 if p_action='register_source' then
  if not (p_data->>'publishable_key' like 'sb_publishable_%') then raise exception 'Usa una clave publicable moderna, nunca una clave secreta.'; end if;
  insert into private.core_sources(project_ref,publishable_key,context_rpc)
   values(p_data->>'project_ref',p_data->>'publishable_key',p_data->>'context_rpc')
   on conflict(project_ref) do update set publishable_key=excluded.publishable_key,context_rpc=excluded.context_rpc;
 elsif p_action='list' then
  return coalesce((select jsonb_agg(to_jsonb(t) order by t.name) from (
   select x.*,s.id subscription_id,s.status subscription_status,s.price,s.currency,s.renewal_day,s.next_renewal_date,
    (select max(p.paid_at) from private.core_payments p where p.gym_id=x.gym_id) last_payment,
    (select count(*) from private.core_devices d where d.gym_id=x.gym_id) devices
   from private.core_gyms x join private.core_subscriptions s using(gym_id)) t),'[]');
 elsif p_action='register_gym' then
  if g is null or nullif(p_data->>'source_gym_id','') is null or g<>nullif(p_data->>'source_gym_id','')::uuid then raise exception 'Conserva el UUID del gimnasio origen.'; end if;
  if not exists(select 1 from private.core_sources where project_ref=p_data->>'source_project_ref') then raise exception 'Registra primero el servidor de origen.'; end if;
  insert into private.core_gyms(gym_id,source_gym_id,source_project_ref,name,product_variant)
   values(g,g,p_data->>'source_project_ref',trim(p_data->>'name'),(select case when context_rpc='reception_account_context' then 'ztattuz' else 'commercial' end from private.core_sources where project_ref=p_data->>'source_project_ref'));
  insert into private.core_subscriptions(gym_id,price,renewal_day,next_renewal_date)
   values(g,(p_data->>'price')::numeric,(p_data->>'renewal_day')::int,(p_data->>'next_renewal_date')::date);
  insert into private.core_reminders(gym_id) values(g);
 elsif p_action='detail' then
  if not exists(select 1 from private.core_gyms where gym_id=g) then raise exception 'Gimnasio no registrado.'; end if;
  return jsonb_build_object('gym',(select to_jsonb(x) from private.core_gyms x where gym_id=g),
   'subscription',(select to_jsonb(x) from private.core_subscriptions x where gym_id=g),
   'payments',coalesce((select jsonb_agg(to_jsonb(x) order by paid_at desc) from private.core_payments x where gym_id=g),'[]'),
   'devices',coalesce((select jsonb_agg(to_jsonb(x) order by last_seen desc) from private.core_devices x where gym_id=g),'[]'),
   'reminders',(select to_jsonb(x) from private.core_reminders x where gym_id=g),
   'notifications',coalesce((select jsonb_agg(to_jsonb(x) order by created_at desc) from private.core_notifications x where gym_id=g or global),'[]'));
 elsif p_action='record_payment' then
  select * into strict sub from private.core_subscriptions where gym_id=g for update;
  idempotency:=(p_data->>'idempotency_key')::uuid;
  select * into payment from private.core_payments where gym_id=g and idempotency_key=idempotency;
  if found then
   if payment.amount<>(p_data->>'amount')::numeric or payment.period_start<>(p_data->>'period_start')::date
    or payment.payment_method is distinct from p_data->>'payment_method' or payment.reference<>coalesce(p_data->>'reference','')
    or payment.currency is distinct from coalesce(p_data->>'currency','COP') or payment.paid_at is distinct from (p_data->>'paid_at')::timestamptz
    or payment.notes<>coalesce(p_data->>'notes','') then
    raise exception 'La misma clave corresponde a otro pago.' using errcode='23505';
   end if;
   return to_jsonb(payment);
  end if;
  start_day:=(p_data->>'period_start')::date; end_day:=(start_day+interval '1 month')::date;
  if extract(day from start_day)<>sub.renewal_day or (p_data->>'amount')::numeric is distinct from sub.price
   or coalesce(p_data->>'currency','COP')<>sub.currency or length(trim(p_data->>'payment_method')) not between 1 and 80
   or (p_data->>'paid_at')::timestamptz>now()+interval '1 day' then raise exception 'Revisa monto, período y fecha reales del pago.'; end if;
  insert into private.core_payments(subscription_id,gym_id,amount,currency,period_start,period_until,due_date,paid_at,
   payment_method,reference,notes,created_by,idempotency_key)
  values(sub.id,g,sub.price,sub.currency,start_day,end_day,start_day,(p_data->>'paid_at')::timestamptz,
   trim(p_data->>'payment_method'),coalesce(p_data->>'reference',''),coalesce(p_data->>'notes',''),auth.uid(),idempotency)
  returning * into payment;
  update private.core_subscriptions set status='ACTIVE',next_renewal_date=greatest(next_renewal_date,end_day),updated_at=now() where gym_id=g;
  -- A recorded payment does not undo an explicit security/license suspension.
  result:=to_jsonb(payment);
 elsif p_action='set_status' then
  if length(trim(coalesce(p_data->>'reason','')))<5 then raise exception 'Escribe un motivo.'; end if;
  update private.core_gyms set status=p_data->>'status',license_status=p_data->>'license_status',updated_at=now() where gym_id=g;
 elsif p_action='configure' then
  cfg:=p_data->'configuration';
  if jsonb_typeof(cfg)<>'object' or exists(select 1 from jsonb_object_keys(cfg) k where k not in
    ('update_channel','notifications_enabled','automatic_door_enabled','store_enabled','whatsapp_enabled')) then raise exception 'Configuración no permitida.'; end if;
  for item in select jsonb_build_object('key',key,'value',value) from jsonb_each(cfg) loop
   if item->>'key'='update_channel' then
    if item->>'value' not in ('stable','beta') then raise exception 'Canal no permitido.'; end if;
   elsif jsonb_typeof(item->'value')<>'boolean' then raise exception 'La opción requiere true/false.'; end if;
  end loop;
  update private.core_gyms set configuration=configuration||cfg,updated_at=now() where gym_id=g;
 elsif p_action='reminders' then
  update private.core_reminders set enabled=(p_data->>'enabled')::boolean,
   offsets_days=array(select jsonb_array_elements_text(p_data->'offsets_days')::int),updated_at=now() where gym_id=g;
 elsif p_action='notify' then
  insert into private.core_notifications(gym_id,global,title,message,type,expires_at,created_by)
   values(g,coalesce((p_data->>'global')::boolean,false),p_data->>'title',p_data->>'message',p_data->>'type',
    nullif(p_data->>'expires_at','')::timestamptz,auth.uid()) returning to_jsonb(core_notifications.*) into result;
 elsif p_action='device_status' then
  update private.core_devices set status=p_data->>'status' where gym_id=g and device_id=p_data->>'device_id';
 elsif p_action='publish_release' then
  insert into private.core_releases(gym_id,product_variant,version,architecture,channel,policy,installer_url,sha256,bytes,minimum_schema,notes,signature_metadata,published,created_by)
   values(g,p_data->>'variant',p_data->>'version',p_data->>'architecture',p_data->>'channel',coalesce(p_data->>'policy','OPTIONAL'),
    p_data->>'installer_url',p_data->>'sha256',(p_data->>'bytes')::bigint,p_data->>'minimum_schema',coalesce(p_data->>'notes',''),
    coalesce(p_data->'signature_metadata','{}'),coalesce((p_data->>'published')::boolean,false),auth.uid())
   returning to_jsonb(core_releases.*) into result;
 else raise exception 'Acción de Core no permitida.'; end if;
 insert into private.core_events(gym_id,actor,action) values(g,auth.uid(),p_action);
 return coalesce(result,jsonb_build_object('ok',true));
end $$;
create or replace function public.core_client_snapshot(p_project_ref text,p_gym_id uuid,p_user_id uuid,
 p_device_id text,p_metadata jsonb,p_read_id uuid default null) returns jsonb
language plpgsql security definer set search_path='' as $$
declare gym private.core_gyms%rowtype; clean jsonb; device_state text; arch text;
begin
 select * into strict gym from private.core_gyms where gym_id=p_gym_id and source_project_ref=p_project_ref;
 if p_user_id is null then raise exception 'Identidad requerida.'; end if;
 arch:=p_metadata->>'architecture';
 select coalesce(jsonb_object_agg(key,value),'{}') into clean from jsonb_each(p_metadata)
 where key in ('sync_status','last_successful_login','update_status','relay_configured','fingerprint_configured');
 if jsonb_typeof(clean->'relay_configured') not in ('boolean') or jsonb_typeof(clean->'fingerprint_configured') not in ('boolean') then raise exception 'Estado de hardware inválido.'; end if;
 if clean ? 'last_successful_login' then perform (clean->>'last_successful_login')::timestamptz; end if;
 if clean ? 'sync_status' and clean->>'sync_status' not in ('SYNCED','OFFLINE','DEGRADED','UNKNOWN') then raise exception 'Estado de sync inválido.'; end if;
 if clean ? 'update_status' and clean->>'update_status' not in ('NO_UPDATE','UPDATE_AVAILABLE','UPDATE_DOWNLOADED','UPDATE_VERIFIED','UPDATE_INSTALLED','UPDATE_FAILED','UPDATE_ROLLED_BACK') then raise exception 'Estado de actualización inválido.'; end if;
 if octet_length(clean::text)>2048 then raise exception 'Telemetría demasiado grande.'; end if;
 insert into private.core_devices(gym_id,device_id,device_name,architecture,os,app_version,edition,metadata)
 values(p_gym_id,p_device_id,p_metadata->>'device_name',arch,p_metadata->>'os',p_metadata->>'app_version',p_metadata->>'edition',clean)
 on conflict(gym_id,device_id) do update set device_name=excluded.device_name,architecture=excluded.architecture,
 os=excluded.os,app_version=excluded.app_version,edition=excluded.edition,metadata=excluded.metadata,last_seen=now()
 returning status into device_state;
 if p_read_id is not null then
  if not exists(select 1 from private.core_notifications n where n.id=p_read_id and (n.gym_id=p_gym_id or n.global)) then raise exception 'Notificación no disponible.'; end if;
  insert into private.core_notification_reads(notification_id,gym_id,user_id) values(p_read_id,p_gym_id,p_user_id) on conflict do nothing;
 end if;
 return jsonb_build_object('product_variant',gym.product_variant,'gym_id',p_gym_id,'status',gym.status,'license_status',gym.license_status,
 'device_status',device_state,'configuration',gym.configuration,'server_time',now(),
 'grace_days',(select grace_days from private.core_subscriptions where gym_id=p_gym_id),
 'subscription',(select jsonb_build_object('status',status,'price',price,'currency',currency,'renewal_day',renewal_day,
 'next_renewal_date',next_renewal_date) from private.core_subscriptions where gym_id=p_gym_id),
 'notifications',coalesce((select jsonb_agg(to_jsonb(n)||jsonb_build_object('read_at',r.read_at) order by n.created_at desc)
 from private.core_notifications n left join private.core_notification_reads r on r.notification_id=n.id and r.gym_id=p_gym_id and r.user_id=p_user_id
 where (n.gym_id=p_gym_id or n.global) and (n.expires_at is null or n.expires_at>now())),'[]'),
 'releases',coalesce((select jsonb_agg(to_jsonb(v)||jsonb_build_object('variant',v.product_variant) order by v.created_at desc) from private.core_releases v
 where v.published and (v.gym_id=p_gym_id or v.gym_id is null) and v.architecture=arch
 and v.product_variant=gym.product_variant and v.channel=coalesce(gym.configuration->>'update_channel','stable')),'[]'));
end $$;
commit;
