import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {database,root} from './migrations.mjs';
const db=await database(); let checks=0;
const O='10000000-0000-4000-8000-000000000001',A='20000000-0000-4000-8000-000000000001',B='30000000-0000-4000-8000-000000000001';
const commercial=fs.existsSync(path.join(root,'sql'));
async function user(id){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[id,JSON.stringify({sub:id,session_id:id})]);await db.exec('set role authenticated');}
async function rootUser(){await db.exec('reset role');await db.exec("select set_config('request.jwt.claim.sub','',false)");}
async function rpc(name,params={}){return (await db.query(`select public.${name}(${Object.keys(params).map((k,i)=>k+' => $'+(i+1)).join(',')}) as r`,Object.values(params))).rows[0].r;}
function equal(a,b,message){assert.deepEqual(a,b,message);checks++;}
async function clock(iso){await rootUser();await db.exec(`create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select '${iso}'::timestamptz$$`);await user(A);}
try {
 for(const [id,email] of [[O,'owner@example.test'],[A,'admin@example.test'],[B,'other@example.test']])await db.query('insert into auth.users(id,email) values($1,$2)',[id,email]);
 let gym,other,otherCode;
 if(commercial){
  const payload=JSON.parse(execFileSync(process.env.PYTHON||'python3',[path.join(root,'tests/owner_payloads.py')],{encoding:'utf8'}));
  await db.query('insert into private.software_owners(user_id) values($1)',[O]);await user(O);
  const g=await rpc('owner_create_gym',payload.create);gym=g.gym_id;const og=await rpc('owner_create_gym',{...payload.create,p_name:'Otro',p_email:'other@example.test'});other=og.gym_id;otherCode=og.activation_code;
  await user(A);await rpc('commercial_accept_invite',{p_code:g.activation_code});
  const license={p_device_hash:'a'.repeat(64),p_device_name:'Prueba aislada'};await rpc('commercial_check_license',license);
  await user(O);const d=(await rpc('owner_gym_detail',{p_gym_id:gym})).devices[0];await rpc('owner_set_device',{p_device_id:d.id,p_blocked:false,p_reason:'Prueba'});
  await user(A);await rpc('commercial_check_license',license);
  await user(B);await rpc('commercial_accept_invite',{p_code:otherCode});
  const bl={p_device_hash:'b'.repeat(64),p_device_name:'Otro equipo aislado'};await rpc('commercial_check_license',bl);
  await user(O);const bd=(await rpc('owner_gym_detail',{p_gym_id:other})).devices[0];await rpc('owner_set_device',{p_device_id:bd.id,p_blocked:false,p_reason:'Prueba'});
  await user(B);await rpc('commercial_check_license',bl);await user(A);
 }else{await user(A);gym=await rpc('create_gym',{p_name:'Consumo diario'});await user(B);other=await rpc('create_gym',{p_name:'Otro'});await user(A);}
 const ins=async(t,row)=> (await db.query(`insert into public.${t}(${Object.keys(row)}) values(${Object.keys(row).map((_,i)=>'$'+(i+1))}) returning id`,Object.values(row))).rows[0].id;
 const cid=await ins('clients',{gym_id:gym,document:'MK1',first_name:'Juan',phone:'3001234567'});
 const pid=await ins('plans',{gym_id:gym,name:'Mensual prueba',duration_days:30,price:70000});
 const ticket=await ins('plans',{gym_id:gym,name:'Tiquetera prueba',duration_days:60,duration_months:2,entry_limit:15,price:90000});

 await clock('2026-10-08T14:00:00Z');
 const fixture=async(quota=null,ending='2026-10-20')=>{
  const n=Math.random().toString(16).slice(2);
  const c=await ins('clients',{gym_id:gym,document:'F'+n,first_name:'Congelación',phone:'3001234567',active:true});
  const p=await ins('plans',{gym_id:gym,name:'Plan '+n,duration_days:30,price:70000,entry_limit:quota});
  const m=await ins('memberships',{gym_id:gym,client_id:c,plan_id:p,start_date:'2026-10-01',end_date:ending,entry_limit:quota,amount:70000,amount_paid:70000,payment_method:'Efectivo'});
  return {c,p,m};
 };
 const snap=f=>rpc('reception_membership_snapshot',{p_gym_id:gym,p_client_id:f.c});
 const freeze=(f,key='70000000-0000-4000-8000-000000000001',override=false)=>rpc('membership_freeze',{p_gym_id:gym,p_membership_id:f.m,p_request_id:key,p_reason:override?'Excepción comprobada':'Solicitud del cliente',p_override:override});
 const enter=(f,override=false,method='MANUAL')=>rpc('admin_register_checkin',{p_gym_id:gym,p_client_id:f.c,p_method:method,p_override:override});
 const denied=async(work)=>{await assert.rejects(work);checks++;};
 const monthly=await fixture();
 let s=await snap(monthly);equal(s.can_freeze,true,'Eligible active cycle');
 const frozen=await freeze(monthly);
 equal([frozen.start_date,frozen.resume_date,frozen.days_added,frozen.new_end_date],['2026-10-08','2026-10-15',7,'2026-10-27']);
 equal(new Date(frozen.starts_at).toISOString(),'2026-10-08T05:00:00.000Z');
 equal(new Date(frozen.ends_at).toISOString(),'2026-10-15T05:00:00.000Z');
 equal((await freeze(monthly)).duplicate,true,'Stable request is idempotent');
 await denied(()=>freeze(monthly,'70000000-0000-4000-8000-000000000002'));
 s=await snap(monthly);equal([s.status,s.allowed,s.end_date,s.resume_date,s.freeze_last_date],['FROZEN',false,'2026-10-27','2026-10-15','2026-10-14']);
 equal(s.denial_message,'Membresía congelada hasta el 15/10/2026.');
 for(const method of ['MANUAL','HUELLA BIOMÉTRICA','CÓDIGO','RECEPCIÓN','ADMINISTRACIÓN']){
  const r=await enter(monthly,true,method);equal(r.result,'DENEGADA','Even admin cannot bypass freeze');
  equal(r.denial_code,'CHECK_IN_DENIED_MEMBERSHIP_FROZEN');
 }
 await rootUser();
 const direct=(await db.query("insert into public.checkins(gym_id,client_id,membership_id,method,result,notes) values($1,$2,$3,'RELAY','PERMITIDA','Autorización manual del administrador') returning result,ticket_consumed",[gym,monthly.c,monthly.m])).rows[0];
 equal(direct.result,'DENEGADA','Direct route remains denied');
 await user(A);
 let logs=await rpc('get_audit_logs',{p_gym_id:gym});
 equal(logs.filter(x=>x.action==='MEMBERSHIP_FROZEN' && String(x.entity_id)===String(monthly.m)).length,1);
 equal(logs.find(x=>x.action==='MEMBERSHIP_FROZEN').actor_user_id,A);
 equal(logs.some(x=>x.action==='CHECK_IN_DENIED_MEMBERSHIP_FROZEN'),true);
 // Reminder already waiting for delivery is made obsolete by the extension.
 await rootUser();
 await db.query("insert into public.marketing_messages(gym_id,client_id,automation_type,source_date,phone,template_name,status,dedupe_key,body) values($1,$2,'MEMBERSHIP_BEFORE','2026-10-08','573001234567','vence','QUEUED','freeze-reminder','Vence el 20')",[gym,cid]);
 await user(A);
 const old=await ins('memberships',{gym_id:gym,client_id:cid,plan_id:pid,start_date:'2026-10-01',end_date:'2026-10-20',amount:70000,amount_paid:70000,payment_method:'Efectivo'});
 const future=await ins('memberships',{gym_id:gym,client_id:cid,plan_id:pid,start_date:'2026-10-21',end_date:'2026-11-20',amount:70000,amount_paid:70000,payment_method:'Efectivo'});
 await freeze({c:cid,p:pid,m:old},'70000000-0000-4000-8000-000000000003');
 equal((await db.query('select start_date::text,end_date::text from public.memberships where id=$1',[future])).rows[0],{start_date:'2026-10-28',end_date:'2026-11-27'});
 equal((await db.query("select status from public.marketing_messages where dedupe_key='freeze-reminder'")).rows[0].status,'SKIPPED');
 // A ticket keeps its quota/consumption, including the once-per-local-day protection.
 const tickets=await fixture(10);
 equal((await enter(tickets)).entries_remaining,9);
 const tf=await freeze(tickets,'70000000-0000-4000-8000-000000000004');
 s=await snap(tickets);equal([s.entries_used,s.entries_remaining,s.end_date],[1,9,'2026-10-27']);
 equal((await enter(tickets)).result,'DENEGADA');
 // Exclusive resume date: UTC midnight still belongs to the frozen prior local day.
 await clock('2026-10-15T00:00:00Z');equal((await enter(monthly)).result,'DENEGADA');
 await clock('2026-10-15T04:59:59Z');equal((await enter(monthly)).result,'DENEGADA');
 await clock('2026-10-15T05:00:00Z');equal((await enter(monthly)).result,'PERMITIDA');
 equal((await snap(monthly)).frozen,false);
 equal((await enter(tickets)).entries_remaining,8);
 equal((await enter(tickets)).entries_remaining,8,'Reentry is not charged twice');
 await denied(()=>freeze(monthly,'70000000-0000-4000-8000-000000000005'));
 await rootUser();await rpc('membership_service_complete_freezes');equal(await rpc('membership_service_complete_freezes'),0,'Completion idempotent');await user(A);
 logs=await rpc('get_audit_logs',{p_gym_id:gym});
 equal(logs.filter(x=>x.action==='MEMBERSHIP_FREEZE_COMPLETED'&&String(x.entity_id)===String(monthly.m)).length,1);
 equal((await freeze(monthly,'70000000-0000-4000-8000-000000000006',true)).administrative_override,true);
 // Cancellation removes unspent days, does not allow reception to add another week.
 const cancel=await fixture(null,'2026-11-01');const cf=await freeze(cancel,'70000000-0000-4000-8000-000000000007');
 await clock('2026-10-18T14:00:00Z');
 const cancelled=await rpc('membership_cancel_freeze',{p_gym_id:gym,p_freeze_id:cf.id,p_reason:'Cliente solicita reanudar'});
 equal([cancelled.days_reversed,cancelled.new_end_date],[4,'2026-11-04']);
 equal((await enter(cancel)).result,'PERMITIDA');
 await denied(()=>freeze(cancel,'70000000-0000-4000-8000-000000000008'));
 // Two independent UI request keys are submitted together; only one grant survives.
 const parallel=await fixture(null,'2026-11-01');
 const races=await Promise.allSettled([freeze(parallel,'70000000-0000-4000-8000-000000000009'),freeze(parallel,'70000000-0000-4000-8000-000000000010')]);
 equal(races.filter(x=>x.status==='fulfilled').length,1,'Concurrent requests cannot both extend');
 equal((await db.query('select count(*)::int n from public.membership_freezes where membership_id=$1',[parallel.m])).rows[0].n,1);
 // Archive preserves cancellation and complete states, dates, quota and references.
 const archive=await rpc('ticket_backup_memberships',{p_gym_id:gym});
 equal(archive.find(x=>x.id===tickets.m).freeze_archive[0].id,tf.id);
 // Wompi uses the existing accumulation rule during an active freeze.
 const sandbox=await rpc('marketing_create_test_client',{p_gym_id:gym});
 const sm=await ins('memberships',{gym_id:gym,client_id:sandbox,plan_id:pid,start_date:'2026-10-01',end_date:'2026-10-25',amount:0,amount_paid:0,payment_method:'Efectivo'});
 await freeze({c:sandbox,p:pid,m:sm},'70000000-0000-4000-8000-000000000011');
 await rootUser();
 await db.query("insert into public.marketing_connections(gym_id,provider,status,mode) values($1,'WOMPI','CONNECTED','test')",[gym]);
 await db.query("insert into public.marketing_settings(gym_id,online_payments_enabled) values($1,true) on conflict(gym_id) do update set online_payments_enabled=true",[gym]);
 const req=await rpc('marketing_service_payment_request',{p_gym_id:gym,p_client_id:sandbox,p_plan_id:pid,p_key:'freeze-online-payment'});
 const tx={id:'frozen-online-1',reference:req.reference,status:'APPROVED',amount_in_cents:req.amount_in_cents,currency:'COP',mode:'test',created_at:new Date().toISOString()};
 const paid=await rpc('marketing_service_apply_payment',{p_gym_id:gym,p_transaction:tx});
 equal((await rpc('marketing_service_apply_payment',{p_gym_id:gym,p_transaction:tx})).duplicate,true);
 equal((await db.query('select start_date::text from public.memberships where id=$1',[paid.membership_id])).rows[0].start_date,'2026-11-02');
 await user(A);equal((await snap({c:sandbox})).status,'FROZEN');
 await user(B);await denied(()=>rpc('membership_freeze_info',{p_gym_id:gym,p_client_id:monthly.c}));
 equal((await db.query('select count(*)::int n from public.membership_freezes where gym_id=$1',[gym])).rows[0].n,0,'Cross-gym RLS');
 await user(A);
 await denied(()=>db.query("update public.membership_freezes set days_added=365 where gym_id=$1",[gym]));
 // Policy per plan and another IANA timezone respect the gym calendar.
 await rootUser();await db.query("update public.gyms set timezone='America/New_York' where id=$1",[other]);await user(B);
 const op=await ins('plans',{gym_id:other,name:'NY policy',duration_days:30,price:70000});
 const oc=await ins('clients',{gym_id:other,document:'NYF',first_name:'NY client'});
 const om=await ins('memberships',{gym_id:other,client_id:oc,plan_id:op,start_date:'2026-10-01',end_date:'2026-10-25',amount:70000,payment_method:'Efectivo'});
 await rpc('membership_save_freeze_policy',{p_gym_id:other,p_plan_id:op,p_enabled:true,p_duration_days:5,p_max_per_membership:2});
 await rootUser();await db.exec("create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select '2026-10-08T04:30:00Z'::timestamptz$$");await user(B);
 const nf=await rpc('membership_freeze',{p_gym_id:other,p_membership_id:om,p_request_id:'70000000-0000-4000-8000-000000000012'});
 equal([nf.start_date,nf.days_added,nf.new_end_date],['2026-10-08',5,'2026-10-30']);
 equal(new Date(nf.starts_at).toISOString(),'2026-10-08T04:00:00.000Z');
 await user(A);equal((await rpc('gym_local_clock',{p_gym_id:gym})).today,'2026-10-07');
 console.log(`PASS: ${checks} freeze checks (${commercial?'commercial':'ZTATTUZ'})`);
}catch(e){console.error('FAIL FREEZE:',e.message,e.where||'',e.detail||'');process.exitCode=1;}finally{await db.close();}
