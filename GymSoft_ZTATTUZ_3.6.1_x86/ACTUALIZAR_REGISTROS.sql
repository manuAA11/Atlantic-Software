-- Real event times and readable client names; existing audit rows are not rewritten.
begin;
set local lock_timeout='8s';
set local statement_timeout='90s';
alter table public.audit_logs alter column created_at set default clock_timestamp();
create index if not exists audit_client_history on public.audit_logs(gym_id,entity_id,created_at desc,id desc) where entity_type='clients';
create index if not exists audit_client_name_snapshot on public.audit_logs(gym_id,(details->>'client_id'),created_at desc,id desc) where details ? 'client_name';
create or replace function private.audit_client_name(p_gym uuid,p_client text) returns text
language sql stable security definer set search_path='' as $$
 select coalesce(
  (select nullif(btrim(concat_ws(' ',c.first_name,c.last_name)),'') from public.clients c where c.gym_id=p_gym and c.id=case when p_client ~ '^[0-9]{1,18}$' then p_client::bigint end),
  (select nullif(a.details->>'client_name','') from public.audit_logs a where a.gym_id=p_gym and a.entity_type='clients' and a.entity_id=p_client and nullif(a.details->>'client_name','') is not null order by a.created_at desc,a.id desc limit 1),
  (select nullif(a.details->>'client_name','') from public.audit_logs a where a.gym_id=p_gym and a.details->>'client_id'=p_client and a.details ? 'client_name' and nullif(a.details->>'client_name','') is not null order by a.created_at desc,a.id desc limit 1)
 )
$$;
create or replace function private.audit_readable_summary(p_summary text,p_name text) returns text
language sql immutable set search_path='' as $$
 select regexp_replace(coalesce(p_summary,''),'\mcliente\s+#?\s*[0-9]+\M',replace(coalesce(nullif(p_name,''),'Cliente eliminado (nombre no disponible)'),E'\\',E'\\\\'),'gi')
$$;
create or replace function private.audit_prepare_record() returns trigger
language plpgsql security definer set search_path='' as $$
declare cid text;label text;actor uuid:=auth.uid();begin
 cid:=coalesce(nullif(new.details->>'client_id',''),new.details#>>'{after,client_id}',new.details#>>'{before,client_id}',case when new.entity_type='clients' then new.entity_id end);
 if cid is not null then
  label:=coalesce(nullif(new.details->>'client_name',''),private.audit_client_name(new.gym_id,cid));
  new.details:=new.details||jsonb_build_object('client_id',cid,'client_name',label);
  new.summary:=private.audit_readable_summary(new.summary,label);
 end if;
 -- recorded_by belongs to the original payment; the editor is the current user.
 if actor is not null then
  new.actor_user_id:=actor;
  select coalesce(u.email,'Usuario'),coalesce(gu.role,'authenticated') into new.actor_email,new.actor_role
  from auth.users u left join public.gym_users gu on gu.user_id=u.id and gu.gym_id=new.gym_id where u.id=actor;
 end if;
 return new;
end$$;
drop trigger if exists audit_prepare_record on public.audit_logs;
create trigger audit_prepare_record before insert on public.audit_logs for each row execute function private.audit_prepare_record();
create or replace function private.audit_local_iso(p_time timestamptz,p_zone text) returns text
language sql stable set search_path='' as $$
 select to_char(p_time at time zone p_zone,'YYYY-MM-DD"T"HH24:MI:SS.US') || case when seconds<0 then '-' else '+' end || to_char(make_interval(secs=>abs(seconds)::double precision),'HH24:MI')
 from (select extract(epoch from ((p_time at time zone p_zone)-(p_time at time zone 'UTC'))) seconds) x
$$;
create or replace function public.get_audit_logs(p_gym_id uuid,p_limit integer default 200,p_action text default '') returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare result jsonb;zone text;begin
 if auth.uid() is null or not private.user_has_gym_role(p_gym_id,array['admin']::text[]) then raise exception 'La auditoría es exclusiva del administrador.' using errcode='42501';end if;
 select coalesce(to_jsonb(g)->>'timezone','America/Bogota') into zone from public.gyms g where id=p_gym_id;
 select coalesce(jsonb_agg(to_jsonb(x)||jsonb_build_object('summary',private.audit_readable_summary(x.summary,n.client_name),'client_name',n.client_name,'timezone',zone,'occurred_at',x.created_at,'created_at',private.audit_local_iso(x.created_at,zone),'created_at_local',to_char(x.created_at at time zone zone,'DD/MM/YYYY HH24:MI:SS')) order by x.created_at desc,x.id desc),'[]') into result
 from (select * from public.audit_logs where gym_id=p_gym_id and (btrim(coalesce(p_action,''))='' or action=btrim(p_action)) order by created_at desc,id desc limit least(greatest(coalesce(p_limit,200),1),500)) x
 cross join lateral (select coalesce(nullif(x.details->>'client_name',''),private.audit_client_name(p_gym_id,coalesce(x.details->>'client_id',x.details#>>'{after,client_id}',x.details#>>'{before,client_id}',case when x.entity_type='clients' then x.entity_id end))) client_name) n;
 return result;
end$$;
revoke all on function private.audit_client_name(uuid,text),private.audit_readable_summary(text,text),private.audit_prepare_record(),private.audit_local_iso(timestamptz,text) from public,anon,authenticated;
revoke all on function public.get_audit_logs(uuid,integer,text) from public,anon,authenticated;
grant execute on function public.get_audit_logs(uuid,integer,text) to authenticated;
commit;
