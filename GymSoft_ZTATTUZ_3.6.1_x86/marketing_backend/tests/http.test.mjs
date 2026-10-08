import test from 'node:test';import assert from 'node:assert/strict';
import {createHandler} from '../handler.mjs';import {wompiWebhook,metaWebhook} from '../core/webhooks.mjs';
import {sha256,hmacHex} from '../core/security.mjs';import {dispatch} from '../core/worker.mjs';
const base='https://example.test/functions/v1/marketing',gym='20000000-0000-4000-8000-000000000001';
const keys={public_key:'pub_test_demo',private_key:'prv_test_demo',events_secret:'test_events_demo',integrity_secret:'test_integrity_demo'};
function request(path,body,headers={}){return new Request(base+path,{method:'POST',headers:{'content-type':'application/json',...headers},body:JSON.stringify(body)});}
test('Admin mutations require authorization before provider access',async()=>{let sends=0;const db={authorize:async()=>{throw Object.assign(new Error(),{code:'x'})},rpc:async()=>{sends++;}};const r=await createHandler({db,baseURL:base})(request('/admin',{gym_id:gym,action:'connect_wompi',credentials:keys}));assert.equal(r.status,500);assert.equal(sends,0);});
test('Scheduler rejects missing token',async()=>{const h=createHandler({db:{rpc:async()=>false},baseURL:base});assert.equal((await h(request('/jobs',{}))).status,403);});
test('Hosted Edge mount resolves health and still authenticates scheduler requests',async()=>{
 const calls=[];const h=createHandler({db:{rpc:async(n)=>{calls.push(n);return n==='marketing_service_health'?{database:true,scheduler_installed:true}:false;}},baseURL:base});
 assert.equal((await h(new Request('http://edge.internal/marketing/health'))).status,200);
 const job=await h(new Request('http://edge.internal/marketing/jobs',{method:'POST',body:'{}'}));
 assert.equal(job.status,403);
 assert.deepEqual(calls,['marketing_service_health','marketing_service_scheduler_authorized']);
});
test('A similarly named function cannot match the protected mount',async()=>{
 let calls=0;const h=createHandler({db:{rpc:async()=>{calls++;}},baseURL:base});
 for(const p of ['/marketing-extra/jobs','/functions/v1/marketing-extra/jobs']){
  assert.equal((await h(new Request('http://edge.internal'+p,{method:'POST',body:'{}'}))).status,404);
 }
 assert.equal(calls,0);
});
test('Health probes the database and requires an installed scheduler',async()=>{
 let installed=false;const calls=[];
 const h=createHandler({db:{rpc:async(n)=>{calls.push(n);return {database:true,scheduler_installed:installed,server_now:'2026-10-08T02:30:00Z'};}},baseURL:base});
 let r=await h(new Request(base+'/health'));assert.equal(r.status,503);assert.equal((await r.json()).ready,false);
 installed=true;r=await h(new Request(base+'/health'));assert.equal(r.status,200);
 assert.deepEqual(await r.json(),{service:'marketing',ready:true,database:true,scheduler_installed:true,server_now:'2026-10-08T02:30:00Z'});
 assert.deepEqual(calls,['marketing_service_health','marketing_service_health']);
});
test('A failed database is never reported healthy or exposes its response',async()=>{
 const h=createHandler({db:{rpc:async()=>{throw new Error('PRIVATE KEY detail');}},baseURL:base});
 const r=await h(new Request(base+'/health'));assert.equal(r.status,500);assert.equal((await r.text()).includes('PRIVATE KEY'),false);
});
test('Browser origin must match configured authorization page',async()=>{const h=createHandler({db:{rpc:async()=>({onboarding_origin:'https://authorized.test'})},baseURL:base});assert.equal((await h(request('/admin',{}, {Origin:'https://attacker.test'}))).status,403);});
test('Wompi invalid signature cannot call payment processing',async()=>{let called=0;const db={credentials:async()=>keys,rpc:async()=>called++};await assert.rejects(()=>wompiWebhook(db,gym,'{}','fake'),/Firma/);assert.equal(called,0);});
test('Wompi trusts canonical merchant transaction, not unsigned currency/reference fields',async()=>{let applied;const event={event:'transaction.updated',timestamp:Math.floor(Date.now()/1000),data:{transaction:{id:'tx-1',status:'APPROVED',amount_in_cents:7000000,reference:'forged',currency:'USD'}},signature:{properties:['transaction.id','transaction.status','transaction.amount_in_cents']}};event.signature.checksum=await sha256('tx-1APPROVED7000000'+event.timestamp+keys.events_secret);const db={credentials:async()=>keys,connection:async()=>({metadata:{}}),patch:async()=>{},rpc:async(name,args)=>{if(name==='marketing_service_apply_payment'){applied=args.p_transaction;return {duplicate:false}}return true;}};await wompiWebhook(db,gym,JSON.stringify(event),null,async(url,opts)=>{assert.equal(opts.headers.Authorization,'Bearer '+keys.private_key);return Response.json({data:{id:'tx-1',reference:'GS-real',currency:'COP',status:'APPROVED',amount_in_cents:7000000}})});assert.equal(applied.reference,'GS-real');assert.equal(applied.currency,'COP');});
test('Duplicate provider receipt does not reapply payment',async()=>{const event={event:'transaction.updated',timestamp:Math.floor(Date.now()/1000),data:{transaction:{id:'tx-1'}},signature:{properties:['transaction.id']}};event.signature.checksum=await sha256('tx-1'+event.timestamp+keys.events_secret);let applies=0;const db={credentials:async()=>keys,rpc:async(name)=>{if(name==='marketing_service_apply_payment')applies++;return false;}};const r=await wompiWebhook(db,gym,JSON.stringify(event),null,async()=>Response.json({data:{id:'tx-1'}}));assert.equal(r.duplicate,true);assert.equal(applies,0);});
test('Meta history synchronization does not invoke chatbot',async()=>{let called=[];const raw=JSON.stringify({object:'whatsapp_business_account',entry:[{id:'waba',changes:[{field:'history',value:{messages:[{id:'old',from:'573001234567'}]}}]}]});const db={rpc:async(n)=>{called.push(n);return n==='marketing_service_platform'?{app_secret:'secret'}:[]},read:async()=>[{gym_id:gym}]};await metaWebhook(db,base,raw,'sha256='+await hmacHex('secret',raw));assert.equal(called.includes('marketing_service_chat'),false);});
test('Coexistence human echo pauses chatbot on the correct gym',async()=>{let action;const raw=JSON.stringify({object:'whatsapp_business_account',entry:[{id:'waba',changes:[{field:'smb_message_echoes',value:{metadata:{phone_number_id:'123'},message_echoes:[{id:'human-1',to:'573001234567',text:{body:'Hola'}}]}}]}]});const db={rpc:async(n,a)=>{if(n==='marketing_service_chat')action=a;return n==='marketing_service_platform'?{app_secret:'secret'}:[]},read:async()=>[{gym_id:gym}]};await metaWebhook(db,base,raw,'sha256='+await hmacHex('secret',raw));assert.equal(action.p_action,'human_echo');assert.equal(action.p_gym_id,gym);});
test('Consent revoked after queuing blocks the actual provider call',async()=>{let result;let sends=0;const db={rpc:async(n,a)=>{if(n==='marketing_service_claim')return [{id:1,claim_id:'c',gym_id:gym}];if(n==='marketing_service_send_guard')return {allowed:false,reason:'NO_CONSENT'};if(n==='marketing_service_send_result')result=a;}};await dispatch(db,{fetcher:async()=>{sends++}});assert.equal(sends,0);assert.equal(result.p_status,'NO_CONSENT');});
test('Ambiguous Meta timeout is UNCERTAIN, never blindly queued for resend',async()=>{let result;const db={rpc:async(n,a)=>{if(n==='marketing_service_claim')return [{id:1,claim_id:'c',gym_id:gym,phone:'573001234567',automation_type:'BIRTHDAY',template_parameters:[]}];if(n==='marketing_service_send_guard')return {allowed:true};if(n==='marketing_service_send_result')result=a;},connection:async()=>({status:'CONNECTED',phone_number_id:'123'}),credentials:async()=>({access_token:'secret'})};await dispatch(db,{fetcher:async()=>{throw new Error('timeout')}});assert.equal(result.p_status,'UNCERTAIN');assert.equal(JSON.stringify(result).includes('secret'),false);});

