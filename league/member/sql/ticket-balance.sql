-- Display-only League projection of the authoritative Gym ticket balance.
-- Does not change membership rules, payment values, consumption or access decisions.
create or replace function league_member_private.membership(p_actor uuid,p_gym uuid)
returns jsonb language plpgsql security invoker set search_path='' as $$
declare source_client bigint;s jsonb;
begin
 source_client:=(league_member_private.connection(p_actor,p_gym)->>'client_id')::bigint;
 if source_client is null then raise exception 'Perfil no disponible.' using errcode='42501';end if;
 s:=private.membership_snapshot_json(p_gym,source_client);
 return jsonb_build_object('membership_id',nullif(s->>'membership_id',''),'plan_name',nullif(s->>'plan_name',''),
  'active',coalesce((s->>'allowed')::boolean,false),'frozen',coalesce((s->>'frozen')::boolean,false),
  'starts_at',nullif(s->>'membership_start',''),'ends_at',case when coalesce((s->>'has_expiration')::boolean,true) then nullif(s->>'membership_end','') else null end,
  'status',case when coalesce((s->>'frozen')::boolean,false) then 'FROZEN' when nullif(s->>'membership_id','') is null then 'NO_PLAN' else coalesce(s->>'status',s->>'membership_state','INACTIVE') end,
  'remaining_days',case when not coalesce((s->>'frozen')::boolean,false) and coalesce((s->>'has_expiration')::boolean,true) and nullif(s->>'membership_end','') is not null then greatest(0,nullif(s->>'membership_end','')::date-private.gym_local_date(p_gym)) else null end,
  'has_expiration',coalesce((s->>'has_expiration')::boolean,true),
  'entry_limit',s->'entry_limit','entries_used',s->'entries_used','entries_remaining',s->'entries_remaining',
  'already_consumed_today',coalesce((s->>'already_consumed_today')::boolean,false),
  'renewable',coalesce(s->>'membership_type','COMMERCIAL')<>'INTERNAL');
end $$;
revoke all on function league_member_private.membership(uuid,uuid) from public,anon,authenticated;
grant execute on function league_member_private.membership(uuid,uuid) to service_role;
