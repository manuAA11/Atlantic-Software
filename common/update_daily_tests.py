from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for e in ROOT.glob('GymSoft_*'):
 p=e/'tests/migrations.mjs';s=p.read_text()
 if 'daily=true' not in s:
  s=s.replace('export async function database() {','export async function database({daily=true}={}) {').replace('database({upgrade=true}={})','database({upgrade=true,daily=true}={})')
  s=s.replace(' return db;',' if(daily'+(' && upgrade' if 'ZTATTUZ' in e.name else '')+") await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_CONSUMO_DIARIO.sql'),'utf8'));\n return db;")
 p.write_text(s)
 p=e/'tests/daily_tickets.mjs';p.write_text(p.read_text().replace('await database();','await database({daily:false});'))
 p=e/'run_validation.py';s=p.read_text()
 if "'daily_tickets'" not in s:s=s.replace('SQL_TESTS=(',"SQL_TESTS=('daily_tickets',")
 p.write_text(s)
 p=e/'tests/ticket_plans.mjs';s=p.read_text()
 if 'advanceDay' not in s:
  s=s.replace(' for(let i=0;i<15;i++){', ''' const baseDay=new Date((await rpc('gym_local_clock',{p_gym_id:id})).today+'T15:00:00Z');
 async function advanceDay(days){
  await db.exec('RESET ROLE');
  const d=new Date(baseDay.getTime()+days*86400000).toISOString();
  await db.exec(`create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select '${d}'::timestamptz$$`);
  await user(A);
 }
 for(let i=0;i<15;i++){
  await advanceDay(i);''')
  s=s.replace(" ok((await rpc('admin_register_checkin'", " await advanceDay(15);\n ok((await rpc('admin_register_checkin'",1)
 p.write_text(s)
 p=e/'tests/gym_simulation.py';s=p.read_text().replace("self.check(reception.register_checkin(single,'MANUAL')['result']=='DENEGADA','Sesión agotada no permite segunda entrada')","self.check(reception.register_checkin(single,'MANUAL')['already_consumed_today'],'Sesión permite reentrada el mismo día sin descontar')");p.write_text(s)
 p=e/'tests/fingerprint_journey.py';s=p.read_text();new='''result=event('access')
            check(result['result']=='PERMITIDA' and result['already_consumed_today'] and result['entries_remaining']==0,'Tiquetera agotada permite reentrada el mismo día')
'''
 if 'ZTATTUZ' in e.name:new+='            until(lambda:not door._pending)\n'
 new+='''            engine.sql("create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select now()+interval '1 day'$$")
            service.last[clients['tiquetera']]-=11;reader.samples.put(templates['tiquetera'])
            check(event('access')['result']=='DENEGADA','Sin saldo se deniega el día siguiente')
            engine.sql("create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select now()$$")'''
 s=s.replace("check(event('access')['result']=='DENEGADA','Tiquetera agotada rechazada en intento posterior')",new)
 s=s.replace('usb.frames.count(RELAY_ON)==2','usb.frames.count(RELAY_ON)==3').replace('Repetida, agotada, desconocida y eliminada no abren; el relé termina en OFF','Reentrada abre; repetida inmediata, agotada al día siguiente, desconocida y eliminada no abren; el relé termina en OFF')
 p.write_text(s)
 p=e/'tests/security.mjs';s=p.read_text().replace("ok(check.result==='DENEGADA','cannot consume another entry')", "ok(check.result==='PERMITIDA' && check.entries_remaining===0 && check.already_consumed_today && !check.ticket_consumed,'same-day reentry does not consume another entry')");p.write_text(s)
print('Daily-rule regression tests updated.')
