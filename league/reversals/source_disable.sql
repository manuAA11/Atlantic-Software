-- Non-destructive, repeatable rollback. Execute only in the reviewed target.
begin;
update public.league_gym_settings set enabled=false,allow_all_clients=false;
-- Existing Gym tables, client profile mappings and reservation capacity guard remain intact.
commit;
