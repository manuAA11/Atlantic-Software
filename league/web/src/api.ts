import {createClient} from '@supabase/supabase-js';
import {secureStorage} from './storage';
const env=import.meta.env;
function secureUrl(value:string|undefined){try{const u=new URL(value||'');return u.protocol==='https:'&&!u.username&&!u.password?u.href:null;}catch{return null;}}
const url=secureUrl(env.VITE_SUPABASE_URL),key=env.VITE_SUPABASE_PUBLISHABLE_KEY||'';
export const legacyEndpoint=secureUrl(env.VITE_LEAGUE_ENDPOINT);
export const memberEndpoint=secureUrl(env.VITE_MEMBER_ENDPOINT);
export const accessEndpoint=secureUrl(env.VITE_MEMBER_ACCESS_ENDPOINT);
export const accessGym=env.VITE_MEMBER_GYM_ID||'';
export const routinesUrl=secureUrl(env.VITE_ROUTINES_URL);
export const supabase=url&&key.startsWith('sb_publishable_')?createClient(url,key,{auth:{storage:secureStorage,storageKey:'atlantic-league-auth',flowType:'pkce',persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}}):null;
export async function signInMember(document:string,password:string){
 if(!supabase||!accessEndpoint||!accessGym)throw Error('El acceso del gimnasio todavía no está habilitado.');
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
 try{
  const response=await fetch(accessEndpoint,{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({gym_id:accessGym,document:document.trim(),password}),signal:controller.signal});
  const body=await response.json();
  if(!response.ok||!body.data?.access_token||!body.data?.refresh_token)throw Error(body.message||'No se pudo iniciar sesión. Revisa tu cédula y contraseña.');
  const {error}=await supabase.auth.setSession(body.data);if(error)throw Error('No se pudo guardar tu sesión. Vuelve a intentarlo.');
 }finally{clearTimeout(timeout);}
}
export async function call<T>(action:string,data:Record<string,unknown>={},member=false):Promise<T>{
 const endpoint=memberEndpoint||(member?null:legacyEndpoint);
 if(!supabase||!endpoint)throw Error('Este servicio todavía no está habilitado para el piloto.');
 if(!navigator.onLine)throw Error('Sin conexión. Conéctate para consultar o confirmar cambios.');
 const {data:auth,error}=await supabase.auth.getSession();
 if(error||!auth.session)throw Error('Tu sesión necesita renovarse. Vuelve a entrar.');
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),20000);
 try{
  const response=await fetch(endpoint,{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json',Authorization:'Bearer '+auth.session.access_token},body:JSON.stringify({audience:'athlete',action,data}),signal:controller.signal});
  const body=await response.json();
  if(!response.ok)throw Error(body.message||'No se pudo confirmar la operación. Actualiza antes de repetirla.');
  return body.data as T;
 }catch(error){if(error instanceof DOMException&&error.name==='AbortError')throw Error('La respuesta tardó demasiado. Actualiza para comprobar el resultado.');throw error;}
 finally{clearTimeout(timeout);}
}
