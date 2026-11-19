import {createClient} from 'npm:@supabase/supabase-js@2.118.0';
import {memberEnvironment} from '../../../member-config.mjs';
const env=memberEnvironment(Deno.env);
import {createMemberAccessHandler} from '../../../member-access.mjs';
const required=(name:string)=>{const value=env.get(name);if(!value)throw Error('Missing server configuration: '+name);return value;};
const url=required('SUPABASE_URL'),secret=required('SUPABASE_SERVICE_ROLE_KEY'),publicKey=required('SUPABASE_ANON_KEY');
const options={auth:{persistSession:false,autoRefreshToken:false,detectSessionInUrl:false}};
// Admin transport never signs in as a member. Each password exchange has its own client.
const admin=createClient(url,secret,options);
const auth={admin:admin.auth.admin,signInWithPassword:(credentials:{email:string;password:string})=>createClient(url,publicKey,options).auth.signInWithPassword(credentials)};
async function rpc(action:string,gym:string,data:Record<string,unknown>){const result=await admin.rpc('league_member_access',{p_action:action,p_gym:gym,p_data:data});if(result.error)throw Error('Member access unavailable');return result.data;}
const store={attempt:(gym:string,bucket:string)=>rpc('attempt',gym,{bucket}),resolve:(gym:string,document:string)=>rpc('resolve',gym,{document}),activate:(gym:string,client_id:string,auth_user_id:string)=>rpc('activate',gym,{client_id,auth_user_id})};
const settings=await admin.rpc('league_member_settings',{p_action:'get',p_data:{}});
if(settings.error||!settings.data?.access_pepper)throw Error('Member access configuration unavailable');
Deno.serve(createMemberAccessHandler({auth,store,pepper:settings.data.access_pepper,allowedOrigins:required('LEAGUE_WEB_ORIGINS').split(',').map(s=>s.trim()).filter(Boolean)}));
