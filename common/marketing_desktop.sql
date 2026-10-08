create or replace function public.marketing_lookup_clients(p_gym_id uuid,p_search text default '',p_limit integer default 30) returns jsonb language plpgsql stable security definer set search_path='' as $$
declare r jsonb;begin perform public.marketing_access(p_gym_id,true);
 select coalesce(jsonb_agg(x),'[]') into r from (select id,first_name,last_name,document,phone,whatsapp_opt_in from public.clients where gym_id=p_gym_id and (btrim(p_search)='' or concat_ws(' ',first_name,last_name,document,phone) ilike '%'||replace(replace(replace(left(p_search,120),E'\\',E'\\\\'),'%',E'\\%'),'_',E'\\_')||'%') order by first_name,last_name,id limit least(greatest(p_limit,1),100)) x;return r;end$$;
create or replace function public.marketing_history(p_gym_id uuid,p_kind text,p_offset integer default 0,p_limit integer default 100) returns jsonb language plpgsql stable security definer set search_path='' as $$
declare r jsonb;begin perform public.marketing_access(p_gym_id);if p_offset<0 or p_offset>1000000 or p_limit not between 1 and 200 then raise exception 'Página no válida.';end if;
 if p_kind='messages' then
 select coalesce(jsonb_agg(to_jsonb(x) order by x.created_at desc,x.id desc),'[]') into r from (select m.*,p.status payment_status,p.reference payment_reference from public.marketing_messages m left join public.payment_requests p on p.id=m.payment_request_id and p.gym_id=m.gym_id where m.gym_id=p_gym_id order by m.created_at desc,m.id desc offset p_offset limit p_limit) x;
 elsif p_kind='payments' then
 select coalesce(jsonb_agg(to_jsonb(x) order by x.created_at desc,x.id desc),'[]') into r from (select p.*,coalesce(nullif(btrim(concat_ws(' ',c.first_name,c.last_name)),''),'Cliente eliminado') client_name,(select t.provider_transaction_id from public.payment_transactions t where t.payment_request_id=p.id and t.gym_id=p_gym_id order by t.processed_at desc limit 1) transaction_id,(select t.provider_created_at from public.payment_transactions t where t.payment_request_id=p.id and t.gym_id=p_gym_id order by t.processed_at desc limit 1) provider_created_at from public.payment_requests p left join public.clients c on c.id=p.client_id and c.gym_id=p.gym_id where p.gym_id=p_gym_id order by p.created_at desc,p.id desc offset p_offset limit p_limit) x;
 else raise exception 'Historial no válido.';end if;return r;end$$;
create or replace function public.marketing_workspace(p_gym_id uuid) returns jsonb language plpgsql stable security definer set search_path='' as $$
begin perform public.marketing_access(p_gym_id);
 return jsonb_build_object('summary',public.marketing_summary(p_gym_id),
 'automations',coalesce((select jsonb_agg(a order by a.created_at desc) from public.marketing_automations a where a.gym_id=p_gym_id and a.deleted_at is null),'[]'),
 'templates',coalesce((select jsonb_agg(t order by t.name) from public.whatsapp_templates t where t.gym_id=p_gym_id),'[]'),
 'plans',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'name',p.name,'price',p.price,'entry_limit',p.entry_limit,'active',p.active) order by p.name) from public.plans p where p.gym_id=p_gym_id),'[]'),
 'conversations',coalesce((select jsonb_agg(x) from (select c.id,c.sender_number,c.mode,c.verification_state,c.last_inbound_at,c.last_human_at,c.pause_until from public.whatsapp_conversations c where c.gym_id=p_gym_id order by c.updated_at desc limit 100) x),'[]'),
 'links',coalesce((select jsonb_agg(x) from (select l.*,c.sender_number from public.chatbot_link_requests l join public.whatsapp_conversations c on c.id=l.conversation_id and c.gym_id=l.gym_id where l.gym_id=p_gym_id and l.status='PENDING' order by l.created_at limit 100) x),'[]'),
 'messages',public.marketing_history(p_gym_id,'messages'), 'payments',public.marketing_history(p_gym_id,'payments'),
 'health',jsonb_build_object('last_worker_at',(select last_finished_at from private.marketing_scheduler where gym_id=p_gym_id),'worker_error',(select last_error from private.marketing_scheduler where gym_id=p_gym_id),'recent_errors',(select count(*) from public.marketing_messages where gym_id=p_gym_id and status in ('FAILED','UNCERTAIN') and created_at>now()-interval '7 days')));
end$$;
create or replace function public.marketing_activate_setup(p_gym_id uuid,p_rule_ids uuid[],p_chatbot boolean default true) returns jsonb language plpgsql security definer set search_path='' as $$
declare a public.marketing_automations;n integer:=0;begin perform public.marketing_access(p_gym_id);
 if cardinality(p_rule_ids)>30 then raise exception 'Selecciona hasta 30 automatizaciones.';end if;
 for a in select * from public.marketing_automations where gym_id=p_gym_id and deleted_at is null and id=any(p_rule_ids) order by id for update loop
 perform private.marketing_rule_ready(p_gym_id,a.template_id,a.include_payment_link,a.body);n:=n+1;end loop;
 if n<>cardinality(p_rule_ids) then raise exception 'Actualiza la selección de automatizaciones.';end if;
 perform public.marketing_features(p_gym_id,jsonb_build_object('whatsapp_enabled',true,'chatbot_enabled',p_chatbot,'marketing_automation_enabled',n>0));
 update public.marketing_automations set enabled=true,revision=revision+1,updated_at=now() where gym_id=p_gym_id and id=any(p_rule_ids);
 perform private.marketing_audit(p_gym_id,'SETUP_ACTIVATED','settings',p_gym_id::text,jsonb_build_object('rules',p_rule_ids,'chatbot',p_chatbot));return jsonb_build_object('active',n,'chatbot',p_chatbot);
