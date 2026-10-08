create or replace function private.marketing_audit(p_gym uuid,p_action text,p_entity text,p_id text,p_details jsonb default '{}') returns void language sql security definer set search_path='' as $$
 insert into public.marketing_audit(gym_id,actor_id,action,entity_type,entity_id,details) values(p_gym,auth.uid(),p_action,p_entity,p_id,p_details)
$$;
-- Integration events share the main activity clock and operator identity.
create or replace function private.marketing_audit_to_activity() returns trigger
language plpgsql security definer set search_path='' as $$
declare cid bigint;actor uuid:=new.actor_id;email text;role_name text;label text;begin
 if new.entity_type='client' and new.entity_id ~ '^[0-9]+$' then cid:=new.entity_id::bigint;
 elsif new.entity_type='membership' and new.entity_id ~ '^[0-9]+$' then
 select client_id into cid from public.memberships where gym_id=new.gym_id and id=new.entity_id::bigint;
 elsif new.entity_type='payment_request' then
 select client_id into cid from public.payment_requests where gym_id=new.gym_id and id::text=new.entity_id;
 elsif new.entity_type='conversation' then
 select client_id into cid from public.whatsapp_conversations where gym_id=new.gym_id and id::text=new.entity_id;end if;
 if actor is null and coalesce(new.details->>'responsible_user_id','') ~ '^[a-f0-9-]{36}$' then
 select gu.user_id into actor from public.gym_users gu where gu.gym_id=new.gym_id and gu.user_id::text=new.details->>'responsible_user_id' and gu.role='admin';end if;
 select u.email,gu.role into email,role_name from auth.users u
 left join public.gym_users gu on gu.user_id=u.id and gu.gym_id=new.gym_id where u.id=actor;
 label:=case new.action when 'META_CONNECTED' then 'WhatsApp conectado' when 'META_DISCONNECTED' then 'WhatsApp desconectado'
 when 'WOMPI_CONNECTED' then 'Wompi conectado' when 'WOMPI_DISCONNECTED' then 'Wompi desconectado'
 when 'PAYMENT_PROCESSED' then 'Pago online confirmado' when 'PAYMENT_REQUIRES_REVIEW' then 'Pago online requiere revisión'
 when 'MEMBERSHIP_RENEWED' then 'Membresía renovada online' when 'CHATBOT_VERIFIED' then 'Cliente verificado por chatbot'
 when 'CHATBOT_VERIFICATION_FAILED' then 'Verificación de chatbot fallida' when 'HUMAN_HANDOFF' then 'Chatbot derivado a atención humana'
 when 'HUMAN_MESSAGE' then 'Chatbot pausado por respuesta humana' else initcap(replace(new.action,'_',' ')) end;
 insert into public.audit_logs(gym_id,actor_user_id,actor_email,actor_role,action,entity_type,entity_id,summary,details)
 values(new.gym_id,actor,coalesce(email,'Sistema'),coalesce(role_name,'system'),'MARKETING_'||new.action,
 new.entity_type,new.entity_id,label,new.details||jsonb_build_object('client_id',cid,'integration_audit_id',new.id));
 return new;
end$$;
drop trigger if exists marketing_activity_audit on public.marketing_audit;
create trigger marketing_activity_audit after insert on public.marketing_audit for each row execute function private.marketing_audit_to_activity();
create or replace function private.marketing_message_activity() returns trigger
language plpgsql security definer set search_path='' as $$
declare action text;label text;begin
 if tg_op='UPDATE' and new.status is not distinct from old.status then return new;end if;
 if tg_op='UPDATE' and new.status not in ('SENT','DELIVERED','READ','FAILED','UNCERTAIN','SKIPPED','NO_CONSENT') then return new;end if;
 action:=case when new.direction='HUMAN' then 'HUMAN' when new.direction='IN' then 'RECEIVED' else new.status end;
 label:=case action when 'HUMAN' then 'Respuesta humana por WhatsApp' when 'RECEIVED' then 'Mensaje recibido por WhatsApp'
 when 'QUEUED' then 'Mensaje WhatsApp programado' when 'SENT' then 'Mensaje WhatsApp enviado'
 when 'DELIVERED' then 'Mensaje WhatsApp entregado' when 'READ' then 'Mensaje WhatsApp leído'
 when 'FAILED' then 'Envío WhatsApp fallido' when 'UNCERTAIN' then 'Envío WhatsApp sin confirmación'
 when 'NO_CONSENT' then 'WhatsApp omitido por falta de autorización' when 'SKIPPED' then 'WhatsApp omitido'
 else 'Estado de mensaje WhatsApp actualizado' end;
 insert into public.audit_logs(gym_id,action,entity_type,entity_id,summary,details)
 values(new.gym_id,'MARKETING_MESSAGE_'||action,'marketing_messages',new.id::text,label,
 jsonb_build_object('client_id',new.client_id,'message_id',new.id,'automation_type',new.automation_type,'status',new.status,
 'sent_at',new.sent_at,'delivered_at',new.delivered_at,'read_at',new.read_at));
 return new;
