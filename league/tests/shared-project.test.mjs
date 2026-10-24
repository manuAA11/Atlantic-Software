import {test} from 'node:test';
import assert from 'node:assert/strict';
import {PGlite} from '@electric-sql/pglite';
import {authFixture,sourceFixture,migrations,identity,app,gateway,ALICE,BOB,ADMIN,GYM,EXERCISE} from './database-fixture.mjs';

test('League and Gym coexist in one database; deleting League preserves Gym identity and operation',async()=>{
 const db=new PGlite();try{
  await db.exec(authFixture+sourceFixture);
  const original=(await db.query('select * from public.clients order by id')).rows;
  await migrations(db,'source');await migrations(db,'hub');
  await identity(db,ADMIN);await app(db,'profile.ensure',{alias:'Entrenador'});
  // A shared account is allowed to use League; this must not make it a new staff member.
  await identity(db,ALICE);await app(db,'profile.ensure',{alias:'Deportista'});
  const workout={id:crypto.randomUUID(),name:'Actividad personal',started_at:new Date().toISOString(),sets:[{exercise_id:EXERCISE,weight_kg:20,reps:8}]};
  await app(db,'workout.save',workout);
  assert.equal((await app(db,'snapshot')).workouts.length,1);
  await assert.rejects(gateway(db,'profile.delete',{athlete_id:ADMIN}),/permission denied/);
  await identity(db,null,'service_role');
  await gateway(db,'profile.delete',{athlete_id:ADMIN});
  await db.exec('reset role');
  assert.equal((await db.query('select count(*)::int as n from auth.users where id=$1',[ADMIN])).rows[0].n,1);
  assert.equal((await db.query('select role from public.gym_users where user_id=$1',[ADMIN])).rows[0].role,'admin');
  assert.deepEqual((await db.query('select * from public.clients order by id')).rows,original);
  assert.equal((await db.query('select count(*)::int as n from public.league_profiles where id=$1',[ADMIN])).rows[0].n,0);
  await identity(db,ALICE);assert.equal((await app(db,'snapshot')).workouts.length,1);
  await identity(db,null,'service_role');await gateway(db,'profile.delete',{athlete_id:ALICE});
  await db.exec('reset role');
  assert.equal((await db.query('select count(*)::int as n from public.league_workouts where athlete_id=$1',[ALICE])).rows[0].n,0);
  assert.equal((await db.query('select count(*)::int as n from auth.users where id=$1',[ALICE])).rows[0].n,1);
  assert.deepEqual((await db.query('select * from public.clients order by id')).rows,original);
 }finally{await db.close();}
});

test('shared runtime uses the existing project and its server key for both athlete and staff',async()=>{
 const {createConfiguredLeagueHandler}=await import('../backend/runtime.mjs');
 const REF='aaaaaaaaaaaaaaaaaaaa',CORE='bbbbbbbbbbbbbbbbbbbb',calls=[];
 const env=new Map([
  ['LEAGUE_SHARED_PROJECT','true'],['SUPABASE_URL','https://'+REF+'.supabase.co'],
  ['SUPABASE_SERVICE_ROLE_KEY','sb_secret_shared-test'],['LEAGUE_CORE_REF',CORE],
  ['LEAGUE_CORE_SECRET','sb_secret_core-test'],['LEAGUE_ACTIVATION_URL','https://league.example.test/'],
  ['LEAGUE_WEB_ORIGINS','https://league.example.test'],
 ]);
 const fetcher=async(url,options)=>{
  calls.push({url,key:options.headers.get('apikey'),bearer:options.headers.get('Authorization'),body:JSON.parse(options.body||'null')});
  if(url.endsWith('/auth/v1/user'))return Response.json({id:ADMIN,email_confirmed_at:new Date().toISOString()});
  if(url.endsWith('/rpc/league_staff'))return Response.json({actor_id:ADMIN,gym_id:GYM,role:'admin'});
  if(url.endsWith('/rpc/core_league_entitlement'))return Response.json({enabled:true,gym_id:GYM,source_ref:REF,name:'Shared QA',athlete_code:'AL-QA1234'});
  if(url.endsWith('/rpc/league_gateway'))return Response.json([]);
  return Response.json({ok:true});
 };
 const handler=createConfiguredLeagueHandler(env,{fetcher});
 const req=body=>new Request('https://gateway.example.test',{method:'POST',headers:{Authorization:'Bearer own-user-jwt','Content-Type':'application/json',Origin:'https://league.example.test'},body:JSON.stringify(body)});
 assert.equal((await handler(req({action:'profile.ensure'}))).status,200);
 assert.equal((await handler(req({audience:'staff',project_ref:REF,gym_id:GYM,action:'catalog'}))).status,200);
 assert.ok(calls.some(c=>c.url.includes(REF)&&c.url.endsWith('/rpc/league_app')));
 assert.ok(calls.some(c=>c.url.includes(REF)&&c.url.endsWith('/rpc/league_staff')));
 assert.ok(calls.filter(c=>c.url.includes(REF)).every(c=>c.key==='sb_secret_shared-test'));
 assert.ok(calls.filter(c=>c.url.endsWith('/auth/v1/user')).every(c=>c.bearer==='Bearer own-user-jwt'));
 assert.ok(calls.some(c=>c.url.includes(CORE)&&c.key==='sb_secret_core-test'));
 assert.ok(!env.has('LEAGUE_HUB_SECRET')&&!env.has('LEAGUE_SOURCES_JSON'));
});

