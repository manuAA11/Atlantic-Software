// Reproduce an existing server without STAFF, then upgrade without losing history.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
import {fixture} from './membership_feature_fixture.mjs';

const f=await fixture({features:false});
const {db,root,gym,user,system,A,rpc,monthly,enter}=f;
const diagnostic=fs.readFileSync(path.join(root,'DIAGNOSTICAR_PANEL.sql'),'utf8');
const upgrade=fs.readFileSync(path.join(root,'ACTUALIZAR_SERVIDOR_MEMBRESIAS.sql'),'utf8');
const protectedTables=['clients','plans','memberships','checkins','audit_logs','membership_freezes','membership_freeze_policies','ticket_daily_consumptions'];
async function columnSnapshot(){
 return (await db.query(`select table_schema,table_name,column_name,data_type,is_nullable,column_default
  from information_schema.columns where table_schema in ('public','private')
  order by table_schema,table_name,ordinal_position`)).rows;
}
async function rowSnapshot(){
 const result={};
 for(const table of protectedTables)result[table]=(await db.query(`select to_jsonb(t) as row from public.${table} t order by to_jsonb(t)::text`)).rows;
 return result;
}
let checks=0;
const eq=(actual,expected,label)=>{assert.deepEqual(actual,expected,label);checks++;};
try{
 const member=await monthly();
 const ticket=await monthly({ticket:3});
 await monthly({end:'2026-10-10'});
 await enter(member.c);await enter(ticket.c);
 // A closed legacy freeze retains every old identifier, date and instant.
 const freeze=await rpc('membership_freeze',{p_gym_id:gym,p_membership_id:member.m,p_request_id:randomUUID()});
 await rpc('membership_cancel_freeze',{p_gym_id:gym,p_freeze_id:freeze.id,p_reason:'Prueba de actualización'});
 const clients=await rpc('reception_list_clients',{p_gym_id:gym,p_search:''});
 eq(clients.length,3,'The old server still returns existing clients');
 await assert.rejects(()=>rpc('membership_population',{p_gym_id:gym}),{code:'42883'});checks++;
 await system();
 const before={};
 for(const table of protectedTables){
  const columns=(await db.query("select column_name from information_schema.columns where table_schema='public' and table_name=$1 and column_name<>'updated_at' order by ordinal_position",[table])).rows.map(row=>row.column_name);
  const ordering=columns.includes('id')?'id':'gym_id,membership_id,local_date';
  const query=`select ${columns.map(name=>'"'+name+'"').join(',')} from public.${table} order by ${ordering}`;
  before[table]={query,rows:(await db.query(query)).rows};
 }
 const missing=(await db.query(diagnostic)).rows.filter(row=>row.estado==='FALTA').map(row=>row.componente).sort();
 eq(missing,['Duración efectiva de congelación','Editor de planes','Panel de membresías y STAFF','Reanudación anticipada','Tipo de membresía'].sort());
 // A second diagnostic is read-only and produces the same result.
 eq((await db.query(diagnostic)).rows.filter(row=>row.estado==='FALTA').map(row=>row.componente).sort(),missing);
 for(const [table,{query,rows}] of Object.entries(before))eq((await db.query(query)).rows,rows,'Read-only diagnostic preserved '+table);
 // Missing dependencies are all reported before any new column or backfill.
 await db.exec(`alter function private.audit_membership_payment() rename to audit_payment_preflight_fixture;
  alter function public.marketing_service_payment_request(uuid,bigint,bigint,text) rename to payment_request_preflight_fixture;
  alter table public.membership_freezes rename column starts_at to starts_at_preflight_fixture;`);
 const incompleteColumns=await columnSnapshot(),incompleteRows=await rowSnapshot();
 let failure;
 try{await db.exec(upgrade);}catch(error){failure=error;}
 await db.exec('rollback');
 eq(failure?.code,'P0001','An incomplete starting server cannot receive a partial upgrade');
 for(const missing of ['private.audit_membership_payment()','public.marketing_service_payment_request(uuid,bigint,bigint,text)','public.membership_freezes.starts_at']){
  eq(failure.detail.includes(missing),true,'Preflight names the missing prerequisite '+missing);
 }
 eq(await columnSnapshot(),incompleteColumns,'A failed combined upgrade created no columns or tables');
 eq(await rowSnapshot(),incompleteRows,'A failed combined upgrade changed no historical rows or audits');
 await db.exec(`alter function private.audit_payment_preflight_fixture() rename to audit_membership_payment;
  alter function public.payment_request_preflight_fixture(uuid,bigint,bigint,text) rename to marketing_service_payment_request;
  alter table public.membership_freezes rename column starts_at_preflight_fixture to starts_at;`);
 // A late failure also rolls back both source upgrades; there is no intermediate COMMIT.
 const legacyRows=await rowSnapshot(),legacyColumns=await columnSnapshot();
 let lateFailure;
 try{await db.exec(upgrade.replace(/\ncommit;\s*$/,'\nselect 1/0;\ncommit;\n'));}catch(error){lateFailure=error;}
 await db.exec('rollback');
 eq(lateFailure?.code,'22012','The test fails after both upgrade bodies and before the final commit');
 eq(await rowSnapshot(),legacyRows,'A late failure preserves all historical rows and audits');
 eq(await columnSnapshot(),legacyColumns,'A late failure removes every new object from both upgrades');
 await db.exec(upgrade);
 eq((await db.query(diagnostic)).rows.filter(row=>row.estado==='FALTA'),[],'Required objects are present after the additive upgrades');
 for(const [table,{query,rows}] of Object.entries(before)){
  const actual=(await db.query(query)).rows;
  if(table==='audit_logs'){
   const previousIds=new Set(rows.map(row=>row.id));
   eq(actual.filter(row=>previousIds.has(row.id)),rows,'Upgrade preserved every previous audit entry');
   // Descriptive plan backfills have their own audit entries. They must never
   // rewrite historical entries or invent a financial payment event.
   eq(actual.filter(row=>!previousIds.has(row.id)).every(row=>row.action==='PLAN_EDITADO'&&row.entity_type==='plans'&&row.actor_user_id===null),true);
  }else eq(actual,rows,'Upgrade preserved historical fields in '+table);
 }
 await user(A);
 const population=await rpc('membership_population',{p_gym_id:gym});
 eq(population.metrics.active_clients,3);
 eq(population.metrics.valid_memberships,2);
 eq(population.metrics.expired_memberships,1);
 eq(population.metrics.checkins_today,2);
 eq(population.metrics.internal_memberships,0,'No STAFF plan or member is invented by an upgrade');
 eq((await rpc('reception_list_clients',{p_gym_id:gym,p_search:''})).length,clients.length);
 await system();
 const upgradedRows=await rowSnapshot(),upgradedColumns=await columnSnapshot();
 await db.exec(upgrade);
 eq(await rowSnapshot(),upgradedRows,'Reapplying the same combined upgrade preserves every row, payment, audit and freeze');
 eq(await columnSnapshot(),upgradedColumns,'Reapplying adds no duplicate columns or tables');
 await user(A);
 eq(await rpc('membership_population',{p_gym_id:gym}),population,'Reapplying retains the same server membership state');
 console.log(`DASHBOARD UPGRADE ${checks} CHECKS PASS (${f.commercial?'Commercial':'ZTATTUZ'}): missing RPC, read-only diagnosis, atomic preflight, legacy history, idempotent combined upgrade and server metrics.`);
}finally{await db.close();}
