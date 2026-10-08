create or replace function private.marketing_operable(p_gym uuid) returns boolean language plpgsql security definer set search_path='' as $$
declare v boolean;begin if not exists(select 1 from public.gyms where id=p_gym) then return false;end if;
 if to_regprocedure('private.subscription_open(uuid)') is not null then execute 'select private.subscription_open($1)' into v using p_gym;return v;end if;return true;end$$;
create or replace function public.marketing_service_credentials(p_gym_id uuid,p_provider text) returns jsonb language plpgsql security definer set search_path='' as $$
declare v jsonb;begin
 -- Vault stays server-side, never returned by an authenticated desktop RPC.
 execute 'select v.decrypted_secret::jsonb from vault.decrypted_secrets v join private.marketing_credentials c on c.secret_id=v.id where c.gym_id=$1 and c.provider=$2' into v using p_gym_id,p_provider;return v;end$$;
create or replace function public.marketing_service_connect(p_gym_id uuid,p_provider text,p_secrets jsonb,p_display jsonb,p_mode text default 'test') returns void language plpgsql security definer set search_path='' as $$
declare sid uuid;begin
 if p_provider not in ('META','WOMPI') or p_mode not in ('test','prod') or not private.marketing_operable(p_gym_id) then raise exception 'Conexión no permitida.';end if;
 if p_mode='prod' and not (select production_allowed from private.marketing_platform where singleton) then raise exception 'La producción necesita autorización del propietario.';end if;
 perform pg_advisory_xact_lock(hashtextextended(p_gym_id::text||p_provider,0));
 select secret_id into sid from private.marketing_credentials where gym_id=p_gym_id and provider=p_provider;
 if sid is null then execute 'select vault.create_secret($1,$2,$3)' into sid using p_secrets::text,'marketing/'||p_gym_id||'/'||p_provider,'Credenciales privadas de integración';
 else execute 'select vault.update_secret($1,$2)' using sid,p_secrets::text;end if;
 insert into private.marketing_credentials(gym_id,provider,secret_id) values(p_gym_id,p_provider,sid) on conflict(gym_id,provider) do update set secret_id=excluded.secret_id,updated_at=now();
 insert into public.marketing_connections(gym_id,provider,status,mode,display_number,provider_account_id,phone_number_id,coexistence,metadata,last_checked_at)
 values(p_gym_id,p_provider,'CONNECTED',p_mode,coalesce(p_display->>'display_number',''),coalesce(p_display->>'provider_account_id',''),coalesce(p_display->>'phone_number_id',''),coalesce((p_display->>'coexistence')::boolean,false),jsonb_build_object('merchant_name',p_display->>'merchant_name','webhook_confirmed',coalesce((p_display->>'webhook_confirmed')::boolean,false)),now())
 on conflict(gym_id,provider) do update set status='CONNECTED',mode=excluded.mode,display_number=excluded.display_number,provider_account_id=excluded.provider_account_id,phone_number_id=excluded.phone_number_id,coexistence=excluded.coexistence,metadata=excluded.metadata,last_checked_at=now(),last_error='',updated_at=now();
 insert into public.marketing_settings(gym_id) values(p_gym_id) on conflict do nothing;
 perform private.marketing_audit(p_gym_id,p_provider||'_CONNECTED','connection',p_provider,jsonb_build_object('mode',p_mode,'responsible_user_id',p_display->>'actor_user_id'));end$$;
create or replace function public.marketing_disconnect(p_gym_id uuid,p_provider text) returns void language plpgsql security definer set search_path='' as $$
begin perform public.marketing_access(p_gym_id);
 if p_provider not in ('META','WOMPI') then raise exception 'Servicio no válido.';end if;
 update public.marketing_connections set status='DISCONNECTED',updated_at=now() where gym_id=p_gym_id and provider=p_provider;
 if p_provider='META' then update public.marketing_settings set whatsapp_enabled=false,chatbot_enabled=false,marketing_automation_enabled=false where gym_id=p_gym_id;
 else update public.marketing_settings set online_payments_enabled=false where gym_id=p_gym_id;end if;
 -- Existing provider credentials are retained to reconcile payments already in flight.
 -- Disconnecting here never deregisters or migrates an existing WhatsApp Business number.
 perform private.marketing_audit(p_gym_id,p_provider||'_DISCONNECTED','connection',p_provider);end$$;
