/** Revalidate Core/source membership before each reminder and each queued push. */
export function createMemberJobsHandler({secret,jobs,authorize,sendPush}){
 if(typeof secret!=='string'||secret.length<32)throw Error('A private job key is required');
 return async request=>{
  if(request.method!=='POST')return new Response(null,{status:405});
  const token=request.headers.get('Authorization')||'';
  if(token!=='Bearer '+secret)return new Response(null,{status:401});
  try{
   const targets=await jobs('targets',{});let reconciled=0,sent=0,failed=0;
   for(const target of targets){try{await authorize(target.actor,target.gym);await jobs('reconcile',target);reconciled++;}catch{failed++;}}
   if(sendPush)for(const item of await jobs('claim',{})){
    let outcome='RETRY';
    try{await authorize(item.athlete_id,item.gym_id);if(!await jobs('validate_delivery',{id:item.id})){await jobs('finish',{id:item.id,outcome:'OBSOLETE'});continue;}await sendPush({endpoint:item.endpoint,keys:{p256dh:item.p256dh,auth:item.auth}});outcome='SENT';sent++;}
    catch(e){if([404,410].includes(e?.statusCode))outcome='GONE';failed++;}
    await jobs('finish',{id:item.id,outcome});
   }
   return Response.json({reconciled,sent,failed},{headers:{'Cache-Control':'no-store'}});
  }catch{return Response.json({error:'JOB_FAILED'},{status:503});}
 };
}
