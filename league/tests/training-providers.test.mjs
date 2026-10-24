import {test} from 'node:test';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {database as commercial} from '../../GymSoft_Comercial_3.6.0/tests/migrations.mjs';
import {database as legacy} from '../../GymSoft_ZTATTUZ_3.6.1_x86/tests/migrations.mjs';
import {migrations} from './database-fixture.mjs';
import {trainingMigration,trainingSeed} from './training-fixture.mjs';
for(const [name,factory] of [['commercial',commercial],['legacy',legacy]])test('training additive installation preserves '+name+' schema and RLS',async()=>{
 const db=await factory();try{
 const before=await db.query("select (select count(*) from public.clients)::int clients,(select count(*) from public.memberships)::int memberships");
 await migrations(db,'hub');await migrations(db,'source');await db.exec(trainingMigration);await db.exec(trainingMigration);await db.exec(trainingSeed);await db.exec(trainingSeed);
 assert.deepEqual((await db.query("select (select count(*) from public.clients)::int clients,(select count(*) from public.memberships)::int memberships")).rows,before.rows);
 assert.equal((await db.query('select count(*)::int n from public.league_exercise_catalog')).rows[0].n,44);
 assert.equal((await db.query("select count(*)::int n from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and (relname='gym_routine_templates' or relname like 'league_%') and c.relkind='r' and not relrowsecurity")).rows[0].n,0);
 const OWNER=randomUUID(),ADMIN=randomUUID(),RECEPTION=randomUUID(),sid=randomUUID();
 if(name==='commercial'){
  for(const [id,email] of [[OWNER,'owner@qa.invalid'],[ADMIN,'admin@qa.invalid'],[RECEPTION,'reception@qa.invalid']])await db.query('insert into auth.users(id,email) values($1,$2)',[id,email]);
  await db.query('insert into private.software_owners(user_id) values($1)',[OWNER]);
  async function user(id){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[id,JSON.stringify({sub:id,session_id:id===ADMIN?sid:id})]);await db.exec('set role authenticated');}
  async function rpc(name,args=[]){return(await db.query(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) value`,args)).rows[0].value;}
  await user(OWNER);const gym=await rpc('owner_create_gym',['Training QA','admin@qa.invalid',40,'USD',1,7]);
  await user(ADMIN);await rpc('commercial_accept_invite',[gym.activation_code]);
  const training=(a,d={})=>rpc('gym_training',[gym.gym_id,a,d]);
  await assert.rejects(training('context'),/acceso/); // Existing device/license gate still applies.
  await rpc('commercial_check_license',['a'.repeat(64),'QA PC']);await user(OWNER);
  const detail=await rpc('owner_gym_detail',[gym.gym_id]);await rpc('owner_set_device',[detail.devices[0].id,false,'QA only']);
  const invite=await rpc('owner_invite_user',[gym.gym_id,'reception@qa.invalid','receptionist']);
  await user(ADMIN);await rpc('commercial_check_license',['a'.repeat(64),'QA PC']);assert.equal((await training('context')).role,'admin');
  const created=await training('class.save',{name:'Realtime QA',starts_at:new Date(Date.now()+86400000).toISOString(),capacity:2,duration_minutes:45,request_id:randomUUID()});
  assert.equal((await db.query("select count(*)::int n from public.gym_events where gym_id=$1 and event_type='classes:insert'",[gym.gym_id])).rows[0].n,1);

  await user(RECEPTION);await rpc('commercial_accept_invite',[invite]);await rpc('commercial_check_license',['a'.repeat(64),'QA PC']);
  await assert.rejects(training('context'),/permiso/);
  await user(ADMIN);await training('coach.grant',{user_id:RECEPTION,enabled:true,request_id:randomUUID()});
  await user(RECEPTION);assert.equal((await training('context')).role,'coach');
  await assert.rejects(rpc('get_finance_dashboard',[gym.gym_id,null,null]));
  await assert.rejects(training('staff'),/administración/);
 }
 }finally{await db.close();}
});