test('controlled pilot blocks other confirmed accounts through SQL while preserving existing gym roles',async()=>{
 const db=new PGlite();try{
  await db.exec(authFixture+sourceFixture);await migrations(db,'hub');
  await db.exec(`insert into league_private.pilot_settings values(true,true);insert into league_private.pilot_accounts values('${ALICE}');`);
  await identity(db,BOB);await assert.rejects(app(db,'profile.ensure'),/piloto/);
  await identity(db,ADMIN);await assert.rejects(app(db,'profile.ensure'),/piloto/);
  await identity(db,ALICE);await app(db,'profile.ensure');
  assert.equal((await app(db,'snapshot')).profile.id,ALICE);
  await assert.rejects(db.query('select public.league_pilot_allowed($1)',[BOB]),/permission denied/);
  await db.exec('reset role');
  assert.equal((await db.query('select count(*)::int as n from public.gym_users')).rows[0].n,3);
 }finally{await db.close();}
});

test('shared pilot uses only public Core directory metadata and rejects a non-allowlisted identity',async()=>{
 const {createConfiguredLeagueHandler}=await import('../backend/runtime.mjs');
 const REF='aaaaaaaaaaaaaaaaaaaa',CORE='bbbbbbbbbbbbbbbbbbbb',calls=[];
 const env=new Map([['LEAGUE_SHARED_PROJECT','true'],['LEAGUE_PILOT_ONLY','true'],['SUPABASE_URL','https://'+REF+'.supabase.co'],['SUPABASE_SERVICE_ROLE_KEY','sb_secret_test-only'],['LEAGUE_CORE_REF',CORE],['LEAGUE_CORE_PUBLIC_KEY','sb_publishable_directory-only'],['LEAGUE_ACTIVATION_URL','https://league.example.test/']]);
 const fetcher=async(url,options)=>{
  const body=JSON.parse(options.body||'null');calls.push({url,headers:options.headers,body});
  if(url.endsWith('/auth/v1/user'))return Response.json({id:options.headers.get('Authorization')==='Bearer other-user'?BOB:ADMIN,email_confirmed_at:new Date().toISOString()});
  if(url.endsWith('/rpc/league_pilot_allowed'))return Response.json(body.p_user_id===ADMIN);
  if(url.endsWith('/rpc/league_staff'))return Response.json({actor_id:ADMIN,gym_id:GYM,role:'admin'});
  if(url.endsWith('/rpc/core_league_public_directory'))return Response.json([{enabled:true,gym_id:GYM,source_ref:REF,name:'QA',athlete_code:'AL-QA1234'}]);
  return Response.json([]);
 };
 const handler=createConfiguredLeagueHandler(env,{fetcher});
 const req=(body,jwt='own-user')=>new Request('https://gateway.example.test',{method:'POST',headers:{Authorization:'Bearer '+jwt,'Content-Type':'application/json'},body:JSON.stringify(body)});
 assert.equal((await handler(req({audience:'staff',project_ref:REF,gym_id:GYM,action:'catalog'}))).status,200);
 const core=calls.find(c=>c.url.includes(CORE));assert.ok(core);assert.equal(core.headers.get('apikey'),'sb_publishable_directory-only');assert.equal(core.headers.get('Authorization'),null);assert.ok(!env.has('LEAGUE_CORE_SECRET'));
 assert.equal((await handler(req({action:'snapshot'},'other-user'))).status,403);
 assert.ok(!calls.some(c=>c.body?.p_action==='snapshot'));
});
