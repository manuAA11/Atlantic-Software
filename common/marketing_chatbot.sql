create or replace function private.marketing_phone(p_phone text) returns text language sql immutable set search_path='' as $$
 select case when length(d)=10 then '57'||d when d ~ '^[1-9][0-9]{7,14}$' then d else null end from (select regexp_replace(coalesce(p_phone,''),'[^0-9]','','g') d) x
$$;
create index if not exists clients_marketing_phone on public.clients(gym_id,private.marketing_phone(phone));
alter table public.whatsapp_conversations add column if not exists verified_registered_phone text;
create or replace function public.marketing_service_chat(p_gym_id uuid,p_sender text,p_action text,p_data jsonb default '{}') returns jsonb language plpgsql security definer set search_path='' as $$
declare conv public.whatsapp_conversations;c public.clients;cid bigint;num integer;v_date date;mins integer;begin
 if p_sender !~ '^[1-9][0-9]{7,14}$' or not private.marketing_operable(p_gym_id) then raise exception 'Solicitud no válida.';end if;
 if not exists(select 1 from public.marketing_settings where gym_id=p_gym_id and whatsapp_enabled and chatbot_enabled) then return '{"state":"DISABLED"}';end if;
 insert into public.whatsapp_conversations(gym_id,sender_number) values(p_gym_id,p_sender) on conflict do nothing;
 select * into conv from public.whatsapp_conversations where gym_id=p_gym_id and sender_number=p_sender for update;
 if p_action='human_echo' then
 update public.whatsapp_conversations set mode='HUMAN',last_human_at=now(),pause_until=now()+make_interval(mins=>(select human_pause_minutes from public.marketing_settings where gym_id=p_gym_id)),updated_at=now() where id=conv.id;
 perform private.marketing_audit(p_gym_id,'HUMAN_MESSAGE','conversation',conv.id::text);return '{"state":"HUMAN"}';end if;
 if p_action='inbound' then update public.whatsapp_conversations set last_inbound_at=now(),updated_at=now() where id=conv.id;conv.last_inbound_at:=now();end if;
 if conv.mode='HUMAN' and conv.pause_until<=now() then update public.whatsapp_conversations set mode='BOT',pause_until=null where id=conv.id;conv.mode:='BOT';end if;
 if conv.mode<>'BOT' then return jsonb_build_object('state',conv.mode,'conversation_id',conv.id);end if;
 if conv.locked_until>now() then return jsonb_build_object('state','LOCKED','conversation_id',conv.id);end if;
 if conv.client_id is not null then select * into c from public.clients where gym_id=p_gym_id and id=conv.client_id;end if;
 if p_action in ('inbound','session') and conv.verification_state='VERIFIED' and conv.verified_until>now() and conv.verified_phone=p_sender and c.id is not null and conv.verified_registered_phone is not distinct from private.marketing_phone(c.phone) then
 return jsonb_build_object('state','VERIFIED','conversation_id',conv.id,'client_id',c.id,'first_name',c.first_name,'last_inbound_at',coalesce(conv.last_inbound_at,now()),'membership',private.membership_snapshot_json(p_gym_id,c.id));end if;
 if p_action='handoff' then
 update public.whatsapp_conversations set mode='HUMAN',last_human_at=now(),pause_until=now()+make_interval(mins=>(select human_pause_minutes from public.marketing_settings where gym_id=p_gym_id)),updated_at=now() where id=conv.id;
 perform private.marketing_audit(p_gym_id,'HUMAN_HANDOFF','conversation',conv.id::text);return '{"state":"HUMAN"}';end if;
 if p_action='verify' then
 if not public.marketing_service_limit(p_gym_id,'verify/'||p_sender,5,3600) then update public.whatsapp_conversations set locked_until=now()+interval '1 hour',verification_state='LOCKED' where id=conv.id;return '{"state":"LOCKED"}';end if;
 select count(*),min(id) into num,cid from public.clients where gym_id=p_gym_id and private.marketing_phone(phone)=p_sender;
 begin v_date:=(p_data->>'birth_date')::date;exception when others then v_date:=null;end;
 if num=1 then select * into c from public.clients where gym_id=p_gym_id and id=cid;end if;
 if num=1 and v_date is not null and coalesce(c.birth_date,c.birthdate)=v_date then
 select bot_session_minutes into mins from public.marketing_settings where gym_id=p_gym_id;
 update public.whatsapp_conversations set client_id=cid,verification_state='VERIFIED',verified_until=now()+make_interval(mins=>mins),verified_phone=p_sender,verified_registered_phone=private.marketing_phone(c.phone),failed_attempts=0,locked_until=null,updated_at=now() where id=conv.id;
 perform private.marketing_audit(p_gym_id,'CHATBOT_VERIFIED','conversation',conv.id::text);return jsonb_build_object('state','VERIFIED','conversation_id',conv.id,'client_id',cid,'first_name',c.first_name,'last_inbound_at',conv.last_inbound_at,'membership',private.membership_snapshot_json(p_gym_id,cid));end if;
 update public.whatsapp_conversations set failed_attempts=failed_attempts+1,verification_state=case when failed_attempts>=4 then 'LOCKED' else 'DOB' end,locked_until=case when failed_attempts>=4 then now()+interval '1 hour' else null end,verified_until=null,updated_at=now() where id=conv.id;
 perform private.marketing_audit(p_gym_id,'CHATBOT_VERIFICATION_FAILED','conversation',conv.id::text);
 return jsonb_build_object('state','VERIFICATION_FAILED','conversation_id',conv.id);end if;
 if p_action='request_link' then
 if not public.marketing_service_limit(p_gym_id,'link/'||p_sender,3,86400) then return '{"state":"LOCKED"}';end if;
 if length(trim(coalesce(p_data->>'name',''))) not between 2 and 120 then return '{"state":"NEED_LINK_DETAILS"}';end if;
 begin v_date:=(p_data->>'birth_date')::date;exception when others then v_date:=null;end;
 insert into public.chatbot_link_requests(gym_id,conversation_id,supplied_name,birth_date) values(p_gym_id,conv.id,trim(p_data->>'name'),v_date) on conflict(conversation_id) where status='PENDING' do nothing;
 update public.whatsapp_conversations set verification_state='LINK_REQUEST',verified_until=null where id=conv.id;return '{"state":"LINK_PENDING"}';end if;
 if exists(select 1 from public.chatbot_link_requests where gym_id=p_gym_id and conversation_id=conv.id and status='PENDING') then return jsonb_build_object('state','LINK_PENDING','conversation_id',conv.id);end if;
 select count(*) into num from public.clients where gym_id=p_gym_id and private.marketing_phone(phone)=p_sender;
 update public.whatsapp_conversations set verification_state=case when num=1 then 'DOB' else 'LINK_REQUEST' end,verified_until=null where id=conv.id;
 return jsonb_build_object('state',case when num=1 then 'NEED_DOB' else 'NEED_LINK_DETAILS' end,'conversation_id',conv.id,'last_inbound_at',coalesce(conv.last_inbound_at,now()));end$$;
