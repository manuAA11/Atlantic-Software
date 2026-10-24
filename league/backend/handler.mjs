import {BackendDB} from '../../backend/core/database.mjs';

const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const failure=(code,message,status=400)=>Object.assign(new Error(message),{code,status});
const digest=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))).map(n=>n.toString(16).padStart(2,'0')).join('');
async function bodyOf(request){
 const reader=request.body?.getReader();if(!reader)throw failure('INVALID_REQUEST','Revisa la solicitud.');
 let length=0;const chunks=[];
 while(true){const {value,done}=await reader.read();if(done)break;length+=value.byteLength;if(length>131072){await reader.cancel();throw failure('REQUEST_TOO_LARGE','La solicitud es demasiado grande.',413);}chunks.push(value);}
 const joined=new Uint8Array(length);let offset=0;for(const chunk of chunks){joined.set(chunk,offset);offset+=chunk.length;}
 try{const body=JSON.parse(new TextDecoder().decode(joined));if(!body||typeof body!=='object'||Array.isArray(body))throw Error();return body;}catch{throw failure('INVALID_REQUEST','Revisa la solicitud.');}
}

/** All injected transports are server-owned. No client-selected URL/key/project. */
export function createLeagueHandler({hub,core,sources,allowedOrigins=[],invitationBase='atlanticleague://activate',deliverInvitation,authorizePilot}){
 const rate=new Map();
 function limited(id){
  const now=Date.now(),old=rate.get(id);const entry=old&&old.until>now?old:{until:now+60000,hits:0};entry.hits++;rate.set(id,entry);
  if(rate.size>5000)for(const [key,value] of rate)if(value.until<now)rate.delete(key);
  if(entry.hits>90)throw failure('TRY_LATER','Espera un momento y vuelve a intentarlo.',429);
 }
 async function moduleFor(gym){
  if(!uuid.test(gym||''))throw failure('GYM_UNAVAILABLE','El gimnasio no está disponible.',403);
  const config=await core.rpc('core_league_entitlement',{p_gym_id:gym});
  if(!config?.enabled||config.gym_id!==gym||!sources[config.source_ref])throw failure('MODULE_DISABLED','League no está habilitado en este gimnasio.',403);
  if(!/^[A-Z0-9-]{6,24}$/.test(config.athlete_code||''))throw failure('GYM_UNAVAILABLE','El gimnasio no está disponible.',403);
  await hub.rpc('league_gateway',{p_action:'directory.sync',p_data:{gym_id:gym,source_ref:config.source_ref,name:config.name,athlete_code:config.athlete_code,enabled:true}});
  return {config,source:sources[config.source_ref]};
 }
 async function userOf(transport,jwt){
  if(!jwt||jwt===transport.key)throw failure('LOGIN_REQUIRED','Inicia sesión para continuar.',401);
  const user=await transport.withUser(jwt).request('/auth/v1/user');
  if(!user?.id||!user.email_confirmed_at)throw failure('LOGIN_REQUIRED','Confirma tu correo e inicia sesión.',401);
  return user;
 }
 return async request=>{
  const origin=request.headers.get('Origin');
  const cors=origin&&allowedOrigins.includes(origin)?{'Access-Control-Allow-Origin':origin,'Vary':'Origin','Access-Control-Allow-Headers':'authorization,content-type,apikey','Access-Control-Allow-Methods':'POST,OPTIONS'}:{};
  const respond=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...cors}});
  try{
   if(origin&&!allowedOrigins.includes(origin))return respond({error:'ORIGIN_NOT_ALLOWED',message:'Origen no permitido.'},403);
   if(request.method==='OPTIONS')return new Response(null,{status:204,headers:cors});
   if(request.method!=='POST')return respond({error:'METHOD_NOT_ALLOWED'},405);
   const authorization=request.headers.get('Authorization')||'';
   if(!authorization.startsWith('Bearer ')||authorization.length>16000)throw failure('LOGIN_REQUIRED','Inicia sesión para continuar.',401);
   const jwt=authorization.slice(7),body=await bodyOf(request),data=body.data||{};
   if(typeof body.action!=='string'||body.action.length>80||!data||typeof data!=='object'||Array.isArray(data))throw failure('INVALID_REQUEST','Revisa la solicitud.');
   const action=body.action;
   if(body.audience==='staff'){
    const source=sources[body.project_ref];if(!source)throw failure('SOURCE_NOT_REGISTERED','Origen no autorizado.',403);
    const actor=await userOf(source,jwt);if(authorizePilot&&!await authorizePilot(actor.id))throw failure('PILOT_ONLY','Esta cuenta todavía no está habilitada para el piloto.',403);limited('staff:'+body.project_ref+':'+actor.id);
    const context=await source.withUser(jwt).rpc('league_staff',{p_gym_id:body.gym_id,p_action:'context',p_data:{}});
    if(context?.actor_id!==actor.id||context.gym_id!==body.gym_id||!['admin','coach'].includes(context.role))throw failure('NOT_AUTHORIZED','Tu cuenta no tiene permiso para esta acción.',403);
    const {config}=await moduleFor(context.gym_id);
    if(config.source_ref!==body.project_ref)throw failure('SOURCE_NOT_REGISTERED','El origen no corresponde al gimnasio.',403);
    const staff={gym_id:context.gym_id,actor_id:actor.id,actor_role:context.role,actor_email:actor.email};
    if(['clients','provision','machines','machine.create','routine.assign','events','event.create','event.cancel','reservation.cancel','coach.grant'].includes(action)){
     let safe=data;
     if(action==='routine.assign'){
      const catalog=await hub.rpc('league_gateway',{p_action:'staff.catalog',p_data:staff});
      if(!Array.isArray(data.exercises)||data.exercises.length>100)throw failure('INVALID_REQUEST','Selecciona los ejercicios.');
      safe={...data,exercises:data.exercises.map(item=>{
       const entry=catalog.find(e=>e.id===item.catalog_id);if(!entry)throw failure('INVALID_EXERCISE','El ejercicio no está disponible.');
       return {...item,name:entry.name};
      })};
     }
     return respond({data:await source.withUser(jwt).rpc('league_staff',{p_gym_id:context.gym_id,p_action:action,p_data:safe})});
    }
    if(action==='invite'){
     if(context.role!=='admin')throw failure('NOT_AUTHORIZED','Esta acción requiere administración.',403);
     if(typeof data.email!=='string'||!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email))throw failure('INVALID_EMAIL','Revisa el correo de la invitación.');
     const prepared=await source.withUser(jwt).rpc('league_staff',{p_gym_id:context.gym_id,p_action:'provision',p_data:{client_id:data.client_id}});
     const bytes=crypto.getRandomValues(new Uint8Array(32)),token=Array.from(bytes,n=>n.toString(16).padStart(2,'0')).join('');
     await hub.rpc('league_gateway',{p_action:'staff.invite',p_data:{...staff,source_profile_id:prepared.profile_id,email:data.email,token_hash:await digest(token)}});
     const link=invitationBase+'?token='+token;
     if(deliverInvitation){await deliverInvitation({email:data.email,link,gymName:config.name});return respond({data:{sent:true}});}
     return respond({data:{sent:false,activation_link:link,message:'Invitación preparada. Compártela de forma privada con el titular.'}});
    }
    if(action==='approve_join'){
     if(context.role!=='admin')throw failure('NOT_AUTHORIZED','Esta acción requiere administración.',403);
     const prepared=await source.withUser(jwt).rpc('league_staff',{p_gym_id:context.gym_id,p_action:'provision',p_data:{client_id:data.client_id}});
     return respond({data:await hub.rpc('league_gateway',{p_action:'staff.approve_join',p_data:{...staff,request_id:data.request_id,source_profile_id:prepared.profile_id}})});
    }
    if(action==='evidence'){
     const item=await hub.rpc('league_gateway',{p_action:'staff.evidence',p_data:{...staff,request_id:data.request_id}});
     if(!item?.path)throw failure('EVIDENCE_UNAVAILABLE','La solicitud no tiene una imagen adjunta.',404);
     const signed=await hub.request('/storage/v1/object/sign/league-evidence/'+item.path.split('/').map(encodeURIComponent).join('/'),{method:'POST',body:{expiresIn:120}});
     return respond({data:{url:hub.url+'/storage/v1'+signed.signedURL}});
    }
    if(!['pending','catalog','catalog_create','verify','reject_join'].includes(action))throw failure('INVALID_ACTION','Acción no disponible.');
    return respond({data:await hub.rpc('league_gateway',{p_action:'staff.'+action,p_data:{...data,...staff}})});
   }
   if(body.audience&&body.audience!=='athlete')throw failure('INVALID_REQUEST','Revisa la solicitud.');
   const athlete=await userOf(hub,jwt);if(authorizePilot&&!await authorizePilot(athlete.id))throw failure('PILOT_ONLY','Esta cuenta todavía no está habilitada para el piloto.',403);limited('athlete:'+athlete.id);
   const actorHub=hub.withUser(jwt),app=(a,d={})=>actorHub.rpc('league_app',{p_action:a,p_data:d});
   if(action==='gym.search'){
    if(typeof data.query!=='string'||data.query.trim().length<2)return respond({data:[]});
    const found=await core.rpc('core_league_search',{p_query:data.query.slice(0,80)});
    for(const row of found)if(sources[row.source_ref])await moduleFor(row.gym_id);
    return respond({data:await app('gym.search',data)});
   }
   if(action==='gym.request'){
    // Find via a known directory, then re-attest the module in Core before joining.
    if(typeof data.code!=='string'||!/^[A-Z0-9-]{6,24}$/.test(data.code.trim().toUpperCase()))throw failure('GYM_UNAVAILABLE','Revisa el código del gimnasio.',404);
    const found=await core.rpc('core_league_search',{p_query:data.code.trim().toUpperCase()});
    const exact=found.filter(row=>row.athlete_code===data.code.trim().toUpperCase()&&sources[row.source_ref]);
    if(!exact?.[0])throw failure('GYM_UNAVAILABLE','Revisa el código del gimnasio.',404);
    await moduleFor(exact[0].gym_id);
    return respond({data:await app(action,data)});
   }
   if(action.startsWith('gym.')&&['gym.routines','gym.calendar','gym.reserve','gym.cancel','gym.membership','gym.attendance','gym.workout.start'].includes(action)){
    const {source}=await moduleFor(data.gym_id);
    const connection=await app('gym.connection',{gym_id:data.gym_id});
    if(!connection?.source_profile_id)throw failure('LINK_REQUIRED','Tu vinculación todavía no está aprobada.',403);
    const sourceCall=(a,d={})=>source.rpc('league_source',{p_gym_id:data.gym_id,p_profile_id:connection.source_profile_id,p_action:a,p_data:d});
    if(action==='gym.workout.start'){
     const snapshot=await sourceCall('routine.snapshot',{routine_id:data.routine_id});
     if(!snapshot)throw failure('ROUTINE_UNAVAILABLE','La rutina no está disponible.',404);
     return respond({data:await hub.rpc('league_gateway',{p_action:'draft.open',p_data:{gym_id:data.gym_id,athlete_id:athlete.id,routine_snapshot:snapshot}})});
    }
    if(action==='gym.attendance'){
     const rows=await sourceCall('attendance');
     for(const row of rows)await hub.rpc('league_gateway',{p_action:'attendance.credit',p_data:{gym_id:data.gym_id,athlete_id:athlete.id,local_date:row.local_date}});
     return respond({data:{days:rows.length}});
    }
    return respond({data:await sourceCall(action.slice(4),data)});
   }
   if(action==='record.submit')await moduleFor(data.gym_id);
   if(action==='account.delete'){
    if(data.confirm!=='ELIMINAR'||!athlete.last_sign_in_at||Date.now()-Date.parse(athlete.last_sign_in_at)>300000)throw failure('REAUTH_REQUIRED','Vuelve a iniciar sesión antes de eliminar tu cuenta.',403);
    // Only this athlete's private evidence. Never delete the original Gym client/member record.
    for(let page=0;page<50;page++){
     const items=await hub.request('/storage/v1/object/list/league-evidence',{method:'POST',body:{prefix:athlete.id,limit:100,offset:0}});
     const paths=(items||[]).filter(x=>x.id&&/^[a-f0-9-]{36}[.](jpg|png|webp)$/.test(x.name)).map(x=>athlete.id+'/'+x.name);
     if(!paths.length)break;
     await hub.request('/storage/v1/object/league-evidence',{method:'DELETE',body:{prefixes:paths}});
     if(page===49)throw failure('TRY_LATER','Vuelve a intentarlo para terminar la eliminación.',503);
    }
    // Auth may be shared with Gym/Core. Delete League data only, never the shared identity.
    await hub.rpc('league_gateway',{p_action:'profile.delete',p_data:{athlete_id:athlete.id}});
    return respond({data:{deleted:true}});
   }
   const personal=['profile.ensure','profile.update','snapshot','catalog','exercise.personal','workout.save','gym.search','invitation.accept','record.submit','leaderboard'];
   if(!personal.includes(action))throw failure('INVALID_ACTION','Acción no disponible.');
   return respond({data:await app(action,data)});
  }catch(error){
   const status=[400,401,403,404,413,429,503].includes(error?.status)?error.status:503;
   return respond({error:typeof error?.code==='string'?error.code:'SERVICE_UNAVAILABLE',
    message:typeof error?.status==='number'&&error.status<500?error.message:'No se pudo confirmar la operación. Actualiza antes de repetirla.'},status);
  }
 };
}

export function configuredSource({projectRef,serviceKey,fetcher=fetch}){
 if(!/^[a-z0-9]{20}$/.test(projectRef))throw Error('Invalid source configuration');
 if(!serviceKey||(!serviceKey.startsWith('eyJ')&&!serviceKey.startsWith('sb_secret_')))throw Error('A server-only key is required');
 // New secret keys identify the server through apikey; they are not user JWTs.
 const transport=(url,options)=>{
  const headers=new Headers(options.headers);
  if(serviceKey.startsWith('sb_secret_')&&headers.get('Authorization')==='Bearer '+serviceKey)headers.delete('Authorization');
  return fetcher(url,{...options,headers});
 };
 return new BackendDB('https://'+projectRef+'.supabase.co',serviceKey,transport);
}
