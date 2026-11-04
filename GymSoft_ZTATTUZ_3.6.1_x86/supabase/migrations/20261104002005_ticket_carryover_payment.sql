-- Additive RPC: old clients retain the original zero-charge carryover contract.
create or replace function private.register_ticket_carryover_with_payment(
 p_gym_id uuid, p_client_id bigint, p_plan_id bigint, p_start date,
 p_entries_used bigint, p_notes text, p_request_id uuid,
 p_amount bigint, p_payment_method text, p_payment_reference text
) returns table(membership_id bigint, start_date date, end_date date)
language plpgsql security definer set search_path = '' as $$
declare
 p public.plans%rowtype; m public.memberships%rowtype; ending date; mid bigint;
 method text; reference text; note text;
begin
 if not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
  raise exception 'No tienes permiso para registrar una tiquetera.' using errcode='42501';
 end if;
 if not private.client_belongs_to_gym(p_client_id,p_gym_id) then
  raise exception 'El cliente no pertenece al gimnasio.' using errcode='23503';
 end if;
 if p_request_id is null or p_start is null or p_start>private.gym_local_date(p_gym_id) or p_entries_used is null then
  raise exception 'Revisa la fecha de inicio y las entradas utilizadas.' using errcode='22023';
 end if;
 if p_amount is null or p_amount<0 then
  raise exception 'El cobro debe ser cero o un valor positivo.' using errcode='22023';
 end if;
 if p_amount>0 and nullif(trim(p_payment_method),'') is null then
  raise exception 'Indica el método del cobro.' using errcode='22023';
 end if;
 method:=case when p_amount=0 then 'Saldo inicial' else trim(p_payment_method) end;
 reference:=case when p_amount=0 then '' else trim(coalesce(p_payment_reference,'')) end;
 note:=case when p_amount=0 then 'Tiquetera trasladada sin nuevo cobro. '
  else 'Tiquetera ya iniciada con cobro registrado ahora. ' end || trim(coalesce(p_notes,''));
 perform pg_catalog.pg_advisory_xact_lock(p_client_id);
 select * into m from public.memberships where gym_id=p_gym_id and carryover_key=p_request_id;
 if found then
  if m.client_id<>p_client_id or m.plan_id<>p_plan_id or m.start_date<>p_start
   or m.initial_entries_used<>p_entries_used or m.payment_status<>'posted'
   or m.amount<>p_amount or m.amount_paid<>p_amount
   or m.payment_method<>method or coalesce(m.payment_reference,'')<>reference
   or coalesce(m.notes,'')<>note then
   raise exception 'Esta solicitud ya corresponde a otra operación. Actualiza la ficha.' using errcode='22023';
  end if;
  return query select m.id,m.start_date,m.end_date; return;
 end if;
 select * into p from public.plans where gym_id=p_gym_id and id=p_plan_id and active for share;
 if not found or p.entry_limit is null or p.plan_type='INTERNAL' then
  raise exception 'Selecciona una tiquetera comercial activa.' using errcode='22023';
 end if;
 if p_entries_used<0 or p_entries_used>p.entry_limit then
  raise exception 'Las entradas utilizadas exceden el cupo de la tiquetera.' using errcode='22023';
 end if;
 ending:=private.ticket_end_date(p_start,p.duration_days,p.duration_months);
 if exists(select 1 from public.memberships x where x.gym_id=p_gym_id and x.client_id=p_client_id
  and x.payment_status='posted' and x.start_date<=ending and x.end_date>=p_start) then
  raise exception 'Ya existe una membresía en esas fechas. Revisa los registros del cliente antes de trasladar esta tiquetera.' using errcode='22023';
 end if;
 insert into public.memberships(gym_id,client_id,plan_id,start_date,end_date,entry_limit,initial_entries_used,
  amount,amount_paid,payment_method,payment_reference,notes,recorded_by,carryover_key,paid_at)
 values(p_gym_id,p_client_id,p_plan_id,p_start,ending,p.entry_limit,p_entries_used,
  p_amount,p_amount,method,reference,note,auth.uid(),p_request_id,
  case when p_amount>0 then private.gym_server_now()
   else p_start::timestamp at time zone private.gym_timezone(p_gym_id) end)
 returning id into mid;
 return query select mid,p_start,ending;
end $$;

create or replace function public.register_ticket_carryover_with_payment(
 p_gym_id uuid, p_client_id bigint, p_plan_id bigint, p_start date,
 p_entries_used bigint, p_notes text, p_request_id uuid,
 p_amount bigint, p_payment_method text, p_payment_reference text
) returns table(membership_id bigint, start_date date, end_date date)
language sql security invoker set search_path = '' as $$
 select * from private.register_ticket_carryover_with_payment(
  p_gym_id,p_client_id,p_plan_id,p_start,p_entries_used,p_notes,p_request_id,
  p_amount,p_payment_method,p_payment_reference)
$$;
revoke all on function private.register_ticket_carryover_with_payment(uuid,bigint,bigint,date,bigint,text,uuid,bigint,text,text) from public,anon;
revoke all on function public.register_ticket_carryover_with_payment(uuid,bigint,bigint,date,bigint,text,uuid,bigint,text,text) from public,anon;
grant execute on function private.register_ticket_carryover_with_payment(uuid,bigint,bigint,date,bigint,text,uuid,bigint,text,text) to authenticated;
grant execute on function public.register_ticket_carryover_with_payment(uuid,bigint,bigint,date,bigint,text,uuid,bigint,text,text) to authenticated;
notify pgrst,'reload schema';
