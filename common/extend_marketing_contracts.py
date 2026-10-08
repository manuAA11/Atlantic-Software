from pathlib import Path
R=Path(__file__).resolve().parents[1];p=R/'common/marketing_contracts.mjs';s=p.read_text();at=s.index(' console.log(`PASS:')
s=s[:at]+'''
 await user(A);const workspace=await rpc('marketing_workspace',{p_gym_id:gym});
 equal(workspace.plans.some(p=>p.id===pid)&&workspace.plans.some(p=>p.id===ticket),true);
 equal(workspace.payments.length,4);equal(workspace.payments.every(p=>p.client_name==='PRUEBA Integraciones'),true);
 equal(workspace.payments.some(p=>p.transaction_id==='sandbox-tx-3'),true);
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
''' +s[at:];s=s.replace("e.message,e.where||''", "e.stack||e.message,e.where||''");s=s.replace(" await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_MARKETING.sql'),'utf8'));",'');p.write_text(s)
p=R/'backend/tests/http.test.mjs';s=p.read_text().replace("field:'smb_message_echoes',value:{message_echoes", "field:'smb_message_echoes',value:{metadata:{phone_number_id:'123'},message_echoes")
s+='''\ntest('WABA template updates reach every authorized gym phone',async()=>{const patched=[];const raw=JSON.stringify({object:'whatsapp_business_account',entry:[{id:'waba',changes:[{field:'message_template_status_update',value:{event:'APPROVED',message_template_id:'t1'}}]}]});const db={rpc:async(n)=>n==='marketing_service_platform'?{app_secret:'secret'}:[],read:async()=>[{gym_id:gym},{gym_id:'other'}],patch:async(t,filter)=>patched.push(filter.gym_id)};await metaWebhook(db,base,raw,'sha256='+await hmacHex('secret',raw));assert.deepEqual(patched,['eq.'+gym,'eq.other']);});
test('Inbound without destination phone cannot choose an arbitrary gym',async()=>{const called=[];const raw=JSON.stringify({object:'whatsapp_business_account',entry:[{id:'waba',changes:[{field:'messages',value:{messages:[{id:'m1',from:'573001234567',timestamp:String(Date.now()/1000),text:{body:'Hola'}}]}}]}]});const db={rpc:async(n)=>{called.push(n);return n==='marketing_service_platform'?{app_secret:'secret'}:[];},read:async()=>[{gym_id:gym}]};await metaWebhook(db,base,raw,'sha256='+await hmacHex('secret',raw));assert.equal(called.includes('marketing_service_inbound_record'),false);});
''';p.write_text(s)
