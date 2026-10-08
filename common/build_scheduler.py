"""Synchronize scheduler installation while preserving the original applied migration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'common/marketing_scheduler.sql').read_text()
start = source.index('create or replace function public.marketing_service_install_scheduler')
end = source.index('create or replace function public.marketing_service_health')
fix = ("-- Supabase pgcrypto resides in extensions; SECURITY DEFINER uses an empty search_path.\n"
       "-- Additive correction: retain the previously applied scheduler migration unchanged.\n"
       "begin;\nset local lock_timeout='8s';\n" + source[start:end] + "commit;\n")
name = '20261008182100_scheduler_crypto_schema.sql'
(ROOT / 'supabase/migrations' / name).write_text(fix)
for product in ROOT.glob('GymSoft_*'):
    (product / 'ACTUALIZAR_SCHEDULER.sql').write_text(source)
    (product / 'supabase/migrations' / name).write_text(fix)
print('Scheduler synchronized; original migration preserved; additive crypto correction added')
