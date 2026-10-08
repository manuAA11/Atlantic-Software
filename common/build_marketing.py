from pathlib import Path
root=Path(__file__).resolve().parents[1]
parts=['marketing_schema.sql','marketing_api.sql','marketing_service.sql','marketing_payments.sql','marketing_chatbot.sql','marketing_worker.sql','marketing_desktop.sql']
footer='''\ndo $$declare r record;begin
 for r in select p.oid::regprocedure f,n.nspname,p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('private','public') and p.proname like 'marketing_%' loop
 execute format('revoke all on function %s from public,anon,authenticated,service_role',r.f);
 if r.nspname='public' then execute format('grant execute on function %s to %I',r.f,case when r.proname like 'marketing_service_%' then 'service_role' else 'authenticated' end);end if;
 end loop;
end$$;
grant execute on function private.marketing_phone(text) to authenticated,service_role;
commit;
'''
sql='\n'.join((root/'common'/n).read_text() for n in parts if (root/'common'/n).exists())+footer
for product in root.glob('GymSoft_*'):
 (product/'ACTUALIZAR_MARKETING.sql').write_text(sql)
 p=product/'supabase/migrations/20261003124254_marketing_automation.sql';p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():p.write_text(sql)
p=root/'supabase/migrations/20261003124254_marketing_automation.sql';p.parent.mkdir(parents=True,exist_ok=True)
if not p.exists():p.write_text(sql)
print('Marketing updater generated; existing migration snapshots preserved')
