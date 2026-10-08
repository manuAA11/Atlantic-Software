create or replace function public.marketing_create_test_client(p_gym_id uuid) returns bigint language plpgsql security definer set search_path='' as $$
declare cid bigint;begin perform public.marketing_access(p_gym_id);perform pg_advisory_xact_lock(hashtextextended(p_gym_id::text||'/sandbox',0));
 select client_id into cid from private.marketing_sandbox_clients where gym_id=p_gym_id;if cid is not null then return cid;end if;
 insert into public.clients(gym_id,document,first_name,last_name,active) values(p_gym_id,'TEST-'||gen_random_uuid(),'PRUEBA','Integraciones',true) returning id into cid;
 insert into private.marketing_sandbox_clients(gym_id,client_id,created_by) values(p_gym_id,cid,auth.uid());
 perform private.marketing_audit(p_gym_id,'SANDBOX_CLIENT_CREATED','client',cid::text);return cid;end$$;
create or replace function public.marketing_service_payment_request(p_gym_id uuid,p_client_id bigint,p_plan_id bigint,p_key text) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.payment_requests;p public.plans;conn public.marketing_connections;begin
 if not private.marketing_operable(p_gym_id) then raise exception 'El gimnasio no tiene una suscripción activa.';end if;
 select * into conn from public.marketing_connections where gym_id=p_gym_id and provider='WOMPI' and status='CONNECTED';
 if not found or not exists(select 1 from public.marketing_settings where gym_id=p_gym_id and online_payments_enabled) then raise exception 'Los pagos online todavía no están habilitados.';end if;
 if conn.mode='prod' and not (select production_allowed from private.marketing_platform where singleton) then raise exception 'Producción no autorizada.';end if;
 if conn.mode='test' and not exists(select 1 from private.marketing_sandbox_clients where gym_id=p_gym_id and client_id=p_client_id) then raise exception 'Sandbox utiliza únicamente el cliente de prueba de integraciones.';end if;
 if not exists(select 1 from public.clients where gym_id=p_gym_id and id=p_client_id and active) then raise exception 'Cliente no disponible.';end if;
 select * into p from public.plans where gym_id=p_gym_id and id=p_plan_id and active and price>0;
 if not found then raise exception 'El plan no está disponible para pagos online.';end if;
 if length(p_key) not between 8 and 200 then raise exception 'Referencia de solicitud no válida.';end if;
 insert into public.payment_requests(gym_id,client_id,plan_id,plan_snapshot,mode,amount_in_cents,reference,idempotency_key,expires_at)
 values(p_gym_id,p_client_id,p.id,to_jsonb(p),conn.mode,p.price*100,'GS-'||replace(gen_random_uuid()::text,'-',''),p_key,now()+interval '48 hours') on conflict(gym_id,idempotency_key) do nothing returning * into r;
 if not found then select * into r from public.payment_requests where gym_id=p_gym_id and idempotency_key=p_key;
 if r.client_id<>p_client_id or r.plan_id<>p_plan_id or r.mode<>conn.mode then raise exception 'La referencia ya pertenece a otra solicitud.';end if;end if;return to_jsonb(r);end$$;
-- Reuse the installed, already tested calendar/quota renewal implementation.
-- Only the permission prelude is replaced; this private clone is service-only.
do $$declare def text;before text;sig regprocedure;begin
 sig:=to_regprocedure('private.ztattuz_add_membership(uuid,bigint,bigint,date,bigint,text,text,text)');
 if sig is null then sig:=to_regprocedure('public.add_membership_accumulating_internal(uuid,bigint,bigint,date,bigint,text,text,text)');end if;
 if sig is null then raise exception 'No se encontró el motor actual de renovación.';end if;
 def:=pg_get_functiondef(sig);before:=def;
 def:=regexp_replace(def,'CREATE OR REPLACE FUNCTION (private.ztattuz_add_membership|public.add_membership_accumulating_internal)\(', 'CREATE OR REPLACE FUNCTION private.marketing_apply_membership(');
 def:=replace(def,'p_notes text)','p_notes text, p_plan_snapshot jsonb)');
 def:=regexp_replace(def,'if not private.user_has_gym_role\([\s\S]*?end if;','','i');
 if def=before or position('user_has_gym_role' in def)>0 then raise exception 'Revisa la compatibilidad del motor de renovación antes de continuar.';end if;
 def:=replace(def,'from public.plans p','from jsonb_populate_record(null::public.plans,p_plan_snapshot) p');
 if position('jsonb_populate_record' in def)=0 then raise exception 'No se pudo fijar el plan de la solicitud.';end if;execute def;
