import test from 'node:test';
import assert from 'node:assert/strict';
import {createCoreHandler} from '../platform/handler.mjs';
const project='syntheticprojectref0';
const source={project_ref:project,publishable_key:'sb_publishable_synthetic',context_rpc:'reception_account_context'};
function fixture(){
 const calls=[];
 const core={rpc:async(name,args)=>{calls.push({name,args});return name==='core_source_configuration'?source:{license_status:'ACTIVE'};}};
 const fetcher=async(url,options)=>{
  calls.push({url,options});
  assert.equal(options.headers.Authorization,'Bearer synthetic-jwt');
  return new Response(JSON.stringify(url.endsWith('/user')?{id:'user-id'}:{gym_id:'server-gym-id',role:'receptionist'}),{status:200});
 };
 const handler=createCoreHandler({core,fetcher});
 const request=(body={},headers={Authorization:'Bearer synthetic-jwt'})=>new Request('https://core.invalid/',{method:'POST',headers,body:JSON.stringify({project_ref:project,device_id:'a'.repeat(64),metadata:{architecture:'windows-x86'},...body})});
 return {handler,request,calls,core};
}
test('source validates token and server context supplies gym/user, ignoring spoofed fields',async()=>{
 const f=fixture();const result=await f.handler(f.request({gym_id:'attacker',user_id:'attacker'}));
 assert.equal(result.status,200);
 const call=f.calls.find(c=>c.name==='core_client_snapshot');assert.equal(call.args.p_gym_id,'server-gym-id');assert.equal(call.args.p_user_id,'user-id');
 assert.equal(f.calls.filter(c=>c.url).length,2);
});
test('no bearer is rejected before accessing Core',async()=>{
 const f=fixture();assert.equal((await f.handler(f.request({},{}))).status,401);assert.equal(f.calls.length,0);
});
test('unregistered source never becomes an arbitrary outbound host',async()=>{
 const f=fixture();f.core.rpc=async()=>null;
 assert.equal((await f.handler(f.request())).status,403);assert.equal(f.calls.length,0);
 assert.equal((await f.handler(f.request({project_ref:'evil.invalid/path'}))).status,400);
});
test('provider failures disclose no token or raw server errors',async()=>{
 const f=fixture();f.core.rpc=async()=>{throw new Error('secret-token-not-for-client');};
 const result=await f.handler(f.request());assert.equal(result.status,503);assert.equal((await result.text()).includes('secret-token'),false);
});
test('method and size are bounded',async()=>{
 const f=fixture();assert.equal((await f.handler(new Request('https://core.invalid/'))).status,405);
 assert.equal((await f.handler(f.request({extra:'x'.repeat(9000)}))).status,413);
});
