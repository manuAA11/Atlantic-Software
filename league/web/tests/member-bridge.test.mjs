import test from 'node:test';
import assert from 'node:assert/strict';
import {createMemberBridge} from '../../backend/member-runtime.mjs';
test('member bridge validates live Core entitlement and routes canonical profile without moving a legacy link',async()=>{
 const calls=[],sourceRef='abcdefghijklmnopqrst';
 const hub={async rpc(name,args){calls.push({name,args});if(name==='league_member_gateway')return {source_profile_id:'legacy-profile',source_ref:sourceRef};if(name==='league_source')return {reserved:true};}};
 const core={async rpc(){return [{gym_id:'gym-a',source_ref:sourceRef,enabled:true}];}};
 const bridge=createMemberBridge({hub,core,sourceRef});
 assert.deepEqual(await bridge({actor:'new-mobile-identity',gym:'gym-a',action:'reserve',data:{class_id:'1'}}),{reserved:true});
 assert.equal(calls[0].args.p_actor,'new-mobile-identity');assert.equal(calls[1].args.p_profile_id,'legacy-profile');
 await assert.rejects(bridge({actor:'new-mobile-identity',gym:'gym-b',action:'calendar',data:{}}),/habilitado/);
 const denied=createMemberBridge({hub,core:{rpc:async()=>[{gym_id:'gym-a',source_ref:sourceRef,enabled:false}]},sourceRef});
 await assert.rejects(denied({actor:'a',gym:'gym-a',action:'reserve',data:{class_id:'1'}}),/habilitado/);
});