end$$;
drop trigger if exists marketing_message_activity on public.marketing_messages;
create trigger marketing_message_activity after insert or update of status on public.marketing_messages
 for each row execute function private.marketing_message_activity();
create or replace function public.marketing_access(p_gym_id uuid,p_reception boolean default false) returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,case when p_reception then array['admin','receptionist'] else array['admin'] end) then
 raise exception 'No tienes permiso para administrar Marketing en este gimnasio.' using errcode='42501';end if;
 return jsonb_build_object('gym_id',p_gym_id,'user_id',auth.uid(),'admin',private.user_has_gym_role(p_gym_id,array['admin']));end$$;
create or replace function private.marketing_consent() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if (tg_op='INSERT' and new.whatsapp_opt_in) or (tg_op='UPDATE' and new.whatsapp_opt_in is distinct from old.whatsapp_opt_in) then
 new.whatsapp_opt_in_at:=now();new.whatsapp_opt_in_by:=auth.uid();
 new.whatsapp_opt_in_source:=coalesce(nullif(new.whatsapp_opt_in_source,''),'Registro del personal');
 perform private.marketing_audit(new.gym_id,case when new.whatsapp_opt_in then 'CONSENT_GRANTED' else 'CONSENT_REVOKED' end,'client',new.id::text,jsonb_build_object('source',new.whatsapp_opt_in_source));end if;return new;end$$;
create trigger marketing_consent before insert or update of whatsapp_opt_in on public.clients for each row execute function private.marketing_consent();
create or replace function public.marketing_set_consent(p_gym_id uuid,p_client_id bigint,p_enabled boolean,p_source text default 'Registro del personal') returns void language plpgsql security definer set search_path='' as $$
begin perform public.marketing_access(p_gym_id,true);
 update public.clients set whatsapp_opt_in=p_enabled,whatsapp_opt_in_source=left(p_source,160) where gym_id=p_gym_id and id=p_client_id;
 if not found then raise exception 'Cliente no encontrado.';end if;end$$;
create or replace function private.marketing_validate_rule(p_data jsonb) returns void language plpgsql set search_path='' as $$
declare c jsonb;v text;n integer;h integer;begin
 if length(trim(coalesce(p_data->>'name',''))) not between 1 and 120 or length(coalesce(p_data->>'body','')) not between 1 and 4096 then raise exception 'Completa el nombre y el mensaje.';end if;
 if jsonb_typeof(coalesce(p_data->'conditions','[]'))<>'array' or jsonb_array_length(coalesce(p_data->'conditions','[]'))>20 then raise exception 'Condiciones no válidas.';end if;
 for c in select * from jsonb_array_elements(coalesce(p_data->'conditions','[]')) loop
 if coalesce(c->>'field','')<>all(array['plan_id','plan_type','active','status','entries_remaining','days_remaining','days_absent','whatsapp_opt_in','payment_method','payment_pending','client_type']) or
 coalesce(c->>'op','')<>all(array['eq','ne','lt','lte','gt','gte','in']) or not c ? 'value' then raise exception 'Condición no admitida.';end if;end loop;
 n:=coalesce((p_data->'frequency'->>'count')::integer,1);h:=coalesce((p_data->'frequency'->>'hours')::integer,24);
 if n not between 0 and 100 or h not between 1 and 8760 then raise exception 'Frecuencia no válida.';end if;
 n:=coalesce((p_data->'trigger_options'->>'value')::integer,0);
 if n not between 0 and 3650 or (p_data->>'trigger_type' in ('MEMBERSHIP_OVERDUE_REPEAT','EVERY_N_CHECKINS','INACTIVITY') and n=0) then raise exception 'Intervalo no válido.';end if;
 if coalesce(p_data->'trigger_options'->>'time','09:00') !~ '^([01][0-9]|2[0-3]):[0-5][0-9]$' then raise exception 'Hora no válida.';end if;
 for v in select m[1] from regexp_matches(p_data->>'body','\{\{([a-z_]+)\}\}','g') m loop
 if v<>all(array['nombre','apellido','gimnasio','plan','precio','fecha_vencimiento','dias_restantes','entradas_restantes','fecha_ultima_entrada','telefono','link_pago']) then raise exception 'Variable no admitida: %',v;end if;end loop;
