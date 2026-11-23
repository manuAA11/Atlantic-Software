// STDIN-only disposable PostgreSQL fixture for native UI integration. No network listener.
import {createInterface} from 'node:readline';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
const require=createRequire(process.env.ATLANTIC_TEST_EDITION?new URL('../../'+process.env.ATLANTIC_TEST_EDITION+'/package.json',import.meta.url):new URL('../package.json',import.meta.url));
const {PGlite}=require('@electric-sql/pglite');
import {setupTraining} from './training-fixture.mjs';
import {identity,ADMIN,GYM} from './database-fixture.mjs';
const db=new PGlite();await setupTraining(db);await db.exec('reset role');
await db.exec('create table public.league_member_events(id uuid primary key default gen_random_uuid(),gym_id uuid,title text,description text,starts_at timestamptz,location text,organizer text,image_url text,status text,version int not null default 1,updated_at timestamptz default now());');
await db.exec(await readFile(new URL('../member/sql/delivery-admin.sql',import.meta.url),'utf8'));
await db.query("insert into public.league_gym_settings(gym_id,enabled,pilot_client_ids) values($1,true,array[1,2]::bigint[])",[GYM]);
await identity(db,ADMIN);const profiles=[];
for(const clientId of [1,2])profiles.push((await db.query("select public.league_staff($1,'provision',$2) value",[GYM,{client_id:clientId}])).rows[0].value.profile_id);
console.log(JSON.stringify({ready:true}));
for await(const line of createInterface({input:process.stdin,crlfDelay:Infinity})){
 try{
  const r=JSON.parse(line);let value;
  if(r.kind==='stop')break;
  if(r.kind==='member')value=(await db.query('select public.gym_member_admin($1,$2,$3) value',[GYM,r.action,r.data||{}])).rows[0].value;
  else if(r.kind==='training')value=(await db.query('select public.gym_training($1,$2,$3) value',[GYM,r.action,r.data||{}])).rows[0].value;
  else if(r.kind==='league'){
   try{await identity(db,ADMIN,'service_role');value=(await db.query('select public.league_source($1,$2,$3,$4) value',[GYM,profiles[r.client===2?1:0],r.action,r.data||{}])).rows[0].value;}
   finally{await identity(db,ADMIN);}
  }else throw Error('Unsupported fixture command');
  console.log(JSON.stringify({ok:true,value}));
 }catch(e){console.log(JSON.stringify({ok:false,error:e.message}));}
}
process.stdin.destroy();
await db.close();

