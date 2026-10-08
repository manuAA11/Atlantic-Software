import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {database,root} from './migrations.mjs';
const db=await database(); let checks=0;
const O='10000000-0000-4000-8000-000000000001',A='20000000-0000-4000-8000-000000000001',B='30000000-0000-4000-8000-000000000001';
const commercial=fs.existsSync(path.join(root,'sql'));
async function user(id){await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[id,JSON.stringify({sub:id,session_id:id})]);await db.exec('set role authenticated');}
async function rootUser(){await db.exec('reset role');await db.exec("select set_config('request.jwt.claim.sub','',false)");}
async function rpc(name,params={}){return (await db.query(`select public.${name}(${Object.keys(params).map((k,i)=>k+' => $'+(i+1)).join(',')}) as r`,Object.values(params))).rows[0].r;}
function equal(a,b,message){assert.deepEqual(a,b,message);checks++;}
async function clock(iso){await rootUser();await db.exec(`create or replace function private.gym_server_now() returns timestamptz language sql stable as $$select '${iso}'::timestamptz$$`);await user(A);}
try {
 for(const [id,email] of [[O,'owner@example.test'],[A,'admin@example.test'],[B,'other@example.test']])await db.query('insert into auth.users(id,email) values($1,$2)',[id,email]);
 let gym,other;
 if(commercial){
  const payload=JSON.parse(execFileSync(process.env.PYTHON||'python3',[path.join(root,'tests/owner_payloads.py')],{encoding:'utf8'}));
  await db.query('insert into private.software_owners(user_id) values($1)',[O]);await user(O);
  const g=await rpc('owner_create_gym',payload.create);gym=g.gym_id;other=(await rpc('owner_create_gym',{...payload.create,p_name:'Otro',p_email:'other@example.test'})).gym_id;
  await user(A);await rpc('commercial_accept_invite',{p_code:g.activation_code});
  const license={p_device_hash:'a'.repeat(64),p_device_name:'Prueba aislada'};await rpc('commercial_check_license',license);
  await user(O);const d=(await rpc('owner_gym_detail',{p_gym_id:gym})).devices[0];await rpc('owner_set_device',{p_device_id:d.id,p_blocked:false,p_reason:'Prueba'});
  await user(A);await rpc('commercial_check_license',license);
 }else{await user(A);gym=await rpc('create_gym',{p_name:'Consumo diario'});await user(B);other=await rpc('create_gym',{p_name:'Otro'});await user(A);}
 const ins=async(t,row)=> (await db.query(`insert into public.${t}(${Object.keys(row)}) values(${Object.keys(row).map((_,i)=>'$'+(i+1))}) returning id`,Object.values(row))).rows[0].id;
 const cid=await ins('clients',{gym_id:gym,document:'MK1',first_name:'Juan',phone:'3001234567'});
 const pid=await ins('plans',{gym_id:gym,name:'Mensual prueba',duration_days:30,price:70000});
 const ticket=await ins('plans',{gym_id:gym,name:'Tiquetera prueba',duration_days:60,duration_months:2,entry_limit:15,price:90000});
 await rpc('marketing_set_consent',{p_gym_id:gym,p_client_id:cid,p_enabled:true,p_source:'Formulario'});
 const consent=(await db.query('select whatsapp_opt_in,whatsapp_opt_in_by,whatsapp_opt_in_source from public.clients where id=$1',[cid])).rows[0];
 equal([consent.whatsapp_opt_in,consent.whatsapp_opt_in_by,consent.whatsapp_opt_in_source],[true,A,'Formulario']);
 const denied=async(fn,re=/permiso|permission|no válid|referencia|plantilla|sandbox|moneda|ambiente|actualiza|cambió|condición|whatsapp|otra solicitud/i)=>{await assert.rejects(fn,re);checks++;};
 await denied(()=>rpc('marketing_summary',{p_gym_id:other}));
 await denied(()=>rpc('marketing_service_credentials',{p_gym_id:gym,p_provider:'META'}));
 const tmpl=await rpc('marketing_save_template',{p_gym_id:gym,p_data:{name:'saludo_gym',body:'Hola {{nombre}}',variables:['nombre']}});
 const data={name:'Vence pronto',body:'Hola {{nombre}}',trigger_type:'MEMBERSHIP_BEFORE',trigger_options:{value:3,time:'09:00'},conditions:[],frequency:{count:1,hours:24},template_id:tmpl.id};
 let rule=await rpc('marketing_save_automation',{p_gym_id:gym,p_data:data});equal(rule.enabled,false);
 await denied(()=>rpc('marketing_automation_action',{p_gym_id:gym,p_id:rule.id,p_revision:rule.revision,p_action:'enable'}));
 await rootUser();
 await db.query("insert into public.marketing_connections(gym_id,provider,status,mode) values($1,'META','CONNECTED','test'),($1,'WOMPI','CONNECTED','test')",[gym]);
 await user(A);await denied(()=>rpc('marketing_automation_action',{p_gym_id:gym,p_id:rule.id,p_revision:rule.revision,p_action:'enable'}));
 await rootUser();await db.query("update public.whatsapp_templates set status='APPROVED' where id=$1",[tmpl.id]);await user(A);
 rule=await rpc('marketing_automation_action',{p_gym_id:gym,p_id:rule.id,p_revision:rule.revision,p_action:'enable'});equal(rule.enabled,true);
 rule=await rpc('marketing_save_automation',{p_gym_id:gym,p_id:rule.id,p_revision:rule.revision,p_data:{...data,enabled:true,name:'Vence 3 días'}});
 await denied(()=>rpc('marketing_save_automation',{p_gym_id:gym,p_id:rule.id,p_revision:1,p_data:data}));
 const copy=await rpc('marketing_automation_action',{p_gym_id:gym,p_id:rule.id,p_revision:rule.revision,p_action:'duplicate'});equal(copy.enabled,false);
 equal((await rpc('marketing_automation_action',{p_gym_id:gym,p_id:copy.id,p_revision:copy.revision,p_action:'delete'})).deleted_at!==null,true);
 await denied(()=>rpc('marketing_save_automation',{p_gym_id:gym,p_data:{...data,conditions:[{field:'gym_id',op:'eq',value:gym}]}}));
 await rpc('marketing_features',{p_gym_id:gym,p_flags:{whatsapp_enabled:true,marketing_automation_enabled:true,online_payments_enabled:true}});
 const enqueue=key=>rpc('marketing_service_enqueue',{p_gym_id:gym,p_automation_id:rule.id,p_client_id:cid,p_dedupe_key:key,p_phone:'573001234567',p_body:'Hola Juan',p_parameters:['Juan']});
 await rootUser();equal((await enqueue('first')).status,'QUEUED');equal((await enqueue('first')).reason,'DUPLICATE');equal((await enqueue('second')).reason,'FREQUENCY');
 await user(A);await rpc('marketing_set_consent',{p_gym_id:gym,p_client_id:cid,p_enabled:false});await rootUser();equal((await enqueue('third')).status,'NO_CONSENT');
 await user(A);const summary=await rpc('marketing_summary',{p_gym_id:gym});equal([summary.queued,summary.recovered_cents],[1,0]);
 await rootUser();await denied(()=>rpc('marketing_service_payment_request',{p_gym_id:gym,p_client_id:cid,p_plan_id:pid,p_key:'sandbox-real-client'}));
 await user(A);const test=await rpc('marketing_create_test_client',{p_gym_id:gym});equal(test,await rpc('marketing_create_test_client',{p_gym_id:gym}));await rootUser();
 const request=(plan,key)=>rpc('marketing_service_payment_request',{p_gym_id:gym,p_client_id:test,p_plan_id:plan,p_key:key});
 const req=await request(pid,'payment-request-1');equal((await request(pid,'payment-request-1')).id,req.id);await denied(()=>request(ticket,'payment-request-1'));
 const txn={id:'sandbox-tx-1',reference:req.reference,status:'APPROVED',amount_in_cents:7000000,currency:'COP',mode:'test',created_at:new Date().toISOString()};
 const apply=(tx,g=gym)=>rpc('marketing_service_apply_payment',{p_gym_id:g,p_transaction:tx});
 for(const created_at of ['2026-10-08','2026-10-08T02:30:00'])
  await denied(()=>apply({...txn,created_at}),/timezone/i);
 for(const change of [{amount_in_cents:1},{currency:'USD'},{reference:'wrong'},{mode:'prod'}])await denied(()=>apply({...txn,...change}));
 await denied(()=>apply(txn,other));
 let paid=await apply(txn);equal(paid.duplicate,false);equal((await apply(txn)).duplicate,true);
 equal(new Date((await db.query('select provider_created_at from public.payment_transactions where provider_transaction_id=$1',[txn.id])).rows[0].provider_created_at).toISOString(),txn.created_at);
 const m=(await db.query('select * from public.memberships where id=$1',[paid.membership_id])).rows[0];equal([m.amount,m.amount_paid,m.payment_source],[0,0,'WOMPI_TEST']);
 const req2=await request(pid,'payment-request-2');const paid2=await apply({...txn,id:'sandbox-tx-2',reference:req2.reference});equal(new Date(paid2.end_date)>new Date(paid.end_date),true);
 const tr=await request(ticket,'payment-request-ticket');const tp=await apply({...txn,id:'sandbox-tx-3',reference:tr.reference,amount_in_cents:9000000});
 equal((await db.query('select entry_limit from public.memberships where id=$1',[tp.membership_id])).rows[0].entry_limit,15);
 const decline=await request(pid,'payment-request-decline');const dt={...txn,id:'sandbox-tx-4',reference:decline.reference};equal((await apply({...dt,status:'DECLINED'})).status,'DECLINED');equal((await apply(dt)).duplicate,false);
 equal((await apply({...txn,id:'extra-charge'})).requires_review,true);
 equal(await rpc('marketing_service_limit',{p_gym_id:gym,p_bucket:'verification/test',p_max:1,p_seconds:60}),true);equal(await rpc('marketing_service_limit',{p_gym_id:gym,p_bucket:'verification/test',p_max:1,p_seconds:60}),false);
 equal((await db.query("select count(*)::int n from public.marketing_audit where action='PAYMENT_PROCESSED' and gym_id=$1",[gym])).rows[0].n,4);
 await user(A);equal((await db.query('select count(*)::int n from public.marketing_audit where gym_id=$1',[other])).rows[0].n,0);
 await denied(()=>db.query('select * from private.marketing_credentials'));
 await rootUser();const contexts=await rpc('marketing_service_contexts',{p_gym_id:gym});equal(contexts.length,2);

 await user(A);const workspace=await rpc('marketing_workspace',{p_gym_id:gym});
 equal(workspace.plans.some(p=>p.id===pid)&&workspace.plans.some(p=>p.id===ticket),true);
 equal(workspace.payments.length,4);equal(workspace.payments.every(p=>p.client_name==='PRUEBA Integraciones'),true);
 equal(workspace.payments.some(p=>p.transaction_id==='sandbox-tx-3'),true);
 equal(new Date(workspace.payments.find(p=>p.id===req.id).provider_created_at).toISOString(),txn.created_at);
 await denied(()=>rpc('marketing_workspace',{p_gym_id:other}));
 await rpc('marketing_set_consent',{p_gym_id:gym,p_client_id:cid,p_enabled:true});
 await rpc('marketing_features',{p_gym_id:gym,p_flags:{chatbot_enabled:true}});
 await rootUser();await db.query("update public.clients set birth_date='1990-05-12',birthdate='1990-05-12' where id=$1",[cid]);
 let claimed=await rpc('marketing_service_claim',{p_limit:20});const pendingMessage=claimed.find(x=>x.dedupe_key==='first');equal(Boolean(pendingMessage),true);
 await rpc('marketing_service_send_result',{p_id:pendingMessage.id,p_claim_id:pendingMessage.claim_id,p_status:'UNCERTAIN',p_error:'PROVIDER_UNCERTAIN'});
 equal((await enqueue('after-uncertain')).reason,'FREQUENCY');equal((await rpc('marketing_service_claim',{p_limit:20})).some(x=>x.id===pendingMessage.id),false);
 await rpc('marketing_service_status',{p_gym_id:gym,p_message_id:'wamid.fast',p_status:'READ',p_at:new Date().toISOString()});
 await rpc('marketing_service_send_result',{p_id:pendingMessage.id,p_claim_id:pendingMessage.claim_id,p_status:'SENT',p_provider_id:'wamid.fast'});
 equal((await db.query('select status from public.marketing_messages where id=$1',[pendingMessage.id])).rows[0].status,'READ');
 await rpc('marketing_service_status',{p_gym_id:gym,p_message_id:'wamid.fast',p_status:'SENT',p_at:new Date().toISOString()});
 equal((await db.query('select status from public.marketing_messages where id=$1',[pendingMessage.id])).rows[0].status,'READ');
 const testMessage=await rpc('marketing_service_test_message',{p_gym_id:gym,p_client_id:cid,p_template_id:tmpl.id,p_key:'ui-test-key-1',p_body:'Hola Juan',p_parameters:['Juan']});
 claimed=await rpc('marketing_service_claim',{p_limit:1,p_message_id:testMessage});equal(claimed[0].id,testMessage);
 await db.query("update public.marketing_messages set claimed_at=now()-interval '4 minutes' where id=$1",[testMessage]);await rpc('marketing_service_claim',{p_limit:1});
 equal((await db.query('select status from public.marketing_messages where id=$1',[testMessage])).rows[0].status,'UNCERTAIN');
 const chat=(sender,action,data={})=>rpc('marketing_service_chat',{p_gym_id:gym,p_sender:sender,p_action:action,p_data:data});
 const phone='573001234567';const inbound=await chat(phone,'inbound');equal(inbound.state,'NEED_DOB');equal(inbound.membership,undefined);
 const wrong=await chat(phone,'verify',{birth_date:'1980-05-12'});equal(wrong.state,'VERIFICATION_FAILED');equal(wrong.client_id,undefined);
 equal((await chat(phone,'verify',{birth_date:'1990-05-12'})).state,'VERIFIED');equal((await chat(phone,'session')).client_id,cid);
 equal((await chat(phone,'handoff')).state,'HUMAN');equal((await chat(phone,'inbound')).state,'HUMAN');
 await user(A);await rpc('marketing_conversation_mode',{p_gym_id:gym,p_id:inbound.conversation_id,p_mode:'BOT'});await rootUser();
 await db.query("update public.clients set phone='3009990000' where id=$1",[cid]);equal((await chat(phone,'session')).state,'NEED_LINK_DETAILS');
 const stranger='573118889999';const unknown=await chat(stranger,'inbound');equal(unknown.state,'NEED_LINK_DETAILS');equal(unknown.membership,undefined);
 equal((await chat(stranger,'request_link',{name:'Juan',birth_date:'1990-05-12'})).state,'LINK_PENDING');equal((await chat(stranger,'inbound')).state,'LINK_PENDING');
 const link=(await db.query("select id from public.chatbot_link_requests where gym_id=$1 and conversation_id=$2 and status='PENDING'",[gym,unknown.conversation_id])).rows[0].id;
 await db.query("update public.gym_users set role='receptionist' where gym_id=$1 and user_id=$2",[gym,A]);await user(A);
 equal((await rpc('marketing_reception_workspace',{p_gym_id:gym})).links.length,1);
 await denied(()=>rpc('marketing_workspace',{p_gym_id:gym}));await denied(()=>rpc('marketing_reception_workspace',{p_gym_id:other}));
 await denied(()=>rpc('marketing_features',{p_gym_id:gym,p_flags:{chatbot_enabled:false}}));
 await rpc('marketing_review_link',{p_gym_id:gym,p_id:link,p_client_id:cid,p_approved:true});equal((await rpc('marketing_reception_workspace',{p_gym_id:gym})).links.length,0);
 await rootUser();equal((await chat(stranger,'session')).client_id,cid);
 await db.query("update public.gym_users set role='admin' where gym_id=$1 and user_id=$2",[gym,A]);
 await db.query("update public.whatsapp_conversations set verified_until=now()-interval '1 minute' where gym_id=$1 and sender_number=$2",[gym,stranger]);equal((await chat(stranger,'session')).membership,undefined);
 const bad='573222222222';for(let i=0;i<6;i++)await chat(bad,'verify',{birth_date:'2000-01-01'});equal((await chat(bad,'session')).state,'LOCKED');
 if(commercial){await user(O);const status=await rpc('owner_marketing_status',{p_gym_id:gym});equal(status.chatbot_enabled,true);equal(JSON.stringify(status).includes('secret'),false);await user(A);await denied(()=>rpc('owner_marketing_status',{p_gym_id:gym}),/propietario|owner|permission|habilitado/i);}
 await user(A);await rpc('marketing_features',{p_gym_id:gym,p_flags:{chatbot_enabled:false}});await rootUser();equal((await chat(phone,'inbound')).state,'DISABLED');
 // Local Vault stand-in tests the setup contract; hosted encryption is not simulated proof.
 await rootUser();await db.exec(`create schema vault;
 create table vault.decrypted_secrets(id uuid primary key default gen_random_uuid(),decrypted_secret text,name text);
 create function vault.create_secret(text,text,text) returns uuid language sql as $$insert into vault.decrypted_secrets(decrypted_secret,name) values($1,$2) returning id$$;
 create function vault.update_secret(uuid,text) returns void language sql as $$update vault.decrypted_secrets set decrypted_secret=$2 where id=$1$$;`);
 const platform={app_id:'12345678',config_id:'87654321',app_secret:'x'.repeat(32),verify_token:'v'.repeat(40),onboarding_origin:'https://authorized.test',onboarding_url:'https://authorized.test/conectar/'};
 await user(A);await denied(()=>rpc('marketing_service_configure_meta',{p_data:platform}));await rootUser();
 for(const patch of [{app_id:'bad'},{app_secret:''},{onboarding_origin:'http://authorized.test'},
  {onboarding_url:'https://attacker.test/'},{production_allowed:true}])
  await denied(()=>rpc('marketing_service_configure_meta',{p_data:{...platform,...patch}}),/configuraci/i);
 equal((await rpc('marketing_service_configure_meta',{p_data:platform})).configured,true);
 equal(await rpc('marketing_service_platform'),platform);
 await rpc('marketing_service_configure_meta',{p_data:{...platform,app_secret:'y'.repeat(32)}});
 equal((await db.query('select count(*)::int n from vault.decrypted_secrets')).rows[0].n,1);
 equal((await rpc('marketing_service_platform')).app_secret,'y'.repeat(32));
 console.log(`PASS: ${checks} contratos Marketing de automatizaciones, consentimiento, permisos, sandbox, renovación e idempotencia (${commercial?'comercial':'ZTATTUZ'}).`);
}catch(e){console.error('FAIL MARKETING:',e.stack||e.message,e.where||'',e.detail||'');process.exitCode=1;}finally{await db.close();}
