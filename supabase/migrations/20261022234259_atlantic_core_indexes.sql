-- Cover Core foreign-key lookups and per-gym history without touching records.
begin;
create index if not exists core_events_gym_created on private.core_events(gym_id,created_at desc);
create index if not exists core_notifications_gym_created on private.core_notifications(gym_id,created_at desc);
create index if not exists core_reads_gym_user on private.core_notification_reads(gym_id,user_id,notification_id);
commit;
