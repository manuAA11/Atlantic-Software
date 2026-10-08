import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {database,root} from './migrations.mjs';
const db=await database({daily:false}); let checks=0;
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
 let seq=0;
 async function fixture(quota,opts={}){
  const c=await ins('clients',{gym_id:gym,document:'D'+(++seq),first_name:'Cliente '+seq,active:opts.active!==false});
  const p=await ins('plans',{gym_id:gym,name:'Plan '+seq,duration_days:30,price:70000,entry_limit:quota});
  const m=await ins('memberships',{gym_id:gym,client_id:c,plan_id:p,start_date:'2026-10-01',end_date:opts.expired?'2026-10-01':'2026-10-31',entry_limit:quota,initial_entries_used:0,amount:70000,amount_paid:70000,payment_method:"Efectivo",recorded_by:A});
  return {c,p,m};
 }
 const old=await fixture(15);await rootUser();
 for(let i=0;i<3;i++)await ins('checkins',{gym_id:gym,client_id:old.c,membership_id:old.m,checkin_at:'2026-10-01T13:00:00Z',method:'MANUAL',result:'PERMITIDA'});
 const migration=fs.readFileSync(path.join(root,'ACTUALIZAR_CONSUMO_DIARIO.sql'),'utf8');await db.exec(migration);
 equal((await db.query('select private.ticket_consumption_units($1,$2) as n',[gym,old.m])).rows[0].n,3,'Migration preserves prior balance');
 await db.exec(migration);equal((await db.query('select private.ticket_consumption_units($1,$2) as n',[gym,old.m])).rows[0].n,3,'Reapply does not duplicate history');
 await clock('2026-10-02T13:00:00Z');const f=await fixture(15);
 const enter=async(c=f.c,admin=false)=>rpc(admin?'admin_register_checkin':'reception_register_checkin',{p_gym_id:gym,p_client_id:c,p_method:'HUELLA BIOMÉTRICA',...(admin?{p_override:false}:{})});
 let r=await enter();equal([r.entries_remaining,r.ticket_consumed,r.already_consumed_today],[14,true,false],'First consumption');
 for(const time of ['2026-10-02T13:00:01Z','2026-10-02T13:00:03Z','2026-10-02T23:00:00Z','2026-10-03T02:00:00Z']){
  await clock(time);r=await enter();equal([r.entries_remaining,r.ticket_consumed,r.already_consumed_today,r.local_date],[14,false,true,'2026-10-02'],'Reentry in local day');
 }
 await clock('2026-10-03T05:00:00Z');r=await enter(f.c,true);equal([r.entries_remaining,r.ticket_consumed],[13,true],'Midnight Bogota');
 const last=await fixture(1);r=await enter(last.c);equal([r.entries_remaining,r.result],[0,'PERMITIDA']);r=await enter(last.c);equal([r.entries_remaining,r.result,r.already_consumed_today],[0,'PERMITIDA',true]);
 await clock('2026-10-04T05:00:00Z');equal((await enter(last.c)).result,'DENEGADA','No balance next day');
 const monthly=await fixture(null);for(let i=0;i<3;i++)equal((await enter(monthly.c)).entries_remaining,null);
 const inactive=await fixture(10,{active:false}),expired=await fixture(10,{expired:true});equal((await enter(inactive.c)).result,'DENEGADA');equal((await enter(expired.c)).result,'DENEGADA');
 await assert.rejects(()=>db.query("insert into public.ticket_daily_consumptions(gym_id,client_id,membership_id,local_date) values($1,$2,$3,current_date)",[gym,f.c,f.m]),/permission|permiso/i);checks++;
 await assert.rejects(()=>rpc('reception_register_checkin',{p_gym_id:other,p_client_id:f.c}),/permiso|autoriza/i);checks++;
 await rootUser();await db.query('delete from public.checkins where membership_id=$1',[f.m]);equal((await db.query('select private.ticket_consumption_units($1,$2) n',[gym,f.m])).rows[0].n,2,'Delete does not refund');
 await user(A);const backup=await rpc('ticket_backup_memberships',{p_gym_id:gym});const archive=backup.find(m=>m.id===f.m).ticket_consumption_archive;equal(archive.length,2,'Backup keeps deleted visits consumption');
 await rootUser();const restored=await ins('memberships',{gym_id:gym,client_id:f.c,plan_id:f.p,start_date:'2026-10-01',end_date:'2026-10-31',entry_limit:15,amount:70000,payment_method:"Efectivo",ticket_consumption_archive:JSON.stringify(archive)});
 equal((await db.query('select private.ticket_consumption_units($1,$2) n',[gym,restored])).rows[0].n,2,'Restoration remaps membership');
 await db.query("update public.gyms set timezone='America/New_York' where id=$1",[gym]);await clock('2026-10-03T03:59:59Z');const ny=await fixture(15);equal((await enter(ny.c)).local_date,'2026-10-02');await clock('2026-10-03T04:00:00Z');equal((await enter(ny.c)).entries_remaining,13,'New York DST midnight');
 await rootUser();await assert.rejects(()=>db.query("update public.gyms set timezone='Invalid/Timezone' where id=$1",[gym]),/horaria/i);checks++;
 console.log(`PASS: ${checks} comprobaciones de consumo diario, saldos históricos, reentrada, respaldo, permisos y zonas horarias (${commercial?'comercial':'ZTATTUZ'}).`);
}catch(e){console.error('FAIL DAILY:',e.message,e.where||'',e.detail||'');process.exitCode=1;}finally{await db.close();}
