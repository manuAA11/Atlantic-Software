-- Staff-only notices. No payment, membership or access decision is changed.
begin;
set local lock_timeout='8s';
set local statement_timeout='90s';

create table if not exists private.client_staff_notes (
 gym_id uuid not null references public.gyms(id) on delete cascade,
 client_id bigint not null references public.clients(id) on delete cascade,
 note_text text not null default '' check(char_length(note_text)<=2000),
 revision bigint not null default 1 check(revision>0),
 updated_at timestamptz not null default clock_timestamp(),
 updated_by uuid not null,
 primary key(gym_id,client_id)
);
create index if not exists client_staff_notes_client_idx on private.client_staff_notes(client_id);
alter table private.client_staff_notes enable row level security;
revoke all on private.client_staff_notes from public,anon,authenticated;

create or replace function private.staff_access_context(p_gym_id uuid,p_client_id bigint,p_snapshot jsonb)
returns jsonb language plpgsql stable security definer set search_path='' as $$
declare n private.client_staff_notes; membership_note text; reason text; warning text:='';
 today date:=private.gym_local_date(p_gym_id); ends date; starts date; days integer;
 permitted boolean:=coalesce(p_snapshot->>'result',case when (p_snapshot->>'allowed')::boolean then 'PERMITIDA' else 'DENEGADA' end)='PERMITIDA';
begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
  raise exception 'No tienes permiso para consultar las notas de este cliente.' using errcode='42501';
 end if;
 if not exists(select 1 from public.clients where gym_id=p_gym_id and id=p_client_id) then
  raise exception 'Cliente no encontrado.' using errcode='P0002';
 end if;
 select * into n from private.client_staff_notes where gym_id=p_gym_id and client_id=p_client_id;
 select m.notes into membership_note from public.memberships m
 where m.gym_id=p_gym_id and m.client_id=p_client_id and m.id=nullif(p_snapshot->>'membership_id','')::bigint;
 ends:=nullif(p_snapshot->>'membership_end','')::date;
 starts:=nullif(p_snapshot->>'membership_start','')::date;
 if ends is not null and coalesce((p_snapshot->>'has_expiration')::boolean,true) then days:=ends-today;end if;
 if coalesce((p_snapshot->>'override')::boolean,false) and permitted then
  reason:='Ingreso excepcional autorizado por Administración.';
 elsif not coalesce((p_snapshot->>'active')::boolean,true) then
  reason:='El cliente está inactivo.';
 elsif coalesce((p_snapshot->>'frozen')::boolean,false) then
  reason:=coalesce(nullif(p_snapshot->>'denial_message',''),'La membresía está congelada.');
 elsif permitted then
  reason:=case when p_snapshot->>'membership_type'='INTERNAL' then 'Autorización interna vigente.' else 'Membresía vigente.' end;
 elsif nullif(p_snapshot->>'membership_id','') is null then
  reason:='El cliente no tiene una membresía registrada.';
 elsif starts>today then
  reason:='La membresía inicia el '||to_char(starts,'DD/MM/YYYY')||'.';
 elsif days<0 then
  reason:='La membresía venció el '||to_char(ends,'DD/MM/YYYY')||'.';
 elsif p_snapshot->>'membership_active'='false' then
  reason:='La autorización interna está desactivada.';
 elsif p_snapshot->>'entries_remaining'='0' then
  reason:='La tiquetera no tiene entradas disponibles.';
 else
  reason:=coalesce(nullif(p_snapshot->>'denial_message',''),'Estado de la membresía: '||coalesce(p_snapshot->>'status','sin autorización')||'.');
 end if;
 if permitted and not coalesce((p_snapshot->>'frozen')::boolean,false) then
  warning:=case when days=0 then 'La membresía vence hoy.' when days=1 then 'La membresía vence mañana.'
   when days between 2 and 7 then 'La membresía vence en '||days||' días ('||to_char(ends,'DD/MM/YYYY')||').' else '' end;
 end if;
 return p_snapshot||jsonb_build_object('client_notice',coalesce(n.note_text,''),
  'client_notice_revision',coalesce(n.revision,0),'membership_notes',coalesce(membership_note,''),
  'access_detail',reason,'expiry_notice',warning);
end$$;
revoke all on function private.staff_access_context(uuid,bigint,jsonb) from public,anon,authenticated;

create or replace function public.staff_client_notes(p_gym_id uuid,p_client_id bigint)
returns jsonb language plpgsql security definer set search_path='' as $$
declare n private.client_staff_notes;s jsonb;
begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
  raise exception 'No tienes permiso para consultar las notas de este cliente.' using errcode='42501';
 end if;
 s:=private.staff_access_context(p_gym_id,p_client_id,private.membership_snapshot_json(p_gym_id,p_client_id));
 select * into n from private.client_staff_notes where gym_id=p_gym_id and client_id=p_client_id;
 return jsonb_build_object('client_notice',s->>'client_notice','revision',coalesce(n.revision,0),
  'updated_at',n.updated_at,'membership_notes',s->>'membership_notes');
