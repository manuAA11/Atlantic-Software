import {createLeagueHandler,configuredSource} from '../../../handler.mjs';

// Secrets exist only in this isolated gateway's environment, never in Expo or Gym.
const required=(key:string)=>{const value=Deno.env.get(key);if(!value)throw Error('Missing server configuration: '+key);return value;};
const sourceConfig=JSON.parse(required('LEAGUE_SOURCES_JSON'));
const sources:Record<string,unknown>={};
for(const entry of sourceConfig){
 if(sources[entry.projectRef])throw Error('Duplicate provider configuration');
 sources[entry.projectRef]=configuredSource(entry);
}
const handler=createLeagueHandler({
 hub:configuredSource({projectRef:required('LEAGUE_HUB_REF'),serviceKey:required('LEAGUE_HUB_SECRET')}),
 core:configuredSource({projectRef:required('LEAGUE_CORE_REF'),serviceKey:required('LEAGUE_CORE_SECRET')}),
 sources,
 allowedOrigins:(Deno.env.get('LEAGUE_WEB_ORIGINS')||'').split(',').filter(Boolean),
 invitationBase:Deno.env.get('LEAGUE_ACTIVATION_URL')||'atlanticleague://activate',
});
Deno.serve(handler);