end$$;
create or replace function private.marketing_rule_ready(p_gym uuid,p_template uuid,p_link boolean,p_body text) returns void language plpgsql set search_path='' as $$
begin
 if not exists(select 1 from public.marketing_connections where gym_id=p_gym and provider='META' and status='CONNECTED') then raise exception 'Conecta WhatsApp para activar la automatización.';end if;
 if not exists(select 1 from public.whatsapp_templates where gym_id=p_gym and id=p_template and status='APPROVED' and body=p_body) then raise exception 'El mensaje necesita una plantilla aprobada por WhatsApp.';end if;
 if p_link and not exists(select 1 from public.marketing_connections where gym_id=p_gym and provider='WOMPI' and status='CONNECTED') then raise exception 'Para enviar links de renovación primero debes activar los pagos online.';end if;end$$;
create or replace function public.marketing_save_automation(p_gym_id uuid,p_data jsonb,p_id uuid default null,p_revision integer default null) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.marketing_automations;v_enabled boolean:=coalesce((p_data->>'enabled')::boolean,false);v_template uuid:=nullif(p_data->>'template_id','')::uuid;v_link boolean:=coalesce((p_data->>'include_payment_link')::boolean,false);begin
 perform public.marketing_access(p_gym_id);perform private.marketing_validate_rule(p_data);
 if v_enabled then perform private.marketing_rule_ready(p_gym_id,v_template,v_link,p_data->>'body');end if;
 if p_id is null then
 insert into public.marketing_automations(gym_id,name,enabled,trigger_type,trigger_options,conditions,body,include_payment_link,template_id,frequency,created_by)
 values(p_gym_id,trim(p_data->>'name'),v_enabled,p_data->>'trigger_type',coalesce(p_data->'trigger_options','{}'),coalesce(p_data->'conditions','[]'),p_data->>'body',v_link,v_template,coalesce(p_data->'frequency','{"count":1,"hours":24}'),auth.uid()) returning * into r;
 else
 update public.marketing_automations set name=trim(p_data->>'name'),enabled=v_enabled,trigger_type=p_data->>'trigger_type',trigger_options=coalesce(p_data->'trigger_options','{}'),conditions=coalesce(p_data->'conditions','[]'),body=p_data->>'body',include_payment_link=v_link,template_id=v_template,frequency=coalesce(p_data->'frequency','{"count":1,"hours":24}'),revision=revision+1,updated_at=now()
 where id=p_id and gym_id=p_gym_id and revision=p_revision and deleted_at is null returning * into r;
 if not found then raise exception 'La automatización cambió en otro equipo. Actualiza y vuelve a intentarlo.';end if;end if;
 perform private.marketing_audit(p_gym_id,case when p_id is null then 'AUTOMATION_CREATED' else 'AUTOMATION_UPDATED' end,'automation',r.id::text,jsonb_build_object('enabled',r.enabled,'revision',r.revision));return to_jsonb(r);end$$;
