// Disposable local PostgreSQL only: two actual sessions, desktop/mobile last-slot races.
import pg from 'pg';
import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {setTimeout as pause} from 'node:timers/promises';
import {authFixture,sourceFixture,migrations,identity,ADMIN,GYM} from './database-fixture.mjs';
import {trainingMigration,trainingSeed} from './training-fixture.mjs';
const connectionString=process.env.LEAGUE_TEST_DATABASE_URL;
if(!connectionString)throw Error('LEAGUE_TEST_DATABASE_URL is required');
const url=new URL(connectionString);
if(!['localhost','127.0.0.1','::1'].includes(url.hostname)||!(process.env.CI||process.env.LEAGUE_TEST_DATABASE_ALLOW_LOCAL==='1'))throw Error('Only explicitly enabled disposable local PostgreSQL is allowed');
const database='training_qa_'+randomUUID().replaceAll('-','');const admin=new pg.Client({connectionString});await admin.connect();const clients=[];
try{
 await admin.query('create database '+database);const ownUrl=new URL(connectionString);ownUrl.pathname='/'+database;
 async function connection(){const c=new pg.Client({connectionString:ownUrl.toString()});await c.connect();clients.push(c);return c;}
 const setup=await connection(),adapter={exec:sql=>setup.query(sql),query:(sql,args)=>setup.query(sql,args)};
 const roles=authFixture.replace(/create role (anon|authenticated|service_role) ([^;]+);/g,(_,name,options)=>"do $$begin if not exists(select 1 from pg_roles where rolname='"+name+"') then create role "+name+' '+options+';end if;end$$;');
 await setup.query(roles+sourceFixture);await migrations(adapter,'hub');await migrations(adapter,'source');await setup.query(trainingMigration);await setup.query(trainingSeed);
 await setup.query("insert into public.league_gym_settings(gym_id,enabled,pilot_client_ids) values($1,true,array[1,2]::bigint[])",[GYM]);
 await identity(adapter,ADMIN);const profiles=[];
 for(const id of [1,2])profiles.push((await setup.query("select public.league_staff($1,'provision',$2) value",[GYM,{client_id:id}])).rows[0].value.profile_id);
 await setup.query('reset role');const a=await connection(),b=await connection(),evidence=[];
 async function actor(c,role){await c.query('select set_config($1,$2,false)',['request.jwt.claim.sub',ADMIN]);await c.query('set role '+role);}
 async function waited(){for(let i=0;i<100;i++){const row=(await setup.query('select wait_event_type from pg_stat_activity where pid=$1',[b.processID])).rows[0];if(row?.wait_event_type==='Lock')return;await pause(25);}throw Error('Second backend did not wait for the class lock');}
 async function reserve(c,classId,clientId){return c.query("select public.gym_training($1,'reservation.reserve',$2) value",[GYM,{class_id:classId,client_id:clientId,request_id:randomUUID()}]);}
 for(const [index,mode] of ['desktop-vs-desktop','desktop-vs-mobile','duplicate-desktop-retry'].entries()){
  const classId=200+index;await setup.query("insert into public.classes(id,gym_id,name,starts_at,capacity,status) values($1,$2,'Concurrency QA',now()+interval '1 day',1,'PROGRAMADA')",[classId,GYM]);
  await actor(a,'authenticated');await actor(b,mode==='desktop-vs-mobile'?'service_role':'authenticated');await a.query('begin');await b.query('begin');
  await reserve(a,classId,1);
  const pending=(mode==='desktop-vs-mobile'?b.query("select public.league_source($1,$2,'reserve',$3)",[GYM,profiles[1],{class_id:classId}]):reserve(b,classId,mode==='duplicate-desktop-retry'?1:2)).then(()=>({ok:true}),e=>({ok:false,code:e.code}));
  await waited();await a.query('commit');const second=await pending;
  if(mode==='duplicate-desktop-retry'){assert.equal(second.ok,true);await b.query('commit');}else{assert.equal(second.ok,false);assert.equal(second.code,'23514');await b.query('rollback');}
  const total=(await setup.query("select count(*)::int n from public.reservations where class_id=$1 and status='RESERVADA'",[classId])).rows[0].n;assert.equal(total,1);
  evidence.push({mode,backend_a:a.processID,backend_b:b.processID,waited_on_lock:true,confirmed:total,second});
 }
 console.log(JSON.stringify({scope:'Independent local PostgreSQL sessions, synthetic data only',evidence},null,2));
}finally{for(const c of clients)await c.end().catch(()=>{});await admin.query('drop database if exists '+database+' with (force)');await admin.end();}
