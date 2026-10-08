import {IntegrationError,verifyMeta,verifyWompi,sha256,normalizePhone} from './security.mjs';
import {canonicalTransaction} from './providers.mjs';
import {respond,incomingText} from './chatbot.mjs';
import {createPayment,dispatch} from './worker.mjs';
export async function wompiWebhook(db,gym,raw,signature,fetcher=fetch) {
 let event;try{event=JSON.parse(raw);}catch{throw new IntegrationError('INVALID_EVENT','Evento no válido.');}
 const keys=await db.credentials(gym,'WOMPI');
 if(!await verifyWompi(event,signature,keys?.events_secret))throw new IntegrationError('INVALID_SIGNATURE','Firma no válida.',403);
 if(event.timestamp*1000>Date.now()+300000)throw new IntegrationError('INVALID_EVENT','Fecha de evento no válida.');
 if(event.event!=='transaction.updated')return {received:true,ignored:true};
 const transaction=await canonicalTransaction(event.data?.transaction?.id,keys,fetcher);
 const eventKey=await sha256(gym+'/'+transaction.id+'/'+event.signature.checksum);
 const pending=await db.rpc('marketing_service_receipt',{p_provider:'WOMPI',p_key:eventKey,p_gym_id:gym,p_payload:{transaction_id:transaction.id,status:transaction.status}});
 if(!pending)return {received:true,duplicate:true};
 const result=await db.rpc('marketing_service_apply_payment',{p_gym_id:gym,p_transaction:transaction});
 await db.rpc('marketing_service_receipt',{p_provider:'WOMPI',p_key:eventKey,p_gym_id:gym,p_payload:{},p_done:true});
 const connection=await db.connection(gym,'WOMPI');
 await db.patch('marketing_connections',{gym_id:'eq.'+gym,provider:'eq.WOMPI'},{status:'CONNECTED',last_checked_at:new Date().toISOString(),last_error:'',metadata:{...(connection.metadata||{}),webhook_confirmed:true,private_key_verified:true,events_verified:true,integrity_verified:true}});
 return {received:true,...result};
}
export async function metaWebhook(db,baseURL,raw,signature,fetcher=fetch) {
 const platform=await db.rpc('marketing_service_platform');
 if(!await verifyMeta(raw,signature,platform?.app_secret))throw new IntegrationError('INVALID_SIGNATURE','Firma no válida.',403);
 let payload;try{payload=JSON.parse(raw);}catch{throw new IntegrationError('INVALID_EVENT','Evento no válido.');}
 if(payload.object!=='whatsapp_business_account')return {received:true,ignored:true};
 for(const entry of payload.entry||[])for(const change of entry.changes||[]){
  const v=change.value||{};const phone=v.metadata?.phone_number_id;
  const connections=await db.read('marketing_connections',{provider:'eq.META',provider_account_id:'eq.'+entry.id,...(phone?{phone_number_id:'eq.'+phone}:{})});
  for(const conn of connections){const gym=conn.gym_id;
  // Shared WABA template/account events belong to every connected phone; inbound
  // messages must have a unique phone-number destination.
  if(!phone&&['messages','smb_message_echoes'].includes(change.field))continue;
  if(change.field==='account_update'&&['PARTNER_REMOVED','ACCOUNT_DELETED','ACCOUNT_DISABLED'].includes(v.event)){
   await db.patch('marketing_connections',{gym_id:'eq.'+gym,provider:'eq.META'},{status:'ATTENTION',last_error:'La autorización de Meta requiere atención.'});
   await db.patch('marketing_settings',{gym_id:'eq.'+gym},{whatsapp_enabled:false,chatbot_enabled:false,marketing_automation_enabled:false});continue;
  }
  if(change.field==='message_template_status_update'){
   const status=String(v.event||'').toUpperCase();if(['APPROVED','REJECTED','PAUSED','DISABLED'].includes(status))await db.patch('whatsapp_templates',{gym_id:'eq.'+gym,provider_id:'eq.'+v.message_template_id},{status,rejection_reason:status==='REJECTED'?String(v.reason||'Rechazada por Meta').slice(0,500):null,updated_at:new Date().toISOString()});continue;
  }
  // Synchronization/history webhooks are never treated as fresh customer messages.
  if(change.field==='smb_message_echoes'){
   for(const m of v.message_echoes||[]){const sender=normalizePhone(m.to);if(!sender)continue;
    await db.rpc('marketing_service_chat',{p_gym_id:gym,p_sender:sender,p_action:'human_echo'});
    await db.rpc('marketing_service_inbound_record',{p_gym_id:gym,p_sender:sender,p_message_id:m.id,p_body:incomingText(m),p_human:true});
   }continue;
  }
  if(change.field!=='messages')continue;
  for(const s of v.statuses||[]){const at=Number(s.timestamp)*1000;if(!Number.isFinite(at))continue;await db.rpc('marketing_service_status',{p_gym_id:gym,p_message_id:s.id,p_status:String(s.status).toUpperCase(),p_at:new Date(at).toISOString()});}
  for(const m of v.messages||[]){
   const sender=normalizePhone(m.from);if(!sender||!m.id)continue;
   const sentAt=Number(m.timestamp)*1000;
   if(!Number.isFinite(sentAt)||sentAt>Date.now()+300000||sentAt<Date.now()-24*3600000)continue;
   const key=await sha256(gym+'/'+m.id);
   const pending=await db.rpc('marketing_service_receipt',{p_provider:'META',p_key:key,p_gym_id:gym,p_payload:{message_id:m.id}});if(!pending)continue;
   if(!await db.rpc('marketing_service_limit',{p_gym_id:gym,p_bucket:'inbound/'+sender,p_max:30,p_seconds:60}))continue;
   await db.rpc('marketing_service_inbound_record',{p_gym_id:gym,p_sender:sender,p_message_id:m.id,p_body:incomingText(m)});
   const paymentLink=async(client,id)=>{
    const connection=await db.connection(gym,'WOMPI');
    const settings=(await db.read('marketing_settings',{gym_id:'eq.'+gym,limit:'1'}))[0];
    if(!connection||connection.status!=='CONNECTED'||!settings?.online_payments_enabled)throw new IntegrationError('NOT_CONFIGURED','Pagos online no habilitados.');
    const context=await db.context(gym,client);if(!context?.plan?.id)throw new IntegrationError('NO_PLAN','Recepción debe asignarte un plan primero.');
    return (await createPayment(db,baseURL,gym,client,context.plan.id,'chatbot/'+id)).url;
   };
   const result=await respond({rpc:(n,a)=>db.rpc(n,a),paymentLink,gym:await db.rpc('marketing_service_gym',{p_gym_id:gym}),sender,message:m});
   if(result)await db.rpc('marketing_service_queue_reply',{p_gym_id:gym,p_sender:sender,p_key:'reply/'+m.id,p_content:result});
   await db.rpc('marketing_service_receipt',{p_provider:'META',p_key:key,p_gym_id:gym,p_payload:{},p_done:true});
  }
 }
 }
 // Queue is durable before dispatch; failed/ambiguous sends do not rerun the chatbot.
 await dispatch(db,{limit:10,fetcher});return {received:true};
}
