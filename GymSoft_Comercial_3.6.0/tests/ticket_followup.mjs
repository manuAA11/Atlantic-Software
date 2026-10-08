import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
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
 let serial=0;
 async function client(name='Cliente'){return (await db.query('INSERT INTO public.clients(gym_id,document,first_name,phone,email) VALUES($1,$2,$3,$4,$5) RETURNING id',[id,'T-'+(++serial),name,'3001234567','contacto@example.test'])).rows[0].id;}
 async function plan(limit=25,months=2,days=30){return (await db.query('INSERT INTO public.plans(gym_id,name,duration_days,duration_months,price,entry_limit) VALUES($1,$2,$3,$4,9000,$5) RETURNING id',[id,'Plan '+(++serial),days,months,limit])).rows[0].id;}
 const today=(await db.query('SELECT public.gymsoft_today()::text as d')).rows[0].d;
 function ago(n){const value=new Date(today+'T12:00:00Z');value.setUTCDate(value.getUTCDate()-n);return value.toISOString().slice(0,10);}
 const ticket=await plan();
 async function carry(cid,used,start=ago(10),pid=ticket,key=randomUUID()){
  return (await db.query('SELECT membership_id,start_date::text,end_date::text FROM public.register_ticket_carryover($1,$2,$3,$4,$5,$6,$7)',[id,cid,pid,start,used,'Migración desde tiquetera de papel',key])).rows[0];
 }
 async function buy(cid,pid,start=today){return (await db.query('SELECT membership_id,start_date::text,end_date::text FROM public.add_membership_accumulating($1,$2,$3,$4,9000,$5,$6,$7)',[id,cid,pid,start,'Efectivo','',''])).rows[0];}
 const transferred=await client('Ana trasladada'), key=randomUUID();
 const before=(await db.query('SELECT coalesce(sum(amount_paid),0) as n FROM public.memberships WHERE gym_id=$1',[id])).rows[0].n;
 const m=await carry(transferred,12,ago(10),ticket,key);
 const after=(await db.query('SELECT coalesce(sum(amount_paid),0) as n FROM public.memberships WHERE gym_id=$1',[id])).rows[0].n;
 ok(before===after);
 ok((await db.query('SELECT count(*) as n FROM public.checkins WHERE client_id=$1',[transferred])).rows[0].n===0);
 const snap=await rpc('reception_membership_snapshot',{p_gym_id:id,p_client_id:transferred});
 ok(snap.entries_used===12 && snap.entries_remaining===13 && snap.allowed);
 ok((await carry(transferred,12,ago(10),ticket,key)).membership_id===m.membership_id);
 await assert.rejects(()=>carry(transferred,13,ago(10),ticket,key),/otra operación/i);checks++;
 await assert.rejects(()=>carry(transferred,12),/Ya existe/i);checks++;
 for(const used of [-1,26]){await assert.rejects(()=>carry(transferred,used),/cupo/i);checks++;}
 await assert.rejects(()=>carry(transferred,1,ago(-1)),/inicio/i);checks++;
 const entry=await rpc('admin_register_checkin',{p_gym_id:id,p_client_id:transferred,p_method:'MANUAL',p_override:false});
 ok(entry.result==='PERMITIDA' && entry.entries_used===13 && entry.entries_remaining===12);
 const leap=await carry(await client(),0,'2024-01-31',await plan(15,1));
 ok(leap.end_date==='2024-02-28');
 const calendar=await buy(await client(),await plan(15,1),'2026-01-01');
 ok(calendar.end_date==='2026-01-31');
 const monthly=await plan(null,null,30), monthlyClient=await client();
 const monthlySale=await buy(monthlyClient,monthly);
 ok(monthlySale.end_date===ago(-29));
 await assert.rejects(()=>carry(transferred,0,ago(10),monthly),/tiquetera/i);checks++;
 await assert.rejects(()=>plan(null,1),/ticket_months_valid/);checks++;
 const bucketPeople=[];
 for(const remaining of [0,1,5,6,10,11,15,16,20,21]){
  const cid=await client('Saldo '+remaining);await carry(cid,25-remaining);bucketPeople.push([cid,remaining]);
 }
 const report=await rpc('ticket_followup',{p_gym_id:id});
 for(const [cid,left] of bucketPeople)ok(report.some(r=>r.client_id===cid && r.entries_remaining===left));
 ok(!report.some(r=>r.client_id===monthlyClient));
 const depleted=bucketPeople[0][0];
 ok((await rpc('reception_membership_snapshot',{p_gym_id:id,p_client_id:depleted})).status==='SIN ENTRADAS');
 const renewal=await buy(depleted,ticket);ok(renewal.start_date===today);
 ok((await rpc('reception_register_checkin',{p_gym_id:id,p_client_id:depleted,p_method:'MANUAL'})).entries_remaining===24);
 // Las ediciones de un plan solo se usan en compras posteriores.
 await db.query('UPDATE public.plans SET duration_months=3,entry_limit=30 WHERE id=$1',[ticket]);
 ok((await db.query('SELECT entry_limit,end_date FROM public.memberships WHERE id=$1',[m.membership_id])).rows[0].entry_limit===25);
 ok((await db.query('SELECT end_date::text FROM public.memberships WHERE id=$1',[m.membership_id])).rows[0].end_date===m.end_date);
 // Visitas por sesión con límites locales inclusivos de 7/14/30 días.
 const session=await plan(1,null,1), people=[];
 for(const days of [0,6,7,13,14,29,30]){
  const cid=await client('Sesión '+days), membership=await buy(cid,session,ago(days));
  // Historical visits enter through the import engine; a live desktop cannot backdate an event.
  await db.exec('RESET ROLE');
  await db.query("select private.gymsoft_import_insert('checkins',$1,$2::jsonb)",[id,JSON.stringify({client_id:cid,membership_id:membership.membership_id,checkin_at:ago(days)+'T12:00:00-05:00',result:'PERMITIDA',method:'MANUAL'})]);
  await user(A);
  people.push([cid,days]);
 }
 for(const period of [7,14,30]){
  const rows=await rpc('session_followup',{p_gym_id:id,p_days:period});
  for(const [cid,days] of people)ok(rows.some(r=>r.client_id===cid)===(days<period));
  ok(rows.every(r=>r.phone==='3001234567'&&r.email==='contacto@example.test'));
 }
 // Compró mensualidad después de una sesión: se muestra el estado actual.
 const converted=people[1][0];await buy(converted,monthly);
 let sessions=await rpc('session_followup',{p_gym_id:id,p_days:7});
 ok(sessions.find(r=>r.client_id===converted).current_status==='AL DÍA');
 await rpc('admin_register_checkin',{p_gym_id:id,p_client_id:converted,p_method:'MANUAL',p_override:false});
 sessions=await rpc('session_followup',{p_gym_id:id,p_days:7});
 ok(!sessions.some(r=>r.client_id===converted)); // Asistencia mixta en el período.
 await assert.rejects(()=>rpc('session_followup',{p_gym_id:id,p_days:15}),/Selecciona/);checks++;
 await assert.rejects(()=>rpc('ticket_followup',{p_gym_id:other.gym_id}),/permiso/i);checks++;
 await assert.rejects(()=>rpc('session_followup',{p_gym_id:other.gym_id,p_days:7}),/Administración/i);checks++;
 // Recepción puede trasladar y consultar cupos, pero no estadísticas administrativas.
 await user(R);await rpc('commercial_accept_invite',{p_code:invite});await rpc('commercial_check_license',license);
 ok(Array.isArray(await rpc('ticket_followup',{p_gym_id:id})));
 await assert.rejects(()=>rpc('session_followup',{p_gym_id:id,p_days:7}),/Administración/i);checks++;
 const receptionClient=await rpc('reception_save_client',{p_gym_id:id,p_client_id:null,p_document:'RECEPTION-TICKET',p_first_name:'Recepción',p_last_name:'',p_phone:'',p_email:'',p_birthdate:null,p_biometric_identifier:''});
 const rm=await carry(receptionClient,29);ok(rm.membership_id>0);
 ok((await rpc('reception_register_checkin',{p_gym_id:id,p_client_id:receptionClient,p_method:'MANUAL'})).entries_remaining===0);
 const reentry=await rpc('reception_register_checkin',{p_gym_id:id,p_client_id:receptionClient,p_method:'MANUAL'});
 ok(reentry.result==='PERMITIDA' && reentry.already_consumed_today && reentry.entries_remaining===0);
 await user(O);
 const backup=await rpc('owner_editor_backup',{p_gym_id:id});
 ok(backup.tables.memberships.some(r=>r.id===m.membership_id&&r.initial_entries_used===12));
 ok(backup.tables.plans.some(r=>r.id===ticket&&r.duration_months===3));
 const rows=await rpc('owner_editor_rows',{p_gym_id:id,p_table:'memberships'});
 ok(rows.columns.some(c=>c.name==='initial_entries_used'&&c.editable));
 await db.exec('RESET ROLE');
 const functions=(await db.query("SELECT n.nspname,p.proname,has_function_privilege('anon',p.oid,'EXECUTE') as allowed FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE p.proname in ('ticket_followup','session_followup','register_ticket_carryover','ticket_end_date')")).rows;
 ok(functions.every(f=>!f.allowed));
 // La actualización se puede volver a aplicar sin perder saldos ni accesos.
 const fs=await import('node:fs');await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_TIQUETERAS_3.3.0.sql'),'utf8'));
 ok((await db.query('SELECT initial_entries_used FROM public.memberships WHERE id=$1',[m.membership_id])).rows[0].initial_entries_used===12);
 console.log(`PASS: ${checks} comprobaciones de meses calendario, saldos, seguimiento, roles e idempotencia.`);
}finally{await db.close();}
