import test from 'node:test';
import assert from 'node:assert/strict';
import {chunkStorage} from '../mobile/src/lib/chunk-storage.ts';
import {workoutOutbox} from '../mobile/src/lib/outbox.ts';
function storage(){const entries=new Map();return {entries,getItem:async k=>entries.get(k)||null,setItem:async(k,v)=>{assert.ok(Buffer.byteLength(v)<=2048);entries.set(k,Buffer.from(v).toString());},removeItem:async k=>{entries.delete(k);}};}
test('large encrypted session adapter is atomic after a write failure and serializes competing writes',async()=>{
 const base=storage();let count=0;const cache=chunkStorage(base,()=>String(++count));
 const original='á🏋️汉'.repeat(1500);await cache.setItem('session',original);assert.equal(await cache.getItem('session'),original);
 const save=base.setItem;base.setItem=async(k,v)=>{if(k.endsWith('.3'))throw Error('Storage full');await save(k,v);};
 await assert.rejects(()=>cache.setItem('session','replacement'.repeat(500)),/Storage full/);
 assert.equal(await cache.getItem('session'),original);base.setItem=save;
 await Promise.all([cache.setItem('session','first'.repeat(2000)),cache.setItem('session','second'.repeat(2000))]);
 assert.equal(await cache.getItem('session'),'second'.repeat(2000));
 await cache.removeItem('session');assert.equal(await cache.getItem('session'),null);assert.equal(base.entries.size,0);
});
test('outbox preserves the exact UUID/body through ambiguous network failure, concurrent flush and another account',async()=>{
 const base=storage();let n=0;const cache=chunkStorage(base,()=>String(++n)),alice=workoutOutbox(cache,'alice'),bob=workoutOutbox(cache,'bob');
 const payload={id:'one',name:'Strength',started_at:'2026-10-23T12:00:00Z',sets:[{exercise_id:'bench',weight_kg:40,reps:8}]};
 await alice.add(payload);await alice.add(payload);assert.equal((await alice.list()).length,1);assert.equal((await bob.list()).length,0);
 const server=new Map();let first=true;
 const api={call:async(action,data)=>{if(server.has(data.id))assert.deepEqual(server.get(data.id),data);else server.set(data.id,structuredClone(data));if(first){first=false;throw Error('Response lost');}return {saved:true};}};
 await assert.rejects(()=>alice.flush(api));assert.equal((await alice.list()).length,1);
 await assert.rejects(()=>alice.add({...payload,name:'Edited after send'}));
 await Promise.all([alice.flush(api),alice.flush(api)]);assert.equal((await alice.list()).length,0);assert.equal(server.size,1);
});
