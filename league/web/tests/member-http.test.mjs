import test from 'node:test';
import assert from 'node:assert/strict';
import {createLeagueMemberHandler,validatePushEndpoint} from '../../backend/member-handler.mjs';
const actor='a0000000-0000-4000-8000-000000000001',gym='d0000000-0000-4000-8000-000000000004',requestKey='b0000000-0000-4000-8000-000000000002';
function fixture({membership={active:false,frozen:false,ends_at:'2026-11-10'},bridgeStatus=200}={}){
 const calls=[];
 const hub={key:'server-secret',withUser(jwt){assert.equal(jwt,'valid-user-session');return {request:async path=>{assert.equal(path,'/auth/v1/user');return {id:actor,email_confirmed_at:'2026-01-01'};}};},async rpc(name,args){calls.push({name,args});return {id:requestKey,status:'PENDING'};}};
 const handler=createLeagueMemberHandler({hub,allowedOrigins:['https://league.example'],leagueHandler:async req=>{const payload=await req.json();assert.equal(payload.action,'gym.membership');assert.equal(payload.data.gym_id,gym);return Response.json({data:membership},{status:bridgeStatus});}});
 const request=(action,data={},headers={})=>new Request('https://api.example/members',{method:'POST',headers:{Authorization:'Bearer valid-user-session',Origin:'https://league.example','Content-Type':'application/json',...headers},body:JSON.stringify({action,data:{gym_id:gym,...data}})});
 return {handler,request,calls};
}
test('expired membership may request renewal; period and identity come from server',async()=>{
 const {handler,request,calls}=fixture();const res=await handler(request('renewals.create',{request_key:requestKey,period_key:'ATTACKER',athlete_id:requestKey}));
 assert.equal(res.status,200);assert.equal(res.headers.get('Cache-Control'),'no-store');assert.equal(calls.length,1);
 assert.deepEqual(calls[0].args,{p_actor:actor,p_gym:gym,p_action:'renewals.create',p_data:{request_key:requestKey,period_key:'2026-11-10'}});
});
test('foreign origin, missing auth, secret key, foreign gym and unknown action cannot write',async()=>{
 for(const variant of ['origin','auth','key','gym','action']){
  const f=fixture({bridgeStatus:variant==='gym'?403:200});
  const res=await f.handler(f.request(variant==='action'?'renewals.approve':'renewals.create',{request_key:requestKey},variant==='origin'?{Origin:'https://evil.example'}:variant==='auth'?{Authorization:''}:variant==='key'?{Authorization:'Bearer server-secret'}:{}));
  assert.ok(res.status>=400);assert.equal(f.calls.length,0);
 }
});
test('unconfirmed backend operations are not presented as successful',async()=>{
 const f=fixture({bridgeStatus:503});const res=await f.handler(f.request('renewals.create',{request_key:requestKey}));assert.equal(res.status,503);assert.equal(f.calls.length,0);
});
test('invalid or missing payloads and oversized streams are rejected',async()=>{
 const f=fixture();for(const body of ['null','[]','{',JSON.stringify({action:'renewals.list',data:'bad'})]){
  const res=await f.handler(new Request('https://api.example/members',{method:'POST',headers:{Authorization:'Bearer valid-user-session'},body}));assert.equal(res.status,400);
 }
 const large=await f.handler(new Request('https://api.example/members',{method:'POST',headers:{Authorization:'Bearer valid-user-session'},body:'x'.repeat(17000)}));assert.equal(large.status,413);assert.equal(f.calls.length,0);
});
test('push endpoints reject private addresses and untrusted domains',()=>{
 for(const url of ['http://fcm.googleapis.com/x','https://127.0.0.1/x','https://fcm.googleapis.com.evil.example/x','https://user:pass@fcm.googleapis.com/x','https://fcm.googleapis.com:444/x','https://evil.example/x'])assert.equal(validatePushEndpoint(url),false,url);
 for(const url of ['https://fcm.googleapis.com/x','https://web.push.apple.com/x','https://updates.push.services.mozilla.com/x'])assert.equal(validatePushEndpoint(url),true,url);
});
