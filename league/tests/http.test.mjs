import test from 'node:test';
import assert from 'node:assert/strict';
import {createLeagueHandler,configuredSource} from '../backend/handler.mjs';
import {ALICE,ADMIN,GYM,OTHER,EXERCISE} from './database-fixture.mjs';
const REF='aaaaaaaaaaaaaaaaaaaa';
function fixture({enabled=true,linked=true,role='admin',confirmed=true,sourceRef=REF}={}){
 const calls=[];
 const actor={id:ALICE,email:'athlete@example.test',email_confirmed_at:confirmed?'2026-01-01':null,last_sign_in_at:new Date().toISOString()};
 const staff={id:ADMIN,email:'coach@example.test',email_confirmed_at:'2026-01-01'};
 const transport=(name,user)=>({
  key:name+'-server-secret',url:'https://'+name+'.supabase.co',
  withUser(jwt){return {request:async()=>{calls.push([name,'auth',jwt]);if(jwt!==name+'-user-jwt')throw Object.assign(Error('Denied'),{status:401});return user;},rpc:async(action,args)=>{calls.push([name,action,args]);if(action==='league_staff')return args.p_action==='context'?{gym_id:GYM,actor_id:ADMIN,role}:args.p_data;if(action==='league_app')return args.p_action==='gym.connection'?(linked?{source_profile_id:ALICE}:null):{action:args.p_action};}};},
  async rpc(action,args){calls.push([name,action,args]);
   if(name==='core')return {enabled,gym_id:GYM,name:'QA gym',source_ref:sourceRef,athlete_code:'AL-QA1234'};
   if(name==='hub'&&args.p_action==='staff.catalog')return [{id:EXERCISE,name:'Trusted catalog name'}];
   if(name==='source')return {own:true};
   return {ok:true};
  },
  async read(){return [{gym_id:GYM}];},
  async request(path,options){calls.push([name,path,options]);return [];}
 });
 const hub=transport('hub',actor),source=transport('source',staff),core=transport('core',staff);
 return {calls,hub,source,handler:createLeagueHandler({hub,core,sources:{[REF]:source},allowedOrigins:['https://qa.example.test']})};
}
const request=(body,jwt='hub-user-jwt',headers={})=>new Request('https://gateway.example.test',{method:'POST',headers:{Authorization:'Bearer '+jwt,'Content-Type':'application/json',...headers},body:JSON.stringify(body)});
test('personal activity survives a disabled gym; official actions require Core and an approved own link',async()=>{
 const {handler,calls}=fixture({enabled:false});
 assert.equal((await handler(request({action:'workout.save',data:{}}))).status,200);
 assert.ok(!calls.some(c=>c[0]==='core'));
 assert.equal((await handler(request({action:'gym.reserve',data:{gym_id:GYM,class_id:'1'}}))).status,403);
 assert.ok(!calls.some(c=>c[0]==='source'&&c[1]==='league_source'));
 const second=fixture({linked:false});
 assert.equal((await second.handler(request({action:'gym.routines',data:{gym_id:GYM}}))).status,403);
 assert.ok(!second.calls.some(c=>c[0]==='source'));
});
test('athletes cannot pick another profile or gym provider',async()=>{
 const {handler,calls}=fixture();
 assert.equal((await handler(request({action:'gym.routines',data:{gym_id:GYM,profile_id:ADMIN,client_id:'999'}}))).status,200);
 const forwarded=calls.find(c=>c[1]==='league_source')[2];
 assert.equal(forwarded.p_profile_id,ALICE);assert.equal(forwarded.p_gym_id,GYM);
 assert.equal((await handler(request({audience:'staff',project_ref:OTHER,gym_id:GYM,action:'pending'},'source-user-jwt'))).status,403);
 const wrong=fixture({sourceRef:'bbbbbbbbbbbbbbbbbbbb'});
 assert.equal((await wrong.handler(request({audience:'staff',project_ref:REF,gym_id:GYM,action:'pending'},'source-user-jwt'))).status,403);
});
test('staff roles are verified at source; actor/name claims in the body cannot override them',async()=>{
 const {handler,calls}=fixture();
 const result=await handler(request({audience:'staff',project_ref:REF,gym_id:GYM,action:'verify',data:{actor_id:ALICE,actor_role:'owner',gym_id:OTHER,request_id:ALICE}},'source-user-jwt'));
 assert.equal(result.status,200);
 const passed=calls.find(c=>c[1]==='league_gateway'&&c[2].p_action==='staff.verify')[2].p_data;
 assert.equal(passed.actor_id,ADMIN);assert.equal(passed.actor_role,'admin');assert.equal(passed.gym_id,GYM);
 await handler(request({audience:'staff',project_ref:REF,gym_id:GYM,action:'routine.assign',data:{exercises:[{catalog_id:EXERCISE,name:'Untrusted name'}]}},'source-user-jwt'));
 assert.equal(calls.find(c=>c[1]==='league_staff'&&c[2].p_action==='routine.assign')[2].p_data.exercises[0].name,'Trusted catalog name');
 const unauthorized=fixture({role:'receptionist'});
 assert.equal((await unauthorized.handler(request({audience:'staff',project_ref:REF,gym_id:GYM,action:'pending'},'source-user-jwt'))).status,403);
});
test('auth, CORS, size and rate guards reject invalid requests before database writes',async()=>{
 const {handler,hub}=fixture();
 assert.equal((await handler(request({action:'snapshot'},hub.key))).status,401);
 assert.equal((await handler(request({action:'snapshot'},'hub-user-jwt',{Origin:'https://evil.example.test'}))).status,403);
 assert.equal((await handler(request({action:'snapshot',data:{padding:'a'.repeat(140000)}}))).status,413);
 assert.equal((await fixture({confirmed:false}).handler(request({action:'snapshot'}))).status,401);
 const cors=await handler(request({action:'snapshot'},'hub-user-jwt',{Origin:'https://qa.example.test'}));
 assert.equal(cors.headers.get('Access-Control-Allow-Origin'),'https://qa.example.test');
 const rate=fixture();
 for(let i=0;i<90;i++)assert.equal((await rate.handler(request({action:'snapshot'}))).status,200);
 assert.equal((await rate.handler(request({action:'snapshot'}))).status,429);
});
test('account removal requires an explicit recent reauthentication',async()=>{
 const {handler,calls}=fixture();
 assert.equal((await handler(request({action:'account.delete',data:{}}))).status,403);
 assert.ok(!calls.some(c=>String(c[1]).startsWith('/auth/v1/admin')));
 assert.equal((await handler(request({action:'account.delete',data:{confirm:'ELIMINAR'}}))).status,200);
 assert.ok(calls.some(c=>c[1]==='league_gateway'&&c[2].p_action==='profile.delete'&&c[2].p_data.athlete_id===ALICE));
 assert.ok(!calls.some(c=>String(c[1]).startsWith('/auth/v1/admin')));
});
test('new secret keys stay server-side in apikey and user JWTs are forwarded separately',async()=>{
 const seen=[];
 const source=configuredSource({projectRef:REF,serviceKey:'sb_secret_synthetic-test',fetcher:async(url,options)=>{seen.push(options.headers);return Response.json({});}});
 await source.rpc('league_source',{});await source.withUser('user-test-token').rpc('league_staff',{});
 assert.equal(seen[0].get('apikey'),'sb_secret_synthetic-test');assert.equal(seen[0].get('Authorization'),null);
 assert.equal(seen[1].get('Authorization'),'Bearer user-test-token');
 assert.throws(()=>configuredSource({projectRef:'https://evil.example.test',serviceKey:'sb_secret_test'}));
});
