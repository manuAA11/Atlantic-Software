import {IntegrationError} from './security.mjs';
// Server-only transport. The desktop uses its own JWT and public project key.
export class BackendDB {
 constructor(url,key,fetcher=fetch,bearer=key){this.url=url.replace(/\/$/,'');this.key=key;this.bearer=bearer;this.fetcher=fetcher;}
 withUser(jwt){return new BackendDB(this.url,this.key,this.fetcher,jwt);}
 async request(path,{method='GET',body,headers={}}={}){
  let r;try{r=await this.fetcher(this.url+path,{method,headers:{apikey:this.key,Authorization:'Bearer '+this.bearer,'Content-Type':'application/json',...headers},...(body!==undefined?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(15000)});}catch{throw new IntegrationError('DATABASE_UNAVAILABLE','No se pudo confirmar la respuesta del servidor.',503);}
  let data;try{data=await r.json();}catch{data=null;}
  if(!r.ok){
   const auth=['42501','PGRST301','PGRST302'].includes(data?.code)||r.status===401||r.status===403;
   // Provider credentials can be parameters of a failed RPC. Never echo details/hint/query.
   throw new IntegrationError(auth?'NOT_AUTHORIZED':'DATABASE_REJECTED',auth?'Tu sesión no tiene permiso para esta operación.':'No se pudo completar la operación. Actualiza los datos y revisa la configuración.',auth?403:400);
  }return data;
 }
 rpc(name,args={}){return this.request('/rest/v1/rpc/'+name,{method:'POST',body:args});}
 read(table,params={}){return this.request('/rest/v1/'+table+'?'+new URLSearchParams(params));}
 patch(table,filter,body){return this.request('/rest/v1/'+table+'?'+new URLSearchParams(filter),{method:'PATCH',body,headers:{Prefer:'return=representation'}});}
 insert(table,body){return this.request('/rest/v1/'+table,{method:'POST',body,headers:{Prefer:'return=representation'}});}
 async authorize(jwt,gym,reception=false){
  if(!jwt||jwt===this.key)throw new IntegrationError('LOGIN_REQUIRED','Inicia sesión para continuar.',401);
  const user=await this.withUser(jwt).request('/auth/v1/user');
  if(!user?.id)throw new IntegrationError('LOGIN_REQUIRED','Inicia sesión para continuar.',401);
  return this.withUser(jwt).rpc('marketing_access',{p_gym_id:gym,p_reception:reception});
 }
 async connection(gym,provider){return (await this.read('marketing_connections',{gym_id:'eq.'+gym,provider:'eq.'+provider,limit:'1'}))[0];}
 credentials(gym,provider){return this.rpc('marketing_service_credentials',{p_gym_id:gym,p_provider:provider});}
 async context(gym,client){return (await this.rpc('marketing_service_contexts',{p_gym_id:gym,p_after:Number(client)-1,p_limit:1})).find(c=>String(c.client_id)===String(client));}
}
