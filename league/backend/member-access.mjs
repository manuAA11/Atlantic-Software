/** Document/password access for registered Gym members. Dedicated Auth identities only. */
const id=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const failure=(status=401)=>Object.assign(new Error('No se pudo iniciar sesión. Revisa tu cédula y contraseña o consulta con el gimnasio.'),{status});
const encoder=new TextEncoder();
export function createMemberAccessHandler({auth,store,pepper,allowedOrigins=[]}){
 if(typeof pepper!=='string'||pepper.length<32)throw Error('A private member-access pepper is required.');
 const secret=crypto.subtle.importKey('raw',encoder.encode(pepper),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 const digest=async value=>new Uint8Array(await crypto.subtle.sign('HMAC',await secret,encoder.encode(value)));
 const hex=bytes=>Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
 return async request=>{
  const origin=request.headers.get('Origin');
  const headers={'Content-Type':'application/json','Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Vary':'Origin',...(origin&&allowedOrigins.includes(origin)?{'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Headers':'content-type,apikey','Access-Control-Allow-Methods':'POST,OPTIONS'}:{})};
  const respond=(body,status=200)=>Response.json(body,{status,headers});
  try{
   if(origin&&!allowedOrigins.includes(origin))throw failure(403);
   if(request.method==='OPTIONS')return new Response(null,{status:204,headers});
   if(request.method!=='POST')throw failure(405);
   const reader=request.body?.getReader();if(!reader)throw failure(400);let size=0;const chunks=[];
   while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>2048){await reader.cancel();throw failure(413);}chunks.push(value);}
   const bytes=new Uint8Array(size);let offset=0;for(const b of chunks){bytes.set(b,offset);offset+=b.length;}
   let input;try{input=JSON.parse(new TextDecoder().decode(bytes));}catch{throw failure(400);}
   if(!id.test(input?.gym_id||'')||typeof input?.document!=='string'||typeof input?.password!=='string')throw failure();
   const document=input.document.trim(),password=input.password;
   if(!/^[0-9]{5,20}$/.test(document)||password.length>80)throw failure();
   const scope=input.gym_id+':'+document;
   const bucket=hex(await digest('attempt:'+scope));
   if(!await store.attempt(input.gym_id,bucket))throw failure(429);
   // Constant-length digest comparison; no raw password or document is persisted/logged.
   const expected=await digest('credential:'+scope),actual=await digest('credential:'+input.gym_id+':'+password);
   let different=0;for(let i=0;i<expected.length;i++)different|=expected[i]^actual[i];
   if(different)throw failure();
   const client=await store.resolve(input.gym_id,document);
   if(!client?.client_id)throw failure();
   const identity=hex(await digest('identity:'+input.gym_id+':'+client.client_id));
   const email='member-'+identity.slice(0,48)+'@members.atlantic.invalid';
   const internalPassword=hex(await digest('auth-password:'+input.gym_id+':'+client.client_id));
   // The public document never becomes the password of a shared Gym/Core staff user.
   // Internal Auth credentials are unguessable and used only by this server.
   let signed=await auth.signInWithPassword({email,password:internalPassword});
   if(signed.error||!signed.data?.session){
    const created=await auth.admin.createUser({email,password:internalPassword,email_confirm:true,app_metadata:{atlantic_member_only:true}});
    if(created.error){
     // Another request may have provisioned the same deterministic identity.
     signed=await auth.signInWithPassword({email,password:internalPassword});
    }else signed=await auth.signInWithPassword({email,password:internalPassword});
   }
   const user=signed.data?.user,session=signed.data?.session;
   if(signed.error||!session?.access_token||!session.refresh_token||!id.test(user?.id||'')||user.app_metadata?.atlantic_member_only!==true)throw failure();
   await store.activate(input.gym_id,client.client_id,user.id);
   return respond({data:{access_token:session.access_token,refresh_token:session.refresh_token}});
  }catch(e){return respond({error:'ACCESS_DENIED',message:failure().message},[400,401,403,405,413,429].includes(e?.status)?e.status:503);}
 };
}
