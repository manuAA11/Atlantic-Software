-- Stop official gym operations without deleting personal accounts or histories.
begin;
update public.league_gym_directory set enabled=false,entitlement_until=now();
commit;
