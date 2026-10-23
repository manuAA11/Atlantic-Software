import {test} from 'node:test';import assert from 'node:assert/strict';import {randomUUID} from 'node:crypto';
import {PGlite} from '@electric-sql/pglite';
import {authFixture,sourceFixture,migrations,identity,app,gateway,ALICE,BOB,ADMIN,GYM,OTHER,EXERCISE} from './database-fixture.mjs';

test('athlete hub: ownership, idempotency, invitations, rankings and gym isolation',async()=>{
 const db=new PGlite();try{
 await db.exec(authFixture);await migrations(db,'hub');
 await identity(db,ALICE);await app(db,'profile.ensure',{alias:'Alice'});
 await app(db,'profile.update',{alias:'Alice',leaderboard_opt_in:true});
 const workout={id:randomUUID(),name:'Entrenamiento',started_at:new Date().toISOString(),sets:[{exercise_id:EXERCISE,reps:5,weight_kg:50}]};
 await app(db,'workout.save',workout);await app(db,'workout.save',workout);
 assert.equal((await app(db,'snapshot')).xp,20);assert.equal((await app(db,'snapshot')).official_xp,0);
 await assert.rejects(app(db,'workout.save',{...workout,name:'Changed'}),/otro contenido/);
 await assert.rejects(db.query('update public.league_profiles set leaderboard_opt_in=true where id=$1',[ALICE]),/permission denied/);
 await identity(db,BOB);await app(db,'profile.ensure',{alias:'Bob'});
 assert.equal((await db.query('select * from public.league_workouts')).rows.length,0);
 await assert.rejects(app(db,'workout.save',workout),/otro contenido/);
 await assert.rejects(gateway(db,'directory.sync',{gym_id:GYM}),/permission denied/);
 await identity(db,null,'anon');await assert.rejects(app(db,'snapshot'),/permission denied/);
 await identity(db,null,'service_role');
 await gateway(db,'directory.sync',{gym_id:GYM,source_ref:'aaaaaaaaaaaaaaaaaaaa',name:'Gym QA',athlete_code:'QA-GYM-123',enabled:true});
 await gateway(db,'directory.sync',{gym_id:OTHER,source_ref:'aaaaaaaaaaaaaaaaaaaa',name:'Other QA',athlete_code:'OTHER-GYM',enabled:true});
 await identity(db,ALICE);await app(db,'gym.request',{code:'QA-GYM-123'});
 assert.equal(await app(db,'gym.connection',{gym_id:GYM}),null);
 const req=(await app(db,'snapshot')).requests[0].id,profile=randomUUID();
 const staff={gym_id:GYM,actor_id:ADMIN,actor_role:'admin',actor_email:'coach@example.test'};
 await identity(db,null,'service_role');
 await assert.rejects(gateway(db,'staff.approve_join',{...staff,gym_id:OTHER,request_id:req,source_profile_id:profile}),/no disponible/);
 await gateway(db,'staff.approve_join',{...staff,request_id:req,source_profile_id:profile});
 await identity(db,ALICE);assert.equal((await app(db,'gym.connection',{gym_id:GYM})).source_profile_id,profile);
 await app(db,'record.submit',{gym_id:GYM,exercise_id:EXERCISE,weight_kg:50,reps:5,division:'OPEN',weight_class:'60-75',request_key:randomUUID()});
 assert.deepEqual(await app(db,'leaderboard',{kind:'STRENGTH',exercise_id:EXERCISE,division:'OPEN',weight_class:'60-75'}),[]);
 const record=(await app(db,'snapshot')).records[0].id;
 await identity(db,null,'service_role');
 await assert.rejects(gateway(db,'staff.verify',{...staff,actor_email:'alice@example.test',request_id:record,decision:'APPROVED',reason:'Verified in gym'}),/Otra persona/);
 await gateway(db,'staff.verify',{...staff,request_id:record,decision:'APPROVED',reason:'Verified in gym'});
 const attendance={gym_id:GYM,athlete_id:ALICE,local_date:new Date().toISOString().slice(0,10)};
 await gateway(db,'attendance.credit',attendance);await gateway(db,'attendance.credit',attendance);
 const draft=await gateway(db,'draft.open',{gym_id:GYM,athlete_id:ALICE,routine_snapshot:{name:'Original routine',exercises:[]}});
 await identity(db,ALICE);
 const official={...workout,id:randomUUID(),draft_id:draft.draft_id};await app(db,'workout.save',official);
 const state=await app(db,'snapshot');assert.equal(state.xp,45);assert.equal(state.official_xp,25);
 assert.equal(state.workouts.find(x=>x.id===official.id).routine_snapshot.name,'Original routine');
 assert.equal((await app(db,'leaderboard',{exercise_id:EXERCISE,division:'OPEN',weight_class:'60-75'}))[0].alias,'Alice');
 assert.deepEqual(await app(db,'leaderboard',{exercise_id:EXERCISE,division:'OPEN',weight_class:'GT90'}),[]);
 await app(db,'profile.update',{alias:'Alice',leaderboard_opt_in:false});
 assert.deepEqual(await app(db,'leaderboard',{exercise_id:EXERCISE,division:'OPEN',weight_class:'60-75'}),[]);
 await identity(db,null,'service_role');
 await gateway(db,'directory.sync',{gym_id:GYM,source_ref:'aaaaaaaaaaaaaaaaaaaa',name:'Gym QA',athlete_code:'QA-GYM-123',enabled:false});
 await identity(db,ALICE);assert.equal((await app(db,'snapshot')).workouts.length,2);
 await assert.rejects(app(db,'record.submit',{gym_id:GYM,exercise_id:EXERCISE,request_key:randomUUID()}),/no está disponible/);
 }finally{await db.close();}
});

