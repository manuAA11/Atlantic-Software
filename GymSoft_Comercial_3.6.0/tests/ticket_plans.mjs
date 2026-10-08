import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {database,root} from './migrations.mjs';
const payload=JSON.parse(execFileSync(process.env.PYTHON||'python3',[path.join(root,'tests/owner_payloads.py')],{encoding:'utf8'}));
const db=await database();
const O='10000000-0000-4000-8000-000000000001', A='20000000-0000-4000-8000-000000000001', R='30000000-0000-4000-8000-000000000001';
let checks=0;
function ok(value){assert.ok(value);checks++;}
async function user(id){
 await db.exec('RESET ROLE');
 await db.query("SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[id,JSON.stringify({sub:id,session_id:id})]);
 await db.exec('SET ROLE authenticated');
}
async function rpc(name,params={}){
 const args=Object.keys(params).map((k,i)=>`${k} => $${i+1}`).join(',');
 return (await db.query(`SELECT public.${name}(${args}) AS data`,Object.values(params))).rows[0].data;
}
try{
 for(const [id,email] of [[O,'owner@example.test'],[A,'admin@example.test'],[R,'reception@example.test']]) await db.query('INSERT INTO auth.users(id,email) VALUES($1,$2)',[id,email]);
 await db.query('INSERT INTO private.software_owners(user_id) VALUES($1)',[O]);
 await user(O);
 const gym=await rpc('owner_create_gym',payload.create), id=gym.gym_id;
 const other=await rpc('owner_create_gym',{...payload.create,p_name:'Otro gimnasio',p_email:'other@example.test'});
 const invite=await rpc('owner_invite_user',{...payload.invite,p_gym_id:id});
 await user(A);await rpc('commercial_accept_invite',{p_code:gym.activation_code});
 const license={p_device_hash:'b'.repeat(64),p_device_name:'PC pruebas locales'};
 await rpc('commercial_check_license',license);
 await user(O);
 const device=(await rpc('owner_gym_detail',{p_gym_id:id})).devices[0];
 await rpc('owner_set_device',{p_device_id:device.id,p_blocked:false,p_reason:'Prueba local'});
 await user(A);await rpc('commercial_check_license',license);
 const c=(await db.query("INSERT INTO public.clients(gym_id,document,first_name,biometric_identifier) VALUES($1,'C-01','Ana','') RETURNING id",[id])).rows[0].id;
 const c2=(await db.query("INSERT INTO public.clients(gym_id,document,first_name,biometric_identifier) VALUES($1,'C-02','Luis','') RETURNING id",[id])).rows[0].id;
 ok(c!==c2); // múltiples clientes sin huella no chocan con el índice único.
 const plan=(await db.query("INSERT INTO public.plans(gym_id,name,duration_days,price,entry_limit) VALUES($1,'Bono flexible',30,1000,15) RETURNING id",[id])).rows[0].id;
 async function buy(cid,pid){return (await db.query("SELECT * FROM public.add_membership_accumulating($1,$2,$3,null,1000,'Efectivo','','')",[id,cid,pid])).rows[0].membership_id;}
 const m=await buy(c,plan);
 ok((await db.query('SELECT entry_limit FROM public.memberships WHERE id=$1',[m])).rows[0].entry_limit===15);
 await db.query('UPDATE public.plans SET entry_limit=20 WHERE id=$1',[plan]);
 ok((await db.query('SELECT entry_limit FROM public.memberships WHERE id=$1',[m])).rows[0].entry_limit===15);
 const m2=await buy(c2,plan);
 ok((await db.query('SELECT entry_limit FROM public.memberships WHERE id=$1',[m2])).rows[0].entry_limit===20);
 const baseDay=new Date((await rpc('gym_local_clock',{p_gym_id:id})).today+'T15:00:00Z');
 async function advanceDay(days){
  await db.exec('RESET ROLE');
  const d=new Date(baseDay.getTime()+days*86400000).toISOString();
  await db.exec(`create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select '${d}'::timestamptz$$`);
  await user(A);
 }
 for(let i=0;i<15;i++){
  await advanceDay(i);
  const value=await rpc('admin_register_checkin',{p_gym_id:id,p_client_id:c,p_method:'HUELLA BIOMÉTRICA',p_override:false});
  ok(value.result==='PERMITIDA'&&value.entries_remaining===14-i);
 }
 await advanceDay(15);
 ok((await rpc('admin_register_checkin',{p_gym_id:id,p_client_id:c,p_method:'HUELLA BIOMÉTRICA',p_override:false})).result==='DENEGADA');
 const renewed=await buy(c,plan);
 ok(renewed!==m);
 const renewed_entry=await rpc('admin_register_checkin',{p_gym_id:id,p_client_id:c,p_method:'HUELLA BIOMÉTRICA',p_override:false});
 ok(renewed_entry.result==='PERMITIDA'&&renewed_entry.entries_remaining===19);
 const monthly=(await db.query("INSERT INTO public.plans(gym_id,name,duration_days,price,entry_limit) VALUES($1,'Mensual por días',30,1000,null) RETURNING id",[id])).rows[0].id;
 const mc=(await db.query("INSERT INTO public.clients(gym_id,document,first_name) VALUES($1,'C-03','Mensual') RETURNING id",[id])).rows[0].id;
 await buy(mc,monthly);
 const normal=await rpc('admin_register_checkin',{p_gym_id:id,p_client_id:mc,p_method:'MANUAL',p_override:false});
 ok(normal.result==='PERMITIDA'&&normal.entries_remaining===null);
 await db.query("UPDATE public.clients SET biometric_identifier='GS001' WHERE id=$1",[c]);
 await user(R);await rpc('commercial_accept_invite',{p_code:invite});await rpc('commercial_check_license',license);
 const receptionClient=await rpc('reception_save_client',{p_gym_id:id,p_client_id:null,p_document:'R-01',p_first_name:'Recepción',p_last_name:'',p_phone:'',p_email:'',p_birthdate:null,p_biometric_identifier:''});
 ok(receptionClient!==null);
 const found=await rpc('reception_find_client_by_biometric',{p_gym_id:id,p_biometric_identifier:'GS001'});
 ok(found.id===c);
 const entry=await rpc('reception_register_checkin',{p_gym_id:id,p_client_id:c2,p_method:'HUELLA BIOMÉTRICA'});
 ok(entry.result==='PERMITIDA'&&entry.entries_remaining===19);
 await assert.rejects(()=>rpc('reception_find_client_by_biometric',{p_gym_id:other.gym_id,p_biometric_identifier:'GS001'}),/permiso|autoriz/i);checks++;
 console.log(`PASS: ${checks} comprobaciones PostgreSQL de huella opcional, cupos, consumo, renovación, mensualidad y aislamiento.`);
}finally{await db.close();}