end$$;
create or replace function public.marketing_service_gym(p_gym_id uuid) returns jsonb language sql stable security definer set search_path='' as $$select jsonb_build_object('id',id,'name',name,'timezone',timezone) from public.gyms where id=p_gym_id$$;
-- Owner access uses the existing private owner authorization, never a client claim.
do $outer$begin if to_regprocedure('private.require_owner()') is not null then
 execute $fn$create or replace function public.owner_marketing_status(p_gym_id uuid) returns jsonb language plpgsql stable security definer set search_path='' as $body$
 begin perform private.require_owner();return jsonb_build_object('connections',coalesce((select jsonb_agg(jsonb_build_object('provider',provider,'status',status,'mode',mode,'last_checked_at',last_checked_at)) from public.marketing_connections where gym_id=p_gym_id),'[]'),'chatbot_enabled',coalesce((select chatbot_enabled from public.marketing_settings where gym_id=p_gym_id),false),'automations_active',(select count(*) from public.marketing_automations where gym_id=p_gym_id and enabled and deleted_at is null),'last_execution',(select last_finished_at from private.marketing_scheduler where gym_id=p_gym_id),'errors',(select count(*) from public.marketing_messages where gym_id=p_gym_id and status in ('FAILED','UNCERTAIN') and created_at>now()-interval '7 days'));end $body$ $fn$;
 execute 'revoke all on function public.owner_marketing_status(uuid) from public,anon,authenticated';execute 'grant execute on function public.owner_marketing_status(uuid) to authenticated';
 end if;end$outer$;
create or replace function public.marketing_service_test_message(p_gym_id uuid,p_client_id bigint,p_template_id uuid,p_key text,p_body text,p_parameters jsonb) returns bigint language plpgsql security definer set search_path='' as $$
declare c public.clients;t public.whatsapp_templates;mid bigint;begin
 if not private.marketing_operable(p_gym_id) then raise exception 'Gimnasio no disponible.';end if;
 if length(p_key) not between 8 and 160 then raise exception 'Identificador de prueba no válido.';end if;
 select id into mid from public.marketing_messages where gym_id=p_gym_id and dedupe_key='test/'||p_key;
 if found then return mid;end if;
 select * into c from public.clients where gym_id=p_gym_id and id=p_client_id;
 if c.id is null or not c.whatsapp_opt_in or private.marketing_phone(c.phone) is null then raise exception 'El cliente debe autorizar WhatsApp y tener un teléfono válido.';end if;
 select * into t from public.whatsapp_templates where gym_id=p_gym_id and id=p_template_id and status='APPROVED';
 if not found or t.body like '%{{link_pago}}%' then raise exception 'Selecciona una plantilla aprobada sin enlace de pago.';end if;
 if not public.marketing_service_limit(p_gym_id,'test-message/'||p_client_id,3,3600) then raise exception 'Ya se enviaron tres pruebas a este cliente durante esta hora.';end if;
 insert into public.marketing_messages(gym_id,client_id,automation_type,source_date,client_name,phone,template_name,language_code,template_parameters,status,dedupe_key,body)
 values(p_gym_id,c.id,'TEST',private.gym_local_date(p_gym_id),btrim(concat_ws(' ',c.first_name,c.last_name)),private.marketing_phone(c.phone),t.name,t.language,p_parameters,'QUEUED','test/'||p_key,p_body) on conflict(gym_id,dedupe_key) where dedupe_key is not null do nothing returning id into mid;
 if mid is null then select id into mid from public.marketing_messages where gym_id=p_gym_id and dedupe_key='test/'||p_key;end if;
 perform private.marketing_audit(p_gym_id,'TEST_MESSAGE_QUEUED','message',mid::text,jsonb_build_object('client_id',c.id));return mid;end$$;
create or replace function public.marketing_reception_workspace(p_gym_id uuid) returns jsonb language plpgsql stable security definer set search_path='' as $$
begin perform public.marketing_access(p_gym_id,true);
 return jsonb_build_object('connected',exists(select 1 from public.marketing_connections where gym_id=p_gym_id and provider='META' and status='CONNECTED'),
 'conversations',coalesce((select jsonb_agg(x) from (select id,sender_number,mode,last_inbound_at,last_human_at,pause_until from public.whatsapp_conversations where gym_id=p_gym_id order by updated_at desc limit 100) x),'[]'),
 'links',coalesce((select jsonb_agg(x) from (select l.id,l.supplied_name,l.created_at,c.sender_number from public.chatbot_link_requests l join public.whatsapp_conversations c on c.id=l.conversation_id and c.gym_id=l.gym_id where l.gym_id=p_gym_id and l.status='PENDING' order by l.created_at limit 100) x),'[]'));
end$$;
