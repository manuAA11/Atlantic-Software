import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {database,root} from './migrations.mjs';
const db=await database({upgrade:false});let checks=0;
const A=randomUUID(),R=randomUUID();
async function user(id){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);await db.exec('set role authenticated');}
async function rpc(name,args=[]){return (await db.query(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) as data`,args)).rows[0].data;}
function ok(v,label){assert.ok(v,label);checks++;}
try{
 for(const id of [A,R])await db.query('insert into auth.users(id,email) values($1,$2)',[id,id+'@example.test']);
 await user(A);const gid=await rpc('create_gym',['ZTATTUZ anterior']);const code=await rpc('create_reception_invite');
 const client=(await db.query("insert into public.clients(gym_id,document,first_name,biometric_identifier) values($1,'ANT-001','Anterior',null) returning id",[gid])).rows[0].id;
 const ticket=(await db.query("insert into public.plans(gym_id,name,duration_days,price,entry_limit) values($1,'Tiquetera anterior',30,50000,10) returning id",[gid])).rows[0].id;
 const membership=(await db.query("select * from public.add_membership_accumulating($1,$2,$3,null,50000,'Efectivo','ANT-001','Pago anterior')",[gid,client,ticket])).rows[0];
 await user(R);await rpc('redeem_reception_invite',[code]);
 ok((await rpc('reception_register_checkin',[gid,client,'MANUAL'])).entries_remaining===9,'La versión anterior consume una entrada');
 await db.exec('reset role');
 const tables=(await db.query("select table_name as name from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by table_name")).rows;
 const before={};
 for(const {name} of tables){
  const columns=(await db.query("select column_name from information_schema.columns where table_schema='public' and table_name=$1 order by ordinal_position",[name])).rows.map(r=>r.column_name);
  const query=`select ${columns.map(c=>'"'+c+'"').join(',')} from public."${name}" order by 1`;
  before[name]={query,rows:(await db.query(query)).rows};
 }
 const update=fs.readFileSync(path.join(root,'ACTUALIZAR_ZTATTUZ_3.4.5.sql'),'utf8');
 await db.exec(update);await db.exec(update);
 for(const [name,{query,rows}] of Object.entries(before)){
  assert.deepEqual((await db.query(query)).rows,rows,'Se alteraron datos anteriores: '+name);checks++;
 }
 await user(R);
 const snapshot=await rpc('reception_membership_snapshot',[gid,client]);
 ok(snapshot.allowed && snapshot.entries_remaining===9,'La membresía original conserva el saldo');
 ok((await rpc('reception_register_checkin',[gid,client,'MANUAL'])).entries_remaining===8,'La recepción antigua sigue compatible');
 ok((await rpc('reception_account_context')).gym_id===gid,'La cuenta mantiene su gimnasio');
 await user(A);
 const oldApi=(await db.query("select * from public.add_membership_accumulating($1,$2,$3,null,50000,'Efectivo','ANT-002','')",[gid,client,ticket])).rows[0];
 assert.deepEqual(Object.keys(oldApi),['membership_id','start_date','end_date']);checks++;
 ok((await rpc('ztattuz_client_payments',[gid,client,true,0,100])).rows.length===2,'Los pagos anteriores siguen editables');
 ok((await rpc('ztattuz_system_info')).schema_version==='3.4.5','Versión actualizada');
 await db.exec('reset role');
 const dates=(await db.query("select duration_days,duration_months from public.plans where id=$1",[ticket])).rows[0];
 ok(dates.duration_days===30 && dates.duration_months===null,'El plan anterior conserva sus días, sin inventar meses');
 ok((await db.query('select initial_entries_used from public.memberships where id=$1',[membership.membership_id])).rows[0].initial_entries_used===0,'Los consumos anteriores no se cuentan dos veces');
 console.log(`PASS: ${checks} comprobaciones de actualización repetible, datos anteriores, acceso y API compatible.`);
}finally{await db.close();}