end$$;
create or replace function public.marketing_service_apply_payment(p_gym_id uuid,p_transaction jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare r public.payment_requests;existing public.payment_transactions;tid text:=p_transaction->>'id';v_status text:=p_transaction->>'status';v_mode text:=p_transaction->>'mode';v_amount bigint;v_mid bigint;v_end date;v_started timestamptz;begin
 if length(coalesce(tid,'')) not between 1 and 150 or coalesce(v_status,'') not in ('PENDING','APPROVED','DECLINED','VOIDED','ERROR') then raise exception 'Transacción no válida.';end if;
 select * into r from public.payment_requests where gym_id=p_gym_id and reference=p_transaction->>'reference' for update;
 if not found then raise exception 'Referencia de pago desconocida.';end if;
 if (p_transaction->>'amount_in_cents')::bigint is distinct from r.amount_in_cents or (p_transaction->>'currency') is distinct from r.currency or v_mode is distinct from r.mode then raise exception 'El valor, la moneda o el ambiente no coinciden con la solicitud.';end if;
 select * into existing from public.payment_transactions where provider_transaction_id=tid and mode=v_mode;
 if found and (existing.gym_id<>p_gym_id or existing.payment_request_id<>r.id) then raise exception 'Transacción asociada a otra solicitud.';end if;
 if r.status='APPROVED' and existing.status='APPROVED' and v_status='APPROVED' then return jsonb_build_object('duplicate',true,'membership_id',r.renewed_membership_id);end if;
 if p_transaction->>'created_at' is not null and (p_transaction->>'created_at') !~ '^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$' then
 raise exception 'La fecha de la transacción debe incluir hora y timezone.';end if;
 v_started:=(p_transaction->>'created_at')::timestamptz;
 insert into public.payment_transactions(gym_id,payment_request_id,provider_transaction_id,mode,status,amount_in_cents,currency,reference,provider_created_at)
 values(p_gym_id,r.id,tid,v_mode,v_status,r.amount_in_cents,r.currency,r.reference,v_started)
 on conflict(mode,provider_transaction_id) do update set status=excluded.status,processed_at=now();
 if r.status='APPROVED' then
 -- A second charge or reversal needs review; never renew twice or silently undo access.
 update public.payment_transactions set requires_review=true where mode=v_mode and provider_transaction_id=tid;
 perform private.marketing_audit(p_gym_id,'PAYMENT_REQUIRES_REVIEW','payment_request',r.id::text,jsonb_build_object('transaction_id',tid,'status',v_status));
 return jsonb_build_object('duplicate',true,'requires_review',true,'membership_id',r.renewed_membership_id);end if;
 if v_status='APPROVED' then
 if r.client_id is null or r.plan_id is null or v_started is null or v_started>r.expires_at or v_started<r.created_at-interval '1 minute' then raise exception 'No se puede aplicar este pago automáticamente. Requiere revisión.';end if;
 if v_mode='test' and not exists(select 1 from private.marketing_sandbox_clients where gym_id=p_gym_id and client_id=r.client_id) then raise exception 'Cliente sandbox no válido.';end if;
 v_amount:=case when v_mode='test' then 0 else r.amount_in_cents/100 end;
 if r.amount_in_cents%100<>0 then raise exception 'El valor no corresponde al plan.';end if;
 select m.membership_id,m.end_date into v_mid,v_end from private.marketing_apply_membership(p_gym_id,r.client_id,r.plan_id,private.gym_local_date(p_gym_id),v_amount,'Wompi',r.reference,case when v_mode='test' then 'PRUEBA SANDBOX · sin ingreso real' else 'Renovación online confirmada' end,r.plan_snapshot) m;
 update public.memberships set payment_source=case when v_mode='test' then 'WOMPI_TEST' else 'WOMPI' end,paid_at=now() where id=v_mid and gym_id=p_gym_id;
 update public.payment_requests set status='APPROVED',paid_at=now(),renewed_membership_id=v_mid where id=r.id;
 insert into private.marketing_events(gym_id,client_id,event_type,entity_id,payload) values(p_gym_id,r.client_id,'ONLINE_APPROVED',r.id::text,jsonb_build_object('payment_request_id',r.id,'membership_id',v_mid,'mode',v_mode)) on conflict do nothing;
 perform private.marketing_audit(p_gym_id,'PAYMENT_PROCESSED','payment_request',r.id::text,jsonb_build_object('transaction_id',tid,'mode',v_mode));
 perform private.marketing_audit(p_gym_id,'MEMBERSHIP_RENEWED','membership',v_mid::text,jsonb_build_object('payment_request_id',r.id));
 return jsonb_build_object('duplicate',false,'membership_id',v_mid,'end_date',v_end,'mode',v_mode);
 else
 update public.payment_requests set status=v_status where id=r.id;
 if v_status='DECLINED' then insert into private.marketing_events(gym_id,client_id,event_type,entity_id,payload) values(p_gym_id,r.client_id,'ONLINE_DECLINED',tid,jsonb_build_object('payment_request_id',r.id,'mode',v_mode)) on conflict do nothing;end if;
 return jsonb_build_object('status',v_status,'duplicate',false);end if;
end$$;
