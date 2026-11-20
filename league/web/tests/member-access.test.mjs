import test from 'node:test';
import assert from 'node:assert/strict';
import {createMemberAccessHandler} from '../../backend/member-access.mjs';
const gym='d0000000-0000-4000-8000-000000000004',user='a0000000-0000-4000-8000-000000000001';
function fixture({known=false,staff=false,blocked=false,exists=true}={}){
 let provisioned=known;const calls=[];
 const auth={async signInWithPassword(credentials){calls.push(['signIn',credentials]);return provisioned?{data:{user:{id:user,app_metadata:{atlantic_member_only:!staff}},session:{access_token:'test-access',refresh_token:'test-refresh'}},error:null}:{data:{},error:Error('unknown')};},admin:{async createUser(attributes){calls.push(['create',attributes]);provisioned=true;return {data:{user:{id:user}},error:null};}}};
 const store={async attempt(g,bucket){calls.push(['attempt',g,bucket]);return !blocked;},async resolve(g,d){calls.push(['resolve',g,d]);return exists?{client_id:'1'}:null;},async activate(...args){calls.push(['activate',...args]);}};
 const handler=createMemberAccessHandler({auth,store,pepper:'test-only-pepper-at-least-thirty-two-characters',allowedOrigins:['https://league.example']});
 const request=(document='123456789',password=document,origin='https://league.example')=>new Request('https://api.example/access',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({gym_id:gym,document,password})});
 return {handler,request,calls};
}
test('document/document automatically prepares member identity and returns a session without email verification',async()=>{
 const f=fixture();const result=await f.handler(f.request());assert.equal(result.status,200);assert.equal(result.headers.get('Cache-Control'),'no-store');
 assert.deepEqual((await result.json()).data,{access_token:'test-access',refresh_token:'test-refresh'});
 const created=f.calls.find(x=>x[0]==='create')[1];assert.equal(created.email_confirm,true);assert.ok(created.email.split('@')[0].length<=64);assert.equal(created.app_metadata.atlantic_member_only,true);assert.ok(!created.email.includes('123456789'));assert.notEqual(created.password,'123456789');assert.equal(created.password.length,64);
 assert.deepEqual(f.calls.find(x=>x[0]==='activate'),['activate',gym,'1',user]);
});
test('repeated access reuses dedicated identity without creating duplicates',async()=>{
 const f=fixture({known:true});assert.equal((await f.handler(f.request())).status,200);assert.equal(f.calls.filter(x=>x[0]==='create').length,0);
});
test('wrong password and unknown document return the same generic error without an account-creation step',async()=>{
 const wrong=fixture(),unknown=fixture({exists:false});const a=await wrong.handler(wrong.request('123456789','000000000')),b=await unknown.handler(unknown.request());
 assert.equal(a.status,401);assert.equal(b.status,401);assert.deepEqual(await a.json(),await b.json());assert.equal(wrong.calls.some(x=>x[0]==='create'),false);assert.equal(unknown.calls.some(x=>x[0]==='create'),false);
});
test('rate limit and foreign origin stop processing; staff identities never receive a mobile session',async()=>{
 const blocked=fixture({blocked:true});assert.equal((await blocked.handler(blocked.request())).status,429);assert.equal(blocked.calls.some(x=>x[0]==='resolve'),false);
 const origin=fixture();assert.equal((await origin.handler(origin.request('123456789','123456789','https://evil.example'))).status,403);assert.equal(origin.calls.length,0);
 const staff=fixture({known:true,staff:true});assert.equal((await staff.handler(staff.request())).status,401);assert.equal(staff.calls.some(x=>x[0]==='activate'),false);
});
