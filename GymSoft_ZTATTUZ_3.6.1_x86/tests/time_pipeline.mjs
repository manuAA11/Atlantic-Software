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


 await clock('2026-10-08T02:30:00Z');
 const gc=await rpc('gym_local_clock',{p_gym_id:gym});equal([new Date(gc.now).toISOString(),gc.today,gc.timezone],['2026-10-08T02:30:00.000Z','2026-10-07','America/Bogota']);
 const m=await ins('memberships',{gym_id:gym,client_id:cid,plan_id:ticket,start_date:'2026-10-01',end_date:'2026-11-01',entry_limit:15,amount:90000,amount_paid:90000,payment_method:'Efectivo',paid_at:'1999-01-01T00:00:00Z'});
 equal((await db.query('select paid_at>\'2026-01-01\'::timestamptz as real from public.memberships where id=$1',[m])).rows[0].real,true,'Desktop spoofed payment timestamp ignored');
 equal(new Date((await db.query('select paid_at from public.memberships where id=$1',[m])).rows[0].paid_at).toISOString(),'2026-10-08T02:30:00.000Z');
 const enter=()=>rpc('reception_register_checkin',{p_gym_id:gym,p_client_id:cid,p_method:'CÓDIGO'});
 let e=await enter();equal(e.local_date,'2026-10-07');equal(new Date(e.checkin_at).toISOString(),'2026-10-08T02:30:00.000Z');equal(e.entries_remaining,14);
 await clock('2026-10-08T04:59:59Z');e=await enter();equal(e.entries_remaining,14);equal(e.already_consumed_today,true);
 await clock('2026-10-08T05:00:00Z');e=await enter();equal(e.local_date,'2026-10-08');equal(e.entries_remaining,13);
 await clock('2026-10-08T02:30:00Z');
 const exp=await ins('accounting_expenses',{gym_id:gym,expense_date:'2026-10-07',category:'Otros',description:'Hora de servidor',amount:1000,created_at:'1999-01-01T00:00:00Z'});
 equal((await db.query('select created_at>\'2026-01-01\'::timestamptz as real,expense_date::text from public.accounting_expenses where id=$1',[exp])).rows[0],{real:true,expense_date:'2026-10-07'});
 equal(new Date((await db.query('select created_at from public.accounting_expenses where id=$1',[exp])).rows[0].created_at).toISOString(),'2026-10-08T02:30:00.000Z');
 const product=await ins('store_products',{gym_id:gym,name:'Prueba tiempo',sale_price:1000,stock_quantity:10});
 const sale=await ins('store_sales',{gym_id:gym,product_id:product,product_name:'Prueba tiempo',quantity:1,unit_price:1000,total_amount:1000,sold_at:'1999-01-01T00:00:00Z'});
 equal((await db.query('select sold_at>\'2026-01-01\'::timestamptz as real from public.store_sales where id=$1',[sale])).rows[0].real,true);
 equal(new Date((await db.query('select sold_at from public.store_sales where id=$1',[sale])).rows[0].sold_at).toISOString(),'2026-10-08T02:30:00.000Z');
 await rootUser();
 const log=await ins('audit_logs',{gym_id:gym,action:'HISTORICAL_UTC',entity_type:'test',summary:'Instante original',created_at:'2026-10-08T02:30:00Z'});
 await user(A);
 const historical=(await rpc('get_audit_logs',{p_gym_id:gym})).find(x=>x.id===log);
 equal(historical.created_at_local,'07/10/2026 21:30:00');equal(new Date(historical.occurred_at).toISOString(),'2026-10-08T02:30:00.000Z');
 await rootUser();
 const types=(await db.query("select table_name,column_name,data_type from information_schema.columns where table_schema='public'")).rows;
 for(const [t,k] of [['audit_logs','created_at'],['checkins','checkin_at'],['memberships','paid_at'],['accounting_expenses','created_at'],['store_sales','sold_at'],['payment_transactions','processed_at'],['payment_transactions','provider_created_at'],['marketing_messages','sent_at'],['membership_freezes','starts_at'],['membership_freezes','ends_at']])equal(types.find(x=>x.table_name===t&&x.column_name===k)?.data_type,'timestamp with time zone',t+'.'+k);
 for(const [t,k] of [['memberships','start_date'],['memberships','end_date'],['accounting_expenses','expense_date'],['ticket_daily_consumptions','local_date'],['membership_freezes','start_date'],['membership_freezes','resume_date']])equal(types.find(x=>x.table_name===t&&x.column_name===k)?.data_type,'date',t+'.'+k);
 for(const name of ['membership_snapshot_json','ticket_backup_memberships','freeze_active','gym_event_clock','marketing_cron_tick','marketing_audit_to_activity','marketing_message_activity']){
  const rights=(await db.query("select has_function_privilege('anon',p.oid,'EXECUTE') as anon,has_function_privilege('authenticated',p.oid,'EXECUTE') as staff from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='private' and p.proname=$1",[name])).rows;
  equal(rights.length>0,true,name);equal(rights.every(r=>!r.anon&&!r.staff),true,'Private helper is not a caller API: '+name);
 }
 equal((await db.query("select has_function_privilege('authenticated','public.marketing_service_install_scheduler(text)','EXECUTE') as staff")).rows[0].staff,false);
 equal((await db.query("select has_function_privilege('authenticated','public.marketing_service_health()','EXECUTE') as staff")).rows[0].staff,false);
 const health=await rpc('marketing_service_health');
 equal([health.database,health.scheduler_installed],[true,false]);
 equal(new Date(health.server_now).toISOString(),'2026-10-08T02:30:00.000Z');
 await clock('2026-10-08T02:30:00Z');await rootUser();
 await db.query("insert into public.marketing_audit(gym_id,actor_id,action,entity_type,entity_id) values($1,$2,'CHATBOT_VERIFIED','client',$3)",[gym,A,String(cid)]);
 const message=await ins('marketing_messages',{gym_id:gym,client_id:cid,automation_type:'CHATBOT',source_date:'2026-10-07',phone:'573001234567',template_name:'',status:'QUEUED'});
 await db.query("update public.marketing_messages set status='SENT',sent_at='2026-10-08T02:30:00Z' where id=$1",[message]);
 await db.query("update public.marketing_messages set status='SENT' where id=$1",[message]);
 await user(A);const integration=(await rpc('get_audit_logs',{p_gym_id:gym}));
 const bot=integration.find(r=>r.action==='MARKETING_CHATBOT_VERIFIED');
 equal([bot.created_at_local,bot.actor_user_id],['07/10/2026 21:30:00',A]);
 const sent=integration.filter(r=>r.action==='MARKETING_MESSAGE_SENT'&&r.entity_id===String(message));
 equal(sent.length,1);equal(sent[0].created_at_local,'07/10/2026 21:30:00');
 equal(new Date(sent[0].details.sent_at).toISOString(),'2026-10-08T02:30:00.000Z');
 await rootUser();
 // Repeating the installer SQL is safe; dates/history/quota do not change.
 await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_CONGELACION_Y_HORAS.sql'),'utf8'));
 equal((await db.query('select count(*)::integer as n from public.ticket_daily_consumptions where membership_id=$1',[m])).rows[0].n,2);
 console.log(`PASS: ${checks} real time pipeline checks (${commercial?'commercial':'ZTATTUZ'})`);
}catch(e){console.error('FAIL TIME:',e.message,e.where||'',e.detail||'');process.exitCode=1;}finally{await db.close();}
