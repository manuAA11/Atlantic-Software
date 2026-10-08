import {IntegrationError,sha256} from './security.mjs';
import {GRAPH_VERSION,providerJSON,metaRequest} from './providers.mjs';
export async function completeMeta(db,{state,code,waba_id,phone_number_id},fetcher=fetch) {
 const platform=await db.rpc('marketing_service_platform');
 if(!platform?.app_id||!platform?.app_secret)throw new IntegrationError('META_PLATFORM_PENDING','La conexión oficial de WhatsApp todavía no está habilitada. Contacta con Atlantic Tech.');
 if(!/^[0-9]{5,30}$/.test(waba_id||''))throw new IntegrationError('META_ASSETS','No se recibió el negocio autorizado. Vuelve a conectar WhatsApp.');
 const binding=await db.rpc('marketing_service_oauth',{p_hash:await sha256(state),p_consume:true});
 const params=new URLSearchParams({client_id:platform.app_id,client_secret:platform.app_secret,code});
 const token=await providerJSON(`https://graph.facebook.com/${GRAPH_VERSION}/oauth/access_token?${params}`,{},fetcher);
 if(!token.access_token)throw new IntegrationError('META_AUTH','No se pudo completar la autorización.');
 const debug=await providerJSON(`https://graph.facebook.com/${GRAPH_VERSION}/debug_token?`+new URLSearchParams({input_token:token.access_token}),{headers:{Authorization:`Bearer ${platform.app_id}|${platform.app_secret}`}},fetcher);
 if(!debug.data?.is_valid||String(debug.data.app_id)!==String(platform.app_id))throw new IntegrationError('META_AUTH','La autorización no corresponde a esta aplicación.');
 const assets=debug.data.granular_scopes||[];
 if(!assets.some(s=>['whatsapp_business_management','whatsapp_business_messaging'].includes(s.scope)&&s.target_ids?.includes(String(waba_id))))throw new IntegrationError('META_ASSETS','El negocio no figura entre los permisos concedidos.');
 const phones=await metaRequest(`${waba_id}/phone_numbers?fields=id,display_phone_number,is_on_biz_app,platform_type`,token.access_token,{fetcher});
 const phone=phones.data?.find(p=>String(p.id)===String(phone_number_id))||(!phone_number_id&&phones.data?.length===1?phones.data[0]:null);
 if(!phone)throw new IntegrationError('META_PHONE','Selecciona un único número del gimnasio durante la autorización.');
 const coexistence=phone.is_on_biz_app===true&&phone.platform_type==='CLOUD_API';
 if(!coexistence&&phone.platform_type!=='CLOUD_API')throw new IntegrationError('META_REGISTRATION_REQUIRED','Este número necesita completar su registro oficial en Meta. No se ha migrado ni desconectado tu número actual.');
 await metaRequest(`${waba_id}/subscribed_apps`,token.access_token,{method:'POST',body:{},fetcher});
 await db.rpc('marketing_service_connect',{p_gym_id:binding.gym_id,p_provider:'META',p_secrets:{access_token:token.access_token},p_display:{display_number:phone.display_phone_number,provider_account_id:waba_id,phone_number_id:phone.id,coexistence,actor_user_id:binding.user_id},p_mode:'test'});
 const sync={};
 if(coexistence){for(const type of ['smb_app_state_sync','history']){try{const r=await metaRequest(`${phone.id}/smb_app_data`,token.access_token,{method:'POST',body:{messaging_product:'whatsapp',sync_type:type},fetcher});sync[type]={requested:true,request_id:r.request_id||null};}catch{sync[type]={requested:false,requires_attention:true};}}}
 await db.patch('marketing_connections',{gym_id:'eq.'+binding.gym_id,provider:'eq.META'},{metadata:{sync},updated_at:new Date().toISOString()});
 return {connected:true,number:phone.display_phone_number,coexistence};
}
const escapeJSON=o=>JSON.stringify(o).replaceAll('<','\\u003c');
export function signupHTML({app_id,config_id,state,endpoint,allowedBackends}={}) {
 // v4 obtains its products from the official Facebook Login for Business config.
 // No app secret, access token or Supabase JWT is exposed in this page.
 const config=escapeJSON({app_id,config_id,state,endpoint,allowedBackends});
 return `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><title>Conectar WhatsApp · Gym soft</title><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect x='3' y='12' width='26' height='18' rx='5' fill='%2312c794'/%3E%3Cpath d='M9 12V9a7 7 0 0 1 14 0v3' stroke='%2312c794' stroke-width='4' fill='none'/%3E%3C/svg%3E"><style>body{background:#0b1220;color:#e6edf7;font:17px system-ui;max-width:620px;margin:8vh auto;padding:24px}button{background:#12c794;color:#08221a;border:0;border-radius:8px;padding:16px 24px;font:600 16px system-ui;cursor:pointer}button:disabled{opacity:.55;cursor:default}button:focus-visible{outline:3px solid #e6edf7;outline-offset:4px}p{line-height:1.6}small{color:#b4c0d2}h1{font-size:2rem;line-height:1.2}@media(max-width:480px){body{margin:4vh auto;padding:20px}button{width:100%}}</style></head><body><main><h1>Conecta el WhatsApp de tu gimnasio</h1><p>Autoriza tu negocio desde Meta. Si tu número es compatible, podrás seguir usándolo en WhatsApp Business.</p><p><small>Meta puede pedir que vuelvas a vincular dispositivos. La compatibilidad de Coexistence depende de tu cuenta. No aceptes migrar un número existente si quieres conservar la aplicación.</small></p><button id="connect" disabled>Iniciar sesión con Meta</button><p id="status" role="status" aria-live="polite">Cargando conexión segura…</p></main><script>
 const cfg=${config};let assets={},code=null,busy=false;
 const status=document.getElementById('status');
 async function finish(){if(!code||!assets.waba_id||busy)return;busy=true;document.getElementById('connect').disabled=true;status.textContent='Completando conexión…';try{const r=await fetch(cfg.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state:cfg.state,code,waba_id:assets.waba_id,phone_number_id:assets.phone_number_id})});const d=await r.json();if(!r.ok)throw new Error(d.message||'No se pudo conectar.');status.textContent='WhatsApp conectado. Ya puedes volver al programa.';}catch(e){status.textContent=e.message+' Vuelve al programa para iniciar una nueva autorización.';}}
 window.addEventListener('message',e=>{if(!['https://www.facebook.com','https://web.facebook.com'].includes(e.origin))return;let d;try{d=typeof e.data==='string'?JSON.parse(e.data):e.data;}catch{return;}if(d?.type==='WA_EMBEDDED_SIGNUP'&&String(d.event).startsWith('FINISH')){assets=d.data||{};finish();}});
 window.fbAsyncInit=()=>{FB.init({appId:cfg.app_id,autoLogAppEvents:false,xfbml:false,version:'${GRAPH_VERSION}'});document.getElementById('connect').disabled=false;status.textContent='Todo listo para autorizar.';};
 document.getElementById('connect').onclick=()=>FB.login(r=>{if(r.authResponse?.code){code=r.authResponse.code;finish();}else{status.textContent='La autorización no se completó. Puedes volver a intentarlo.';}},{config_id:cfg.config_id,response_type:'code',override_default_response_type:true,extras:{}});
 async function initialize(){try{
  if(cfg.allowedBackends){
   const query=new URL(window.location.href).searchParams;
   const backend=query.get('backend');cfg.state=query.get('state');
   window.history.replaceState(null,'',window.location.pathname);
   if(!cfg.allowedBackends.includes(backend)||!/^[a-f0-9]{64}$/.test(cfg.state||''))throw new Error('Abre esta página desde Conectar WhatsApp en el programa.');
   const r=await fetch(backend+'/oauth/bootstrap',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({state:cfg.state})});
   const d=await r.json();if(!r.ok)throw new Error(d.message||'La autorización no está disponible.');
   if(!/^[0-9]{5,30}$/.test(d.app_id||'')||!/^[0-9]{5,30}$/.test(d.config_id||'')||d.endpoint!==backend+'/oauth/callback')throw new Error('La configuración de Meta necesita revisión.');
   Object.assign(cfg,{app_id:d.app_id,config_id:d.config_id,endpoint:d.endpoint});
  }
  const sdk=document.createElement('script');sdk.async=true;sdk.defer=true;sdk.crossOrigin='anonymous';sdk.src='https://connect.facebook.net/es_LA/sdk.js';
  sdk.onerror=()=>{status.textContent='No se pudo cargar Meta. Revisa la conexión y vuelve a abrir esta página desde el programa.';};document.head.appendChild(sdk);
 }catch(e){status.textContent=e.message;}}
 initialize();
 </script></body></html>`;
}