create or replace function public.marketing_service_limit(p_gym_id uuid,p_bucket text,p_max integer,p_seconds integer) returns boolean language plpgsql security definer set search_path='' as $$
declare n integer;w timestamptz;begin
 if p_max not between 1 and 10000 or p_seconds not between 1 and 86400 or length(p_bucket)>160 then raise exception 'Límite no válido.';end if;
 w:=to_timestamp(floor(extract(epoch from now())/p_seconds)*p_seconds);
 insert into private.marketing_rate_limits(gym_id,bucket,window_start,hits) values(p_gym_id,p_bucket,w,1) on conflict(gym_id,bucket,window_start) do update set hits=private.marketing_rate_limits.hits+1 returning hits into n;return n<=p_max;end$$;
create or replace function public.marketing_service_contexts(p_gym_id uuid,p_after bigint default 0,p_limit integer default 200) returns jsonb language plpgsql security definer set search_path='' as $$
declare v jsonb;begin if not private.marketing_operable(p_gym_id) then return '[]';end if;
 select coalesce(jsonb_agg(x),'[]') into v from (select c.id client_id,c.first_name,c.last_name,c.phone,coalesce(c.birth_date,c.birthdate) birth_date,c.active,c.whatsapp_opt_in,c.created_at,
 g.id gym_id,g.name gym_name,g.timezone,private.gym_local_date(g.id) today,now() server_now,
 private.membership_snapshot_json(g.id,c.id) membership,
 (select to_jsonb(p) from public.plans p join public.memberships m on m.plan_id=p.id and m.gym_id=p.gym_id where m.gym_id=g.id and m.client_id=c.id and m.id=(private.membership_snapshot_json(g.id,c.id)->>'membership_id')::bigint limit 1) plan,
 (select max(ch.checkin_at) from public.checkins ch where ch.gym_id=g.id and ch.client_id=c.id and ch.result='PERMITIDA') last_checkin,
 (select count(*) from public.checkins ch where ch.gym_id=g.id and ch.client_id=c.id and ch.result='PERMITIDA') checkin_count
 from public.clients c join public.gyms g on g.id=c.gym_id where c.gym_id=p_gym_id and c.id>p_after order by c.id limit least(greatest(p_limit,1),500)) x;return v;end$$;
create or replace function private.marketing_capture_event() returns trigger language plpgsql security definer set search_path='' as $$
declare et text;data jsonb;begin
 if not exists(select 1 from public.marketing_settings where gym_id=new.gym_id and (marketing_automation_enabled or chatbot_enabled)) or exists(select 1 from private.ticket_import_context where transaction_id=txid_current() and gym_id=new.gym_id) then return new;end if;
 if tg_table_name='checkins' then if new.result<>'PERMITIDA' then return new;end if;et:='CHECK_IN_SUCCESS';
 else if new.payment_status<>'posted' or new.payment_method='Wompi' then return new;end if;et:='MEMBERSHIP_RENEWED';end if;
 data:=to_jsonb(new);
 if tg_table_name='checkins' then data:=data||jsonb_build_object('first_of_day',(select count(*)=1 from public.checkins ch where ch.gym_id=new.gym_id and ch.client_id=new.client_id and ch.result='PERMITIDA' and (ch.checkin_at at time zone (select timezone from public.gyms where id=new.gym_id))::date=private.gym_local_date(new.gym_id)),'first_of_membership',(select count(*)=1 from public.checkins ch where ch.gym_id=new.gym_id and ch.membership_id=new.membership_id and ch.result='PERMITIDA'),'checkin_count',(select count(*) from public.checkins ch where ch.gym_id=new.gym_id and ch.client_id=new.client_id and ch.result='PERMITIDA'));end if;
 insert into private.marketing_events(gym_id,client_id,event_type,entity_id,payload) values(new.gym_id,new.client_id,et,new.id::text,data) on conflict do nothing;return new;end$$;
