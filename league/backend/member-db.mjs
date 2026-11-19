/** Small server transport. The administrative key is never a user credential. */
export function memberDatabase(url,key,fetcher=fetch){
 if(!/^https:\/\/[a-z0-9]{20}\.supabase\.co$/.test(url)||!key)throw Error('Invalid member database configuration');
 const client=jwt=>({key,withUser:token=>client(token),async request(path,options={}){
  const headers=new Headers({'Content-Type':'application/json',apikey:key});
  if(jwt)headers.set('Authorization','Bearer '+jwt);else if(key.startsWith('eyJ'))headers.set('Authorization','Bearer '+key);
  const response=await fetcher(url+path,{method:options.method||'GET',headers,body:options.body?JSON.stringify(options.body):undefined,signal:AbortSignal.timeout(20000)});
  const body=await response.json().catch(()=>null);
  if(!response.ok)throw Object.assign(Error(response.status<500?body?.message||'Operación no disponible.':'Servicio temporalmente no disponible.'),{status:response.status});
  return body;
 },async rpc(name,args){return this.request('/rest/v1/rpc/'+name,{method:'POST',body:args});}});
 return client(null);
}
