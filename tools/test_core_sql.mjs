import assert from 'node:assert/strict';
import fs from 'node:fs';
import {randomUUID} from 'node:crypto';
import {database} from '../GymSoft_Comercial_3.6.0/tests/migrations.mjs';
const db=await database();
const sql=fs.readFileSync(new URL('../supabase/migrations/20261022233147_atlantic_core_platform.sql',import.meta.url),'utf8');
let checks=0;
const ok=(a,b)=>{assert.deepEqual(a,b);checks++;};
const owner=randomUUID(), stranger=randomUUID(), gym=randomUUID();
const source='syntheticprojectref0';
async function actor(id,role='authenticated'){
 await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[id]);await db.exec('set role '+role);
}
async function call(action,data={}) {return (await db.query('select public.core_owner($1,$2) result',[action,data])).rows[0].result;}
try{
 await db.exec(sql);await db.exec(sql);
 const variant=fs.readFileSync(new URL('../supabase/migrations/20261022235250_atlantic_core_product_variants.sql',import.meta.url),'utf8');
 await db.exec(variant);await db.exec(variant); // Formal additive migration is re-applicable.
 await db.query('insert into auth.users(id,email) values($1,$2),($3,$4)',[owner,'owner@example.invalid',stranger,'other@example.invalid']);
 await db.query('insert into private.software_owners(user_id) values($1)',[owner]);
 await actor(stranger);await assert.rejects(()=>call('list'));checks++;
 await actor(owner);
 await call('register_source',{project_ref:source,publishable_key:'sb_publishable_synthetic',context_rpc:'reception_account_context'});
 await call('register_gym',{gym_id:gym,source_gym_id:gym,source_project_ref:source,name:'Synthetic Gym',price:200000,renewal_day:19,next_renewal_date:'2026-10-19'});
 let detail=await call('detail',{gym_id:gym});ok(detail.gym.gym_id,gym);ok(detail.payments.length,0);ok(detail.subscription.status,'ACTIVE');ok(detail.reminders.enabled,false);
 const payment={gym_id:gym,amount:200000,currency:'COP',period_start:'2026-10-19',paid_at:'2026-10-22T10:00:00Z',payment_method:'Transferencia',reference:'Synthetic only',idempotency_key:randomUUID()};
 let result=await call('record_payment',payment);ok(result.period_until,'2026-11-19');
 ok((await call('record_payment',payment)).id,result.id);
 await assert.rejects(()=>call('record_payment',{...payment,amount:400000}));checks++;
 await assert.rejects(()=>call('record_payment',{...payment,idempotency_key:randomUUID()}));checks++;
 detail=await call('detail',{gym_id:gym});ok(detail.payments.length,1);ok(detail.subscription.next_renewal_date,'2026-11-19');
 await call('set_status',{gym_id:gym,status:'ACTIVE',license_status:'SUSPENDED',reason:'Synthetic test'});
 await call('record_payment',{...payment,period_start:'2026-11-19',idempotency_key:randomUUID()});
 ok((await call('detail',{gym_id:gym})).gym.license_status,'SUSPENDED');
 await assert.rejects(()=>call('configure',{gym_id:gym,configuration:{command:'arbitrary'}}));checks++;
 await call('configure',{gym_id:gym,configuration:{update_channel:'beta',notifications_enabled:true}});
 await call('notify',{gym_id:gym,title:'Prueba',message:'Synthetic test notification',type:'INFO'});
 const release={variant:'ztattuz',version:'3.7.0',architecture:'windows-x86',channel:'beta',installer_url:'https://github.com/manuAA11/Atlantic-Software/releases/download/test/synthetic.exe',sha256:'a'.repeat(64),bytes:100,minimum_schema:'core-1',published:true};
 await call('publish_release',release);
 await assert.rejects(()=>call('publish_release',{...release,version:'3.7.1',installer_url:'https://evil.invalid/setup.exe'}));checks++;
 const metadata={device_name:'Synthetic PC',architecture:'windows-x86',os:'Windows',app_version:'3.7.0',edition:'reception',fingerprint_configured:true,biometric_secret:'must be discarded'};
 await assert.rejects(()=>db.query('select public.core_client_snapshot($1,$2,$3,$4,$5)',[source,gym,owner,'a'.repeat(64),metadata]));checks++;
 await actor(owner,'service_role');
 const snapshot=async project=>(await db.query('select public.core_client_snapshot($1,$2,$3,$4,$5) result',[project,gym,owner,'a'.repeat(64),metadata])).rows[0].result;
 result=await snapshot(source);ok(result.product_variant,'ztattuz');ok(result.notifications.length,1);ok(result.releases.length,1);ok(result.license_status,'SUSPENDED');
 await assert.rejects(()=>snapshot('otherprojectref000000'));checks++;
 // The same application receives global or gym-targeted releases. Other gyms,
 // architectures and channels must never leak into its available updates.
 await actor(owner);
 const secondGym=randomUUID();
 await call('register_gym',{gym_id:secondGym,source_gym_id:secondGym,source_project_ref:source,name:'Second Synthetic Gym',price:200000,renewal_day:19,next_renewal_date:'2026-10-19'});
 await call('configure',{gym_id:secondGym,configuration:{update_channel:'beta'}});
 await call('publish_release',{...release,gym_id:gym,version:'3.7.1'});
 await call('publish_release',{...release,gym_id:secondGym,version:'3.7.2'});
 await call('publish_release',{...release,version:'3.7.3',architecture:'windows-x64'});
 await call('publish_release',{...release,version:'3.7.4',channel:'stable'});
 await actor(owner,'service_role');
 result=await snapshot(source);
 ok(result.releases.map(r=>r.version).sort(),['3.7.0','3.7.1']);
 const second=(await db.query('select public.core_client_snapshot($1,$2,$3,$4,$5) result',[source,secondGym,owner,'b'.repeat(64),metadata])).rows[0].result;
 ok(second.releases.map(r=>r.version).sort(),['3.7.0','3.7.2']);
 ok(result.gym_id,gym);ok(second.gym_id,secondGym);

 await db.exec('reset role');ok((await db.query('select metadata from private.core_devices order by device_id limit 1')).rows[0].metadata,{fingerprint_configured:true});
 console.log(`CORE SQL ${checks} CHECKS PASS: owner scope, preserved IDs, payments, renewal19, no fake initial payments, notifications, architecture, telemetry, idempotency and explicit suspension.`);
}catch(error){console.error('CORE SQL FAIL:',error.message,error.code||'',error.where||'');process.exitCode=1;}finally{await db.close();}