test('WABA template updates reach every authorized gym phone',async()=>{const patched=[];const raw=JSON.stringify({object:'whatsapp_business_account',entry:[{id:'waba',changes:[{field:'message_template_status_update',value:{event:'APPROVED',message_template_id:'t1'}}]}]});const db={rpc:async(n)=>n==='marketing_service_platform'?{app_secret:'secret'}:[],read:async()=>[{gym_id:gym},{gym_id:'other'}],patch:async(t,filter)=>patched.push(filter.gym_id)};await metaWebhook(db,base,raw,'sha256='+await hmacHex('secret',raw));assert.deepEqual(patched,['eq.'+gym,'eq.other']);});
test('Inbound without destination phone cannot choose an arbitrary gym',async()=>{const called=[];const raw=JSON.stringify({object:'whatsapp_business_account',entry:[{id:'waba',changes:[{field:'messages',value:{messages:[{id:'m1',from:'573001234567',timestamp:String(Date.now()/1000),text:{body:'Hola'}}]}}]}]});const db={rpc:async(n)=>{called.push(n);return n==='marketing_service_platform'?{app_secret:'secret'}:[];},read:async()=>[{gym_id:gym}]};await metaWebhook(db,base,raw,'sha256='+await hmacHex('secret',raw));assert.equal(called.includes('marketing_service_inbound_record'),false);});
