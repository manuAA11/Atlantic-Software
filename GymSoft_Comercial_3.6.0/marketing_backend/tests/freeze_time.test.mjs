import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluate,localParts} from '../core/automation.mjs';
import {respond} from '../core/chatbot.mjs';
import {runJobs,dispatch} from '../core/worker.mjs';
const rule={id:'r',revision:1,enabled:true,trigger_type:'MEMBERSHIP_BEFORE',trigger_options:{value:3,time:'09:00'},conditions:[]};
const context={gym_id:'g',client_id:1,first_name:'Ana',active:true,phone:'3001234567',whatsapp_opt_in:true,
 created_at:'2026-01-01T12:00:00Z',timezone:'America/Bogota',today:'2026-10-24',
 server_now:'2026-10-24T14:00:00Z',membership:{membership_id:1,end_date:'2026-10-27',status:'AL DÍA'}};
test('09 AM Bogotá is 14 UTC, independently of server timezone',()=>{
 assert.equal(evaluate(rule,{...context,server_now:'2026-10-24T13:59:59Z'}),null);
 assert.ok(evaluate(rule,context));
 assert.equal(localParts('2026-10-08T02:30:00Z','America/Bogota').date,'2026-10-07');
});
test('A second gym uses its own zone and daylight saving',()=>{
 for(const [today,before,at] of [['2026-07-24','12:59:59','13:00:00'],['2026-01-24','13:59:59','14:00:00']]){
  const c={...context,today,timezone:'America/New_York',membership:{...context.membership,end_date:today.slice(0,8)+'27'}};
  assert.equal(evaluate(rule,{...c,server_now:today+'T'+before+'Z'}),null);
  assert.ok(evaluate(rule,{...c,server_now:today+'T'+at+'Z'}));
 }
});
test('Expiry moved to October 27 sends on October 24, never October 17 or while frozen',()=>{
 assert.ok(evaluate(rule,context));
 assert.equal(evaluate(rule,{...context,today:'2026-10-17',server_now:'2026-10-17T14:00:00Z'}),null);
 assert.equal(evaluate(rule,{...context,membership:{...context.membership,status:'FROZEN',frozen:true}}),null);
});
test('Verified chatbot shows freeze last day, resume day and extended expiry',async()=>{
 const out=await respond({rpc:async()=>({state:'VERIFIED',client_id:1,first_name:'Ana',
  membership:{...context.membership,status:'FROZEN',frozen:true,freeze_last_date:'2026-10-14',resume_date:'2026-10-15'}}),
  gym:{id:'g',name:'ZTATTUZ'},sender:'573001234567',message:{text:{body:'Mi membresía'}}});
 for(const text of ['CONGELADA','2026-10-14','2026-10-15','2026-10-27'])assert.ok(out.interactive.body.text.includes(text));
});
test('Worker completes freezes even when automation jobs are disabled',async()=>{
 const calls=[];
 assert.deepEqual(await runJobs({rpc:async(name)=>{calls.push(name);return name==='marketing_service_jobs'?[]:0;}},'https://example.test'),{processed:0});
 assert.deepEqual(calls,['membership_service_complete_freezes','marketing_service_jobs']);
});
test('Frozen guard prevents an already claimed message from calling Meta',async()=>{
 let provider=0,result;
 const db={rpc:async(name,args)=>{
  if(name==='marketing_service_claim')return[{id:1,claim_id:'c',gym_id:'g'}];
  if(name==='marketing_service_send_guard')return{allowed:false,reason:'MEMBERSHIP_FROZEN'};
  if(name==='marketing_service_send_result'){result=args;return;}
  throw new Error(name);
 }};
 assert.deepEqual(await dispatch(db,{fetcher:()=>{provider++;throw new Error('Unexpected provider');}}),{sent:0});
 assert.equal(provider,0);assert.equal(result.p_status,'SKIPPED');assert.equal(result.p_error,'MEMBERSHIP_FROZEN');
});
