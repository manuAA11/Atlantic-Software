import {createConfiguredLeagueHandler} from '../../../runtime.mjs';
const config={"LEAGUE_SHARED_PROJECT":"true","LEAGUE_PILOT_ONLY":"true","LEAGUE_CORE_REF":"bawrakwhzkxmhmgkczqu","LEAGUE_CORE_PUBLIC_KEY":"sb_publishable_Qav1v1alA8kCaXeLX3f2fA_UKEfZQOq","LEAGUE_WEB_ORIGINS":"https://atlantic-league-piloto.ablebeech7.chatgpt.site","LEAGUE_ACTIVATION_URL":"https://atlantic-league-piloto.ablebeech7.chatgpt.site/"};
Deno.serve(createConfiguredLeagueHandler({get:(key)=>config[key]??Deno.env.get(key)}));
