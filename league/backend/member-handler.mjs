/** Additive League endpoint. Does not alter desktop, routines, payments or memberships. */
const fail=(message,status=400)=>Object.assign(new Error(message),{status});
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const actions=new Set(['push.config','snapshot','gym.calendar','gym.routines','gym.templates','gym.catalog','gym.profile','gym.reserve','gym.cancel','membership.details','renewals.list','renewals.create','renewals.cancel','notifications.list','notifications.read','push.subscribe','push.unsubscribe']);
const pushHosts=new Set(['fcm.googleapis.com','updates.push.services.mozilla.com','web.push.apple.com']);
export function validatePushEndpoint(value){
 try{const u=new URL(value);return value.length<=4096&&u.protocol==='https:'&&!u.username&&!u.password&&!u.port&&(pushHosts.has(u.hostname)||u.hostname.endsWith('.notify.windows.com'));}catch{return false;}
}
export function createLeagueMemberHandler({hub,leagueHandler,memberBridge,authorizeActor,pushPublicKey,allowedOrigins=[]}){
 return async request=>{
  const origin=request.headers.get('Origin');
  const headers={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Vary':'Origin',...(origin&&allowedOrigins.includes(origin)?{'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Headers':'authorization,content-type,apikey','Access-Control-Allow-Methods':'POST,OPTIONS'}:{})};
  const respond=(data,status=200)=>new Response(JSON.stringify(data),{status,headers});
  try{
   if(origin&&!allowedOrigins.includes(origin))throw fail('Origen no permitido.',403);
   if(request.method==='OPTIONS')return new Response(null,{status:204,headers});
   if(request.method!=='POST')throw fail('Método no permitido.',405);
   const authorization=request.headers.get('Authorization')||'';
   if(!authorization.startsWith('Bearer ')||authorization.length>16000)throw fail('Inicia sesión para continuar.',401);
   const jwt=authorization.slice(7);if(!jwt||jwt===hub.key)throw fail('Inicia sesión para continuar.',401);
   const reader=request.body?.getReader();if(!reader)throw fail('Solicitud inválida.');
   const chunks=[];let length=0;
   while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>16384){await reader.cancel();throw fail('Solicitud demasiado grande.',413);}chunks.push(value);}
   const bytes=new Uint8Array(length);let offset=0;for(const c of chunks){bytes.set(c,offset);offset+=c.length;}
   let body;try{body=JSON.parse(new TextDecoder().decode(bytes));}catch{throw fail('Solicitud inválida.');}
   const {action,data}=body||{};
   if(!actions.has(action)||!data||typeof data!=='object'||Array.isArray(data)||(action!=='snapshot'&&!uuid.test(data.gym_id||'')))throw fail('Solicitud inválida.');
   const actor=await hub.withUser(jwt).request('/auth/v1/user');
   if(!uuid.test(actor?.id||'')||!actor.email_confirmed_at)throw fail('Confirma tu acceso para continuar.',401);
   if(authorizeActor&&!await authorizeActor(actor.id))throw fail('Esta cuenta todavía no está habilitada.',403);
   if(action==='push.config')return respond({data:{publicKey:pushPublicKey?await pushPublicKey():null}});
   if(action==='snapshot')return respond({data:await hub.rpc('league_member_gateway',{p_actor:actor.id,p_gym:null,p_action:'snapshot',p_data:{}})});
   let membership;
   if(memberBridge){
    if(action.startsWith('gym.')){
     const operation=action.slice(4),safeData={};
     if(['reserve','cancel'].includes(operation)){
      if(!/^[1-9][0-9]{0,18}$/.test(String(data.class_id||'')))throw fail('Clase no disponible.');safeData.class_id=String(data.class_id);
     }
     const result=await memberBridge({actor:actor.id,gym:data.gym_id,action:operation,data:safeData});
     if(['reserve','cancel'].includes(operation))await hub.rpc('league_member_reservation_notice',{p_actor:actor.id,p_gym:data.gym_id,p_class:safeData.class_id});
     return respond({data:result});
    }
    membership=await memberBridge({actor:actor.id,gym:data.gym_id,action:'membership',data:{}});
   }else{
    const checked=await leagueHandler(new Request(request.url,{method:'POST',headers:{Authorization:authorization,'Content-Type':'application/json',...(origin?{Origin:origin}:{})},body:JSON.stringify({audience:'athlete',action:'gym.membership',data:{gym_id:data.gym_id}})}));
    if(!checked.ok)throw fail('No tienes acceso a este gimnasio o el servicio no está disponible.',checked.status);
    membership=(await checked.json()).data;
   }
   let safe={};
   if(action==='renewals.create'){
    if(!uuid.test(data.request_key||''))throw fail('Identificador de solicitud inválido.');
    // Only the server's current membership period is used for deduplication.
    if(membership?.ends_at!=null&&typeof membership.ends_at!=='string')throw fail('No se pudo comprobar el periodo de la membresía.',503);
    safe={request_key:data.request_key,period_key:membership?.ends_at||'NO_PERIOD'};
   }else if(action==='renewals.cancel'||action==='notifications.read'){
    if(!uuid.test(data.id||''))throw fail('Identificador inválido.');safe={id:data.id};
   }else if(action==='push.subscribe'){
    const s=data.subscription;
    if(!s||!validatePushEndpoint(s.endpoint)||!/^[A-Za-z0-9_-]{80,120}$/.test(s.keys?.p256dh||'')||!/^[A-Za-z0-9_-]{20,32}$/.test(s.keys?.auth||''))throw fail('Suscripción push no válida.');
    safe={endpoint:s.endpoint,p256dh:s.keys.p256dh,auth:s.keys.auth};
   }else if(action==='push.unsubscribe'){
    if(!validatePushEndpoint(data.endpoint))throw fail('Suscripción push no válida.');safe={endpoint:data.endpoint};
   }
   const result=await hub.rpc('league_member_gateway',{p_actor:actor.id,p_gym:data.gym_id,p_action:action,p_data:safe});
   return respond({data:result});
  }catch(e){
   const status=[400,401,403,404,405,413,429].includes(e?.status)?e.status:503;
   return respond({error:'MEMBER_REQUEST_FAILED',message:status<500?e.message:'No se pudo confirmar la operación. Actualiza antes de repetirla.'},status);
  }
 };
}