create or replace function public.marketing_automation_action(p_gym_id uuid,p_id uuid,p_action text,p_revision integer) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.marketing_automations;begin perform public.marketing_access(p_gym_id);
 select * into r from public.marketing_automations where gym_id=p_gym_id and id=p_id and deleted_at is null for update;
 if not found or r.revision<>p_revision then raise exception 'Actualiza la lista de automatizaciones.';end if;
 if p_action='duplicate' then return public.marketing_save_automation(p_gym_id,to_jsonb(r)||jsonb_build_object('name',left(r.name,110)||' (copia)','enabled',false));end if;
 if p_action not in ('enable','pause','delete') then raise exception 'Acción no válida.';end if;
 if p_action='enable' then perform private.marketing_rule_ready(p_gym_id,r.template_id,r.include_payment_link,r.body);end if;
 update public.marketing_automations set enabled=p_action='enable',deleted_at=case when p_action='delete' then now() else null end,revision=revision+1,updated_at=now() where id=r.id returning * into r;
 perform private.marketing_audit(p_gym_id,'AUTOMATION_'||upper(p_action),'automation',r.id::text);return to_jsonb(r);end$$;
create or replace function public.marketing_save_template(p_gym_id uuid,p_data jsonb,p_id uuid default null) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.whatsapp_templates;begin perform public.marketing_access(p_gym_id);
 if p_id is null then
 insert into public.whatsapp_templates(gym_id,name,language,category,body,variables) values(p_gym_id,p_data->>'name',coalesce(p_data->>'language','es_CO'),coalesce(p_data->>'category','UTILITY'),p_data->>'body',array(select jsonb_array_elements_text(coalesce(p_data->'variables','[]')))) returning * into r;
 else update public.whatsapp_templates set name=p_data->>'name',body=p_data->>'body',category=coalesce(p_data->>'category','UTILITY'),variables=array(select jsonb_array_elements_text(coalesce(p_data->'variables','[]'))),status='DRAFT',updated_at=now() where gym_id=p_gym_id and id=p_id and status in ('DRAFT','REJECTED') returning * into r;
 if not found then raise exception 'Crea otra plantilla para modificar un mensaje que ya está en revisión o aprobado.';end if;end if;
 perform private.marketing_audit(p_gym_id,'TEMPLATE_SAVED','template',r.id::text);return to_jsonb(r);end$$;