-- Bind staff-approved sessions to the client's current registered phone too.
create or replace function private.marketing_link_verified_phone() returns trigger language plpgsql set search_path='' as $$
begin if new.verification_state='VERIFIED' and (old.verification_state is distinct from new.verification_state or old.verified_until is distinct from new.verified_until) then
 select private.marketing_phone(phone) into new.verified_registered_phone from public.clients where gym_id=new.gym_id and id=new.client_id;end if;return new;end$$;
drop trigger if exists marketing_link_verified_phone on public.whatsapp_conversations;
create trigger marketing_link_verified_phone before update on public.whatsapp_conversations for each row execute function private.marketing_link_verified_phone();
-- One-time operator setup; app credentials never belong to a desktop profile.
create or replace function public.marketing_service_configure_meta(p_data jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare sid uuid;origin text:=p_data->>'onboarding_origin';page text:=p_data->>'onboarding_url';begin
 if jsonb_typeof(p_data) is distinct from 'object' then raise exception 'Configuración de Meta no válida.';end if;
 if coalesce(p_data->>'app_id','') !~ '^[0-9]{5,30}$'
 or coalesce(p_data->>'config_id','') !~ '^[0-9]{5,30}$'
 or length(coalesce(p_data->>'app_secret','')) not between 20 and 512
 or length(coalesce(p_data->>'verify_token','')) not between 32 and 512
 or coalesce(origin,'') !~ '^https://[a-z0-9.-]+(:[0-9]+)?$'
 or coalesce(page,'') !~ '^https://[a-z0-9.-]+(:[0-9]+)?/[^?#]*$'
 or left(page,length(origin)+1)<>origin||'/'
 or exists(select 1 from jsonb_object_keys(p_data) k where k not in ('app_id','config_id','app_secret','verify_token','onboarding_origin','onboarding_url')) then
 raise exception 'Revisa la configuración oficial de Meta y la página HTTPS de autorización.';end if;
 perform pg_advisory_xact_lock(hashtextextended('gymsoft/meta-platform',0));
 select meta_config_secret_id into sid from private.marketing_platform where singleton for update;
 if sid is null then execute 'select vault.create_secret($1,$2,$3)' into sid using p_data::text,'gymsoft_meta_platform','Configuración privada de Meta';
 else execute 'select vault.update_secret($1,$2)' using sid,p_data::text;end if;
 update private.marketing_platform set meta_config_secret_id=sid where singleton;
 return jsonb_build_object('configured',true,'onboarding_url',page);
end$$;
create or replace function public.marketing_service_platform() returns jsonb language plpgsql security definer set search_path='' as $$
declare v jsonb;begin execute 'select v.decrypted_secret::jsonb from vault.decrypted_secrets v join private.marketing_platform p on p.meta_config_secret_id=v.id where p.singleton' into v;return v;end$$;
create or replace function public.marketing_service_oauth(p_hash text,p_gym_id uuid default null,p_user_id uuid default null,p_consume boolean default false) returns jsonb language plpgsql security definer set search_path='' as $$
declare r private.marketing_oauth_states;begin
 if p_hash !~ '^[a-f0-9]{64}$' then raise exception 'Estado no válido.';end if;
 if p_gym_id is not null then insert into private.marketing_oauth_states(state_hash,gym_id,user_id,expires_at) values(p_hash,p_gym_id,p_user_id,now()+interval '10 minutes') returning * into r;
 elsif p_consume then update private.marketing_oauth_states set used_at=now() where state_hash=p_hash and expires_at>now() and used_at is null returning * into r;
 else select * into r from private.marketing_oauth_states where state_hash=p_hash and expires_at>now() and used_at is null;end if;
 if r.state_hash is null then raise exception 'La autorización venció o ya fue utilizada. Vuelve a conectar WhatsApp.';end if;return jsonb_build_object('gym_id',r.gym_id,'user_id',r.user_id);end$$;
create or replace function public.marketing_service_receipt(p_provider text,p_key text,p_gym_id uuid,p_payload jsonb,p_done boolean default false) returns boolean language plpgsql security definer set search_path='' as $$
declare r private.marketing_webhook_events;begin
 if p_done then update private.marketing_webhook_events set processed_at=now() where provider=p_provider and event_key=p_key and gym_id=p_gym_id;return found;end if;
 insert into private.marketing_webhook_events(provider,event_key,gym_id,payload) values(p_provider,p_key,p_gym_id,p_payload) on conflict do nothing;
 select * into r from private.marketing_webhook_events where provider=p_provider and event_key=p_key for update;
 if r.gym_id<>p_gym_id then raise exception 'Evento asociado a otro gimnasio.';end if;return r.processed_at is null;end$$;
create or replace function public.marketing_service_event_batch(p_gym_id uuid,p_limit integer default 100) returns jsonb language plpgsql security definer set search_path='' as $$
declare v jsonb;begin
 if not private.marketing_operable(p_gym_id) then return '[]';end if;
 select coalesce(jsonb_agg(x),'[]') into v from (select * from private.marketing_events where gym_id=p_gym_id and processed_at is null order by id limit least(greatest(p_limit,1),200)) x;return v;end$$;
create or replace function public.marketing_service_event_done(p_gym_id uuid,p_ids bigint[]) returns void language sql security definer set search_path='' as $$
 update private.marketing_events set processed_at=now() where gym_id=p_gym_id and id=any(p_ids)
$$;
create or replace function public.marketing_service_status(p_gym_id uuid,p_message_id text,p_status text,p_at timestamptz) returns boolean language plpgsql security definer set search_path='' as $$
declare v_found boolean;begin
 if p_status not in ('SENT','DELIVERED','READ','FAILED') or length(coalesce(p_message_id,'')) not between 1 and 512 or p_at is null or p_at>now()+interval '5 minutes' then return false;end if;
 perform pg_advisory_xact_lock(hashtextextended(p_gym_id::text||'/delivery/'||p_message_id,0));
 insert into private.marketing_webhook_events(provider,event_key,gym_id,payload)
 values('META_STATUS',p_gym_id::text||'/'||p_message_id||'/'||p_status,p_gym_id,jsonb_build_object('message_id',p_message_id,'status',p_status,'at',p_at)) on conflict do nothing;
 update public.marketing_messages set status=case when status='READ' then 'READ' when status='DELIVERED' and p_status in ('SENT','FAILED') then 'DELIVERED' else p_status end,
 sent_at=case when p_status='SENT' then coalesce(sent_at,p_at) else sent_at end,
 delivered_at=case when p_status in ('DELIVERED','READ') then coalesce(delivered_at,p_at) else delivered_at end,read_at=case when p_status='READ' then coalesce(read_at,p_at) else read_at end,updated_at=now() where gym_id=p_gym_id and whatsapp_message_id=p_message_id and direction='OUT';
 v_found:=found;
 if v_found then update private.marketing_webhook_events set processed_at=now() where provider='META_STATUS' and event_key=p_gym_id::text||'/'||p_message_id||'/'||p_status and gym_id=p_gym_id;end if;
 return v_found;end$$;
-- Backend table access is intentionally limited to the integration model.
do $$declare t text;begin foreach t in array array['marketing_settings','marketing_connections','whatsapp_templates','marketing_automations','payment_requests','payment_transactions','whatsapp_conversations','chatbot_link_requests','automation_runs','marketing_messages','marketing_audit'] loop execute format('grant select,insert,update on public.%I to service_role',t);end loop;end$$;
