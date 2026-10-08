import assert from 'node:assert/strict';
import {database} from './migrations.mjs';
const db=await database();
let passed=0;
const O='10000000-0000-4000-8000-000000000001',A='20000000-0000-4000-8000-000000000001',B='30000000-0000-4000-8000-000000000001',R='40000000-0000-4000-8000-000000000001';
const sessions=Object.fromEntries([O,A,B,R].map((v,i)=>[v,`90000000-0000-4000-8000-00000000000${i+1}`]));
const hashA='a'.repeat(64),hashB='b'.repeat(64);
async function user(id,sid=sessions[id]){
 await db.exec('RESET ROLE');
 await db.query(`SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)`,[id,JSON.stringify({sub:id,session_id:sid})]);
 await db.exec('SET ROLE authenticated');
}
async function rpc(name,args=[]){return (await db.query(`SELECT public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) AS data`,args)).rows[0].data;}
async function denied(fn,match=/permission|permiso|exclusiv|autoriz|invita|suscrip|rol|row-level|foreign key|invalid|cuenta|column|limit|límite|does not exist/i){
 await assert.rejects(fn,match);passed++;
}
function ok(condition,message){assert.ok(condition,message);passed++;}
try{
 for(const [id,email] of [[O,'owner@example.test'],[A,'a@example.test'],[B,'b@example.test'],[R,'reception@example.test']]){
  await db.query('INSERT INTO auth.users(id,email) VALUES($1,$2)',[id,email]);
 }
 await db.query('INSERT INTO private.software_owners(user_id) VALUES($1)',[O]);
 await user(A);
 await denied(()=>rpc('owner_list_gyms'));
 await denied(()=>rpc('owner_create_gym',['Unauthorized','a@example.test',10]));
 await user(O);
 const ga=await rpc('owner_create_gym',['Gimnasio A','a@example.test',100000,'COP',1,7]);
 const gb=await rpc('owner_create_gym',['Gimnasio B','b@example.test',40,'USD',1,7]);
 ok(ga.gym_id!==gb.gym_id,'unique gym IDs');
 await user(B);await denied(()=>rpc('commercial_accept_invite',[ga.activation_code]));
 await user(A);await rpc('commercial_accept_invite',[ga.activation_code]);
 await denied(()=>rpc('commercial_accept_invite',[ga.activation_code]));
 ok((await rpc('commercial_context')).gym_id===ga.gym_id,'account tied to invited gym');
 await denied(()=>db.query('UPDATE public.gym_users SET role=$1 WHERE user_id=$2',['admin',A]));
 await denied(()=>db.query('INSERT INTO public.gym_users(gym_id,user_id,role) VALUES($1,$2,$3)',[gb.gym_id,A,'admin']));
 ok((await db.query('SELECT * FROM public.clients')).rows.length===0,'no data before device authorization');
 await denied(()=>rpc('reception_list_clients',[ga.gym_id,'']));
 ok((await rpc('commercial_check_license',[hashA,'PC A'])).state==='device_pending','new device needs owner approval');
 await user(O);
 let detail=await rpc('owner_gym_detail',[ga.gym_id]); const devA=detail.devices[0].id;
 await rpc('owner_set_device',[devA,false,'Equipo autorizado']);
 await user(A);ok((await rpc('commercial_check_license',[hashA,'PC A'])).allowed,'approved device works');
 await user(B);await rpc('commercial_accept_invite',[gb.activation_code]);await rpc('commercial_check_license',[hashB,'PC B']);
 await user(O);detail=await rpc('owner_gym_detail',[gb.gym_id]);await rpc('owner_set_device',[detail.devices[0].id,false,'Equipo autorizado']);
 await user(B);await rpc('commercial_check_license',[hashB,'PC B']);
 let clientB=(await db.query("INSERT INTO public.clients(gym_id,document,first_name) VALUES($1,'123','B') RETURNING id",[gb.gym_id])).rows[0].id;
 await user(A);
 let clientA=(await db.query("INSERT INTO public.clients(gym_id,document,first_name) VALUES($1,'123','A') RETURNING id",[ga.gym_id])).rows[0].id;
 ok((await db.query('SELECT first_name FROM public.clients')).rows.map(r=>r.first_name).join()==='A','RLS filters tenant even with no WHERE');
 ok((await db.query('UPDATE public.clients SET first_name=$1 WHERE id=$2 RETURNING id',['HACK',clientB])).rows.length===0,'cannot modify another tenant');
 await denied(()=>rpc('reception_list_clients',[gb.gym_id,'']));
 await denied(()=>db.query("INSERT INTO public.clients(gym_id,document,first_name) VALUES($1,'OTHER','X')",[gb.gym_id]));
 const planA=(await db.query("SELECT id FROM public.plans WHERE name='Tiquetera'")).rows[0].id;
 await db.query('UPDATE public.plans SET entry_limit=1 WHERE id=$1',[planA]);
 await denied(()=>db.query("INSERT INTO public.memberships(gym_id,client_id,plan_id,start_date,end_date,amount,payment_method) VALUES($1,$2,$3,current_date,current_date,1,'Efectivo')",[ga.gym_id,clientB,planA]));
 let member=(await db.query('SELECT * FROM public.add_membership_accumulating($1,$2,$3,$4,$5,$6,$7,$8)',[ga.gym_id,clientA,planA,null,25000,'Efectivo','','Prueba'])).rows[0];
 ok(member.membership_id>0,'paid membership created');
 let check=await rpc('admin_register_checkin',[ga.gym_id,clientA,'MANUAL',false]);
 ok(check.result==='PERMITIDA' && Number(check.entries_remaining)===0,'last entry consumed atomically');
 check=await rpc('admin_register_checkin',[ga.gym_id,clientA,'MANUAL',false]);
 ok(check.result==='PERMITIDA' && check.entries_remaining===0 && check.already_consumed_today && !check.ticket_consumed,'same-day reentry does not consume another entry');
 await denied(()=>db.query('UPDATE public.memberships SET amount=0 WHERE id=$1',[member.membership_id]));
 await rpc('get_finance_dashboard',[ga.gym_id,null,null]);passed++;
 await rpc('get_attendance_statistics',[ga.gym_id,30]);passed++;
 await rpc('admin_store_finance',[ga.gym_id,null,null]);passed++;
 await rpc('admin_staff_dashboard',[ga.gym_id,'2026-09-01','2026-09-30']);passed++;
 await rpc('admin_accounting_expenses',[ga.gym_id,'2026-09-01','2026-09-30']);passed++;
 await user(O);
 let invite=await rpc('owner_invite_user',[ga.gym_id,'reception@example.test','receptionist']);
 await user(R);await rpc('commercial_accept_invite',[invite]);await rpc('commercial_check_license',[hashA,'PC A']);
 ok((await db.query('SELECT * FROM public.clients')).rows.length===0,'reception has no direct client-table access');
 ok((await rpc('reception_list_clients',[ga.gym_id,''])).length===1,'reception permitted RPC works');
 await denied(()=>rpc('get_finance_dashboard',[ga.gym_id,null,null]));
 await denied(()=>rpc('owner_set_status',[ga.gym_id,'active','Unauthorized']));
 await rpc('reception_create_expense',[ga.gym_id,'2026-09-07','Limpieza','Prueba','',1000,'Efectivo','','','']);passed++;
 await user(A);
 const otherHash='c'.repeat(64);
 ok((await rpc('commercial_check_license',[otherHash,'Unapproved'])).state==='device_pending','changed device identifier cannot self-authorize');
 await user(O);detail=await rpc('owner_gym_detail',[ga.gym_id]);const extra=detail.devices.find(d=>d.device_hash===otherHash);
 await denied(()=>rpc('owner_set_device',[extra.id,false,'Exceeds cap']));
 const paymentKey='80000000-0000-4000-8000-000000000001';
 let payment=await rpc('owner_renew',[ga.gym_id,1,100000,'COP','Pago-001',paymentKey]);
 let duplicate=await rpc('owner_renew',[ga.gym_id,1,100000,'COP','Pago-001',paymentKey]);
 ok(payment.id===duplicate.id && payment.period_until===duplicate.period_until,'renewal retries are idempotent');
 await denied(()=>rpc('owner_renew',[ga.gym_id,2,100000,'COP','Pago-001',paymentKey]),/otros datos/);
 await rpc('owner_set_status',[ga.gym_id,'suspended','Pago en revisión']);
 await user(A);
 ok((await db.query('SELECT * FROM public.clients')).rows.length===0,'existing JWT loses table access upon suspension');
 await denied(()=>rpc('reception_list_clients',[ga.gym_id,'']));
 await denied(()=>rpc('admin_replace_gym_from_excel',[{}]));
 await denied(()=>rpc('get_finance_dashboard',[ga.gym_id,null,null]));
 await user(B);ok((await db.query('SELECT * FROM public.clients')).rows.length===1,'another tenant keeps working');
 await user(O);await rpc('owner_set_status',[ga.gym_id,'active','Pago confirmado']);
 await db.exec('RESET ROLE');await db.query("UPDATE private.subscriptions SET expires_at=now()-interval '1 day',grace_until=null WHERE gym_id=$1",[ga.gym_id]);
 await user(A);ok((await rpc('commercial_check_license',[hashA,'PC A'])).state==='expired','server enforces expiration');
 await denied(()=>rpc('admin_register_checkin',[ga.gym_id,clientA,'MANUAL',true]));
 await user(O);await rpc('owner_grant_grace',[ga.gym_id,3,'Plazo autorizado']);
 await user(A);ok((await rpc('commercial_check_license',[hashA,'PC A'])).state==='grace','explicit grace period works');
 await user(O);await rpc('owner_set_device',[devA,true,'Equipo perdido']);
 await user(A);await denied(()=>rpc('reception_list_clients',[ga.gym_id,'']));
 ok((await rpc('commercial_check_license',[hashA,'PC A'])).state==='device_revoked','revoked hardware stays blocked');
 await user(O);await rpc('owner_set_device',[devA,false,'Equipo recuperado']);await rpc('owner_set_user',[A,false,'Baja de usuario']);
 await user(A);await denied(()=>rpc('reception_list_clients',[ga.gym_id,'']));
 await user(R);ok((await rpc('reception_list_clients',[ga.gym_id,''])).length===1,'other authorized staff continue');
 await user(O);await rpc('owner_set_user',[A,true,'Rehabilitado']);
 const backup=await rpc('owner_backup_gym',[ga.gym_id]);
 ok(backup.tables.clients.length===1 && backup.tables.clients[0].gym_id===ga.gym_id,'owner backup belongs to exactly one gym');
 ok(backup.tables.audit_logs.length>0,'auditable operational actions preserved');
 await user(A);
 await denied(()=>db.query('SELECT * FROM private.subscriptions'));
 await denied(()=>db.query('SELECT * FROM private.subscription_payments'));
 await denied(()=>db.query('SELECT private.reception_list_clients($1,$2)',[ga.gym_id,'']));
 await db.exec('RESET ROLE; SET ROLE anon');
 await denied(()=>rpc('owner_list_gyms'));
 await denied(()=>db.query('SELECT * FROM public.clients'));
 console.log(`PASS: ${passed} security and business checks, real PostgreSQL engine (PGlite).`);
}catch(e){console.error('TEST FAILED after',passed,'checks:',e.message,e.detail||'',e.where||'');process.exitCode=1;}
finally{await db.close();}
