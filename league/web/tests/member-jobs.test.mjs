import test from 'node:test';
import assert from 'node:assert/strict';
import {createMemberJobsHandler} from '../../backend/member-jobs.mjs';
const secret='test-job-secret-at-least-thirty-two-characters';
const request=key=>new Request('https://example.test/jobs',{method:'POST',headers:{Authorization:'Bearer '+key}});
test('worker rejects missing job key without reading or sending anything',async()=>{
 let touched=false;
 const handler=createMemberJobsHandler({secret,jobs:async()=>{touched=true;},authorize:async()=>{}});
 assert.equal((await handler(request('wrong'))).status,401);assert.equal(touched,false);
});
test('worker suppresses stale reminders and removes invalid subscriptions after provider 410',async()=>{
 const finished=[],sent=[];
 const jobs=async(action,data)=>{
  if(action==='targets')return [{actor:'a',gym:'g'}];
  if(action==='reconcile')return true;
  if(action==='claim')return [{id:'obsolete',athlete_id:'a',gym_id:'g',endpoint:'https://fcm.googleapis.com/old'},{id:'gone',athlete_id:'a',gym_id:'g',endpoint:'https://fcm.googleapis.com/gone',p256dh:'key',auth:'secret'},{id:'live',athlete_id:'a',gym_id:'g',endpoint:'https://fcm.googleapis.com/live',p256dh:'key',auth:'secret'}];
  if(action==='validate_delivery')return data.id!=='obsolete';
  if(action==='finish'){finished.push(data);return true;}
 };
 const handler=createMemberJobsHandler({secret,jobs,authorize:async()=>true,sendPush:async subscription=>{sent.push(subscription.endpoint);if(subscription.endpoint.endsWith('gone'))throw {statusCode:410};}});
 const res=await handler(request(secret));assert.equal(res.status,200);
 assert.deepEqual(finished,[{id:'obsolete',outcome:'OBSOLETE'},{id:'gone',outcome:'GONE'},{id:'live',outcome:'SENT'}]);
 assert.equal(sent.some(x=>x.endsWith('old')),false);
});
