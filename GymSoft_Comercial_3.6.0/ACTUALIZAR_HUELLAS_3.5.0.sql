begin;
set local lock_timeout='8s';
create table if not exists private.client_fingerprints (
 gym_id uuid not null references public.gyms(id) on delete cascade,
 client_id bigint primary key references public.clients(id) on delete cascade,
 template bytea not null check(octet_length(template) between 30 and 4096),
 revision uuid not null default gen_random_uuid(),
 updated_at timestamptz not null default now(),
 updated_by uuid not null
);
alter table private.client_fingerprints enable row level security;
revoke all on private.client_fingerprints from public,anon,authenticated;
create index if not exists client_fingerprints_gym on private.client_fingerprints(gym_id);
create unique index if not exists client_fingerprints_exact_unique on private.client_fingerprints(gym_id,md5(template));
create or replace function private.gym_fingerprints(p_gym_id uuid,p_action text,p_client_id bigint default null,p_template text default null,p_expected uuid default null)
returns jsonb language plpgsql security definer set search_path='' as $$
declare v_old private.client_fingerprints; v_data bytea; v_result jsonb;
begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
  raise exception 'No tienes acceso a las huellas de este gimnasio.' using errcode='42501';
 end if;
 if p_action='list' then
  select coalesce(jsonb_agg(jsonb_build_object('client_id',f.client_id,'template',replace(encode(f.template,'base64'),E'\n',''),'revision',f.revision) order by f.client_id),'[]'::jsonb)
  into v_result from private.client_fingerprints f join public.clients c on c.id=f.client_id and c.gym_id=f.gym_id
  where f.gym_id=p_gym_id;
  return v_result;
 end if;
 if p_action not in ('save','delete') then raise exception 'Operación no válida.'; end if;
 -- Serialize modifications to a client, even before the first fingerprint exists.
 perform 1 from public.clients where id=p_client_id and gym_id=p_gym_id for update;
 if not found then raise exception 'El cliente no pertenece al gimnasio.' using errcode='42501'; end if;
 select * into v_old from private.client_fingerprints where client_id=p_client_id for update;
 if v_old.revision is distinct from p_expected then
  raise exception 'La huella cambió en otro equipo. Actualiza antes de continuar.' using errcode='40001';
 end if;
 if p_action='delete' then
  delete from private.client_fingerprints where client_id=p_client_id and gym_id=p_gym_id;
  return jsonb_build_object('saved',true);
 end if;
 if p_template is null or length(p_template)>5500 then raise exception 'Plantilla no válida.'; end if;
 v_data:=decode(p_template,'base64');
 if octet_length(v_data) not between 30 and 4096 or substring(v_data from 1 for 4)<>decode('464d5200','hex') then
  raise exception 'La plantilla no es ANSI FMR válida.';
 end if;
 insert into private.client_fingerprints(gym_id,client_id,template,updated_by)
 values(p_gym_id,p_client_id,v_data,auth.uid())
 on conflict(client_id) do update set template=excluded.template,revision=gen_random_uuid(),updated_at=now(),updated_by=auth.uid()
 returning jsonb_build_object('saved',true,'revision',revision) into v_result;
 return v_result;
end $$;
revoke all on function private.gym_fingerprints(uuid,text,bigint,text,uuid) from public,anon,authenticated;
grant execute on function private.gym_fingerprints(uuid,text,bigint,text,uuid) to authenticated;
create or replace function public.gym_fingerprints(p_gym_id uuid,p_action text,p_client_id bigint default null,p_template text default null,p_expected uuid default null)
returns jsonb language sql security invoker set search_path='' as $$
 select private.gym_fingerprints(p_gym_id,p_action,p_client_id,p_template,p_expected)
$$;
revoke all on function public.gym_fingerprints(uuid,text,bigint,text,uuid) from public,anon,authenticated;
grant execute on function public.gym_fingerprints(uuid,text,bigint,text,uuid) to authenticated;
commit;
