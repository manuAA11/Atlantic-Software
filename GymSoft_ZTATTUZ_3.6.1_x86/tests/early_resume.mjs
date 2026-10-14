import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fixture} from './membership_feature_fixture.mjs';
let checks=0;
const eq=(a,b,message)=>{assert.deepEqual(a,b,message);checks++;};
const deny=async work=>{await assert.rejects(work);checks++;};
const iso=value=>new Date(value).toISOString();
const f=await fixture();
const {db,gym,A,O,R,B,user,system,rpc,insert,monthly,snapshot,enter,clock}=f;
const freeze=m=>rpc('membership_freeze',{p_gym_id:gym,p_membership_id:m,p_request_id:randomUUID(),p_reason:'Solicitud autorizada'});
const preview=id=>rpc('membership_resume_preview',{p_gym_id:gym,p_freeze_id:id});
const resume=(id,days)=>rpc('membership_resume_freeze',{p_gym_id:gym,p_freeze_id:id,p_expected_days:days,p_reason:'Cliente solicita reanudar'});
const dates=async m=>(await db.query('select start_date::text,end_date::text from public.memberships where id=$1',[m])).rows[0];
try{
 const base=await monthly(),income=await rpc('get_finance_dashboard',{p_gym_id:gym});
 const frozen=await freeze(base.m);
 eq([frozen.start_date,frozen.resume_date,frozen.days_added,frozen.new_end_date,frozen.freeze_used_days,frozen.freeze_max_days],['2026-10-20','2026-10-27',0,'2026-10-30',0,7]);
 eq(iso(frozen.starts_at),'2026-10-20T14:00:00.000Z');eq(iso(frozen.ends_at),'2026-10-27T14:00:00.000Z');
 eq((await dates(base.m)).end_date,'2026-10-30','No extension is applied on freeze creation');
 eq((await snapshot(base.c)).membership_state,'FROZEN');
 for(const method of ['HUELLA BIOMÉTRICA','CÓDIGO','MANUAL','RECEPCIÓN','RELÉ'])eq((await enter(base.c,true,method)).result,'DENEGADA');
 await clock('2026-10-22T14:00:00Z');const p=await preview(frozen.id);
 eq([p.extension_days,p.new_end_date,p.freeze_remaining_days],[2,'2026-11-01',5]);
 await deny(()=>resume(frozen.id,1));
 const closed=await resume(frozen.id,2);
 eq([closed.status,closed.days_added,closed.freeze_used_days,closed.new_end_date,closed.resumed_by,closed.completion_kind],['RESUMED',2,2,'2026-11-01',A,'MANUAL']);
 eq(iso(closed.resumed_at),'2026-10-22T14:00:00.000Z');eq((await dates(base.m)).end_date,'2026-11-01');
 eq((await enter(base.c)).result,'PERMITIDA');eq((await snapshot(base.c)).can_freeze,false);
 eq((await resume(frozen.id,2)).duplicate,true);eq((await dates(base.m)).end_date,'2026-11-01');
 await deny(()=>freeze(base.m));
 await deny(()=>rpc('membership_freeze',{p_gym_id:gym,p_membership_id:base.m,p_request_id:randomUUID(),p_override:true,p_reason:''}));
 eq((await rpc('get_finance_dashboard',{p_gym_id:gym})).total_income,income.total_income,'Resume causes no payment');
 const logs=await rpc('get_audit_logs',{p_gym_id:gym});
 const audit=logs.filter(x=>x.action==='MEMBERSHIP_FREEZE_RESUMED'&&String(x.entity_id)===String(base.m));eq(audit.length,1);eq(audit[0].actor_user_id,A);eq(audit[0].details.freeze_used_days,2);
 eq(logs.some(x=>x.action==='PAGO_EDITADO'&&String(x.entity_id)===String(base.m)),false,'Resume is audited as membership time, not a payment correction');
 // Less than 24 hours is zero even when the gym calendar changes day.
 await clock('2026-10-21T04:00:00Z');const overnight=await monthly();const on=await freeze(overnight.m);
 eq(on.start_date,'2026-10-20');await clock('2026-10-21T13:00:00Z');eq((await preview(on.id)).extension_days,0);
 eq((await resume(on.id,0)).new_end_date,'2026-10-30');eq((await enter(overnight.c)).result,'PERMITIDA');
 // Same-day and partial-day rounding: 23:59:59 is zero; exactly 48 hours is two.
 await clock('2026-10-20T14:00:00Z');const partial=await monthly(),pf=await freeze(partial.m);
 await clock('2026-10-21T13:59:59Z');eq((await preview(pf.id)).extension_days,0);
 await clock('2026-10-22T13:59:59Z');eq((await preview(pf.id)).extension_days,1);
 await clock('2026-10-22T14:00:00Z');eq((await resume(pf.id,2)).days_added,2);
 // Future purchased cycles shift only by the real duration when the event closes.
 await clock('2026-10-20T14:00:00Z');const future=await monthly(),ff=await freeze(future.m);
 const next=await insert('memberships',{gym_id:gym,client_id:future.c,plan_id:future.p,start_date:'2026-10-31',end_date:'2026-11-29',amount:70000,amount_paid:70000,payment_method:'Efectivo'});
 eq(await dates(next),{start_date:'2026-10-31',end_date:'2026-11-29'});
 await clock('2026-10-22T14:00:00Z');await resume(ff.id,2);eq(await dates(next),{start_date:'2026-11-02',end_date:'2026-12-01'});
 await resume(ff.id,2);eq((await dates(next)).start_date,'2026-11-02');
 // Tickets retain existing consumption and the once-per-local-day ledger.
 await clock('2026-10-20T14:00:00Z');const tickets=await monthly({ticket:10});eq((await enter(tickets.c)).entries_remaining,9);
 const tf=await freeze(tickets.m);eq((await enter(tickets.c)).result,'DENEGADA');
 eq((await snapshot(tickets.c)).entries_remaining,9);await clock('2026-10-22T14:00:00Z');await resume(tf.id,2);
 eq((await enter(tickets.c)).entries_remaining,8);eq((await enter(tickets.c)).entries_remaining,8);eq((await dates(tickets.m)).end_date,'2026-11-01');
 // Late schedulers cap extension at seven days and record the true deadline.
 await clock('2026-10-20T14:00:00Z');const automatic=await monthly(),af=await freeze(automatic.m);
 await clock('2026-10-27T13:59:59Z');eq((await enter(automatic.c)).result,'DENEGADA');
 await clock('2026-10-29T14:00:00Z');await system();assert.ok(await rpc('membership_service_complete_freezes')>=1);checks++;eq(await rpc('membership_service_complete_freezes'),0);
 await user(A);const auto=(await rpc('membership_freeze_info',{p_gym_id:gym,p_client_id:automatic.c})).history[0];
 eq([auto.status,auto.freeze_used_days,auto.completion_kind,auto.resumed_by,auto.extended_end_date],['COMPLETED',7,'AUTOMATIC',null,'2026-11-06']);eq(iso(auto.resumed_at),'2026-10-27T14:00:00.000Z');
 eq((await resume(af.id,7)).duplicate,true);eq((await dates(automatic.m)).end_date,'2026-11-06');eq((await enter(automatic.c)).result,'PERMITIDA');
 // A snapshot closes an overdue event before an old expiry can classify it as a debtor.
 await clock('2026-10-20T14:00:00Z');const soon=await monthly({end:'2026-10-21'}),sf=await freeze(soon.m);
 await clock('2026-10-24T14:00:00Z');const population=await rpc('membership_population',{p_gym_id:gym});eq(population.groups.expired.some(x=>x.client_id===soon.c),false);eq(population.groups.frozen.some(x=>x.client_id===soon.c),true);
 await clock('2026-10-27T14:00:00Z');eq((await snapshot(soon.c)).allowed,true);eq((await dates(soon.m)).end_date,'2026-10-28');
 // Permissions, RLS, explicit exceptions and no double completion.
 await clock('2026-10-20T14:00:00Z');const permissions=await monthly(),perm=await freeze(permissions.m);
 await user(R);eq((await rpc('membership_freeze_info',{p_gym_id:gym,p_client_id:permissions.c})).permissions.can_resume,false);await deny(()=>preview(perm.id));await deny(()=>resume(perm.id,0));
 await user(B);await deny(()=>preview(perm.id));eq((await db.query('select count(*)::int n from public.membership_freezes where gym_id=$1',[gym])).rows[0].n,0);
 await user(A);await resume(perm.id,0);const exceptional=await rpc('membership_freeze',{p_gym_id:gym,p_membership_id:permissions.m,p_request_id:randomUUID(),p_override:true,p_reason:'Excepción administrativa justificada'});eq(exceptional.administrative_override,true);
 await deny(()=>rpc('membership_save_freeze_policy',{p_gym_id:gym,p_enabled:true,p_duration_days:8,p_max_per_membership:1}));await deny(()=>rpc('membership_save_freeze_policy',{p_gym_id:gym,p_enabled:true,p_duration_days:7,p_max_per_membership:2}));
 if(f.commercial){await user(O);eq((await preview(exceptional.id)).extension_days,0);await resume(exceptional.id,0);eq((await rpc('membership_save_freeze_policy',{p_gym_id:gym,p_enabled:true,p_duration_days:7,p_max_per_membership:1})).max_per_membership,1);await user(A);}
 if(!f.commercial)await resume(exceptional.id,0);
 // Requests share a PGlite connection: proves idempotence, not two-session PostgreSQL locking.
 await clock('2026-10-20T14:00:00Z');const racing=await monthly(),rf=await freeze(racing.m);await clock('2026-10-22T14:00:00Z');
 const results=await Promise.all([resume(rf.id,2),resume(rf.id,2)]);eq(results.filter(x=>!x.duplicate).length,1);eq((await dates(racing.m)).end_date,'2026-11-01');
 const archive=await rpc('ticket_backup_memberships',{p_gym_id:gym});const saved=archive.find(x=>x.id===base.m).freeze_archive[0];eq([saved.freeze_used_days,saved.resumed_by,saved.completion_kind],[2,A,'MANUAL']);
 // Actual elapsed days remain 24-hour days across the New York DST boundary.
 await system();await db.query("update public.gyms set timezone='America/New_York' where id=$1",[gym]);await user(A);
 await clock('2026-11-01T03:00:00Z');const dst=await monthly({start:'2026-10-01',end:'2026-11-30'}),df=await freeze(dst.m);
 eq(df.start_date,'2026-10-31');eq(iso(df.ends_at),'2026-11-08T03:00:00.000Z');await clock('2026-11-02T03:00:00Z');eq((await resume(df.id,1)).new_end_date,'2026-12-01');
 console.log(`EARLY RESUME ${checks} CHECKS PASS (${f.commercial?'Commercial':'ZTATTUZ'})`);
}finally{await db.close();}
// Upgrade populated old histories rather than silently reinterpret old pre-applied weeks.
const legacy=await fixture({features:false});
try{
 const m=await legacy.monthly();const old=await legacy.rpc('membership_freeze',{p_gym_id:legacy.gym,p_membership_id:m.m,p_request_id:randomUUID()});eq(old.days_added,7);
 await legacy.system();const columns=['id','starts_at','ends_at','original_end_date','extended_end_date','days_added','days_reversed','status'];
 const prior=(await legacy.db.query('select '+columns.join(',')+' from public.membership_freezes')).rows;
 for(const name of ['ACTUALIZAR_PLANES_INTERNOS.sql','ACTUALIZAR_REANUDACION_MEMBRESIAS.sql'])await legacy.db.exec(fs.readFileSync(path.join(legacy.root,name),'utf8'));
 eq((await legacy.db.query('select '+columns.join(',')+' from public.membership_freezes')).rows,prior,'Historical instants, dates, grants and identifiers survive upgrade');
 await legacy.clock('2026-10-22T14:00:00Z');const p=await legacy.rpc('membership_resume_preview',{p_gym_id:legacy.gym,p_freeze_id:old.id});eq(p.extension_days,2);
 const result=await legacy.rpc('membership_resume_freeze',{p_gym_id:legacy.gym,p_freeze_id:old.id,p_expected_days:2});eq(result.new_end_date,'2026-11-01');eq(result.days_reversed,5);
 console.log('LEGACY FREEZE UPGRADE PASS');
}finally{await legacy.db.close();}
