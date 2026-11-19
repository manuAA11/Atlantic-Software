-- Notifications from confirmed source reservations. This table belongs to League only.
begin;
create table league_member_private.reservation_notices(
 athlete_id uuid not null,gym_id uuid not null,class_id bigint not null,status text not null,revision integer not null,
 primary key(athlete_id,gym_id,class_id)
);
alter table league_member_private.reservation_notices enable row level security;
revoke all on league_member_private.reservation_notices from public,anon,authenticated;
grant all on league_member_private.reservation_notices to service_role;
create function public.league_member_reservation_notice(p_actor uuid,p_gym uuid,p_class bigint) returns void
language plpgsql security invoker set search_path='' as $$
declare client bigint;state text;rev integer;
begin
 client:=(league_member_private.connection(p_actor,p_gym)->>'client_id')::bigint;
 if client is null then raise exception 'Vinculación no disponible.' using errcode='42501';end if;
 select status into state from public.reservations where gym_id=p_gym and class_id=p_class and client_id=client limit 1;
 if state not in ('RESERVADA','CANCELADA') or state is null then return;end if;
 insert into league_member_private.reservation_notices values(p_actor,p_gym,p_class,state,1)
 on conflict(athlete_id,gym_id,class_id) do update
 set status=excluded.status,revision=reservation_notices.revision+case when reservation_notices.status<>excluded.status then 1 else 0 end returning revision into rev;
 perform league_member_private.emit(p_actor,p_gym,'reservation:'||p_class||':'||rev,
  case when state='RESERVADA' then 'Reserva confirmada' else 'Reserva cancelada' end,
  case when state='RESERVADA' then 'Tu cupo quedó reservado. Consulta los detalles en tu agenda.' else 'Tu reserva fue cancelada.' end,'/agenda');
end $$;
revoke all on function public.league_member_reservation_notice(uuid,uuid,bigint) from public,anon,authenticated;
grant execute on function public.league_member_reservation_notice(uuid,uuid,bigint) to service_role;
commit;
