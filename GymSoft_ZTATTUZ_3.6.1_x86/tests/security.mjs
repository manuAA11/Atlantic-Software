import assert from 'node:assert/strict';
import {database} from './migrations.mjs';
import {randomUUID} from 'node:crypto';
const db=await database();let checks=0;
const A=randomUUID(),B=randomUUID(),R=randomUUID();
async function user(id){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);await db.exec('set role authenticated');}
async function rpc(name,args=[]){return (await db.query(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) as data`,args)).rows[0].data;}
function ok(value,label){assert.ok(value,label);checks++;}
async function denied(fn){await assert.rejects(fn,/permission|permiso|autoriz|Administraci|administra|row-level|cuenta|acceso|exclusiv/i);checks++;}
try{
 for(const id of [A,B,R])await db.query('insert into auth.users(id,email) values($1,$2)',[id,id+'@example.test']);
 await user(A);const a=await rpc('create_gym',['A']);const code=await rpc('create_reception_invite');
 await user(B);const b=await rpc('create_gym',['B']);
 const foreign=(await db.query("insert into public.clients(gym_id,document,first_name) values($1,'B-1','Otro') returning id",[b])).rows[0].id;
 await user(A);
 ok((await db.query('select id from public.clients where id=$1',[foreign])).rows.length===0,'RLS oculta otro gimnasio');
 ok((await db.query("update public.clients set first_name='Cambio' where id=$1 returning id",[foreign])).rows.length===0,'RLS protege escrituras');
 await denied(()=>rpc('ticket_followup',[b]));await denied(()=>rpc('session_followup',[b,7]));await denied(()=>rpc('admin_register_checkin',[b,foreign,'MANUAL',true]));
 const cid=(await db.query("insert into public.clients(gym_id,document,first_name) values($1,'A-1','Cliente') returning id",[a])).rows[0].id;
 await db.query("insert into public.gym_branding(gym_id,logo_data) values($1,'prueba')",[a]);
 await user(R);await rpc('redeem_reception_invite',[code]);
 ok((await rpc('reception_account_context')).role==='receptionist','Invitación no escala privilegios');
 await denied(()=>rpc('create_reception_invite'));await denied(()=>rpc('session_followup',[a,7]));await denied(()=>rpc('admin_register_checkin',[a,cid,'MANUAL',true]));
 ok((await db.query('select logo_data from public.gym_branding where gym_id=$1',[a])).rows[0].logo_data==='prueba','Recepción puede consultar logotipo');
 ok((await db.query("update public.gym_branding set logo_data='Cambio' returning gym_id")).rows.length===0,'Recepción no modifica logotipo');
 await denied(()=>rpc('register_ticket_carryover',[b,foreign,1,'2026-01-01',0,'Prueba',randomUUID()]));
 await db.exec('reset role');
 for(const name of ['ztattuz_add_membership','register_ticket_carryover','ticket_followup','session_followup','admin_register_checkin']){
  const rows=(await db.query("select p.oid,p.prosecdef,p.proconfig,has_function_privilege('anon',p.oid,'execute') as anon from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='private' and p.proname=$1",[name])).rows;
  ok(rows.length===1 && rows[0].prosecdef && !rows[0].anon && rows[0].proconfig.includes('search_path=""'),name+' restringida y search_path fijo');
 }
 await db.exec('set role anon');await denied(()=>rpc('ztattuz_system_info'));await denied(()=>rpc('ticket_followup',[a]));
 await denied(()=>rpc('admin_register_checkin',[a,cid,'MANUAL',true]));
 console.log(`PASS: ${checks} comprobaciones de roles, aislamiento y permisos ZTATTUZ.`);
}finally{await db.close();}