drop trigger if exists marketing_checkin_event on public.checkins;
create trigger marketing_checkin_event after insert on public.checkins for each row execute function private.marketing_capture_event();
drop trigger if exists marketing_renewal_event on public.memberships;
create trigger marketing_renewal_event after insert on public.memberships for each row execute function private.marketing_capture_event();
create or replace function public.marketing_service_enqueue(p_gym_id uuid,p_automation_id uuid,p_client_id bigint,p_dedupe_key text,p_phone text,p_body text,p_parameters jsonb,p_payment_request_id uuid default null) returns jsonb language plpgsql security definer set search_path='' as $$
declare a public.marketing_automations;c public.clients;t public.whatsapp_templates;v_status text:='QUEUED';reason text;rid uuid;mid bigint;freq_n integer;freq_hours integer;begin
 if not private.marketing_operable(p_gym_id) then return '{"status":"SKIPPED","reason":"INACTIVE_GYM"}';end if;
 select * into a from public.marketing_automations where id=p_automation_id and gym_id=p_gym_id and enabled and deleted_at is null for update;
 if not found or not exists(select 1 from public.marketing_settings where gym_id=p_gym_id and whatsapp_enabled and marketing_automation_enabled) then return '{"status":"SKIPPED","reason":"DISABLED"}';end if;
 if exists(select 1 from public.automation_runs where gym_id=p_gym_id and dedupe_key=p_dedupe_key) then return '{"status":"SKIPPED","reason":"DUPLICATE"}';end if;
 select * into c from public.clients where gym_id=p_gym_id and id=p_client_id;
 if not found then raise exception 'Cliente no encontrado.';end if;
 select * into t from public.whatsapp_templates where gym_id=p_gym_id and id=a.template_id and status='APPROVED' and body=a.body;
 if not found then v_status:='SKIPPED';reason:='TEMPLATE_NOT_APPROVED';end if;
 if not c.whatsapp_opt_in then v_status:='NO_CONSENT';reason:='NO_CONSENT';end if;
 if p_phone !~ '^[1-9][0-9]{7,14}$' then v_status:='SKIPPED';reason:='INVALID_PHONE';end if;
 if exists(select 1 from public.whatsapp_conversations where gym_id=p_gym_id and sender_number=p_phone and mode<>'BOT') then v_status:='SKIPPED';reason:='HUMAN_HANDOFF';end if;
 if not exists(select 1 from public.marketing_connections where gym_id=p_gym_id and provider='META' and status='CONNECTED') then v_status:='SKIPPED';reason:='DISCONNECTED';end if;
 freq_n:=coalesce((a.frequency->>'count')::integer,1);freq_hours:=coalesce((a.frequency->>'hours')::integer,24);
 if v_status='QUEUED' and freq_n>0 and (select count(*) from public.automation_runs ar where ar.gym_id=p_gym_id and ar.automation_id=a.id and ar.client_id=p_client_id and ar.status in ('QUEUED','SENT','UNCERTAIN') and ar.executed_at>now()-make_interval(hours=>freq_hours))>=freq_n then v_status:='SKIPPED';reason:='FREQUENCY';end if;
 insert into public.automation_runs(gym_id,automation_id,client_id,dedupe_key,status,reason) values(p_gym_id,a.id,c.id,p_dedupe_key,v_status,reason) returning id into rid;
 insert into public.marketing_messages(gym_id,client_id,automation_type,source_date,client_name,phone,template_name,language_code,template_parameters,status,automation_id,dedupe_key,body,payment_request_id,error_message)
 values(p_gym_id,c.id,a.trigger_type,private.gym_local_date(p_gym_id),trim(c.first_name||' '||c.last_name),p_phone,coalesce(t.name,''),coalesce(t.language,'es_CO'),p_parameters,v_status,a.id,p_dedupe_key,p_body,p_payment_request_id,coalesce(reason,'')) returning id into mid;
 update public.marketing_automations set last_run_at=now() where id=a.id;return jsonb_build_object('status',v_status,'reason',reason,'run_id',rid,'message_id',mid);end$$;
