import {BackendDB} from '../core/database.mjs';

const response=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{
 'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});

// Every desktop request is validated by its original provider. No refresh token,
// secret client credential, user-editable metadata or client-supplied gym ID is trusted.
export function createCoreHandler({core,fetcher=fetch}) {
 return async request=>{
  try {
   if(request.method!=='POST')return response({error:'METHOD_NOT_ALLOWED'},405);
   const authorization=request.headers.get('Authorization')||'';
   if(!authorization.startsWith('Bearer ')||authorization.length>12000)return response({error:'LOGIN_REQUIRED'},401);
   const text=await request.text();
   if(text.length>8192)return response({error:'REQUEST_TOO_LARGE'},413);
   let body;try{body=JSON.parse(text);}catch{return response({error:'INVALID_REQUEST'},400);}
   if(!/^[a-z0-9]{20}$/.test(body.project_ref||'')||!/^[a-f0-9]{64}$/.test(body.device_id||''))return response({error:'INVALID_REQUEST'},400);
   const config=await core.rpc('core_source_configuration',{p_project_ref:body.project_ref});
   if(!config||config.project_ref!==body.project_ref||!['commercial_context','reception_account_context'].includes(config.context_rpc))return response({error:'SOURCE_NOT_REGISTERED'},403);
   const jwt=authorization.slice(7);
   if(jwt===config.publishable_key)return response({error:'LOGIN_REQUIRED'},401);
   const source=new BackendDB('https://'+config.project_ref+'.supabase.co',config.publishable_key,fetcher,jwt);
   const user=await source.request('/auth/v1/user');
   if(!user?.id)return response({error:'LOGIN_REQUIRED'},401);
   const context=await source.rpc(config.context_rpc);
   if(!context?.gym_id||!['admin','receptionist'].includes(context.role)||context.enabled===false)return response({error:'NOT_AUTHORIZED'},403);
   const result=await core.rpc('core_client_snapshot',{
    p_project_ref:body.project_ref,p_gym_id:context.gym_id,p_user_id:user.id,
    p_device_id:body.device_id,p_metadata:body.metadata||{},p_read_id:body.read_id||null,
   });
   return response(result);
  }catch(error){
   // Never echo provider errors: they can include JWTs, SQL arguments or credentials.
   return response({error:error?.status===401||error?.status===403?'NOT_AUTHORIZED':'CORE_UNAVAILABLE'},error?.status===401||error?.status===403?403:503);
  }
 };
}
