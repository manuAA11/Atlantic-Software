import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import {randomUUID} from 'node:crypto';import {fixture} from './membership_feature_fixture.mjs';
const f=await fixture();const {db,root,A,R,B:O,gym,user,system,person:client}=f;let checks=0;const ok=v=>{assert.ok(v,`check ${checks+1}`);checks++;};
try{
 await system();await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_TIQUETERA_COBRO.sql'),'utf8'));await user(A);
 const plan=(await db.query("insert into public.plans(gym_id,name,duration_days,price,entry_limit) values($1,'Carryover payment fixture',30,50000,15) returning id",[gym])).rows[0].id,today=(await db.query("select public.gym_local_clock($1)->>'today' as day",[gym])).rows[0].day;
 async function carry(cid,amount=50000,key=randomUUID(),extra={}){const a={p_gym_id:gym,p_client_id:cid,p_plan_id:plan,p_start:today,p_entries_used:7,p_notes:'Nota',p_request_id:key,p_amount:amount,p_payment_method:'Efectivo',p_payment_reference:'ref',...extra};return (await db.query('select * from public.register_ticket_carryover_with_payment('+Object.keys(a).map((k,i)=>k+' => $'+(i+1)).join(',')+')',Object.values(a))).rows[0];}
 const cid=await client(),key=randomUUID(),m=await carry(cid,50000,key);
 let row=(await db.query('select * from public.memberships where id=$1',[m.membership_id])).rows[0];ok(row.amount===50000&&row.amount_paid===50000);ok(row.initial_entries_used===7);ok(row.payment_method==='Efectivo'&&row.payment_reference==='ref');ok(row.notes.includes('cobro registrado ahora'));
 ok((await carry(cid,50000,key)).membership_id===m.membership_id);ok((await db.query('select count(*) as n from public.memberships')).rows[0].n===1);
 for(const extra of [{p_amount:0},{p_payment_method:'Transferencia'},{p_payment_reference:'changed'},{p_notes:'changed'},{p_entries_used:6}]){await assert.rejects(()=>carry(cid,50000,key,extra),/otra operación/i);checks++;}
 const zero=await carry(await client(),0);row=(await db.query('select * from public.memberships where id=$1',[zero.membership_id])).rows[0];ok(row.amount===0&&row.amount_paid===0&&row.payment_method==='Saldo inicial'&&row.payment_reference==='');ok(row.notes.includes('sin nuevo cobro'));
 for(const amount of [-1,null]){await assert.rejects(()=>carry(cid,amount),/cero|positivo/i);checks++;}
 await assert.rejects(()=>carry(cid,50000,randomUUID(),{p_payment_method:' '}),/método/i);checks++;
 await assert.rejects(()=>carry(cid,50000,randomUUID(),{p_entries_used:16}),/cupo/i);checks++;
 await assert.rejects(()=>carry(cid),/Ya existe/i);checks++;
 const lc=await client();await db.query('select * from public.register_ticket_carryover($1,$2,$3,$4,2,$5,$6)',[gym,lc,plan,today,'Legacy',randomUUID()]);ok((await db.query('select amount_paid from public.memberships where client_id=$1',[lc])).rows[0].amount_paid===0);
 const first=(await db.query("select public.admin_register_checkin($1,$2,'MANUAL',false) as data",[gym,cid])).rows[0].data,second=(await db.query("select public.admin_register_checkin($1,$2,'MANUAL',false) as data",[gym,cid])).rows[0].data;ok(first.entries_remaining===7);ok(second.entries_remaining===7&&second.already_consumed_today);
 ok(Number((await db.query('select sum(amount_paid) as total from public.memberships where gym_id=$1',[gym])).rows[0].total)===50000);
 await user(O);await assert.rejects(()=>carry(cid),/permiso/i);checks++;
 await user(R);const rc=(await db.query("select public.reception_save_client($1,null,'R-TICKET','Reception','','','',null,'') as id",[gym])).rows[0].id;ok((await carry(rc,25000)).membership_id>0);
 await db.exec('RESET ROLE');ok((await db.query("select has_function_privilege('anon','public.register_ticket_carryover_with_payment(uuid,bigint,bigint,date,bigint,text,uuid,bigint,text,text)','EXECUTE') as allowed")).rows[0].allowed===false);
 console.log(`PASS: ${checks} ticket carryover payment checks.`);
}finally{await db.close();}
