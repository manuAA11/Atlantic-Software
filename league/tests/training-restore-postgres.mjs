// Actual backup/restore rehearsal. ONLY self-created databases in disposable LOCAL PostgreSQL.
import pg from 'pg';
import assert from 'node:assert/strict';
import {randomUUID,createHash} from 'node:crypto';
import {mkdtemp,open,readFile,rm,writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawn} from 'node:child_process';
import {authFixture,sourceFixture,migrations,identity,ADMIN,GYM,app} from './database-fixture.mjs';
import {trainingMigration,trainingSeed} from './training-fixture.mjs';
import {assessPreflight,readPreflight} from '../scripts/training-preflight.mjs';

const url=new URL(process.env.LEAGUE_TEST_DATABASE_URL||'invalid:');
if(!['postgres:','postgresql:'].includes(url.protocol)||!['localhost','127.0.0.1','[::1]'].includes(url.hostname)||url.search||url.hash||!(process.env.CI==='true'||process.env.LEAGUE_TEST_DATABASE_ALLOW_LOCAL==='1'))throw Error('Explicit disposable local PostgreSQL required; URL overrides are not allowed');
const container=process.env.LEAGUE_TEST_POSTGRES_CONTAINER;
if(container&&(!(process.env.CI==='true')||!(/^[\da-f]{12,64}$/i.test(container))))throw Error('Only the CI PostgreSQL service container is allowed');
const config={host:url.hostname.replace(/^\[|\]$/g,''),port:Number(url.port||5432),user:decodeURIComponent(url.username),password:decodeURIComponent(url.password),database:decodeURIComponent(url.pathname.slice(1)),ssl:false,connectionTimeoutMillis:10000};
const admin=new pg.Client(config);await admin.connect();const databases=[],connections=[];
const directory=await mkdtemp(join(tmpdir(),'atlantic-training-restore-'));
const evidence={scope:'Plain PostgreSQL 17 synthetic fixtures only; not a Supabase production backup',before_restore:false,after_restore:false,rollback_reenable:false,credentials_logged:false};
try{
 async function database(){
  const name='training_restore_'+randomUUID().replaceAll('-','');await admin.query('create database '+name);databases.push(name);
  const db=new pg.Client({...config,database:name});await db.connect();connections.push(db);
  return {name,db,adapter:{query:(...a)=>db.query(...a),exec:sql=>db.query(sql)}};
 }
 async function clientTool(command,name,file){
  assert(databases.includes(name),'Refuse non-owned database');
  const read=command==='pg_restore',handle=await open(file,read?'r':'wx',0o600);
  const args=['--host','127.0.0.1','--port',String(container?5432:config.port),'--username',config.user,'--dbname',name];
  if(read)args.push('--exit-on-error','--single-transaction');else args.push('--format=custom');
  const env={...process.env,PGPASSWORD:config.password};
  for(const key of ['PGSERVICE','PGSERVICEFILE','PGHOST','PGHOSTADDR','PGPORT','PGDATABASE','PGOPTIONS'])delete env[key];
  try{
   await new Promise((resolve,reject)=>{
    const child=spawn(container?'docker':command,container?['exec',...(read?['-i']:[]),'--env','PGPASSWORD',container,command,...args]:args,
     {env,stdio:[read?handle.fd:'ignore',read?'ignore':handle.fd,'pipe']});
    let error='';child.stderr.on('data',data=>{error=(error+data).slice(-4000);});child.on('error',reject);
    child.on('close',code=>code===0?resolve():reject(Error(command+' failed with exit '+code+'; synthetic fixture only: '+error)));
   });
  }finally{await handle.close();}
 }
 const tables=['auth.users','public.clients','public.routines','public.exercises','public.checkins','public.classes','public.reservations','public.league_exercise_catalog','public.league_client_profiles','public.league_gym_settings','public.league_gym_directory','public.league_coaches','public.league_profiles','public.league_workouts','public.league_xp_events','public.league_workout_drafts','public.league_links','public.league_strength_requests','public.gym_routine_templates','league_source_private.training_requests','league_source_private.reservation_history','league_source_private.training_audit'];
 async function fingerprint(db){
  const snapshot={};for(const table of tables){
   if(!(await db.query('select to_regclass($1) as r',[table])).rows[0].r)continue;
   // Constant table names only; rows and Auth details never enter the log/report.
   snapshot[table]=(await db.query(`select count(*)::int as rows,md5(coalesce(jsonb_agg(d order by d::text)::text,'[]')) as digest from (select to_jsonb(t) d from ${table} t) x`)).rows[0];
  }return snapshot;
 }
 const original=await database();
 const roles=authFixture.replace(/create role (anon|authenticated|service_role) ([^;]+);/g,(_,name,options)=>"do $$begin if not exists(select 1 from pg_roles where rolname='"+name+"') then create role "+name+' '+options+';end if;end$$;');
 await original.db.query(roles+sourceFixture);await migrations(original.adapter,'hub');await migrations(original.adapter,'source');
 await original.db.query("select setval(pg_get_serial_sequence('public.classes','id'),(select max(id) from public.classes))");
 const old=(await original.db.query("insert into public.routines(gym_id,client_id,name,goal,notes,active) values($1,1,'Legacy QA','Original goal','Original notes',true) returning id",[GYM])).rows[0].id;
 await original.db.query("insert into public.exercises(gym_id,routine_id,day_name,name,sets,reps,weight,notes,position) values($1,$2,'Lunes','Legacy exercise','3','10','20','Original exercise notes',1)",[GYM,old]);
 assert.equal(assessPreflight(await readPreflight(original.db)).state,'ready_for_migration');
 const baseline=await fingerprint(original.db),before=join(directory,'before.backup');await clientTool('pg_dump',original.name,before);
 const migrated=await database();await clientTool('pg_restore',migrated.name,before);assert.deepEqual(await fingerprint(migrated.db),baseline);evidence.before_restore=true;
 await migrated.db.query(trainingMigration);await migrated.db.query(trainingMigration);await migrated.db.query(trainingSeed);await migrated.db.query(trainingSeed);
 assert.equal(assessPreflight(await readPreflight(migrated.db)).state,'installed');
 assert.deepEqual((await migrated.db.query('select name,goal,notes,active from public.routines where id=$1',[old])).rows[0],{name:'Legacy QA',goal:'Original goal',notes:'Original notes',active:true});
 assert.equal((await migrated.db.query('select count(*)::int n from public.clients')).rows[0].n,4);
 await identity(migrated.adapter,ADMIN);
 await app(migrated.adapter,'profile.ensure',{alias:'Backup QA athlete'});
 const workoutId=randomUUID();await app(migrated.adapter,'workout.save',{id:workoutId,name:'Backup QA workout',started_at:new Date().toISOString(),sets:[{exercise_id:'10000000-0000-4000-8000-000000000002',weight_kg:20,reps:10}]});
 const rpc=async(db,a,d)=>(await db.query('select public.gym_training($1,$2,$3) value',[GYM,a,d])).rows[0].value;
 const request={request_id:randomUUID(),name:'Restorable QA plan',clients:[1],exercises:[{catalog_id:'10000000-0000-4000-8000-000000000002',day:'Día 1',sets:3,reps:10,weight_kg:20,rest_seconds:60,notes:'Preserve after restore'}]};
 const assignment=await rpc(migrated.db,'routine.assign',request);
 const classData={request_id:randomUUID(),name:'Restorable QA class',starts_at:new Date(Date.now()+86400000).toISOString(),capacity:1,duration_minutes:50,requires_membership:false};
 const classId=(await rpc(migrated.db,'class.save',classData))[0].class_id;
 const reservation={request_id:randomUUID(),class_id:classId,client_id:1};const booked=await rpc(migrated.db,'reservation.reserve',reservation);
 await migrated.db.query('reset role');
 await migrated.db.query("insert into public.league_gym_settings(gym_id,enabled,pilot_client_ids) values($1,true,array[1]::bigint[])",[GYM]);
 await identity(migrated.adapter,ADMIN);const profile=(await migrated.db.query("select public.league_staff($1,'provision',$2) value",[GYM,{client_id:1}])).rows[0].value.profile_id;
 await migrated.db.query('reset role');const expected=await fingerprint(migrated.db),after=join(directory,'after.backup');await clientTool('pg_dump',migrated.name,after);
 const restored=await database();await clientTool('pg_restore',restored.name,after);assert.deepEqual(await fingerprint(restored.db),expected);evidence.after_restore=true;
 assert.equal(assessPreflight(await readPreflight(restored.db)).state,'installed');
 await identity(restored.adapter,ADMIN);assert.deepEqual(await rpc(restored.db,'routine.assign',request),assignment);assert.deepEqual(await rpc(restored.db,'reservation.reserve',reservation),booked);
 assert((await app(restored.adapter,'snapshot')).workouts.some(w=>w.id===workoutId));
 await identity(restored.adapter,null,'service_role');
 const calendar=(await restored.db.query("select public.league_source($1,$2,'calendar','{}') value",[GYM,profile])).rows[0].value;
 assert(calendar.some(c=>c.id===String(classId)&&c.mine));
 await restored.db.query('reset role');
 await restored.db.query(await readFile(new URL('../../training/rollback/disable_workspace.sql',import.meta.url),'utf8'));
 assert.equal(assessPreflight(await readPreflight(restored.db)).state,'disabled');assert.deepEqual(await fingerprint(restored.db),expected);
 await identity(restored.adapter,ADMIN);await assert.rejects(rpc(restored.db,'context',{}),/permission denied/);
 await restored.db.query('reset role');await restored.db.query(trainingMigration);assert.equal(assessPreflight(await readPreflight(restored.db)).state,'installed');
 await identity(restored.adapter,ADMIN);assert.deepEqual(await rpc(restored.db,'routine.assign',request),assignment);evidence.rollback_reenable=true;
 evidence.tables_compared=Object.keys(expected).length;evidence.before_sha256=createHash('sha256').update(await readFile(before)).digest('hex');evidence.after_sha256=createHash('sha256').update(await readFile(after)).digest('hex');
 const broken=join(directory,'corrupt.backup');await writeFile(broken,'invalid archive',{mode:0o600});await assert.rejects(clientTool('pg_restore',restored.name,broken),/failed with exit/);evidence.corrupt_archive_rejected=true;
 const nextClass=(await rpc(restored.db,'class.save',{...classData,request_id:randomUUID(),name:'Sequence QA'}))[0].class_id;assert(nextClass>classId);evidence.sequence_advanced=true;
 console.log(JSON.stringify(evidence,null,2));
}finally{
 for(const c of connections)await c.end().catch(()=>{});
 for(const name of databases)await admin.query('drop database '+name+' with (force)');
 await admin.end();await rm(directory,{recursive:true,force:true});
}
