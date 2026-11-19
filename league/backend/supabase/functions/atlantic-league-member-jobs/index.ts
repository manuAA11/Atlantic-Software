import {createClient} from 'npm:@supabase/supabase-js@2.118.0';
import webPush from 'npm:web-push@3.6.7';
import {memberEnvironment} from '../../../member-config.mjs';
import {memberDatabase} from '../../../member-db.mjs';
import {createMemberBridge} from '../../../member-runtime.mjs';
import {createMemberJobsHandler} from '../../../member-jobs.mjs';
const env=memberEnvironment(Deno.env),url=env.get('SUPABASE_URL')!,key=env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const admin=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
async function rpc(name:string,args:Record<string,unknown>){const r=await admin.rpc(name,args);if(r.error)throw Error('Member job unavailable');return r.data;}
let settings=await rpc('league_member_settings',{p_action:'project.initialize',p_data:{url}});
if(!settings.vapid_public){const pair=webPush.generateVAPIDKeys();settings=await rpc('league_member_settings',{p_action:'vapid.initialize',p_data:{public:pair.publicKey,private:pair.privateKey}});}
webPush.setVapidDetails(env.get('LEAGUE_WEB_ORIGINS')!.split(',')[0],settings.vapid_public,settings.vapid_private);
const hub=memberDatabase(url,key),core={rpc:async(name:string,args:Record<string,unknown>)=>{
 const response=await fetch('https://'+env.get('LEAGUE_CORE_REF')+'.supabase.co/rest/v1/rpc/'+name,{method:'POST',headers:{apikey:env.get('LEAGUE_CORE_PUBLIC_KEY')!,'Content-Type':'application/json'},body:JSON.stringify(args),signal:AbortSignal.timeout(15000)});
 if(!response.ok)throw Error('Directory unavailable');return response.json();
}};
const bridge=createMemberBridge({hub,core,sourceRef:new URL(url).hostname.split('.')[0]});
Deno.serve(createMemberJobsHandler({secret:settings.job_key,jobs:(action:string,data:Record<string,unknown>)=>rpc('league_member_jobs',{p_action:action,p_data:data}),
 authorize:(actor:string,gym:string)=>bridge({actor,gym,action:'membership',data:{}}),
 sendPush:(subscription:unknown)=>webPush.sendNotification(subscription,JSON.stringify({type:'notice'}),{TTL:3600,urgency:'normal',timeout:15000})}));
