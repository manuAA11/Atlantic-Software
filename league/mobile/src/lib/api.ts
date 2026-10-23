import 'react-native-url-polyfill/auto';
import {AppState,Platform} from 'react-native';
import {createClient,processLock} from '@supabase/supabase-js';
import {secureStorage} from './storage';
const url=process.env.EXPO_PUBLIC_SUPABASE_URL||'',key=process.env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY||'';
export const endpoint=process.env.EXPO_PUBLIC_LEAGUE_ENDPOINT||'';
export const configured=/^https:\/\/[a-z0-9]{20}\.supabase\.co$/.test(url)&&key.startsWith('sb_publishable_')&&/^https:\/\/[a-z0-9]{20}\.supabase\.co\/functions\/v1\/atlantic-league$/.test(endpoint);
export const supabase=configured?createClient(url,key,{auth:{storage:secureStorage,storageKey:'atlantic-league-auth',autoRefreshToken:true,persistSession:Platform.OS!=='web',detectSessionInUrl:false,flowType:'pkce',lock:processLock}}):null;
// Suspension stops the refresh timer. The SDK refreshes the session after foregrounding.
if(supabase&&Platform.OS!=='web'){
 if(AppState.currentState==='active')supabase.auth.startAutoRefresh();
 AppState.addEventListener('change',state=>{if(state==='active')supabase.auth.startAutoRefresh();else supabase.auth.stopAutoRefresh();});
}
export type LeagueApi={call:<T=unknown>(action:string,data?:Record<string,unknown>)=>Promise<T>};
export class ApiError extends Error{constructor(message:string,public code:string,public status:number){super(message);}}
export const liveApi:LeagueApi={async call<T>(action:string,data:Record<string,unknown>={}){
 if(!supabase)throw new ApiError('La conexión de pruebas todavía no está configurada.','NOT_CONFIGURED',503);
 const {data:sessionData,error}=await supabase.auth.getSession();
 if(error||!sessionData.session)throw new ApiError('Inicia sesión para continuar.','LOGIN_REQUIRED',401);
 let response:Response;
 try{response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+sessionData.session.access_token},body:JSON.stringify({audience:'athlete',action,data}),signal:AbortSignal.timeout(20000)});}catch{throw new ApiError('No hay conexión. Tus entrenamientos guardados se enviarán cuando vuelvas a conectarte.','OFFLINE',0);}
 const value=await response.json().catch(()=>({}));
 if(!response.ok)throw new ApiError(value.message||'No se pudo completar la operación. Inténtalo de nuevo.',value.error||'REQUEST_FAILED',response.status);
 return value.data as T;
}};
