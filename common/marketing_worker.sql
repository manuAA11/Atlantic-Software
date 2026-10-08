create table if not exists private.marketing_scheduler(
 gym_id uuid primary key references public.gyms(id) on delete cascade,cursor_client bigint not null default 0,
 lease_id uuid,lease_until timestamptz,last_started_at timestamptz,last_finished_at timestamptz,last_error text not null default '');
alter table private.marketing_scheduler enable row level security;
revoke all on private.marketing_scheduler from public,anon,authenticated;
create or replace function public.marketing_service_jobs(p_limit integer default 10) returns jsonb language plpgsql security definer set search_path='' as $$
declare v jsonb;begin
 insert into private.marketing_scheduler(gym_id) select gym_id from public.marketing_settings where marketing_automation_enabled and whatsapp_enabled on conflict do nothing;
 with candidates as(select j.gym_id from private.marketing_scheduler j join public.marketing_settings s using(gym_id) where s.whatsapp_enabled and s.marketing_automation_enabled and private.marketing_operable(j.gym_id) and (j.lease_until is null or j.lease_until<now()) order by j.last_started_at nulls first for update of j skip locked limit least(greatest(p_limit,1),20)),claimed as(update private.marketing_scheduler j set lease_id=gen_random_uuid(),lease_until=now()+interval '2 minutes',last_started_at=now() from candidates c where j.gym_id=c.gym_id returning j.*) select coalesce(jsonb_agg(claimed),'[]') into v from claimed;return v;end$$;
create or replace function public.marketing_service_job_done(p_gym_id uuid,p_lease uuid,p_cursor bigint,p_error text default '') returns void language plpgsql security definer set search_path='' as $$
begin
 update private.marketing_scheduler set cursor_client=p_cursor,lease_until=null,last_finished_at=now(),last_error=left(p_error,200) where gym_id=p_gym_id and lease_id=p_lease;
 update public.marketing_settings set last_worker_at=now(),last_error=left(p_error,200) where gym_id=p_gym_id;end$$;
create or replace function public.marketing_service_scheduler_authorized(p_token text) returns boolean language plpgsql security definer set search_path='' as $$
declare v text;begin execute 'select v.decrypted_secret from vault.decrypted_secrets v join private.marketing_platform p on p.scheduler_secret_id=v.id where p.singleton' into v;
 return v is not null and length(p_token)>=32 and v=p_token;end$$;
create or replace function public.marketing_service_send_guard(p_id bigint,p_claim uuid) returns jsonb language plpgsql security definer set search_path='' as $$
declare m public.marketing_messages;c public.clients;conv public.whatsapp_conversations;begin
 select * into m from public.marketing_messages where id=p_id and claim_id=p_claim and status='PROCESSING';
 if not found then return '{"allowed":false,"reason":"STALE_CLAIM"}';end if;
 if not private.marketing_operable(m.gym_id) or not exists(select 1 from public.marketing_settings where gym_id=m.gym_id and whatsapp_enabled) then return '{"allowed":false,"reason":"DISABLED"}';end if;
 select * into c from public.clients where id=m.client_id and gym_id=m.gym_id;
 select * into conv from public.whatsapp_conversations where gym_id=m.gym_id and sender_number=m.phone;
 if conv.mode<>'BOT' and m.automation_type<>'HANDOFF_ACK' then return '{"allowed":false,"reason":"HUMAN_HANDOFF"}';end if;
 if m.automation_id is not null then
 if not coalesce(c.whatsapp_opt_in,false) then return '{"allowed":false,"reason":"NO_CONSENT"}';end if;
 if private.marketing_phone(c.phone) is distinct from m.phone then return '{"allowed":false,"reason":"PHONE_CHANGED"}';end if;
 if not exists(select 1 from public.marketing_automations a join public.whatsapp_templates t on t.id=a.template_id and t.gym_id=a.gym_id where a.id=m.automation_id and a.gym_id=m.gym_id and a.enabled and a.deleted_at is null and t.status='APPROVED' and t.name=m.template_name and t.language=m.language_code and t.body=a.body) then return '{"allowed":false,"reason":"AUTOMATION_CHANGED"}';end if;
 elsif m.automation_type='TEST' then
 if not coalesce(c.whatsapp_opt_in,false) then return '{"allowed":false,"reason":"NO_CONSENT"}';end if;
 if private.marketing_phone(c.phone) is distinct from m.phone then return '{"allowed":false,"reason":"PHONE_CHANGED"}';end if;
 if not exists(select 1 from public.whatsapp_templates where gym_id=m.gym_id and name=m.template_name and language=m.language_code and status='APPROVED') then return '{"allowed":false,"reason":"TEMPLATE_NOT_APPROVED"}';end if;
 elsif m.automation_type in ('CHATBOT','HANDOFF_ACK') and (conv.last_inbound_at is null or conv.last_inbound_at<now()-interval '24 hours') then return '{"allowed":false,"reason":"WINDOW_CLOSED"}';end if;
 return jsonb_build_object('allowed',true,'last_inbound_at',conv.last_inbound_at);end$$;
