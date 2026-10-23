-- Optional private evidence, never public athlete photos or identity documents.
begin;
do $$begin
 if to_regclass('storage.buckets') is not null then
  insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
   values('league-evidence','league-evidence',false,6291456,array['image/jpeg','image/png','image/webp'])
   on conflict(id) do update set public=false,file_size_limit=excluded.file_size_limit,allowed_mime_types=excluded.allowed_mime_types;
  execute $p$create policy league_evidence_read on storage.objects for select to authenticated using(
   bucket_id='league-evidence' and name ~ ('^'||(select auth.uid())::text||'/[a-f0-9-]{36}[.](jpg|png|webp)$')
   and exists(select 1 from public.league_profiles where id=(select auth.uid())))$p$;
  execute $p$create policy league_evidence_insert on storage.objects for insert to authenticated with check(
   bucket_id='league-evidence' and name ~ ('^'||(select auth.uid())::text||'/[a-f0-9-]{36}[.](jpg|png|webp)$')
   and exists(select 1 from public.league_profiles where id=(select auth.uid())))$p$;
  -- No client UPDATE/UPSERT: evidence cannot change after submission.
 end if;
end$$;
commit;
