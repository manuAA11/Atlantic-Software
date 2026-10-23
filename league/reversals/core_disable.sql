-- Non-destructive rollback of this optional module, independent of Gym licenses.
begin;
update private.core_league_modules set enabled=false,updated_at=now();
commit;
