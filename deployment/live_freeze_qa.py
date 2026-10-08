"""Generate isolated, reversible hosted SQL tests. Contains no provider credentials.

SQL identity claims below belong only to a disposable test user and exercise the
database permissions. They do not substitute for a signed desktop login pilot.
"""
import json
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'evidence/live_freeze_fixtures_20261008.json'
if STATE.exists():
    fixtures = json.loads(STATE.read_text())
else:
    fixtures = {}
    for edition in ('commercial', 'ztattuz'):
        fixtures[edition] = {k: str(uuid4()) for k in ('gym', 'user', 'device', 'session1', 'session2', 'request1', 'request2')}
        fixtures[edition]['name'] = 'GYMSOFT_QA_FREEZE_' + fixtures[edition]['gym'][-8:]
    STATE.write_text(json.dumps(fixtures, indent=2))
for f in fixtures.values():
    for key in ('cron_request1','cron_request2'):
        f.setdefault(key,str(uuid4()))
STATE.write_text(json.dumps(fixtures,indent=2))

def build(edition):
    f = fixtures[edition]
    g, u = f['gym'], f['user']
    commercial = edition == 'commercial'
    setup = f"""do $fixture$
    declare c bigint; p bigint;today date;begin
    if exists(select 1 from public.gyms where id='{g}') or exists(select 1 from auth.users where id='{u}') then
      raise exception 'Fixture already exists: inspect before retrying';end if;
    insert into auth.users(id,email) values('{u}','qa-{u}@example.test');
    insert into public.gyms(id,name,timezone{',created_by' if not commercial else ''})
      values('{g}','{f['name']}','America/Bogota'{",'"+u+"'" if not commercial else ''});
    insert into public.gym_users(gym_id,user_id,role) values('{g}','{u}','admin');
    """
    if commercial:
        setup += f"""
        insert into private.subscriptions(gym_id,contact_email,status,expires_at)
          values('{g}','qa-{u}@example.test','active',now()+interval '1 day');
        insert into private.license_devices(id,gym_id,device_hash,name,approved)
          values('{f['device']}','{g}',repeat('e',64),'Disposable SQL QA',true);
        insert into private.license_sessions(session_id,gym_id,user_id,device_id)
          values('{f['session1']}','{g}','{u}','{f['device']}'),('{f['session2']}','{g}','{u}','{f['device']}');
        """
    setup += f"""
    today:=private.gym_local_date('{g}');
    insert into public.plans(gym_id,name,duration_days,price,entry_limit)
      values('{g}','QA ticket',30,0,10) returning id into p;
    insert into public.clients(gym_id,document,first_name,last_name,active)
      values('{g}','QA_FREEZE','PRUEBA','CONGELACION',true) returning id into c;
    insert into public.memberships(gym_id,client_id,plan_id,start_date,end_date,amount,amount_paid,entry_limit)
      values('{g}',c,p,today-7,today+12,0,0,10);
    insert into public.clients(gym_id,document,first_name,last_name,active)
      values('{g}','QA_TICKET','PRUEBA','CONSUMO',true) returning id into c;
    insert into public.memberships(gym_id,client_id,plan_id,start_date,end_date,amount,amount_paid,entry_limit)
      values('{g}',c,p,today-7,today+12,0,0,10);
    end$fixture$;
    select id,name,timezone from public.gyms where id='{g}';
    """
    def identity(session):
        claims = json.dumps({'sub': u, 'session_id': f[session]})
        return f"select set_config('request.jwt.claim.sub','{u}',true),set_config('request.jwt.claims','{claims}',true);set local role authenticated;\n"
    races = []
    for n in (1, 2):
        races.append(identity(f'session{n}') + f"""-- gymsoft_live_freeze_race_{g}
        with started as materialized(select pg_backend_pid() as pid,clock_timestamp() as started_at),
        frozen as materialized(select public.membership_freeze('{g}',
          (select m.id from public.memberships m join public.clients c on c.id=m.client_id
           where m.gym_id='{g}' and c.document='QA_FREEZE'),'{f['request'+str(n)]}','Disposable concurrent SQL QA',false) as result from started),
        held as materialized(select pg_sleep(20) from frozen)
        select started.*,clock_timestamp() as finished_at,frozen.result from started,frozen,held;""")
    observe = f"select pid,query_start,state,wait_event_type,wait_event from pg_stat_activity where pid<>pg_backend_pid() and query like '%gymsoft_live_freeze_race_{g}%' and state='active';"
    verify = f"""select
     (select count(*) from public.membership_freezes where gym_id='{g}') as freezes,
     (select end_date-private.gym_local_date('{g}') from public.memberships m join public.clients c on c.id=m.client_id where m.gym_id='{g}' and c.document='QA_FREEZE') as expiration_days_from_today,
     (select jsonb_agg(jsonb_build_object('start_date',start_date,'resume_date',resume_date,'starts_at',starts_at,'ends_at',ends_at,'days_added',days_added,'status',status,'responsible',created_by)) from public.membership_freezes where gym_id='{g}') as ledger,
     (select count(*) from public.audit_logs where gym_id='{g}' and action='MEMBERSHIP_FROZEN') as freeze_audits;
    """
    denied = identity('session1') + f"""select public.admin_register_checkin('{g}',(select id from public.clients where gym_id='{g}' and document='QA_FREEZE_CRON2'),'HUELLA BIOMÉTRICA',true) as frozen_checkin;
    """
    tickets = [identity(f'session{n}') + f"""with started as materialized(select pg_backend_pid() as pid,clock_timestamp() as started_at),
     entered as materialized(select public.reception_register_checkin('{g}',(select id from public.clients where gym_id='{g}' and document='QA_TICKET'),'CÓDIGO') as result from started),
     held as materialized(select pg_sleep(5) from entered)
     select started.*,clock_timestamp() as finished_at,entered.result from started,entered,held;""" for n in (1, 2)]
    ticket_verify = f"""select count(*) as daily_consumptions,min(local_date) as local_date,
      (select count(*) from public.checkins where gym_id='{g}' and result='PERMITIDA') as allowed_entries,
      private.gym_local_date('{g}') as gym_today
      from public.ticket_daily_consumptions where gym_id='{g}';"""
    audit_clock = identity('session1') + f"""select event->>'action' as action,event->>'occurred_at' as occurred_at,event->>'created_at_local' as created_at_local
     from jsonb_array_elements(public.get_audit_logs('{g}')) event where event->>'action' in ('MEMBERSHIP_FROZEN','CHECK_IN_DENIED_MEMBERSHIP_FROZEN');"""
    cron_verify = f"""select m.end_date,m.entry_limit,
      (select count(*) from public.membership_freezes where membership_id=m.id) as freezes,
      (select jsonb_agg(jsonb_build_object('start_date',start_date,'resume_date',resume_date,'starts_at',starts_at,'ends_at',ends_at,'days_added',days_added,'original_end_date',original_end_date,'extended_end_date',extended_end_date)) from public.membership_freezes where membership_id=m.id) as ledger,
      (select count(*) from public.audit_logs where gym_id='{g}' and action='MEMBERSHIP_FROZEN' and entity_id=m.id::text) as frozen_audits
      from public.memberships m join public.clients c on c.id=m.client_id where m.gym_id='{g}' and c.document='QA_FREEZE_CRON2';"""
    cleanup = f"""do $cleanup$begin
     if not exists(select 1 from public.gyms where id='{g}' and name='{f['name']}') then raise exception 'Fixture identity not verified';end if;
     perform cron.unschedule(jobid) from cron.job where jobname like 'gymsoft-qa-{g[-8:]}-%';
     delete from public.ticket_daily_consumptions where gym_id='{g}';
     delete from public.checkins where gym_id='{g}';
     delete from public.membership_freezes where gym_id='{g}';
     delete from public.memberships where gym_id='{g}';
     delete from public.plans where gym_id='{g}';
     delete from public.clients where gym_id='{g}';
     delete from public.marketing_settings where gym_id='{g}';
     delete from public.audit_logs where gym_id='{g}';
     delete from public.gym_users where gym_id='{g}';
     """
    if commercial:
        cleanup += f"delete from private.license_sessions where gym_id='{g}';delete from private.license_devices where gym_id='{g}';delete from private.subscriptions where gym_id='{g}';"
    cleanup += f"""delete from public.gyms where id='{g}' and name='{f['name']}';
     delete from auth.users where id='{u}' and email='qa-{u}@example.test';end$cleanup$;
     select exists(select 1 from public.gyms where id='{g}') as gym_remaining,exists(select 1 from auth.users where id='{u}') as user_remaining;"""
    cron_prepare = f"""do $fixture$declare c bigint;p bigint;today date;begin
     if not exists(select 1 from public.gyms where id='{g}' and name='{f['name']}') then raise exception 'Fixture identity not verified';end if;
     if exists(select 1 from public.clients where gym_id='{g}' and document='QA_FREEZE_CRON2') then raise exception 'Cron fixture already exists';end if;
     today:=private.gym_local_date('{g}');select id into p from public.plans where gym_id='{g}' and name='QA ticket';
     insert into public.clients(gym_id,document,first_name,last_name,active) values('{g}','QA_FREEZE_CRON2','PRUEBA','CONCURRENCIA',true) returning id into c;
     insert into public.memberships(gym_id,client_id,plan_id,start_date,end_date,amount,amount_paid,entry_limit) values('{g}',c,p,today-7,today+12,0,0,10);
     end$fixture$;"""
    cron_schedule = ''
    for kind in ('FREEZE','TICKET'):
        for n in (1,2):
            name = f"gymsoft-qa-{g[-8:]}-{kind.lower()}-{n}"
            claims = json.dumps({'sub':u,'session_id':f[f'session{n}']})
            doc = 'QA_FREEZE_CRON2' if kind=='FREEZE' else 'QA_TICKET'
            call = (f"public.membership_freeze('{g}',m,'{f['cron_request'+str(n)]}','Disposable cron concurrency QA',false)" if kind=='FREEZE'
                    else f"public.reception_register_checkin('{g}',c,'CÓDIGO')")
            command=f"""do $qa$declare c bigint;m bigint;r jsonb;outcome text;err text;started timestamptz:=clock_timestamp();begin
             perform cron.unschedule('{name}');
             perform set_config('request.jwt.claim.sub','{u}',true);
             perform set_config('request.jwt.claims','{claims}',true);
             select id into c from public.clients where gym_id='{g}' and document='{doc}';
             select id into m from public.memberships where gym_id='{g}' and client_id=c;
             begin r:={call};outcome:='SUCCESS';perform pg_sleep(10);
             exception when others then outcome:='REJECTED';err:=SQLERRM;end;
             insert into public.audit_logs(gym_id,actor_user_id,action,entity_type,entity_id,summary,details)
             values('{g}','{u}','QA_{kind}_RACE_RESULT','test',m::text,'Disposable hosted concurrent SQL QA',
               jsonb_build_object('run','v2','pid',pg_backend_pid(),'started_at',started,'finished_at',clock_timestamp(),'request', {n},'outcome',outcome,'error',err,'result',r));
             end$qa$;"""
            cron_schedule+=f"select cron.schedule('{name}','* * * * *',$command${command}$command$);\n"
    cron_results=f"""select action,details,created_at,to_char(created_at at time zone 'America/Bogota','DD/MM/YYYY HH24:MI:SS') as local_time
     from public.audit_logs where gym_id='{g}' and action in ('QA_FREEZE_RACE_RESULT','QA_TICKET_RACE_RESULT') and details->>'run'='v2' order by action,details->>'request';"""
    return dict(setup=setup,races=races,observe=observe,verify=verify,denied=denied,tickets=tickets,ticket_verify=ticket_verify,cleanup=cleanup,
                cron_prepare=cron_prepare,cron_schedule=cron_schedule,cron_results=cron_results,audit_clock=audit_clock,cron_verify=cron_verify)

print(json.dumps({k: build(k) for k in fixtures}))