create or replace function public.marketing_features(p_gym_id uuid,p_flags jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.marketing_settings;begin perform public.marketing_access(p_gym_id);
 if (coalesce((p_flags->>'whatsapp_enabled')::boolean,false) or coalesce((p_flags->>'chatbot_enabled')::boolean,false) or coalesce((p_flags->>'marketing_automation_enabled')::boolean,false)) and not exists(select 1 from public.marketing_connections where gym_id=p_gym_id and provider='META' and status='CONNECTED') then raise exception 'Conecta WhatsApp primero.';end if;
 if coalesce((p_flags->>'online_payments_enabled')::boolean,false) and not exists(select 1 from public.marketing_connections where gym_id=p_gym_id and provider='WOMPI' and status='CONNECTED') then raise exception 'Conecta Wompi primero.';end if;
 insert into public.marketing_settings(gym_id) values(p_gym_id) on conflict do nothing;
 update public.marketing_settings set whatsapp_enabled=coalesce((p_flags->>'whatsapp_enabled')::boolean,whatsapp_enabled),online_payments_enabled=coalesce((p_flags->>'online_payments_enabled')::boolean,online_payments_enabled),chatbot_enabled=coalesce((p_flags->>'chatbot_enabled')::boolean,chatbot_enabled),marketing_automation_enabled=coalesce((p_flags->>'marketing_automation_enabled')::boolean,marketing_automation_enabled),human_pause_minutes=coalesce((p_flags->>'human_pause_minutes')::integer,human_pause_minutes),bot_session_minutes=coalesce((p_flags->>'bot_session_minutes')::integer,bot_session_minutes),updated_at=now(),updated_by=auth.uid() where gym_id=p_gym_id returning * into r;
 perform private.marketing_audit(p_gym_id,'FEATURES_UPDATED','settings',p_gym_id::text,p_flags);return to_jsonb(r);end$$;
create or replace function public.marketing_summary(p_gym_id uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare since timestamptz;begin perform public.marketing_access(p_gym_id);
 select date_trunc('month',now() at time zone g.timezone) at time zone g.timezone into since from public.gyms g where id=p_gym_id;
 return jsonb_build_object('settings',(select to_jsonb(s) from public.marketing_settings s where s.gym_id=p_gym_id),'connections',coalesce((select jsonb_agg(c) from public.marketing_connections c where c.gym_id=p_gym_id),'[]'),
 'automations_active',(select count(*) from public.marketing_automations where gym_id=p_gym_id and enabled and deleted_at is null),
 'sent',(select count(*) from public.marketing_messages where gym_id=p_gym_id and direction='OUT' and status in ('SENT','DELIVERED','READ') and created_at>=since),
 'delivered',(select count(*) from public.marketing_messages where gym_id=p_gym_id and direction='OUT' and status in ('DELIVERED','READ') and created_at>=since),
 'read',(select count(*) from public.marketing_messages where gym_id=p_gym_id and direction='OUT' and status='READ' and created_at>=since),
 'queued',(select count(*) from public.marketing_messages where gym_id=p_gym_id and status in ('QUEUED','PROCESSING')),
 'links',(select count(*) from public.payment_requests where gym_id=p_gym_id and created_at>=since),
 'payments_started',(select count(distinct payment_request_id) from public.payment_transactions where gym_id=p_gym_id and processed_at>=since),
 'payments_approved',(select count(*) from public.payment_requests where gym_id=p_gym_id and status='APPROVED' and paid_at>=since),
 'recovered_cents',coalesce((select sum(amount_in_cents) from public.payment_requests p where p.gym_id=p_gym_id and p.status='APPROVED' and p.mode='prod' and p.paid_at>=since and exists(select 1 from public.marketing_messages m where m.gym_id=p_gym_id and m.payment_request_id=p.id and m.automation_id is not null)),0));end$$;
create or replace function public.marketing_conversation_mode(p_gym_id uuid,p_id uuid,p_mode text) returns void language plpgsql security definer set search_path='' as $$
begin perform public.marketing_access(p_gym_id,true);
 if p_mode not in ('BOT','HUMAN','PAUSED') then raise exception 'Estado no válido.';end if;
 update public.whatsapp_conversations set mode=p_mode,last_human_at=case when p_mode='HUMAN' then now() else last_human_at end,pause_until=case when p_mode='HUMAN' then now()+make_interval(mins=>coalesce((select human_pause_minutes from public.marketing_settings where gym_id=p_gym_id),120)) else null end,updated_at=now() where id=p_id and gym_id=p_gym_id;
 if not found then raise exception 'Conversación no encontrada.';end if;perform private.marketing_audit(p_gym_id,'CONVERSATION_'||p_mode,'conversation',p_id::text);end$$;
create or replace function public.marketing_review_link(p_gym_id uuid,p_id uuid,p_client_id bigint,p_approved boolean) returns void language plpgsql security definer set search_path='' as $$
declare r public.chatbot_link_requests;begin perform public.marketing_access(p_gym_id,true);
 select * into r from public.chatbot_link_requests where gym_id=p_gym_id and id=p_id and status='PENDING' for update;
 if not found then raise exception 'La solicitud ya fue atendida.';end if;
 if p_approved and not exists(select 1 from public.clients where id=p_client_id and gym_id=p_gym_id and active) then raise exception 'Cliente no encontrado.';end if;
 update public.chatbot_link_requests set status=case when p_approved then 'APPROVED' else 'REJECTED' end,client_id=case when p_approved then p_client_id end,reviewed_by=auth.uid(),reviewed_at=now() where id=p_id;
 if p_approved then update public.whatsapp_conversations set client_id=p_client_id,verification_state='VERIFIED',verified_phone=sender_number,verified_until=now()+interval '30 minutes',failed_attempts=0,locked_until=null where id=r.conversation_id and gym_id=p_gym_id;end if;
 perform private.marketing_audit(p_gym_id,'CHATBOT_LINK_'||case when p_approved then 'APPROVED' else 'REJECTED' end,'link_request',p_id::text);end$$;