end$$;

create or replace function public.save_staff_client_note(p_gym_id uuid,p_client_id bigint,p_note text,p_expected_revision bigint)
returns jsonb language plpgsql security definer set search_path='' as $$
declare n private.client_staff_notes; clean text:=btrim(coalesce(p_note,''));old_text text;
begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin','receptionist']) then
  raise exception 'No tienes permiso para editar las notas de este cliente.' using errcode='42501';
 end if;
 if char_length(clean)>2000 then raise exception 'La nota admite un máximo de 2000 caracteres.' using errcode='22001';end if;
 -- Same client lock as saves/deletes; serializes the first note and revision checks.
 perform 1 from public.clients where gym_id=p_gym_id and id=p_client_id for update;
 if not found then raise exception 'Cliente no encontrado.' using errcode='P0002';end if;
 select * into n from private.client_staff_notes where gym_id=p_gym_id and client_id=p_client_id;
 old_text:=coalesce(n.note_text,'');
 if clean=old_text then
  return jsonb_build_object('client_notice',old_text,'revision',coalesce(n.revision,0),'updated_at',n.updated_at);
 end if;
 if p_expected_revision is distinct from coalesce(n.revision,0) then
  raise exception 'La nota cambió en otro equipo. Cierra y vuelve a abrir Notas y avisos para consultar la versión actual antes de guardar.' using errcode='40001';
 end if;
 insert into private.client_staff_notes(gym_id,client_id,note_text,revision,updated_at,updated_by)
 values(p_gym_id,p_client_id,clean,coalesce(n.revision,0)+1,private.gym_server_now(),auth.uid())
 on conflict(gym_id,client_id) do update set note_text=excluded.note_text,revision=excluded.revision,
  updated_at=excluded.updated_at,updated_by=excluded.updated_by returning * into n;
 insert into public.audit_logs(gym_id,action,entity_type,entity_id,summary,details)
 values(p_gym_id,'CLIENT_NOTE_UPDATED','clients',p_client_id::text,'Nota del cliente actualizada',
  jsonb_build_object('previous_note',old_text,'note',clean,'revision',n.revision));
 return jsonb_build_object('client_notice',n.note_text,'revision',n.revision,'updated_at',n.updated_at);
end$$;
revoke all on function public.staff_client_notes(uuid,bigint),public.save_staff_client_note(uuid,bigint,text,bigint) from public,anon;
grant execute on function public.staff_client_notes(uuid,bigint),public.save_staff_client_note(uuid,bigint,text,bigint) to authenticated;

-- Enrich staff routes only. The generic snapshot is also used by member-facing
-- chat/League and MUST NOT contain internal notices. Keep commercial wrappers,
-- licence checks, searches and all original registration/consumption logic.
do $patch$
declare f record;def text;pattern text;matches integer;patched integer:=0;
begin
 for f in select p.oid,p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
  where n.nspname in ('public','private') and p.proname in ('reception_list_clients','reception_membership_snapshot') loop
  def:=pg_get_functiondef(f.oid);
  if position('private.staff_access_context' in def)>0 then patched:=patched+1;continue;end if;
  pattern:=case f.proname when 'reception_list_clients' then
   'private\.membership_snapshot_json\(\s*p_gym_id\s*,\s*c\.id\s*\)' else
   'private\.membership_snapshot_json\(\s*p_gym_id\s*,\s*p_client_id\s*\)' end;
  select count(*) into matches from regexp_matches(def,pattern,'g');
  if matches=1 then
   def:=regexp_replace(def,pattern,case f.proname when 'reception_list_clients' then
    'private.staff_access_context(p_gym_id,c.id,private.membership_snapshot_json(p_gym_id,c.id))' else
    'private.staff_access_context(p_gym_id,p_client_id,private.membership_snapshot_json(p_gym_id,p_client_id))' end);
   execute def;patched:=patched+1;
  elsif position('private.require_current_access' in def)=0 then
   raise exception 'Ruta de personal inesperada: %',f.oid::regprocedure;
  end if;
 end loop;
 if patched<>2 then raise exception 'No se encontraron ambas rutas de consulta de personal.';end if;
 select pg_get_functiondef('private.daily_register_checkin(uuid,bigint,text,boolean)'::regprocedure) into def;
 if position('private.staff_access_context' in def)=0 then
  if (length(def)-length(replace(def,'return s||jsonb_build_object(','')))/length('return s||jsonb_build_object(')<>1
   or (length(def)-length(replace(def,'''local_date'',ch.local_date);','')))/length('''local_date'',ch.local_date);')<>1 then
   raise exception 'Retorno de registro de entrada inesperado; no se modificó la autorización.';
  end if;
  def:=replace(def,'return s||jsonb_build_object(','return private.staff_access_context(p_gym_id,p_client_id,s||jsonb_build_object(');
  def:=replace(def,'''local_date'',ch.local_date);','''local_date'',ch.local_date));');
  execute def;
 end if;
end $patch$;
notify pgrst,'reload schema';
commit;
