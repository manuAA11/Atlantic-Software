import test from 'node:test';
import assert from 'node:assert/strict';
import {createReadFlights} from '../src/read-flight.ts';
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
test('20 concurrent catalog reads use one transport; sequential reads stay fresh',async()=>{
 const flights=createReadFlights(),gate=deferred();let calls=0;
 const load=()=>{calls++;return gate.promise;};
 const reads=Array.from({length:20},()=>flights.run('session-A','gym.catalog',{gym_id:'A'},load));
 await Promise.resolve();assert.equal(calls,1);gate.resolve(['catalog']);
 assert.deepEqual(await Promise.all(reads),Array.from({length:20},()=>['catalog']));
 await flights.run('session-A','gym.catalog',{gym_id:'A'},load);assert.equal(calls,2);
});
test('isolation covers session/claims, endpoint, gym, action and filters',async()=>{
 const flights=createReadFlights();let calls=0;const gate=deferred(),load=()=>{calls++;return gate.promise;};
 const reads=[
  flights.run('endpoint-A/token-A','gym.catalog',{gym_id:'A'},load),
  flights.run('endpoint-A/token-B','gym.catalog',{gym_id:'A'},load),
  flights.run('endpoint-B/token-A','gym.catalog',{gym_id:'A'},load),
  flights.run('endpoint-A/token-A','gym.catalog',{gym_id:'B'},load),
  flights.run('endpoint-A/token-A','gym.templates',{gym_id:'A'},load),
  flights.run('endpoint-A/token-A','gym.catalog',{gym_id:'A',query:'x'},load),
 ];await Promise.resolve();assert.equal(calls,6);gate.resolve([]);await Promise.all(reads);
});
test('mutations, critical reads and unknown actions are never shared',async()=>{
 for(const action of ['gym.reserve','gym.cancel','membership.details','gym.membership','snapshot','renewals.create','notifications.read','unknown']){
  const flights=createReadFlights();let calls=0;const load=async()=>++calls;
  await Promise.all([flights.run('A',action,{},load),flights.run('A',action,{},load)]);
  assert.equal(calls,2,action);
 }
});
test('errors are evicted and retry gets a fresh request',async()=>{
 const flights=createReadFlights();let calls=0;
 const load=async()=>{calls++;throw Error('network');};
 const reads=[flights.run('A','gym.catalog',{},load),flights.run('A','gym.catalog',{},load)];
 const results=await Promise.allSettled(reads);assert.ok(results.every(x=>x.status==='rejected'));assert.equal(calls,1);
 await assert.rejects(flights.run('A','gym.catalog',{},load),/network/);assert.equal(calls,2);
});
test('write completion prevents joining a read started before the write',async()=>{
 const flights=createReadFlights(),gate=deferred();let calls=0;
 const stale=flights.run('A','gym.catalog',{},()=>{calls++;return gate.promise;});
 await flights.run('A','catalog.save',{},async()=>({saved:true}));
 const fresh=flights.run('A','gym.catalog',{},async()=>{calls++;return 'fresh';});
 assert.equal(await fresh,'fresh');assert.equal(calls,2);gate.resolve('old');await stale;
});
test('logout invalidation and older completion do not evict a new flight',async()=>{
 const flights=createReadFlights(),old=deferred(),next=deferred();let calls=0;
 const first=flights.run('A','gym.catalog',{},()=>{calls++;return old.promise;});
 await Promise.resolve();flights.clear();
 const replacement=flights.run('A','gym.catalog',{},()=>{calls++;return next.promise;});
 old.resolve('old');await first;
 const joined=flights.run('A','gym.catalog',{},()=>{throw Error('duplicate');});
 assert.equal(joined,replacement);next.resolve('new');assert.equal(await joined,'new');assert.equal(calls,2);
});
