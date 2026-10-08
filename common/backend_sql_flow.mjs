// HTTP/backend/migrated SQL integration. External transport and Vault are fixtures, not a live pilot.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {database,root} from './migrations.mjs';
import {createHandler} from '../marketing_backend/handler.mjs';
import {hmacHex,sha256} from '../marketing_backend/core/security.mjs';
const sql=await database();let checks=0;
const owner='10000000-0000-4000-8000-000000000001',admin='20000000-0000-4000-8000-000000000001';
const equal=(a,b)=>{assert.deepEqual(a,b);checks++;};
async function user(id){await sql.exec('reset role');await sql.query("select set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[id,JSON.stringify({sub:id,session_id:id})]);await sql.exec('set role authenticated');}
async function service(){await sql.exec('reset role');await sql.exec("select set_config('request.jwt.claim.sub','',false)");}
async function rpc(name,args={}){assert.match(name,/^[a-z_]+$/);return (await sql.query(`select public.${name}(${Object.keys(args).map((k,i)=>k+' => $'+(i+1)).join(',')}) as r`,Object.values(args))).rows[0].r;}
function where(filters,values){return Object.entries(filters).map(([name,value])=>{assert.match(name,/^[a-z_]+$/);assert.ok(value.startsWith('eq.'));values.push(value.slice(3));return `${name}=$${values.length}`;}).join(' and ');}
const db={rpc,
 async read(table,params){assert.match(table,/^[a-z_]+$/);const {limit,order,select,...filter}=params;const values=[];return (await sql.query(`select * from public.${table} where ${where(filter,values)}`,values)).rows;},
 async patch(table,filter,data){assert.match(table,/^[a-z_]+$/);const values=Object.values(data);const set=Object.keys(data).map((k,i)=>{assert.match(k,/^[a-z_]+$/);return `${k}=$${i+1}`;}).join(',');return (await sql.query(`update public.${table} set ${set} where ${where(filter,values)} returning *`,values)).rows;},
 credentials(gym,provider){return rpc('marketing_service_credentials',{p_gym_id:gym,p_provider:provider});},
 async connection(gym,provider){return (await this.read('marketing_connections',{gym_id:'eq.'+gym,provider:'eq.'+provider}))[0];},
 async context(gym,client){return (await rpc('marketing_service_contexts',{p_gym_id:gym,p_after:client-1,p_limit:1}))[0];}
};
try {
 for(const [id,email] of [[owner,'owner@example.test'],[admin,'admin@example.test']])await sql.query('insert into auth.users(id,email) values($1,$2)',[id,email]);
 let gym;
 if(fs.existsSync(path.join(root,'sql'))){
  const payload=JSON.parse(execFileSync(process.env.PYTHON||'python3',[path.join(root,'tests/owner_payloads.py')],{encoding:'utf8'}));
  await sql.query('insert into private.software_owners(user_id) values($1)',[owner]);await user(owner);const g=await rpc('owner_create_gym',payload.create);gym=g.gym_id;
  await user(admin);await rpc('commercial_accept_invite',{p_code:g.activation_code});const device={p_device_hash:'a'.repeat(64),p_device_name:'Cross-layer fixture'};await rpc('commercial_check_license',device);
  await user(owner);const d=(await rpc('owner_gym_detail',{p_gym_id:gym})).devices[0];await rpc('owner_set_device',{p_device_id:d.id,p_blocked:false,p_reason:'Local test'});await user(admin);await rpc('commercial_check_license',device);
 }else{await user(admin);gym=await rpc('create_gym',{p_name:'Cross-layer local test'});}
 const client=await rpc('marketing_create_test_client',{p_gym_id:gym});
 await sql.query("update public.clients set phone='3001234567',birth_date='1990-05-12',birthdate='1990-05-12' where id=$1",[client]);
 const plan=(await sql.query("insert into public.plans(gym_id,name,duration_days,price) values($1,'Cross-layer monthly',30,70000) returning id",[gym])).rows[0].id;
 await service();const today=(await sql.query('select private.gym_local_date($1)::text as day',[gym])).rows[0].day;await user(admin);
 const membership=(await sql.query("insert into public.memberships(gym_id,client_id,plan_id,start_date,end_date,amount,amount_paid,payment_method) values($1,$2,$3,($4::date-7),($4::date+20),0,0,'Efectivo') returning id",[gym,client,plan,today])).rows[0].id;
 const freeze=await rpc('membership_freeze',{p_gym_id:gym,p_membership_id:membership,p_request_id:'70000000-0000-4000-8000-000000000001',p_reason:'Local regression'});equal(freeze.days_added,7);
 await rpc('marketing_set_consent',{p_gym_id:gym,p_client_id:client,p_enabled:true,p_source:'Local fixture'});await service();
 // In-memory Vault stand-in: only synthetic secrets; production SQL credentials RPC remains in use.
 await sql.exec('create schema vault; create table vault.decrypted_secrets(id uuid primary key,decrypted_secret text);');
 const appSecret='local-fixture-app-secret-000000',keys={public_key:'pub_test_local_fixture',private_key:'prv_test_local_fixture',events_secret:'test_events_local_fixture',integrity_secret:'test_integrity_local_fixture'};
 const secrets=[['90000000-0000-4000-8000-000000000001',{app_secret:appSecret}],['90000000-0000-4000-8000-000000000002',{access_token:'local-fixture-token'}],['90000000-0000-4000-8000-000000000003',keys]];
 for(const [id,value] of secrets)await sql.query('insert into vault.decrypted_secrets values($1,$2)',[id,JSON.stringify(value)]);
 await sql.query('update private.marketing_platform set meta_config_secret_id=$1 where singleton',[secrets[0][0]]);
 for(const [provider,id] of [['META',secrets[1][0]],['WOMPI',secrets[2][0]]])await sql.query('insert into private.marketing_credentials(gym_id,provider,secret_id) values($1,$2,$3)',[gym,provider,id]);
 await sql.query("insert into public.marketing_connections(gym_id,provider,status,mode,provider_account_id,phone_number_id) values($1,'META','CONNECTED','test','waba-local','phone-local'),($1,'WOMPI','CONNECTED','test','','')",[gym]);
 await user(admin);await rpc('marketing_features',{p_gym_id:gym,p_flags:{whatsapp_enabled:true,chatbot_enabled:true,online_payments_enabled:true}});await service();
 const sent=[];let transaction;
 const fetcher=async(url,options)=>{if(String(url).startsWith('https://graph.facebook.com/')){sent.push(JSON.parse(options.body));return Response.json({messages:[{id:'wamid.local.'+sent.length}]});}equal(String(url),'https://sandbox.wompi.co/v1/transactions/local-transaction-1');return Response.json({data:transaction});};
 const base='https://local.example/functions/v1/marketing',handler=createHandler({db,baseURL:base,fetcher});
 const inbound=async(id,text)=>{
  const raw=JSON.stringify({object:'whatsapp_business_account',entry:[{id:'waba-local',changes:[{field:'messages',value:{metadata:{phone_number_id:'phone-local'},messages:[{id,from:'573001234567',timestamp:String(Math.floor(Date.now()/1000)),type:'text',text:{body:text}}]}}]}]});
  const signature='sha256='+await hmacHex(appSecret,raw);const result=await handler(new Request(base+'/webhooks/meta',{method:'POST',body:raw,headers:{'x-hub-signature-256':signature}}));assert.equal(result.status,200,await result.clone().text());checks++;return result.json();
 };
 await inbound('inbound-1','membership');assert.match(sent.at(-1).text.body,/fecha de nacimiento/);checks++;
 await inbound('inbound-2','12/05/1990');assert.match(sent.at(-1).interactive.body.text,/CONGELADA/);assert.ok(sent.at(-1).interactive.body.text.includes(freeze.new_end_date));checks+=2;
 const beforeDuplicate=sent.length;await inbound('inbound-2','12/05/1990');equal(sent.length,beforeDuplicate);
 await inbound('inbound-3','pay');assert.match(sent.at(-1).text.body,/https:\/\/local.example\/functions\/v1\/marketing\/pay\/GS-/);checks++;
 const request=(await sql.query('select * from public.payment_requests where gym_id=$1',[gym])).rows[0];equal(request.status,'PENDING');
 const redirect=await handler(new Request(base+'/pay/'+request.reference));equal(redirect.status,303);equal(new URL(redirect.headers.get('Location')).origin,'https://checkout.wompi.co');
 transaction={id:'local-transaction-1',reference:request.reference,status:'APPROVED',amount_in_cents:request.amount_in_cents,currency:'COP',created_at:new Date().toISOString()};
 const event={event:'transaction.updated',timestamp:Math.floor(Date.now()/1000),data:{transaction},signature:{properties:['transaction.id','transaction.status','transaction.amount_in_cents'],checksum:''}};
 event.signature.checksum=await sha256(transaction.id+transaction.status+transaction.amount_in_cents+event.timestamp+keys.events_secret);
 const webhook=signature=>handler(new Request(base+'/webhooks/wompi/'+gym,{method:'POST',body:JSON.stringify(event),headers:{'x-event-checksum':signature}}));
 equal((await webhook('0'.repeat(64))).status,403);equal((await sql.query('select status from public.payment_requests where id=$1',[request.id])).rows[0].status,'PENDING');
 const approved=await webhook(event.signature.checksum);equal(approved.status,200);equal((await approved.json()).duplicate,false);
 const duplicate=await webhook(event.signature.checksum);equal(duplicate.status,200);equal((await duplicate.json()).duplicate,true);
 equal((await sql.query('select count(*)::int n from public.payment_transactions where payment_request_id=$1',[request.id])).rows[0].n,1);
 equal((await sql.query('select count(*)::int n from public.membership_freezes where membership_id=$1',[membership])).rows[0].n,1);
 await user(admin);const snapshot=await rpc('reception_membership_snapshot',{p_gym_id:gym,p_client_id:client});equal(snapshot.status,'FROZEN');equal(snapshot.allowed,false);await service();
 await inbound('inbound-4','membership');assert.match(sent.at(-1).interactive.body.text,/CONGELADA/);checks++;
 equal((await handler(new Request(base+'/pay/'+request.reference))).status,200);
 console.log(`PASS: ${checks} cross-layer checks (HTTP, signed Meta/chatbot, real SQL freeze, payment link, signed Wompi renewal/idempotency). External transport and Vault simulated; no external pilot.`);
} finally {await sql.close();}
