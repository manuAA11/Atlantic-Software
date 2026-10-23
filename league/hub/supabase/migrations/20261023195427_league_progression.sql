begin;
alter table public.league_profiles add column weekly_goal integer not null default 3 check(weekly_goal between 1 and 7);
alter table public.league_xp_events drop constraint league_xp_events_kind_check;
alter table public.league_xp_events add constraint league_xp_events_kind_check check(kind in ('WORKOUT','ATTENDANCE','STREAK','GOAL'));
create function league_private.workout_rewards() returns trigger language plpgsql security definer set search_path='' as $$
declare day_utc date:=(new.finished_at at time zone 'UTC')::date;
 week_utc timestamp:=date_trunc('week',new.finished_at at time zone 'UTC');days integer;target integer;
begin
 select count(distinct (finished_at at time zone 'UTC')::date) into days
  from public.league_workouts where athlete_id=new.athlete_id and
  (finished_at at time zone 'UTC')::date between day_utc-2 and day_utc;
 if days=3 then
  insert into public.league_xp_events(athlete_id,kind,source_key,points)
   values(new.athlete_id,'STREAK',day_utc::text,10) on conflict do nothing;
 end if;
 select weekly_goal into target from public.league_profiles where id=new.athlete_id;
 select count(distinct (finished_at at time zone 'UTC')::date) into days from public.league_workouts
  where athlete_id=new.athlete_id and finished_at at time zone 'UTC'>=week_utc
  and finished_at at time zone 'UTC'<week_utc+interval '7 days';
 if days>=target then
  insert into public.league_xp_events(athlete_id,kind,source_key,points)
   values(new.athlete_id,'GOAL',week_utc::date::text,50) on conflict do nothing;
 end if;
 return new;
end $$;
revoke all on function league_private.workout_rewards() from public,anon,authenticated;
create trigger league_workout_rewards after insert on public.league_workouts for each row execute function league_private.workout_rewards();
commit;
