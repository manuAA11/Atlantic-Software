// Real PostgreSQL, independent backends, shared last-slot locks. Never a production URL.
import pg from 'pg';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {setTimeout as pause} from 'node:timers/promises';
import {authFixture,sourceFixture,migrations,identity,ADMIN,GYM} from './database-fixture.mjs';
const connectionString=process.env.LEAGUE_TEST_DATABASE_URL;
if(!connectionString)throw Error('LEAGUE_TEST_DATABASE_URL is required');
const url=new URL(connectionString);
if(!['localhost','127.0.0.1','::1'].includes(url.hostname)||!(process.env.CI||process.env.LEAGUE_TEST_DATABASE_ALLOW_LOCAL==='1'))throw Error('Only an explicitly enabled local disposable PostgreSQL is allowed');
const database='league_qa_'+randomUUID().replaceAll('-','');
const admin=new pg.Client({connectionString});await admin.connect();
const clients=[];
try{
 await admin.query('create database '+database);
 const ownUrl=new URL(connectionString);ownUrl.pathname='/'+database;
 async function connection(){const c=new pg.Client({connectionString:ownUrl.toString()});await c.connect();clients.push(c);return c;}
 const setup=await connection(),adapter={exec:sql=>setup.query(sql),query:(sql,args)=>setup.query(sql,args)};
 const roleSql=authFixture.replace(/create role (anon|authenticated|service_role) ([^;]+);/g,(_,name,options)=>"do $$begin if not exists(select 1 from pg_roles where rolname='"+name+"') then create role "+name+' '+options+';end if;end$$;');
 await setup.query(roleSql+sourceFixture);await migrations(adapter,'source');
 await setup.query("insert into public.league_gym_settings(gym_id,enabled,pilot_client_ids) values($1,true,array[1,2,3]::bigint[])",[GYM]);
 await identity(adapter,ADMIN);
 const profiles=[];
 for(const clientId of [1,2])profiles.push((await setup.query("select public.league_staff($1,'provision',$2::jsonb) as value",[GYM,JSON.stringify({client_id:clientId})])).rows[0].value.profile_id);
 await setup.query('reset role');
 const a=await connection(),b=await connection();
 assert.notEqual(a.processID,b.processID);
 async function waitForLock(){
  for(let i=0;i<100;i++){
   const row=(await setup.query("select wait_event_type from pg_stat_activity where pid=$1",[b.processID])).rows[0];
   if(row?.wait_event_type==='Lock')return true;await pause(25);
  }throw Error('The second PostgreSQL backend did not wait on the class lock');
 }
 const evidence=[];
 for(const mode of ['mobile-rpc','legacy-desktop-writer']){
  const classId=mode==='mobile-rpc'?101:102;
  await setup.query("insert into public.classes(id,gym_id,name,starts_at,capacity,status) values($1,$2,'Concurrency QA',now()+interval '1 day',1,'PROGRAMADA')",[classId,GYM]);
  await a.query('begin');await b.query('begin');
  if(mode==='mobile-rpc'){await a.query('set local role service_role');await b.query('set local role service_role');}
  const reserve=(client,index)=>mode==='mobile-rpc'
   ?client.query("select public.league_source($1,$2,'reserve',$3::jsonb)",[GYM,profiles[index],JSON.stringify({class_id:classId})])
   :client.query("insert into public.reservations(gym_id,class_id,client_id,status) values($1,$2,$3,'RESERVADA')",[GYM,classId,index+1]);
  await reserve(a,0);
  const pending=reserve(b,1).then(()=>({ok:true}),error=>({ok:false,code:error.code}));
  await waitForLock();await a.query('commit');
  const second=await pending;assert.equal(second.ok,false);assert.equal(second.code,'23514');await b.query('rollback');
  const count=Number((await setup.query("select count(*) from public.reservations where class_id=$1 and status='RESERVADA'",[classId])).rows[0].count);
  assert.equal(count,1);evidence.push({mode,backend_a:a.processID,backend_b:b.processID,waited_on_lock:true,last_slot_winners:count,second_sqlstate:second.code});
 }
 await setup.query("insert into public.classes(id,gym_id,name,starts_at,capacity,status) values(103,$1,'Retry QA',now()+interval '1 day',2,'PROGRAMADA')",[GYM]);
 await a.query('begin');await b.query('begin');await a.query('set local role service_role');await b.query('set local role service_role');
 const args=[GYM,profiles[0],JSON.stringify({class_id:103})];
 await a.query("select public.league_source($1,$2,'reserve',$3::jsonb)",args);
 const retry=b.query("select public.league_source($1,$2,'reserve',$3::jsonb)",args);await waitForLock();await a.query('commit');await retry;await b.query('commit');
 assert.equal(Number((await setup.query('select count(*) from public.reservations where class_id=103')).rows[0].count),1);
 console.log(JSON.stringify({scope:'Actual local PostgreSQL, independent sessions, synthetic fixtures',version:(await setup.query('select version()')).rows[0].version,evidence,duplicate_retry_rows:1},null,2));
}finally{
 for(const client of clients)await client.end().catch(()=>{});
 await admin.query('drop database if exists '+database+' with (force)');await admin.end();
}
