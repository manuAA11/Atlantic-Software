from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'GymSoft_ZTATTUZ_3.6.1_x86/ACTUALIZAR_ZTATTUZ_3.4.5.sql').read_text()
snapshot=source[source.index('CREATE OR REPLACE FUNCTION private.membership_snapshot_json'):]
# The block boundary above also includes preceding comments; keep only the first function.
snapshot=snapshot[:snapshot.index('$function$',snapshot.index('AS $function$')+len('AS $function$'))+len('$function$')]+';\n'
snapshot=snapshot.replace('v_today date := public.ztattuz_today();','v_today date := private.gym_local_date(p_gym_id);\n    v_consumed boolean := false;')
start=snapshot.index('        select count(*)')
end=snapshot.index('    end if;',start)
snapshot=snapshot[:start]+'''        select private.ticket_consumption_units(p_gym_id,v_membership_id) + m.initial_entries_used
        into v_entries_used from public.memberships m where m.gym_id=p_gym_id and m.id=v_membership_id;
        v_consumed:=private.ticket_consumed_on(p_gym_id,p_client_id,v_membership_id,v_today);
'''+snapshot[end:]
snapshot=snapshot.replace('v_entries_used >= v_entry_limit then','v_entries_used >= v_entry_limit and not v_consumed then')
snapshot=snapshot.replace('m.end_date desc,','case when private.ticket_consumed_on(p_gym_id,p_client_id,m.id,v_today) then 0 else 1 end,\n        m.end_date desc,')
snapshot=snapshot.replace("'id', v_client.id,", "'already_consumed_today',v_consumed,'local_date',v_today,\n        'id', v_client.id,")
content=(ROOT/'common/daily_tickets.sql').read_text()+'\n'+snapshot+'\n'+(ROOT/'common/daily_api.sql').read_text()+'\n'+(ROOT/'common/audit_display.sql').read_text()
path=next((ROOT/'supabase/migrations').glob('*_daily_tickets_timezone.sql'));path.write_text(content)
for edition in ROOT.glob('GymSoft_*'):
 (edition/'ACTUALIZAR_CONSUMO_DIARIO.sql').write_text(content)
 target=edition/'supabase/migrations';target.mkdir(parents=True,exist_ok=True);(target/path.name).write_text(content)
print('Updated daily ticket migration:',path.name)
