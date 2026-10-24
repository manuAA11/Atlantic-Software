import {BackendDB} from '../../backend/core/database.mjs';
import {createLeagueHandler,configuredSource} from './handler.mjs';

/** Co-located hub/provider uses built-in server credentials; never client config. */
export function createConfiguredLeagueHandler(env,{fetcher=fetch}={}){
 const required=key=>{const value=env.get(key);if(!value)throw Error('Missing server configuration: '+key);return value;};
 const shared=env.get('LEAGUE_SHARED_PROJECT')==='true';
 let hubRef,hubKey,sourceConfig;
 if(shared){
  const url=required('SUPABASE_URL');
  if(!/^https:\/\/[a-z0-9]{20}\.supabase\.co$/.test(url))throw Error('Invalid shared project configuration');
  hubRef=new URL(url).hostname.split('.')[0];hubKey=required('SUPABASE_SERVICE_ROLE_KEY');
  // No caller-selected provider, and no third project or duplicated secret is required.
  sourceConfig=[{projectRef:hubRef,serviceKey:hubKey}];
 }else{
  hubRef=required('LEAGUE_HUB_REF');hubKey=required('LEAGUE_HUB_SECRET');
  sourceConfig=JSON.parse(required('LEAGUE_SOURCES_JSON'));
 }
 const sources={};
 for(const entry of sourceConfig){if(sources[entry.projectRef])throw Error('Duplicate provider configuration');sources[entry.projectRef]=configuredSource({...entry,fetcher});}
 const hub=configuredSource({projectRef:hubRef,serviceKey:hubKey,fetcher});
 let core;
 if(env.get('LEAGUE_CORE_PUBLIC_KEY')){
  const ref=required('LEAGUE_CORE_REF'),key=required('LEAGUE_CORE_PUBLIC_KEY');
  if(!/^[a-z0-9]{20}$/.test(ref)||(!key.startsWith('sb_publishable_')&&!key.startsWith('eyJ')))throw Error('Invalid public Core configuration');
  const transport=(url,options)=>{const headers=new Headers(options.headers);if(key.startsWith('sb_publishable_'))headers.delete('Authorization');return fetcher(url,{...options,headers});};
  const directory=new BackendDB('https://'+ref+'.supabase.co',key,transport);
  core={async rpc(name,args){if(!['core_league_entitlement','core_league_search'].includes(name))throw Error('Unsupported directory action');const rows=await directory.rpc('core_league_public_directory',{p_gym_id:args.p_gym_id||null,p_query:args.p_query||null});return name==='core_league_entitlement'?rows[0]:rows;}};
 }else core=configuredSource({projectRef:required('LEAGUE_CORE_REF'),serviceKey:required('LEAGUE_CORE_SECRET'),fetcher});
 return createLeagueHandler({hub,core,
  ...(env.get('LEAGUE_PILOT_ONLY')==='true'?{authorizePilot:id=>hub.rpc('league_pilot_allowed',{p_user_id:id})}:{}),
  sources,
  allowedOrigins:(env.get('LEAGUE_WEB_ORIGINS')||'').split(',').map(value=>value.trim()).filter(Boolean),
  invitationBase:required('LEAGUE_ACTIVATION_URL'),
 });
}
