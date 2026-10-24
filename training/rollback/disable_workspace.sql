-- Non-destructive feature rollback. Retains all plans, catalog data and history.
-- Deploy the previous client and disable only the new training entry points.
begin;
revoke execute on function public.gym_training(uuid,text,jsonb) from authenticated;
revoke execute on function league_source_private.training(uuid,text,jsonb) from authenticated;
notify pgrst,'reload schema';
commit;
-- Re-enable by reapplying the versioned migration after verification.
-- Do not drop data tables or restore a full backup over newer customer activity.
