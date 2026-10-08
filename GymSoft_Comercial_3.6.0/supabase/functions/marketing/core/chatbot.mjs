import {cleanText} from './security.mjs';
export const textMessage=body=>({type:'text',text:{body:cleanText(body)}});
export function menu(gym) {return {type:'interactive',interactive:{type:'list',body:{text:`Hola 👋 Soy el asistente virtual de ${cleanText(gym,120)}. ¿En qué puedo ayudarte?`},action:{button:'Ver opciones',sections:[{title:'Tu gimnasio',rows:[{id:'membership',title:'Mi membresía'},{id:'renew',title:'Renovar'},{id:'entries',title:'Mis entradas'},{id:'reception',title:'Hablar con recepción'}]}]}}};}
export function parseBirthDate(text) {
 const m=String(text).trim().match(/^(\d{2})[/-](\d{2})[/-](\d{4})$/);if(!m)return null;
 const iso=`${m[3]}-${m[2]}-${m[1]}`;const date=new Date(iso+'T12:00:00Z');
 return Number(m[3])>=1900&&Number.isFinite(+date)&&date.toISOString().slice(0,10)===iso&&+date<Date.now()?iso:null;
}
export function incomingText(message) {return cleanText(message?.interactive?.list_reply?.id||message?.interactive?.button_reply?.id||message?.button?.payload||message?.text?.body||'',1000);}
export function command(value) {
 const t=value.trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
 if(['reception','recepcion','humano','hablar con recepcion'].includes(t))return 'reception';
 if(['membership','mi membresia','membresia'].includes(t))return 'membership';
 if(['entries','mis entradas','entradas'].includes(t))return 'entries';
 if(['renew','renovar'].includes(t))return 'renew';
 if(['pay','pagar','pagar ahora'].includes(t))return 'pay';
 return 'menu';
}
export async function respond({rpc,paymentLink,gym,sender,message}) {
 const raw=incomingText(message),action=command(raw);const args={p_gym_id:gym.id,p_sender:sender};
 // Record the inbound window before handoff; existing human conversations stay silent.
 let session=await rpc('marketing_service_chat',{...args,p_action:'inbound'});
 if(['DISABLED','HUMAN','PAUSED'].includes(session.state))return null;
 if(action==='reception') {await rpc('marketing_service_chat',{...args,p_action:'handoff'});return {...textMessage('Te comunicaremos con recepción. El asistente quedará en pausa.'),_handoff_ack:true};}
 if(session.state==='LOCKED')return textMessage('Por seguridad, la verificación está pausada. Contacta con recepción o inténtalo más tarde.');
 const dob=parseBirthDate(raw);
 if(dob&&session.state!=='VERIFIED')session=await rpc('marketing_service_chat',{...args,p_action:'verify',p_data:{birth_date:dob}});
 if(session.state==='VERIFICATION_FAILED')return textMessage('No pudimos verificar esos datos. Revisa tu fecha de nacimiento o escribe RECEPCIÓN.');
 if(session.state==='NEED_LINK_DETAILS') {
   const match=raw.match(/^(.{2,120})\s*[,;]\s*(\d{2}[/-]\d{2}[/-]\d{4})$/);
   if(match&&parseBirthDate(match[2])) {
    const link=await rpc('marketing_service_chat',{...args,p_action:'request_link',p_data:{name:match[1].trim(),birth_date:parseBirthDate(match[2])}});
    if(link.state==='LOCKED')return textMessage('Ya se alcanzó el límite de solicitudes. Contacta con recepción.');
    return textMessage('Recepción revisará tu solicitud de vinculación. Tu información permanecerá protegida hasta que la aprueben.');
   }
   return textMessage('Para vincular este número, envía tu nombre y fecha de nacimiento separados por una coma (Nombre, DD/MM/AAAA). Recepción deberá confirmar tu identidad antes de que puedas consultar tus datos.');
 }
 if(session.state==='LINK_PENDING')return textMessage('Tu solicitud está pendiente de recepción.');
 if(session.state!=='VERIFIED') {
   if(action==='menu'&&!dob)return menu(gym.name);
   return textMessage('Para proteger tu información, confirma tu fecha de nacimiento en formato DD/MM/AAAA.');
 }
 const m=session.membership||{};
 if(action==='pay') {
   try {return textMessage('Renueva de forma segura aquí:\n'+await paymentLink(session.client_id,message.id));}
   catch(e){if(e.code==='NOT_CONFIGURED'){await rpc('marketing_service_chat',{...args,p_action:'handoff'});return {...textMessage('Los pagos online todavía no están habilitados. Te comunicaremos con recepción.'),_handoff_ack:true};}throw e;}
 }
 if(action==='renew')return {type:'interactive',interactive:{type:'button',body:{text:`Tu plan actual: ${m.plan_name||'Sin plan'}. El importe exacto aparecerá antes de confirmar el pago.`},action:{buttons:[{type:'reply',reply:{id:'pay',title:'Pagar ahora'}},{type:'reply',reply:{id:'reception',title:'Recepción'}}]}}};
 if(action==='membership'||action==='entries'||dob){
  const frozen=m.frozen===true||m.status==='FROZEN';
  const dates=frozen?`\nCongelada hasta: ${m.freeze_last_date}\nSe reactiva: ${m.resume_date}\nNuevo vencimiento: ${m.end_date||m.membership_end}`:`\nVence: ${m.end_date||m.membership_end||'Sin plan'}`;
  return {type:'interactive',interactive:{type:'button',body:{text:`Hola ${session.first_name} 👋\nPlan: ${m.plan_name||'Sin plan'}\nEstado: ${frozen?'CONGELADA':m.status||'Sin plan'}${dates}${m.entry_limit!=null?'\nEntradas restantes: '+String(m.entries_remaining??0):''}`},action:{buttons:[{type:'reply',reply:{id:'renew',title:'Renovar'}},{type:'reply',reply:{id:'reception',title:'Recepción'}}]}}};
 }
 return menu(gym.name);
}
