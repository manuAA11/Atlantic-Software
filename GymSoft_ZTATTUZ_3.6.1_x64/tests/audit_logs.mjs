import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {database,root} from './migrations.mjs';
const db=await database();  let checks=0;
const O='10000000-0000-4000-8000-000000000001',A='20000000-0000-4000-8000-000000000001',B='30000000-0000-4000-8000-000000000001';
const commercial=fs.existsSync(path.join(root,'sql'));
async function user(id){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[id,JSON.stringify({sub:id,session_id:id})]);await db.exec('set role authenticated');}
async function rootUser(){await db.exec('reset role');await db.exec("select set_config('request.jwt.claim.sub','',false)");}
async function rpc(name,params={}){return (await db.query(`select public.${name}(${Object.keys(params).map((k,i)=>k+' => $'+(i+1)).join(',')}) as r`,Object.values(params))).rows[0].r;}
function equal(a,b,message){assert.deepEqual(a,b,message);checks++;}
async function clock(iso){await rootUser();await db.exec(`create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select '${iso}'::timestamptz$$`);await user(A);}
try {
 for(const [id,email] of [[O,'owner@example.test'],[A,'admin@example.test'],[B,'other@example.test']])await db.query('insert into auth.users(id,email) values($1,$2)',[id,email]);
 let gym,other;
 if(commercial){
  const payload=JSON.parse(execFileSync(process.env.PYTHON||'python3',[path.join(root,'tests/owner_payloads.py')],{encoding:'utf8'}));
  await db.query('insert into private.software_owners(user_id) values($1)',[O]);await user(O);
  const g=await rpc('owner_create_gym',payload.create);gym=g.gym_id;other=(await rpc('owner_create_gym',{...payload.create,p_name:'Otro',p_email:'other@example.test'})).gym_id;
  await user(A);await rpc('commercial_accept_invite',{p_code:g.activation_code});
  const license={p_device_hash:'a'.repeat(64),p_device_name:'Prueba aislada'};await rpc('commercial_check_license',license);
  await user(O);const d=(await rpc('owner_gym_detail',{p_gym_id:gym})).devices[0];await rpc('owner_set_device',{p_device_id:d.id,p_blocked:false,p_reason:'Prueba'});
  await user(A);await rpc('commercial_check_license',license);
 }else{await user(A);gym=await rpc('create_gym',{p_name:'Consumo diario'});await user(B);other=await rpc('create_gym',{p_name:'Otro'});await user(A);}
 const ins=async(t,row)=> (await db.query(`insert into public.${t}(${Object.keys(row)}) values(${Object.keys(row).map((_,i)=>'$'+(i+1))}) returning id`,Object.values(row))).rows[0].id;
 const cid=await ins('clients',{gym_id:gym,document:'MK1',first_name:'Juan',phone:'3001234567'});
 const pid=await ins('plans',{gym_id:gym,name:'Mensual prueba',duration_days:30,price:70000});
 const ticket=await ins('plans',{gym_id:gym,name:'Tiquetera prueba',duration_days:60,duration_months:2,entry_limit:15,price:90000});

 const log=(await rpc('get_audit_logs',{p_gym_id:gym})).find(x=>x.entity_type==='clients'&&String(x.entity_id)===String(cid));
 equal(log.client_name,'Juan');equal(log.timezone,'America/Bogota');
 await rootUser();
 const membership=(await db.query("insert into public.memberships(gym_id,client_id,plan_id,start_date,end_date,amount,amount_paid,payment_method,paid_at) values($1,$2,$3,current_date,current_date+30,70000,70000,'Efectivo','2020-01-01T03:00:00Z') returning id",[gym,cid,pid])).rows[0].id;
 await user(A);
 let logs=await rpc('get_audit_logs',{p_gym_id:gym,p_action:'PAGO_REGISTRADO'});let payment=logs.find(x=>String(x.entity_id)===String(membership));
 equal(payment.summary.includes('Juan'),true);equal(payment.summary.includes('cliente #'),false);
 equal(new Date(payment.created_at).getUTCFullYear()>=2026,true);
 equal(new Date(payment.occurred_at).valueOf(),new Date(payment.created_at).valueOf());
 await db.query("update public.clients set first_name='Juan Carlos' where gym_id=$1 and id=$2",[gym,cid]);
 equal((await rpc('get_audit_logs',{p_gym_id:gym,p_action:'PAGO_REGISTRADO'})).find(x=>String(x.entity_id)===String(membership)).client_name,'Juan');
 await rootUser();await db.exec('alter table public.audit_logs disable trigger audit_prepare_record');
 const old=(await db.query("insert into public.audit_logs(gym_id,action,entity_type,entity_id,summary,details,created_at) values($1,'PAGO_EDITADO','memberships',$2,$3,$4,'2026-01-02T02:34:56Z') returning id",[gym,String(membership),'Pago corregido · cliente #'+cid,JSON.stringify({client_id:cid})])).rows[0].id;
 await db.exec('alter table public.audit_logs enable trigger audit_prepare_record');await user(A);
 const historical=(await rpc('get_audit_logs',{p_gym_id:gym})).find(x=>x.id===old);
 equal(historical.summary,'Pago corregido · Juan Carlos');equal(historical.created_at_local,'01/01/2026 21:34:56');
 await rootUser();equal((await db.query('select summary from public.audit_logs where id=$1',[old])).rows[0].summary,'Pago corregido · cliente #'+cid);
 await user(A);await assert.rejects(()=>rpc('get_audit_logs',{p_gym_id:other}),/auditoría/i);checks++;
 await assert.rejects(()=>db.query("update public.audit_logs set created_at='2000-01-01' where gym_id=$1",[gym]),/permission/i);checks++;
 await rootUser();await db.query('delete from public.memberships where gym_id=$1 and client_id=$2',[gym,cid]);await db.query('delete from public.clients where gym_id=$1 and id=$2',[gym,cid]);await user(A);
 equal((await rpc('get_audit_logs',{p_gym_id:gym,p_action:'PAGO_REGISTRADO'})).find(x=>String(x.entity_id)===String(membership)).client_name,'Juan');
 await rootUser();await db.exec('begin');await db.query('select pg_sleep(0.03)');
 const row=(await db.query("insert into public.audit_logs(gym_id,action,entity_type,summary) values($1,'TEST','test','Prueba aislada') returning created_at > transaction_timestamp() as actual",[gym])).rows[0];equal(row.actual,true);await db.exec('rollback');
 console.log(`PASS: ${checks} comprobaciones de nombres, hora real, historial conservado y permisos (${commercial?'comercial':'ZTATTUZ'}).`);
}catch(e){console.error('FAIL AUDIT:',e.message,e.where||'',e.detail||'');process.exitCode=1;}finally{await db.close();}
