import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fixture} from './membership_feature_fixture.mjs';
const f=await fixture();const {db,gym,other,A,O,R,B,user,system,rpc,tableRpc,insert,person,monthly,snapshot,enter}=f;
let checks=0;
const eq=(a,b,label)=>{assert.deepEqual(a,b,label);checks++;};
const reject=async work=>{await assert.rejects(work);checks++;};
try{
 eq((await db.query("select count(*)::int n from public.plans where plan_type='INTERNAL'")).rows[0].n,0,'Internal plans are optional, never pre-created');
 const ordinary=await monthly();const before=await rpc('get_finance_dashboard',{p_gym_id:gym,p_date_from:'2026-10-01',p_date_to:'2026-10-31'});
 eq(before.payment_count,1);eq(Number(before.average_payment),70000);
 const make=async(name,overrides={})=>rpc('save_membership_plan',{p_gym_id:gym,p_reason:'Plan interno autorizado',p_data:{name,plan_type:'INTERNAL',duration_days:null,duration_months:null,price:0,entry_limit:null,unlimited_access:true,has_expiration:false,include_in_financial_stats:false,...overrides}});
 const staff=await make('STAFF');const trainer=await make('Entrenador especial');eq(staff.plan_type,'INTERNAL');eq(trainer.name,'Entrenador especial');
 eq([staff.duration_days,staff.duration_months,staff.entry_limit],[null,null,null]);
 eq([staff.price,staff.unlimited_access,staff.has_expiration,staff.include_in_financial_stats],[0,true,false,false]);
 const c=await person(),key=randomUUID();
 const assign=()=>tableRpc('assign_internal_membership',{p_gym_id:gym,p_client_id:c,p_plan_id:staff.id,p_request_id:key,p_start_date:'2026-10-20',p_notes:'Personal autorizado'});
 const [m]=await assign();eq(m.end_date,null);eq((await assign())[0].membership_id,m.membership_id,'Stable assignment reference is idempotent');
 const row=(await db.query('select * from public.memberships where id=$1',[m.membership_id])).rows[0];
 eq([row.end_date,row.paid_at,row.payment_status,row.amount,row.amount_paid,row.payment_method],[null,null,'non_commercial',0,0,'']);
 await reject(()=>db.query('update public.memberships set assignment_request_id=$1 where id=$2',[randomUUID(),m.membership_id]));
 const s=await snapshot(c);eq([s.status,s.allowed,s.unlimited_access,s.has_expiration,s.entries_remaining],['ACTIVE',true,true,false,null]);
 for(const method of ['HUELLA BIOMÉTRICA','CÓDIGO','MANUAL','RECEPCIÓN']){
  const visit=await enter(c,false,method);eq(visit.result,'PERMITIDA');eq(visit.ticket_consumed,false);eq(visit.entries_remaining,null);
 }
 eq((await db.query('select count(*)::int n from public.checkins where client_id=$1',[c])).rows[0].n,4,'Every attendance is recorded');
 eq((await db.query('select count(*)::int n from public.ticket_daily_consumptions where client_id=$1',[c])).rows[0].n,0,'Unlimited access does not consume tickets');
 const after=await rpc('get_finance_dashboard',{p_gym_id:gym,p_date_from:'2026-10-01',p_date_to:'2026-10-31'});
 eq(after,before,'Internal $0 assignment affects no financial field or average');
 const payName=f.commercial?'gymsoft_client_payments':'ztattuz_client_payments';
 const history=await rpc(payName,{p_gym_id:gym,p_client_id:c,p_include_void:true,p_offset:0,p_limit:50});
 eq(Array.isArray(history)?history.length:history.rows?.length??history.payments?.length??history.items?.length,0,'No payment row in the cashier history');
 const population=await rpc('membership_population',{p_gym_id:gym});eq(population.metrics.internal_memberships,1);eq(population.groups.expired.some(x=>x.id===c),false);eq(population.groups.internal.some(x=>x.id===c),true);eq(population.metrics.staff_checkins_today,4);eq(population.metrics.checkins_today,0);
 const chart=await rpc('get_attendance_statistics',{p_gym_id:gym,p_days:30});eq(Number(chart.metrics.today_entries),0,'Staff visits never inflate commercial charts');
 await reject(()=>rpc('membership_freeze',{p_gym_id:gym,p_membership_id:m.membership_id,p_request_id:randomUUID()}));
 await rpc('set_internal_membership_active',{p_gym_id:gym,p_membership_id:m.membership_id,p_active:false,p_reason:'Fin de autorización'});
 eq((await snapshot(c)).status,'INACTIVE');eq((await enter(c)).result,'DENEGADA');eq((await enter(c,true)).result,'DENEGADA','Override cannot bypass a deactivated internal membership');
 await rpc('set_internal_membership_active',{p_gym_id:gym,p_membership_id:m.membership_id,p_active:true,p_reason:'Autorización renovada'});eq((await enter(c)).result,'PERMITIDA');
 await reject(()=>rpc('save_membership_plan',{p_gym_id:gym,p_reason:'Inválido',p_data:{name:'Mal',plan_type:'INTERNAL',price:5000,duration_days:null,has_expiration:false,include_in_financial_stats:false}}));
 await reject(()=>db.query("update public.plans set plan_type='COMMERCIAL',has_expiration=true,duration_days=30 where id=$1",[staff.id]));
 await user(R);await reject(make.bind(null,'No permitido'));
 await reject(()=>tableRpc('assign_internal_membership',{p_gym_id:gym,p_client_id:c,p_plan_id:staff.id,p_request_id:randomUUID()}));
 await reject(()=>rpc('set_internal_membership_active',{p_gym_id:gym,p_membership_id:m.membership_id,p_active:false,p_reason:'No permitido'}));
 await user(B);await reject(()=>rpc('membership_population',{p_gym_id:gym}));await reject(()=>rpc('save_membership_plan',{p_gym_id:gym,p_data:{name:'Cruce'},p_reason:'Otro gimnasio'}));
 await user(A);
 const logs=await rpc('get_audit_logs',{p_gym_id:gym});
 for(const action of ['INTERNAL_PLAN_CREATED','INTERNAL_MEMBERSHIP_ASSIGNED','INTERNAL_MEMBERSHIP_DEACTIVATED','INTERNAL_MEMBERSHIP_ACTIVATED']){
  const log=logs.find(x=>x.action===action);assert.ok(log,action);checks++;eq(log.actor_user_id,A);assert.ok(log.created_at);checks++;
 }
 eq(logs.some(x=>x.action==='PAGO_REGISTRADO'&&String(x.entity_id)===String(m.membership_id)),false);
 if(f.commercial){await user(O);eq((await make('Propietario')).name,'Propietario');await user(A);}
 const finite=await make('Invitado por días',{has_expiration:true,duration_days:3});const cp=await person();
 const [fm]=await tableRpc('assign_internal_membership',{p_gym_id:gym,p_client_id:cp,p_plan_id:finite.id,p_request_id:randomUUID()});
 eq(new Date(fm.end_date).toISOString().slice(0,10),'2026-10-22');eq((await enter(cp)).result,'PERMITIDA');
 const limited=await make('Colaborador limitado',{unlimited_access:false,entry_limit:2});const lc=await person();
 await tableRpc('assign_internal_membership',{p_gym_id:gym,p_client_id:lc,p_plan_id:limited.id,p_request_id:randomUUID()});
 eq((await enter(lc)).entries_remaining,1);eq((await enter(lc)).entries_remaining,1,'Limited internal visits retain daily consumption policy');
 const ticket=await monthly({ticket:2});eq((await enter(ticket.c)).entries_remaining,1);eq((await enter(ticket.c)).entries_remaining,1);eq((await enter(ordinary.c)).result,'PERMITIDA');
 await system();
 // Service API cannot create a Wompi request for an internal person, even selecting a commercial plan.
 await reject(()=>rpc('marketing_service_payment_request',{p_gym_id:gym,p_client_id:c,p_plan_id:ordinary.p,p_key:'internal-no-wompi'}));
 await reject(()=>rpc('marketing_service_payment_request',{p_gym_id:gym,p_client_id:c,p_plan_id:staff.id,p_key:'internal-no-wompi-plan'}));
 eq((await db.query('select count(*)::int n from public.payment_requests')).rows[0].n,0);
 eq((await db.query('select count(*)::int n from public.payment_transactions')).rows[0].n,0);
 eq((await db.query("select count(*)::int n from private.marketing_events where client_id=$1 and event_type='MEMBERSHIP_RENEWED'",[c])).rows[0].n,0);
 // Direct service callers are subject to the same no-billing rule as the JavaScript worker.
 await user(A);await rpc('marketing_set_consent',{p_gym_id:gym,p_client_id:c,p_enabled:true,p_source:'Prueba local'});
 const tmpl=await rpc('marketing_save_template',{p_gym_id:gym,p_data:{name:'staff_test',body:'Hola {{nombre}}',variables:['nombre']}});
 await system();await db.query("update public.whatsapp_templates set status='APPROVED' where id=$1",[tmpl.id]);
 await db.query("insert into public.marketing_connections(gym_id,provider,status,mode) values($1,'META','CONNECTED','test')",[gym]);
 await user(A);await rpc('marketing_features',{p_gym_id:gym,p_flags:{whatsapp_enabled:true,marketing_automation_enabled:true}});
 const automation=await rpc('marketing_save_automation',{p_gym_id:gym,p_data:{name:'No cobros para STAFF',body:'Hola {{nombre}}',trigger_type:'MEMBERSHIP_RENEWED',trigger_options:{},conditions:[],frequency:{count:1,hours:24},template_id:tmpl.id}});
 const rule=await rpc('marketing_automation_action',{p_gym_id:gym,p_id:automation.id,p_revision:automation.revision,p_action:'enable'});
 await system();const blocked=await rpc('marketing_service_enqueue',{p_gym_id:gym,p_automation_id:rule.id,p_client_id:c,p_dedupe_key:'no-staff-reminder',p_phone:'573001234567',p_body:'Hola personal',p_parameters:['Personal']});
 eq([blocked.status,blocked.reason],['SKIPPED','INTERNAL_MEMBERSHIP']);
 const claim=randomUUID();await db.query("update public.marketing_messages set status='PROCESSING',claim_id=$1,claimed_at=now() where id=$2",[claim,blocked.message_id]);
 eq((await rpc('marketing_service_send_guard',{p_id:blocked.message_id,p_claim:claim})).allowed,false,'A stale queued bill cannot reach the provider');
 // A payment accepted before changing to STAFF remains a charge to review, never an automatic renewal.
 const req=(await db.query("insert into public.payment_requests(gym_id,client_id,plan_id,plan_snapshot,amount_in_cents,currency,mode,reference,idempotency_key,status,expires_at) values($1,$2,$3,'{}',7000000,'COP','test','STAFF-OLD-CHARGE','old-staff-charge','VOIDED',now()+interval '1 day') returning *",[gym,c,ordinary.p])).rows[0];
 const tx={id:'staff-old-confirmed-charge',reference:req.reference,status:'APPROVED',amount_in_cents:7000000,currency:'COP',mode:'test',created_at:new Date(req.created_at).toISOString()};
 const review=await rpc('marketing_service_apply_payment',{p_gym_id:gym,p_transaction:tx});eq(review.requires_review,true);eq(review.membership_id,undefined);
 eq((await db.query('select count(*)::int n from public.memberships where client_id=$1',[c])).rows[0].n,1);
 eq((await db.query("select requires_review from public.payment_transactions where provider_transaction_id='staff-old-confirmed-charge'")).rows[0].requires_review,true);
 await user(A);
 await f.clock('2026-10-23T14:00:00Z');eq((await enter(cp)).result,'DENEGADA');eq((await enter(c)).result,'PERMITIDA','Unlimited indefinite access still works in later months');
 // New migrations can be reapplied without creating Staff, rewriting history or changing balances.
 const backup=await rpc('ticket_backup_memberships',{p_gym_id:gym});eq(backup.find(x=>x.id===m.membership_id).membership_type,'INTERNAL');eq(backup.find(x=>x.id===m.membership_id).end_date,null);
 await f.clock('2030-10-20T14:00:00Z');eq((await enter(c)).result,'PERMITIDA','No artificial end date is required even years later');
 const beforeRerun=(await db.query('select * from public.memberships order by id')).rows;
 for(const file of ['ACTUALIZAR_PLANES_INTERNOS.sql','ACTUALIZAR_REANUDACION_MEMBRESIAS.sql']){await system();await db.exec(fs.readFileSync(path.join(f.root,file),'utf8'));}
 eq((await db.query('select * from public.memberships order by id')).rows,beforeRerun);
 console.log(`INTERNAL MEMBERSHIPS ${checks} CHECKS PASS (${f.commercial?'Commercial':'ZTATTUZ'})`);
}finally{await db.close();}
