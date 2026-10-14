import test from 'node:test';
import assert from 'node:assert/strict';
import {respond} from '../core/chatbot.mjs';
import {evaluate,variablesFor} from '../core/automation.mjs';
const m={plan_name:'STAFF',membership_type:'INTERNAL',membership_state:'ACTIVE',status:'ACTIVE',allowed:true,unlimited_access:true,has_expiration:false,end_date:null};
const context={client_id:1,first_name:'Ana',phone:'3001234567',active:true,whatsapp_opt_in:true,timezone:'America/Bogota',today:'2026-10-20',server_now:'2026-10-20T14:00:00Z',created_at:'2026-01-01T14:00:00Z',membership:m};
for(const action of ['Mi membresía','Mis entradas','Renovar','Pagar ahora','menu'])test('STAFF chatbot '+action+' never generates a payment',async()=>{
 let calls=0;const out=await respond({rpc:async()=>({state:'VERIFIED',client_id:1,first_name:'Ana',membership:m}),paymentLink:async()=>{calls++;return 'fake';},gym:{id:'g',name:'ZTATTUZ'},sender:'573001234567',message:{text:{body:action}}});
 assert.equal(calls,0);assert.doesNotMatch(JSON.stringify(out),/"id":"renew"|"id":"pay"|Vence:|2099|999999/);
 if(action==='Mi membresía')assert.match(out.interactive.body.text,/STAFF[\s\S]*ACTIVE[\s\S]*Ilimitado/);
});
for(const type of ['MEMBERSHIP_BEFORE','MEMBERSHIP_TODAY','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','TICKET_EXPIRING','TICKET_REMAINING','INACTIVITY','MEMBERSHIP_RENEWED','MANUAL_PAYMENT','ONLINE_APPROVED','PAYMENT_PENDING'])test('STAFF excludes '+type,()=>{
 const rule={id:'r',revision:1,enabled:true,trigger_type:type,trigger_options:{value:0,time:'09:00'}};
 assert.equal(evaluate(rule,context,{id:1,event_type:type,payload:{age_hours:10}}),null);assert.equal(evaluate(rule,context),null);
});
test('Internal attendance automation can run, with no financial variables or links',()=>{
 const rule={id:'r',revision:1,enabled:true,trigger_type:'CHECK_IN_SUCCESS',trigger_options:{}};
 const event={id:1,event_type:'CHECK_IN_SUCCESS',payload:{ticket_consumed:false}};
 assert.ok(evaluate(rule,context,event));assert.equal(evaluate({...rule,include_payment_link:true},context,event),null);
 assert.equal(variablesFor(context,'https://example.test/pay').link_pago,'');
});
test('Resumed verified member receives the real extended expiry',async()=>{
 const out=await respond({rpc:async()=>({state:'VERIFIED',first_name:'Ana',membership:{plan_name:'Mensual',membership_state:'ACTIVE',status:'AL DÍA',end_date:'2026-11-01',frozen:false}}),gym:{id:'g'},sender:'x',message:{text:{body:'Mi membresía'}}});
 assert.match(out.interactive.body.text,/2026-11-01/);assert.doesNotMatch(out.interactive.body.text,/CONGELADA|2026-11-06/);
});
