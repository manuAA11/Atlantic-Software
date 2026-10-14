import {database,root} from './migrations.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';

export async function fixture({features=true}={}){
 const db=await database({features});
 const O='10000000-0000-4000-8000-000000000031',A='20000000-0000-4000-8000-000000000031',R='30000000-0000-4000-8000-000000000031',B='40000000-0000-4000-8000-000000000031';
 async function user(id){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[id,JSON.stringify({sub:id,session_id:id})]);await db.exec('set role authenticated');}
 async function system(){await db.exec('reset role');await db.exec("select set_config('request.jwt.claim.sub','',false)");}
 async function rpc(name,params={}){return (await db.query(`select public.${name}(${Object.keys(params).map((k,i)=>k+' => $'+(i+1)).join(',')}) r`,Object.values(params))).rows[0].r;}
 async function tableRpc(name,params){return (await db.query(`select * from public.${name}(${Object.keys(params).map((k,i)=>k+' => $'+(i+1)).join(',')})`,Object.values(params))).rows;}
 async function insert(table,values){return (await db.query(`insert into public.${table}(${Object.keys(values)}) values(${Object.keys(values).map((_,i)=>'$'+(i+1))}) returning id`,Object.values(values))).rows[0].id;}
 for(const [id,email] of [[O,'owner@example.test'],[A,'admin@example.test'],[R,'reception@example.test'],[B,'other@example.test']])await db.query('insert into auth.users(id,email) values($1,$2)',[id,email]);
 const commercial=fs.existsSync(path.join(root,'sql'));let gym,other;
 if(commercial){
  const payload=JSON.parse(execFileSync(process.env.PYTHON||'python3',[path.join(root,'tests/owner_payloads.py')],{encoding:'utf8'}));
  await db.query('insert into private.software_owners(user_id) values($1)',[O]);await user(O);
  const g=await rpc('owner_create_gym',payload.create);gym=g.gym_id;
  const og=await rpc('owner_create_gym',{...payload.create,p_name:'Otro',p_email:'other@example.test'});other=og.gym_id;
  for(const [id,gid,code,hash] of [[A,gym,g.activation_code,'a'],[B,other,og.activation_code,'b']]){
   await user(id);await rpc('commercial_accept_invite',{p_code:code});
   const lic={p_device_hash:hash.repeat(64),p_device_name:'Prueba aislada'};await rpc('commercial_check_license',lic);
   await user(O);const d=(await rpc('owner_gym_detail',{p_gym_id:gid})).devices[0];await rpc('owner_set_device',{p_device_id:d.id,p_blocked:false,p_reason:'Prueba'});
   await user(id);await rpc('commercial_check_license',lic);
  }
 }else{
  await user(A);gym=await rpc('create_gym',{p_name:'Membresías locales'});
  await user(B);other=await rpc('create_gym',{p_name:'Otro'});
 }
 await system();await db.query("insert into public.gym_users(gym_id,user_id,role) values($1,$2,'receptionist')",[gym,R]);
 if(commercial){await user(R);await rpc('commercial_check_license',{p_device_hash:'a'.repeat(64),p_device_name:'Prueba aislada'});}

 async function clock(instant){await system();await db.exec(`create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select '${instant}'::timestamptz$$`);await user(A);}
 let n=0;
 async function person(){return insert('clients',{gym_id:gym,document:'TEST-'+(++n),first_name:'Persona '+n,phone:'3001234567',active:true});}
 async function monthly({ticket=null,end='2026-10-30',start='2026-10-01'}={}){
  const c=await person();const p=await insert('plans',{gym_id:gym,name:'Comercial '+(++n),duration_days:30,price:70000,entry_limit:ticket});
  const m=await insert('memberships',{gym_id:gym,client_id:c,plan_id:p,start_date:start,end_date:end,entry_limit:ticket,amount:70000,amount_paid:70000,payment_method:'Efectivo'});
  return {c,p,m};
 }
 const snapshot=c=>rpc('reception_membership_snapshot',{p_gym_id:gym,p_client_id:c});
 const enter=(c,override=false,method='HUELLA BIOMÉTRICA')=>rpc('admin_register_checkin',{p_gym_id:gym,p_client_id:c,p_method:method,p_override:override});
 await clock('2026-10-20T14:00:00Z');
 return {db,root,commercial,O,A,R,B,gym,other,user,system,rpc,tableRpc,insert,clock,person,monthly,snapshot,enter};
}
