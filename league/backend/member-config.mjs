// Public routing settings from the existing owner-private pilot; no server credentials.
const defaults={LEAGUE_SHARED_PROJECT:'true',LEAGUE_PILOT_ONLY:'true',LEAGUE_CORE_REF:'bawrakwhzkxmhmgkczqu',LEAGUE_CORE_PUBLIC_KEY:'sb_publishable_Qav1v1alA8kCaXeLX3f2fA_UKEfZQOq',LEAGUE_WEB_ORIGINS:'https://atlantic-league-piloto.manuel411cm.chatgpt.site,https://atlantic-league-piloto.ablebeech7.chatgpt.site'};
export const memberEnvironment=env=>({get:key=>env.get(key)??defaults[key]});
