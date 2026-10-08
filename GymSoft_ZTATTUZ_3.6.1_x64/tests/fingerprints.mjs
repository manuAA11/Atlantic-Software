import assert from 'node:assert/strict';
import {database,root} from './migrations.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
const db=await database(); let checks=0;
const commercial=fs.existsSync(path.join(root,'sql/030_commercial.sql'));
const O=randomUUID(),A=randomUUID(),B=randomUUID(),R=randomUUID();
async function user(id){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[id,JSON.stringify({sub:id,session_id:id})]);await db.exec('set role authenticated');}
async function rpc(name,args=[]){return (await db.query(`select public.${name}(${args.map((_,i)=>'$'+(i+1)).join(',')}) as data`,args)).rows[0].data;}
function ok(value){assert.ok(value);checks++;}
async function deny(fn){await assert.rejects(fn);checks++;}
let a,b;
try{
 for(const id of [O,A,B,R])await db.query('insert into auth.users(id,email) values($1,$2)',[id,id+'@example.test']);
 if(commercial){
  await db.query('insert into private.software_owners(user_id) values($1)',[O]);
  async function create(id,name,hash){
   await user(O);const g=await rpc('owner_create_gym',[name,id+'@example.test',1000,'COP',3,7]);
   await user(id);await rpc('commercial_accept_invite',[g.activation_code]);await rpc('commercial_check_license',[hash.repeat(64),'Test PC']);
   await user(O);const detail=await rpc('owner_gym_detail',[g.gym_id]);await rpc('owner_set_device',[detail.devices[0].id,false,'Test']);
   await user(id);await rpc('commercial_check_license',[hash.repeat(64),'Test PC']);return g.gym_id;
  }
  a=await create(A,'A','a');b=await create(B,'B','b');
 }else{
  await user(A);a=await rpc('create_gym',['A']);await user(B);b=await rpc('create_gym',['B']);
 }
 await user(A);
 const c=(await db.query("insert into public.clients(gym_id,document,first_name) values($1,'FP1','Prueba') returning id",[a])).rows[0].id;
 const c2=(await db.query("insert into public.clients(gym_id,document,first_name) values($1,'FP2','Prueba 2') returning id",[a])).rows[0].id;
 const f=Buffer.concat([Buffer.from([70,77,82,0]),Buffer.alloc(40,1)]).toString('base64');
 let saved=await rpc('gym_fingerprints',[a,'save',c,f,null]);ok(saved.saved);
 let rows=await rpc('gym_fingerprints',[a,'list']);ok(rows.length===1&&rows[0].template===f);
 await deny(()=>rpc('gym_fingerprints',[a,'save',c,f,null])); // optimistic concurrency
 await deny(()=>rpc('gym_fingerprints',[a,'save',c2,f,null])); // exact duplicate
 await deny(()=>rpc('gym_fingerprints',[a,'save',c2,'bad',null]));
 await deny(()=>db.query('select * from private.client_fingerprints'));
 await user(B);await deny(()=>rpc('gym_fingerprints',[a,'list']));await deny(()=>rpc('gym_fingerprints',[b,'save',c,f,null]));
 ok((await rpc('gym_fingerprints',[b,'list'])).length===0);
 await user(R);await deny(()=>rpc('gym_fingerprints',[a,'list']));
 await user(A);saved=await rpc('gym_fingerprints',[a,'save',c,f,saved.revision]);ok(saved.saved);
 ok((await rpc('gym_fingerprints',[a,'delete',c,null,saved.revision])).saved);
 ok((await rpc('gym_fingerprints',[a,'list'])).length===0);
 await db.exec('reset role');await db.exec('set role anon');await deny(()=>rpc('gym_fingerprints',[a,'list']));
 await db.exec('reset role');
 const meta=(await db.query("select relrowsecurity from pg_class where oid='private.client_fingerprints'::regclass")).rows[0];ok(meta.relrowsecurity);
 // Migration is idempotent and does not write test or real biometric rows.
 await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_HUELLAS_3.5.0.sql'),'utf8'));checks++;
 console.log(`PASS: ${checks} comprobaciones SQL de huellas, permisos, aislamiento y cambios simultáneos (${commercial?'Comercial':'ZTATTUZ'}).`);
}finally{await db.close();}