create or replace function public.marketing_service_claim(p_limit integer default 50,p_message_id bigint default null) returns jsonb language plpgsql security definer set search_path='' as $$
declare v jsonb;begin
 -- No automatic resend after an ambiguous provider timeout: Meta has no send idempotency key.
 with stale as (
 update public.marketing_messages set status='UNCERTAIN',error_message='No se pudo confirmar el resultado del envío.',updated_at=now() where status='PROCESSING' and claimed_at<now()-interval '3 minutes' returning gym_id,dedupe_key
 ) update public.automation_runs a set status='UNCERTAIN',reason='PROVIDER_UNCERTAIN' from stale s where a.gym_id=s.gym_id and a.dedupe_key=s.dedupe_key;
 with candidates as(select m.id from public.marketing_messages m join public.marketing_settings s on s.gym_id=m.gym_id join public.marketing_connections c on c.gym_id=m.gym_id and c.provider='META' where m.status='QUEUED' and (p_message_id is null or m.id=p_message_id) and m.scheduled_for<=now() and s.whatsapp_enabled and c.status='CONNECTED' and private.marketing_operable(m.gym_id) order by m.id for update of m skip locked limit least(greatest(p_limit,1),100)),claimed as(update public.marketing_messages m set status='PROCESSING',claim_id=gen_random_uuid(),claimed_at=now(),attempts=attempts+1 from candidates c where m.id=c.id returning m.*) select coalesce(jsonb_agg(claimed),'[]') into v from claimed;return v;end$$;
create or replace function public.marketing_service_send_result(p_id bigint,p_claim_id uuid,p_status text,p_provider_id text default '',p_error text default '') returns boolean language plpgsql security definer set search_path='' as $$
declare r public.marketing_messages;e record;v_gym uuid;begin
 if p_status not in ('SENT','FAILED','SKIPPED','NO_CONSENT','UNCERTAIN') then raise exception 'Estado no válido.';end if;
 if coalesce(p_provider_id,'')<>'' then
 select gym_id into v_gym from public.marketing_messages where id=p_id and claim_id=p_claim_id;
 perform pg_advisory_xact_lock(hashtextextended(v_gym::text||'/delivery/'||p_provider_id,0));
 end if;
 update public.marketing_messages set status=p_status,whatsapp_message_id=p_provider_id,error_message=left(p_error,500),sent_at=case when p_status='SENT' then now() end,updated_at=now() where id=p_id and claim_id=p_claim_id and status in ('PROCESSING','UNCERTAIN') returning * into r;
 if not found then return false;end if;
 update public.automation_runs set status=p_status,reason=left(p_error,500) where gym_id=r.gym_id and dedupe_key=r.dedupe_key;
 -- Provider delivery callbacks can precede the HTTP send response. Replay their
 -- stored, signed states under the same lock instead of losing them.
 if coalesce(p_provider_id,'')<>'' then
 for e in select payload from private.marketing_webhook_events where provider='META_STATUS' and gym_id=r.gym_id and payload->>'message_id'=p_provider_id order by received_at loop
 perform public.marketing_service_status(r.gym_id,p_provider_id,e.payload->>'status',(e.payload->>'at')::timestamptz);
 end loop;end if;return true;end$$;
