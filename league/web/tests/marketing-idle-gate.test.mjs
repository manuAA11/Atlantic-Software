import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';
const proposal=await readFile(new URL('../../../docs/optimization/proposals/marketing-idle-gate.sql',import.meta.url),'utf8');
const rollback=await readFile(new URL('../../../docs/optimization/proposals/marketing-idle-gate.rollback.sql',import.meta.url),'utf8');
async function fixture(){
 const db=new PGlite();
 await db.exec(`
 create role anon; create role authenticated; create role service_role;
 create schema private; create schema cron; create schema vault; create schema net;
 create table private.marketing_scheduler_config(singleton boolean primary key,project_url text,last_requested_at timestamptz,last_request_id bigint);
 create table private.marketing_platform(singleton boolean primary key,scheduler_secret_id uuid);
 create table vault.decrypted_secrets(id uuid primary key,decrypted_secret text);
 create table public.marketing_settings(whatsapp_enabled boolean,chatbot_enabled boolean,marketing_automation_enabled boolean,online_payments_enabled boolean);
 create table public.marketing_automations(enabled boolean,deleted_at timestamptz);
 create table public.marketing_messages(status text,scheduled_for timestamptz,claimed_at timestamptz);
 create table cron.job(jobname text,active boolean,schedule text,database text,command text,username text default current_user);
 create table net.requests(url text,headers jsonb,body jsonb,timeout_milliseconds int);
 create function net.http_post(url text,headers jsonb,body jsonb,timeout_milliseconds int) returns bigint language plpgsql as $$
 begin insert into net.requests values(url,headers,body,timeout_milliseconds);return (select count(*) from net.requests);end$$;
 insert into private.marketing_scheduler_config values(true,'https://synthetic.supabase.co',null,null);
 insert into private.marketing_platform values(true,'00000000-0000-0000-0000-000000000001');
 insert into vault.decrypted_secrets values('00000000-0000-0000-0000-000000000001','synthetic-scheduler-token');
 insert into public.marketing_settings values(false,false,false,false);
 insert into cron.job values('gymsoft-freeze-completion',true,'* * * * *',current_database(),'select private.freeze_complete_due()',current_user);
 `);
 await db.exec(rollback);
 await db.exec('revoke all on function private.marketing_cron_tick() from public,anon,authenticated,service_role');
 await db.exec(proposal);return db;
}
const tick=async db=>(await db.query('select private.marketing_cron_tick() value')).rows[0].value;
const count=async db=>(await db.query('select count(*)::int n from net.requests')).rows[0].n;
test('idle cycles skip HTTP, Vault and config writes; repeat installation retains ACL/security',async()=>{
 const db=await fixture();try{
  const before=(await db.query("select proacl,prosecdef,proconfig from pg_proc where oid='private.marketing_cron_tick()'::regprocedure")).rows;
  await db.exec(proposal);await db.exec('delete from vault.decrypted_secrets');
  for(let i=0;i<20;i++)assert.equal(await tick(db),null);
  assert.equal(await count(db),0);
  assert.deepEqual((await db.query('select last_requested_at,last_request_id from private.marketing_scheduler_config')).rows,[{last_requested_at:null,last_request_id:null}]);
  assert.deepEqual((await db.query("select proacl,prosecdef,proconfig from pg_proc where oid='private.marketing_cron_tick()'::regprocedure")).rows,before);
  for(const role of ['anon','authenticated','service_role']){
   await db.exec('set role '+role);await assert.rejects(tick(db),/permission denied/);await db.exec('reset role');
  }
 }finally{await db.close();}
});
test('each enabled feature in any gym or enabled rule keeps the original worker cadence',async()=>{
 const db=await fixture();try{
  for(const column of ['whatsapp_enabled','chatbot_enabled','marketing_automation_enabled','online_payments_enabled']){
   await db.exec('update public.marketing_settings set '+column+'=true');assert.ok(await tick(db));
   await db.exec('update public.marketing_settings set '+column+'=false');
  }
  await db.exec('insert into public.marketing_settings values(false,true,false,false)');assert.ok(await tick(db));
  await db.exec('delete from public.marketing_settings;insert into public.marketing_automations values(true,null)');
  assert.ok(await tick(db));
  await db.exec('update public.marketing_automations set deleted_at=now()');assert.equal(await tick(db),null);
 }finally{await db.close();}
});
test('queued future messages and stale PROCESSING wake the original claims without resending UNCERTAIN',async()=>{
 const db=await fixture();try{
  for(const status of ['QUEUED','PROCESSING']){
   await db.query("insert into public.marketing_messages values($1,now()+interval '1 day',now()-interval '4 minutes')",[status]);
   assert.ok(await tick(db));await db.exec('delete from public.marketing_messages');
  }
  for(const status of ['UNCERTAIN','FAILED','SENT']){
   await db.query('insert into public.marketing_messages(status) values($1)',[status]);
   assert.equal(await tick(db),null);
  }
  assert.equal(await count(db),2);
  assert.equal((await db.query('select count(*)::int n from public.marketing_messages')).rows[0].n,3);
 }finally{await db.close();}
});
test('missing, disabled, slower, wrong-database or changed freeze job fails open to the old worker',async()=>{
 const db=await fixture();try{
  for(const change of ["active=false","schedule='*/5 * * * *'","database='other_database'","command='select changed_function()'","username='other_role'"]){
   await db.exec('begin;update cron.job set '+change);assert.ok(await tick(db));await db.exec('rollback');
  }
  await db.exec("update cron.job set command='select private.freeze_complete_due();'");assert.equal(await tick(db),null);
  await db.exec('delete from cron.job');assert.ok(await tick(db));
 }finally{await db.close();}
});
test('enabled errors still fail, request contract unchanged, rollback restores unconditional invocation',async()=>{
 const db=await fixture();try{
  await db.exec('update public.marketing_settings set whatsapp_enabled=true');
  assert.ok(await tick(db));
  assert.deepEqual((await db.query('select * from net.requests')).rows,[{url:'https://synthetic.supabase.co/functions/v1/marketing/jobs',headers:{'Content-Type':'application/json','x-marketing-scheduler':'synthetic-scheduler-token'},body:{},timeout_milliseconds:55000}]);
  await db.exec('delete from vault.decrypted_secrets');await assert.rejects(tick(db),/Scheduler no configurado/);
  await db.exec("insert into vault.decrypted_secrets values('00000000-0000-0000-0000-000000000001','synthetic-scheduler-token');update public.marketing_settings set whatsapp_enabled=false");
  await db.exec(rollback);assert.ok(await tick(db));assert.equal(await count(db),2);
  await db.exec(proposal);assert.equal(await tick(db),null);
  await db.exec('delete from private.marketing_scheduler_config');assert.equal(await tick(db),null);
 }finally{await db.close();}
});
