// Public routing settings for the existing League pilot; no server credentials.
const defaults={LEAGUE_SHARED_PROJECT:'true',LEAGUE_PILOT_ONLY:'true',LEAGUE_CORE_REF:'bawrakwhzkxmhmgkczqu',LEAGUE_CORE_PUBLIC_KEY:'sb_publishable_Qav1v1alA8kCaXeLX3f2fA_UKEfZQOq',LEAGUE_WEB_ORIGINS:'https://atlantic-league-piloto.manuel411cm.chatgpt.site,https://atlantic-league-piloto.ablebeech7.chatgpt.site'};
const approvedCloudflareOrigin='https://atlantic-league.atlanticsoftware11.workers.dev';
export const memberEnvironment=env=>({get:key=>{
 const value=env.get(key)??defaults[key];
 if(key!=='LEAGUE_WEB_ORIGINS')return value;
 return [...new Set([...String(value??'').split(',').map(s=>s.trim()).filter(Boolean),approvedCloudflareOrigin])].join(',');
}});