test('source reuses Gym tables, enforces capacity, membership, staff roles and tenant boundaries',async()=>{
 const db=new PGlite();try{
 await db.exec(authFixture+sourceFixture);await migrations(db,'source');
 await db.exec(`insert into public.league_gym_settings(gym_id,enabled,pilot_client_ids) values('${GYM}',true,array[1,2,3]),('${OTHER}',true,array[4]);`);
 await identity(db,ADMIN);
 const call=async(a,d={},g=GYM)=>(await db.query('select public.league_staff($1,$2,$3::jsonb) as value',[g,a,JSON.stringify(d)])).rows[0].value;
 const p1=await call('provision',{client_id:'1'}),p2=await call('provision',{client_id:'2'}),p3=await call('provision',{client_id:'3'});
 await assert.rejects(call('provision',{client_id:'4'}),/piloto|disponible/);
 await assert.rejects(call('clients',{},OTHER),/permiso/);
 await identity(db,ALICE);await assert.rejects(call('context'),/permiso/);
 await identity(db,ADMIN);
 await call('routine.assign',{name:'Rutina QA',profiles:[p1.profile_id,p2.profile_id],exercises:[{catalog_id:EXERCISE,name:'Press de banca',sets:3,reps:10,rest_seconds:60,weight_kg:30,day:'Día 1'}]});
 await identity(db,null,'service_role');
 const athlete=async(profile,action,data={})=>(await db.query('select public.league_source($1,$2,$3,$4::jsonb) as value',[GYM,profile,action,JSON.stringify(data)])).rows[0].value;
 assert.equal((await athlete(p1.profile_id,'routines')).length,1);
 assert.equal((await athlete(p1.profile_id,'calendar'))[0].reserved,0);
 await athlete(p1.profile_id,'reserve',{class_id:'1'});await athlete(p1.profile_id,'reserve',{class_id:'1'});
 await assert.rejects(athlete(p2.profile_id,'reserve',{class_id:'1'}),/cupos/);
 await assert.rejects(athlete(p3.profile_id,'reserve',{class_id:'1'}),/membresía/);
 await assert.rejects(athlete(p2.profile_id,'reserve',{class_id:'2'}),/no disponible/);
 await athlete(p1.profile_id,'cancel',{class_id:'1'});await athlete(p2.profile_id,'reserve',{class_id:'1'});
 assert.equal((await athlete(p2.profile_id,'calendar'))[0].mine,true);
 await identity(db,ALICE);await assert.rejects(athlete(p1.profile_id,'calendar'),/permission denied/);
 }finally{await db.close();}
});
