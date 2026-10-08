import {IntegrationError,randomToken,sha256,requireUUID,normalizePhone,constantEqual} from './core/security.mjs';
import {validateWompi,metaRequest,templateComponents} from './core/providers.mjs';
import {recommendedRules,variablesFor,renderMessage,evaluate} from './core/automation.mjs';
import {completeMeta} from './core/onboarding.mjs';
import {createPayment,runJobs,dispatch} from './core/worker.mjs';
import {metaWebhook,wompiWebhook} from './core/webhooks.mjs';
function json(data,status=200,extra={}){return new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',...extra}});}
async function bodyJSON(req,max=65536){const text=await req.text();if(text.length>max)throw new IntegrationError('TOO_LARGE','Solicitud demasiado grande.',413);try{return JSON.parse(text);}catch{throw new IntegrationError('INVALID_JSON','Solicitud no válida.');}}
export function createHandler({db,baseURL,fetcher=fetch}) {
 return async request=>{
  let cors={};try{
   const url=new URL(request.url);const base=new URL(baseURL);
   // The hosted Edge gateway can strip /functions/v1 before passing the request.
   // Match a complete mount segment, preserving authentication on every route.
   const mounts=[base.pathname.replace(/\/$/,''),'/'+base.pathname.split('/').filter(Boolean).at(-1)];
   const mount=mounts.find(p=>url.pathname===p||url.pathname.startsWith(p+'/'));
   const path=mount?url.pathname.slice(mount.length):url.pathname;
   const origin=request.headers.get('Origin');
   if(origin){const platform=await db.rpc('marketing_service_platform');if(origin!==platform?.onboarding_origin)throw new IntegrationError('ORIGIN_BLOCKED','Origen no autorizado.',403);cors={'Access-Control-Allow-Origin':origin,'Vary':'Origin','Access-Control-Allow-Methods':'POST,GET,OPTIONS','Access-Control-Allow-Headers':'content-type,authorization,apikey'};}
   if(request.method==='OPTIONS')return new Response(null,{status:204,headers:cors});
   if(request.method==='GET'&&path==='/health'){
    const health=await db.rpc('marketing_service_health');
    const ready=health?.database===true&&health?.scheduler_installed===true;
    return json({service:'marketing',ready,database:health?.database===true,
     scheduler_installed:health?.scheduler_installed===true,server_now:health?.server_now||null},ready?200:503,cors);
   }
   if(path==='/webhooks/meta'){
    if(request.method==='GET'){
     const p=await db.rpc('marketing_service_platform');
     if(url.searchParams.get('hub.mode')!=='subscribe'||!p?.verify_token||!constantEqual(url.searchParams.get('hub.verify_token'),p.verify_token))throw new IntegrationError('INVALID_VERIFICATION','Verificación no válida.',403);
     return new Response(url.searchParams.get('hub.challenge')||'',{headers:{'Content-Type':'text/plain'}});
    }
    if(request.method!=='POST')throw new IntegrationError('METHOD','Método no permitido.',405);
    const raw=await request.text();if(raw.length>1048576)throw new IntegrationError('TOO_LARGE','Evento demasiado grande.',413);
    return json(await metaWebhook(db,baseURL,raw,request.headers.get('x-hub-signature-256'),fetcher));
   }
   if(path.startsWith('/webhooks/wompi/')&&request.method==='POST'){
    const gym=requireUUID(path.split('/').at(-1));const raw=await request.text();if(raw.length>65536)throw new IntegrationError('TOO_LARGE','Evento demasiado grande.',413);
    return json(await wompiWebhook(db,gym,raw,request.headers.get('x-event-checksum'),fetcher));
   }
   if(path==='/jobs'&&request.method==='POST'){
    if(!await db.rpc('marketing_service_scheduler_authorized',{p_token:request.headers.get('x-marketing-scheduler')||''}))throw new IntegrationError('NOT_AUTHORIZED','No autorizado.',403);
    const result=await runJobs(db,baseURL);return json({...result,...await dispatch(db,{fetcher})});
   }
   if(path.startsWith('/pay/')&&request.method==='GET'){
    const reference=path.split('/').at(-1);if(!/^GS-[a-f0-9]{32}$/.test(reference))throw new IntegrationError('NOT_FOUND','Enlace no encontrado.',404);
    const p=await db.rpc('marketing_service_open_payment',{p_reference:reference});
    if(p.state==='READY'&&p.checkout_url){const target=new URL(p.checkout_url);if(target.origin!=='https://checkout.wompi.co')throw new Error('Invalid stored checkout origin');return new Response(null,{status:303,headers:{Location:p.checkout_url,'Cache-Control':'no-store','Referrer-Policy':'no-referrer'}});}
    return new Response(p.state==='PAID'?'Este pago ya fue confirmado.':p.state==='EXPIRED'?'Este enlace venció. Solicita otro al gimnasio.':'El enlace no está disponible.',{status:p.state==='PAID'?200:410,headers:{'Content-Type':'text/plain; charset=utf-8'}});
   }
   if(path==='/oauth/bootstrap'&&request.method==='POST'){
    const data=await bodyJSON(request);await db.rpc('marketing_service_oauth',{p_hash:await sha256(data.state||'')});const p=await db.rpc('marketing_service_platform');
    return json({app_id:p.app_id,config_id:p.config_id,endpoint:baseURL+'/oauth/callback'},200,cors);
   }
   if(path==='/oauth/callback'&&request.method==='POST')return json(await completeMeta(db,await bodyJSON(request),fetcher),200,cors);
   if(path!=='/admin'||request.method!=='POST')throw new IntegrationError('NOT_FOUND','Recurso no encontrado.',404);
   const data=await bodyJSON(request);const gym=requireUUID(data.gym_id);const jwt=(request.headers.get('Authorization')||'').replace(/^Bearer /i,'');
   const access=await db.authorize(jwt,gym);const user=db.withUser(jwt);
   if(!await db.rpc('marketing_service_limit',{p_gym_id:gym,p_bucket:'admin/'+access.user_id,p_max:60,p_seconds:60}))throw new IntegrationError('RATE_LIMIT','Espera un momento antes de volver a intentarlo.',429);
   switch(data.action){
    case 'connect_whatsapp':{
     const p=await db.rpc('marketing_service_platform');
     if(!p?.app_id||!p?.config_id||!p?.onboarding_url)throw new IntegrationError('META_PLATFORM_PENDING','Atlantic Tech debe completar la habilitación inicial de Meta para ofrecer la conexión oficial.');
     const dest=new URL(p.onboarding_url);if(dest.protocol!=='https:'||dest.origin!==p.onboarding_origin)throw new IntegrationError('META_PLATFORM_PENDING','La página de autorización necesita revisión.');
     const state=randomToken();await db.rpc('marketing_service_oauth',{p_hash:await sha256(state),p_gym_id:gym,p_user_id:access.user_id});dest.searchParams.set('state',state);dest.searchParams.set('backend',baseURL);return json({url:dest.href},200,cors);
    }
    case 'connect_wompi':{
     const info=await validateWompi(data.credentials,fetcher);
     await db.rpc('marketing_service_connect',{p_gym_id:gym,p_provider:'WOMPI',p_secrets:data.credentials,p_display:{...info,actor_user_id:access.user_id},p_mode:info.mode});
     return json({mode:info.mode,requires_test:true,webhook_url:baseURL+'/webhooks/wompi/'+gym,message:'Cuenta encontrada. Completa el pago de prueba para verificar la conexión de extremo a extremo.'},200,cors);
    }
    case 'payment_test':{
     const c=await user.rpc('marketing_create_test_client',{p_gym_id:gym});
     const conn=await db.connection(gym,'WOMPI');if(conn?.mode!=='test')throw new IntegrationError('SANDBOX_ONLY','La prueba solo está disponible en Sandbox.');
     await user.rpc('marketing_features',{p_gym_id:gym,p_flags:{online_payments_enabled:true}});
     return json(await createPayment(db,baseURL,gym,c,Number(data.plan_id),'manual-test/'+data.request_key),200,cors);
    }
    case 'recommended':{
     const existing=await user.read('marketing_automations',{gym_id:'eq.'+gym,deleted_at:'is.null'});const saved=[];
     for(const rule of recommendedRules())if(!existing.some(r=>r.name===rule.name))saved.push(await user.rpc('marketing_save_automation',{p_gym_id:gym,p_data:rule}));return json({created:saved.length},200,cors);
    }
    case 'preview':{
     const [r]=await user.read('marketing_automations',{gym_id:'eq.'+gym,id:'eq.'+data.automation_id,limit:'1'});if(!r)throw new IntegrationError('NOT_FOUND','Automatización no encontrada.',404);
     const c=await db.context(gym,Number(data.client_id));if(!c)throw new IntegrationError('NOT_FOUND','Cliente no encontrado.',404);
     return json({message:renderMessage(r.body,variablesFor(c,'[Enlace de prueba: no genera un cobro]')),matches:!!evaluate({...r,enabled:true},c),sent:false,payment_created:false},200,cors);
    }
    case 'prepare_rule_template':{
     const [rule]=await user.read('marketing_automations',{gym_id:'eq.'+gym,id:'eq.'+data.automation_id,deleted_at:'is.null',limit:'1'});
     if(!rule)throw new IntegrationError('NOT_FOUND','Automatización no encontrada.',404);
     const existing=await user.read('whatsapp_templates',{gym_id:'eq.'+gym,body:'eq.'+rule.body,limit:'1'});
     const template=existing[0]||await user.rpc('marketing_save_template',{p_gym_id:gym,p_data:{name:'gym_'+rule.id.replaceAll('-','').slice(0,20)+'_'+rule.revision,body:rule.body,category:['BIRTHDAY','BIRTHDAY_BEFORE','INACTIVITY','DAILY','WEEKLY','MONTHLY','CUSTOM_DATE'].includes(rule.trigger_type)?'MARKETING':'UTILITY',variables:[...new Set([...rule.body.matchAll(/\{\{([a-z_]+)\}\}/g)].map(m=>m[1]))]}});
     await user.rpc('marketing_save_automation',{p_gym_id:gym,p_id:rule.id,p_revision:rule.revision,p_data:{...rule,template_id:template.id,enabled:false}});
     return json({template_id:template.id,status:template.status},200,cors);
    }
    case 'test_message':{
     if(data.confirmed!==true)throw new IntegrationError('CONFIRM_REQUIRED','Confirma el destinatario y el envío real antes de continuar.');
     const [template]=await user.read('whatsapp_templates',{gym_id:'eq.'+gym,id:'eq.'+data.template_id,status:'eq.APPROVED',limit:'1'});
     const context=await db.context(gym,Number(data.client_id));
     if(!template||!context?.whatsapp_opt_in||template.body.includes('{{link_pago}}'))throw new IntegrationError('TEST_NOT_READY','Usa un cliente con autorización y una plantilla aprobada sin enlace de pago.');
     const variables=variablesFor(context);await user.rpc('marketing_features',{p_gym_id:gym,p_flags:{whatsapp_enabled:true}});
     const mid=await db.rpc('marketing_service_test_message',{p_gym_id:gym,p_client_id:context.client_id,p_template_id:template.id,p_key:data.request_key,p_body:renderMessage(template.body,variables),p_parameters:template.variables.map(v=>variables[v]||'')});
     await dispatch(db,{messageId:mid,limit:1,fetcher});
     const [record]=await user.read('marketing_messages',{gym_id:'eq.'+gym,id:'eq.'+mid,select:'id,status,error_message',limit:'1'});
     return json(record,200,cors);
    }
    case 'submit_template':{
     const [t]=await user.read('whatsapp_templates',{gym_id:'eq.'+gym,id:'eq.'+data.template_id,limit:'1'});if(!t||!['DRAFT','REJECTED'].includes(t.status))throw new IntegrationError('TEMPLATE_STATE','La plantilla ya fue enviada o no está disponible.');
     const conn=await db.connection(gym,'META'),keys=await db.credentials(gym,'META');if(conn?.status!=='CONNECTED')throw new IntegrationError('NOT_CONFIGURED','Conecta WhatsApp primero.');
     const result=await metaRequest(`${conn.provider_account_id}/message_templates`,keys.access_token,{method:'POST',body:{name:t.name,language:t.language,category:t.category,components:templateComponents(t.body,t.variables,data.samples||{})},fetcher});
     await db.patch('whatsapp_templates',{gym_id:'eq.'+gym,id:'eq.'+t.id},{status:result.status==='APPROVED'?'APPROVED':'PENDING',provider_id:String(result.id),updated_at:new Date().toISOString()});return json({submitted:true},200,cors);
    }
    case 'repair':{
     const conn=await db.connection(gym,data.provider);if(!conn)throw new IntegrationError('NOT_CONFIGURED','Conecta el servicio primero.');
     const keys=await db.credentials(gym,data.provider);
     if(data.provider==='META'){
      const phone=await metaRequest(`${conn.phone_number_id}?fields=display_phone_number,is_on_biz_app,platform_type`,keys.access_token,{fetcher});
      await metaRequest(`${conn.provider_account_id}/subscribed_apps`,keys.access_token,{method:'POST',body:{},fetcher});
      const templates=await metaRequest(`${conn.provider_account_id}/message_templates?fields=id,name,status,language&limit=100`,keys.access_token,{fetcher});
      for(const t of templates.data||[])if(['APPROVED','PENDING','REJECTED','PAUSED','DISABLED'].includes(t.status))await db.patch('whatsapp_templates',{gym_id:'eq.'+gym,name:'eq.'+t.name,language:'eq.'+t.language},{provider_id:t.id,status:t.status,updated_at:new Date().toISOString()});
      await db.patch('marketing_connections',{gym_id:'eq.'+gym,provider:'eq.META'},{status:'CONNECTED',last_error:'',last_checked_at:new Date().toISOString(),display_number:phone.display_phone_number});
     }else if(data.provider==='WOMPI'){await validateWompi(keys,fetcher);await db.patch('marketing_connections',{gym_id:'eq.'+gym,provider:'eq.WOMPI'},{last_checked_at:new Date().toISOString()});}
     else throw new IntegrationError('INVALID_PROVIDER','Servicio no válido.');return json({checked:true},200,cors);
    }
    default:throw new IntegrationError('INVALID_ACTION','Acción no disponible.');
   }
  }catch(e){return json({error:e instanceof IntegrationError?e.code:'INTERNAL_ERROR',message:e instanceof IntegrationError?e.message:'No se pudo completar la operación. Contacta con soporte si vuelve a ocurrir.'},e instanceof IntegrationError?e.status:500,cors);}
 };
}
