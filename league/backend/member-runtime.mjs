import {memberDatabase} from './member-db.mjs';
import {createLeagueMemberHandler} from './member-handler.mjs';
export function createMemberBridge({hub,core,sourceRef}){
 return async({actor,gym,action,data})=>{
  const rows=await core.rpc('core_league_public_directory',{p_gym_id:gym,p_query:null});
  const entitlement=rows?.find(x=>x.gym_id===gym&&x.enabled&&x.source_ref===sourceRef);
  if(!entitlement)throw Object.assign(Error('El gimnasio no está habilitado.'),{status:403});
  const connection=await hub.rpc('league_member_gateway',{p_actor:actor,p_gym:gym,p_action:'connection',p_data:{}});
  if(!connection?.source_profile_id||connection.source_ref!==sourceRef)throw Object.assign(Error('Vinculación no disponible.'),{status:403});
  if(['calendar','templates','catalog','profile'].includes(action))return hub.rpc('league_member_content',{p_actor:actor,p_gym:gym,p_action:action});
  return hub.rpc('league_source',{p_gym_id:gym,p_profile_id:connection.source_profile_id,p_action:action,p_data:data});
 };
}
export function createConfiguredMemberHandler(env){
 if(env.get('LEAGUE_SHARED_PROJECT')!=='true')throw Error('Member gateway requires the shared Gym project.');
 const url=env.get('SUPABASE_URL')||'';
 if(!/^https:\/\/[a-z0-9]{20}\.supabase\.co$/.test(url))throw Error('Invalid shared project URL');
 const sourceRef=new URL(url).hostname.split('.')[0];
 const hub=memberDatabase(url,env.get('SUPABASE_SERVICE_ROLE_KEY'));
 const ref=env.get('LEAGUE_CORE_REF'),key=env.get('LEAGUE_CORE_PUBLIC_KEY');
 if(!/^[a-z0-9]{20}$/.test(ref||'')||!key)throw Error('Missing public Core directory configuration');
 const core={async rpc(name,args){const response=await fetch('https://'+ref+'.supabase.co/rest/v1/rpc/'+name,{method:'POST',headers:{apikey:key,'Content-Type':'application/json'},body:JSON.stringify(args),signal:AbortSignal.timeout(15000)});if(!response.ok)throw Error('Directory unavailable');return response.json();}};
 return createLeagueMemberHandler({hub,memberBridge:createMemberBridge({hub,core,sourceRef}),
  pushPublicKey:async()=>{const settings=await hub.rpc('league_member_settings',{p_action:'get',p_data:{}});return settings.vapid_public;},
  authorizeActor:env.get('LEAGUE_PILOT_ONLY')==='true'?actor=>hub.rpc('league_pilot_allowed',{p_user_id:actor}):undefined,
  allowedOrigins:(env.get('LEAGUE_WEB_ORIGINS')||'').split(',').map(s=>s.trim()).filter(Boolean)});
}
