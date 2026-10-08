import {IntegrationError} from './security.mjs';
import {evaluate,variablesFor,renderMessage} from './automation.mjs';
import {checkoutURL,sendTemplate,sendSessionMessage} from './providers.mjs';
export async function createPayment(db,baseURL,gym,client,plan,key) {
 const request=await db.rpc('marketing_service_payment_request',{p_gym_id:gym,p_client_id:client,p_plan_id:plan,p_key:key});
 if(request.status!=='PENDING')throw new IntegrationError('PAYMENT_CLOSED','Esta solicitud ya fue atendida.');
 const keys=await db.credentials(gym,'WOMPI');if(!keys)throw new IntegrationError('NOT_CONFIGURED','Los pagos online todavía no están habilitados.');
 const url=await checkoutURL(request,keys);await db.rpc('marketing_service_payment_link',{p_gym_id:gym,p_id:request.id,p_url:url});
 return {request_id:request.id,reference:request.reference,url:`${baseURL}/pay/${encodeURIComponent(request.reference)}`,mode:request.mode};
}
async function processRule(db,baseURL,rule,context,event=null) {
 const match=evaluate(rule,context,event);if(!match)return;
 let payment=null;
 if(rule.include_payment_link){
  if(!context.plan?.id)return;
  payment=await createPayment(db,baseURL,context.gym_id,context.client_id,context.plan.id,'automation/'+match.key);
 }
 const variables=variablesFor(context,payment?.url||'');
 const templates=await db.read('whatsapp_templates',{id:'eq.'+rule.template_id,gym_id:'eq.'+context.gym_id,limit:'1'});
 const template=templates[0];if(!template||template.status!=='APPROVED')return;
 await db.rpc('marketing_service_enqueue',{p_gym_id:context.gym_id,p_automation_id:rule.id,p_client_id:context.client_id,p_dedupe_key:match.key,p_phone:match.phone,p_body:renderMessage(rule.body,variables),p_parameters:template.variables.map(v=>variables[v]||''),p_payment_request_id:payment?.request_id||null});
}
export async function runJobs(db,baseURL,{budgetMs=45000,now=()=>Date.now()}={}) {
 await db.rpc('membership_service_complete_freezes');
 const deadline=now()+budgetMs;const jobs=await db.rpc('marketing_service_jobs',{p_limit:5});let processed=0;
 for(const job of jobs) {
  let cursor=job.cursor_client||0,error='';
  try {
   const rules=await db.read('marketing_automations',{gym_id:'eq.'+job.gym_id,enabled:'eq.true',deleted_at:'is.null'});
   const events=await db.rpc('marketing_service_event_batch',{p_gym_id:job.gym_id,p_limit:30});
   for(const event of events) {
    if(now()>deadline)break;
    const c=await db.context(job.gym_id,event.client_id);
    if(c)for(const rule of rules)await processRule(db,baseURL,rule,c,event);
    await db.rpc('marketing_service_event_done',{p_gym_id:job.gym_id,p_ids:[event.id]});processed++;
   }
   const clients=await db.rpc('marketing_service_contexts',{p_gym_id:job.gym_id,p_after:cursor,p_limit:100});
   for(const c of clients){if(now()>deadline)break;for(const rule of rules)await processRule(db,baseURL,rule,c);cursor=c.client_id;processed++;}
   if(clients.length<100 && (!clients.length || cursor===clients.at(-1).client_id))cursor=0;
   // Pending/unopened payment rules use hourly stable keys and the same frequency guard.
   const pending=await db.read('payment_requests',{gym_id:'eq.'+job.gym_id,status:'eq.PENDING',order:'created_at.asc',limit:'100'});
   for(const p of pending){
    if(now()>deadline)break;const age=Math.floor((now()-Date.parse(p.created_at))/3600000);if(age<1)continue;
    const c=await db.context(job.gym_id,p.client_id);if(!c)continue;
    for(const type of ['PAYMENT_PENDING',...(!p.opened_at?['UNUSED_PAYMENT_LINK']:[])]) {
     const event={id:`${p.id}/${type}/${age}`,event_type:type,payload:{age_hours:age,status:p.status,payment_request_id:p.id}};
     for(const rule of rules)if(rule.trigger_type===type)await processRule(db,baseURL,rule,c,event);
    }
   }
  }catch(e){error=e.code||'AUTOMATION_FAILED';}
  finally{await db.rpc('marketing_service_job_done',{p_gym_id:job.gym_id,p_lease:job.lease_id,p_cursor:cursor,p_error:error});}
 }
 return {processed};
}
export async function dispatch(db,{limit=20,messageId=null,fetcher=fetch}={}) {
 const messages=await db.rpc('marketing_service_claim',{p_limit:limit,...(messageId?{p_message_id:messageId}:{})});let sent=0;
 for(const m of messages){let status='FAILED',provider='',error='';
  try {
   const guard=await db.rpc('marketing_service_send_guard',{p_id:m.id,p_claim:m.claim_id});
   if(!guard.allowed){status=guard.reason==='NO_CONSENT'?'NO_CONSENT':'SKIPPED';error=guard.reason;}
   else {
    const conn=await db.connection(m.gym_id,'META');const secret=await db.credentials(m.gym_id,'META');
    if(!conn||conn.status!=='CONNECTED'||!secret)throw new IntegrationError('DISCONNECTED','WhatsApp no está conectado.');
    const result=['CHATBOT','HANDOFF_ACK'].includes(m.automation_type)?await sendSessionMessage(conn,secret,m.phone,m.message_payload,guard.last_inbound_at,Date.now(),fetcher):await sendTemplate(conn,secret,m,fetcher);
    provider=result.messages?.[0]?.id||'';
    if(!provider)throw new IntegrationError('PROVIDER_UNCERTAIN','No se pudo confirmar el envío.');
    status='SENT';sent++;
   }
  }catch(e){status=e.code==='PROVIDER_UNCERTAIN'?'UNCERTAIN':'FAILED';error=e.code||'SEND_FAILED';}
  await db.rpc('marketing_service_send_result',{p_id:m.id,p_claim_id:m.claim_id,p_status:status,p_provider_id:provider,p_error:error});
 }
 return {sent};
}