create or replace function public.marketing_service_queue_reply(p_gym_id uuid,p_sender text,p_key text,p_content jsonb) returns bigint language plpgsql security definer set search_path='' as $$
declare conv public.whatsapp_conversations;mid bigint;begin
 select * into conv from public.whatsapp_conversations where gym_id=p_gym_id and sender_number=p_sender;
 if not found or conv.last_inbound_at<now()-interval '24 hours' then return null;end if;
 insert into public.marketing_messages(gym_id,client_id,conversation_id,automation_type,source_date,phone,template_name,status,dedupe_key,body,message_payload)
 values(p_gym_id,conv.client_id,conv.id,case when coalesce((p_content->>'_handoff_ack')::boolean,false) then 'HANDOFF_ACK' else 'CHATBOT' end,private.gym_local_date(p_gym_id),p_sender,'','QUEUED',p_key,coalesce(p_content->'text'->>'body',p_content->'interactive'->'body'->>'text',''),p_content-'_handoff_ack')
 on conflict(gym_id,dedupe_key) where dedupe_key is not null do nothing returning id into mid;return mid;end$$;
create or replace function public.marketing_service_inbound_record(p_gym_id uuid,p_sender text,p_message_id text,p_body text,p_human boolean default false) returns boolean language plpgsql security definer set search_path='' as $$
declare n bigint;begin
 insert into public.marketing_messages(gym_id,automation_type,source_date,phone,template_name,status,direction,dedupe_key,whatsapp_message_id,body)
 values(p_gym_id,'CHATBOT',private.gym_local_date(p_gym_id),p_sender,'','RECEIVED',case when p_human then 'HUMAN' else 'IN' end,'inbound/'||p_message_id,p_message_id,left(p_body,4096)) on conflict do nothing returning id into n;return n is not null;end$$;
create or replace function public.marketing_service_payment_link(p_gym_id uuid,p_id uuid,p_url text) returns void language plpgsql security definer set search_path='' as $$
begin
 if p_url !~ '^https://checkout.wompi.co/p/\?' then raise exception 'Enlace no válido.';end if;
 update public.payment_requests set checkout_url=p_url where id=p_id and gym_id=p_gym_id and status='PENDING';end$$;
-- Payment links expose only a random reference; opening them never records a payment.
create or replace function public.marketing_service_open_payment(p_reference text) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.payment_requests;begin
 select * into r from public.payment_requests where reference=p_reference for update;
 if not found then return '{"state":"NOT_FOUND"}';end if;
 if r.status='APPROVED' then return '{"state":"PAID"}';end if;
 if r.expires_at<now() then update public.payment_requests set status='EXPIRED' where id=r.id and status='PENDING';return '{"state":"EXPIRED"}';end if;
 if r.status<>'PENDING' then return '{"state":"UNAVAILABLE"}';end if;
 update public.payment_requests set opened_at=coalesce(opened_at,now()) where id=r.id;return jsonb_build_object('state','READY','checkout_url',r.checkout_url,'gym_id',r.gym_id,'id',r.id);end$$;
grant usage,select on sequence public.marketing_messages_id_seq,public.marketing_audit_id_seq to service_role;
