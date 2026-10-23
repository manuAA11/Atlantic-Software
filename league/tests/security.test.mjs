import test from 'node:test';
import assert from 'node:assert/strict';
import {randomUUID,createHash} from 'node:crypto';
import {PGlite} from '@electric-sql/pglite';
import {authFixture,migrations,identity,app,gateway,ALICE,BOB,ADMIN,GYM} from './database-fixture.mjs';
test('invitations require matching confirmed email, are single-use and expire',async()=>{
 const db=new PGlite();try{
  await db.exec(authFixture);await migrations(db,'hub');
  for(const user of [ALICE,BOB]){await identity(db,user);await app(db,'profile.ensure');}
  await identity(db,null,'service_role');await gateway(db,'directory.sync',{gym_id:GYM,source_ref:'aaaaaaaaaaaaaaaaaaaa',name:'QA',athlete_code:'AL-QA1234',enabled:true});
  const token='a'.repeat(64),staff={gym_id:GYM,actor_id:ADMIN,actor_role:'admin'};
  await gateway(db,'staff.invite',{...staff,source_profile_id:randomUUID(),email:'alice@example.test',token_hash:createHash('sha256').update(token).digest('hex')});
  await identity(db,BOB);await assert.rejects(app(db,'invitation.accept',{token}),/no disponible/);
  await identity(db,ALICE);assert.equal((await app(db,'invitation.accept',{token})).status,'APPROVED');
  await assert.rejects(app(db,'invitation.accept',{token}),/no disponible/);
  const expired='b'.repeat(64);
  await identity(db,null,'service_role');await gateway(db,'staff.invite',{...staff,source_profile_id:randomUUID(),email:'bob@example.test',token_hash:createHash('sha256').update(expired).digest('hex')});
  await db.exec('reset role');await db.exec("update league_private.invites set expires_at=now()-interval '1 second' where email='bob@example.test'");
  await identity(db,BOB);await assert.rejects(app(db,'invitation.accept',{token:expired}),/no disponible/);
 }finally{await db.close();}
});
test('private evidence rejects other athletes, overwrites and stale JWTs after deletion',async()=>{
 const db=new PGlite();try{
  await db.exec(authFixture+[
   'create schema storage;grant usage on schema storage to authenticated;',
   'create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);',
   'create table storage.objects(id uuid primary key default gen_random_uuid(),bucket_id text,name text,unique(bucket_id,name));',
   'alter table storage.objects enable row level security;grant select,insert,update,delete on storage.objects to authenticated;'
  ].join('\n'));await migrations(db,'hub');
  await identity(db,ALICE);await app(db,'profile.ensure');
  const name=ALICE+'/'+randomUUID()+'.jpg';
  await db.query("insert into storage.objects(bucket_id,name) values('league-evidence',$1)",[name]);
  assert.equal((await db.query('select * from storage.objects')).rows.length,1);
  await db.query("update storage.objects set name=$1 where name=$2",[ALICE+'/'+randomUUID()+'.png',name]);
  assert.equal((await db.query('select name from storage.objects')).rows[0].name,name);
  await identity(db,BOB);await app(db,'profile.ensure');assert.equal((await db.query('select * from storage.objects')).rows.length,0);
  await assert.rejects(db.query("insert into storage.objects(bucket_id,name) values('league-evidence',$1)",[name]),/row-level security/);
  await db.exec('reset role');await db.query('delete from auth.users where id=$1',[ALICE]);
  await identity(db,ALICE);assert.equal((await db.query('select * from storage.objects')).rows.length,0);
  await assert.rejects(app(db,'snapshot'),/Confirma tu cuenta/);
  await assert.rejects(db.query("insert into storage.objects(bucket_id,name) values('league-evidence',$1)",[ALICE+'/'+randomUUID()+'.jpg']),/row-level security/);
 }finally{await db.close();}
});
test('Core toggles League independently and exposes no public SECURITY DEFINER functions',async()=>{
 const db=new PGlite();try{
  await db.exec(authFixture+[
   'create schema private;',
   'create table private.core_gyms(gym_id uuid primary key,name text,source_project_ref text,status text,license_status text);',
   "insert into private.core_gyms values('GYM_UUID','Gym QA','aaaaaaaaaaaaaaaaaaaa','ACTIVE','ACTIVE');",
   "create function private.require_owner() returns void language plpgsql as $$begin if auth.uid() is distinct from 'OWNER_UUID'::uuid then raise exception 'Owner required' using errcode='42501';end if;end$$;"
  ].join('\n').replaceAll('GYM_UUID',GYM).replaceAll('OWNER_UUID',ADMIN));await migrations(db,'core');
  await identity(db,ALICE);await assert.rejects(db.query('select public.core_league_owner($1,true)',[GYM]),/Owner required/);
  await assert.rejects(db.query('select public.core_league_entitlement($1)',[GYM]),/permission denied/);
  await identity(db,ADMIN);const enabled=(await db.query('select public.core_league_owner($1,true) as value',[GYM])).rows[0].value;
  assert.equal(enabled.enabled,true);assert.match(enabled.athlete_code,/^AL-/);
  await identity(db,null,'service_role');assert.equal((await db.query('select public.core_league_entitlement($1) as value',[GYM])).rows[0].value.enabled,true);
  assert.equal((await db.query("select public.core_league_search('Gym') as value")).rows[0].value.length,1);
  await identity(db,ADMIN);await db.query('select public.core_league_owner($1,false)',[GYM]);
  await db.exec('reset role');assert.equal((await db.query('select license_status from private.core_gyms where gym_id=$1',[GYM])).rows[0].license_status,'ACTIVE');
  assert.deepEqual((await db.query("select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prosecdef and proname like '%league%'")).rows,[]);
 }finally{await db.close();}
});
