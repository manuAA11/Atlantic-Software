import assert from 'node:assert/strict';
import {database} from './migrations.mjs';
const db=await database();let checks=0;
const O='10000000-0000-4000-8000-000000000001', A='20000000-0000-4000-8000-000000000001',
 R='30000000-0000-4000-8000-000000000001', U='40000000-0000-4000-8000-000000000001';
async function user(id,role='authenticated'){
 await db.exec('RESET ROLE');
 await db.query("SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[id,JSON.stringify({sub:id,session_id:'90000000-0000-4000-8000-000000000001'})]);
 await db.exec('SET ROLE '+role);
}
async function rpc(name,params={}){
 assert.match(name,/^[a-z_]+$/);for(const k of Object.keys(params))assert.match(k,/^p_[a-z_]+$/);
 return (await db.query(`select public.${name}(${Object.keys(params).map((k,i)=>`${k}=>$${i+1}`).join(',')}) as data`,Object.values(params).map(v=>v!==null&&typeof v==='object'?JSON.stringify(v):v))).rows[0].data;
}
function ok(v,label){assert.ok(v,label);checks++;}
async function deny(fn,pattern){await assert.rejects(fn,pattern);checks++;}
const backup=g=>rpc('owner_editor_backup',{p_gym_id:g});
const list=(g,t)=>rpc('owner_editor_rows',{p_gym_id:g,p_table:t,p_limit:100});
const reason='Corrección verificada por propietario';
async function edit(g,t,item,patch,del=false){return rpc('owner_editor_record',{p_gym_id:g,p_table:t,p_id:item.data.id,p_expected:item.version,p_patch:patch,p_reason:reason,p_delete:del});}
async function suspend(g){return rpc('owner_set_status',{p_gym_id:g,p_status:'suspended',p_reason:reason});}
async function importTo(g,snapshot,source,name){return rpc('owner_editor_import',{p_gym_id:g,p_name:name,p_expected:snapshot.fingerprint,p_reason:reason,p_data:source});}
async function seed(g,t,columns,values){
 assert.match(t,/^[a-z_]+$/);
 return (await db.query(`INSERT INTO public.${t}(gym_id,${columns}) VALUES($1,${values.map((_,i)=>'$'+(i+2)).join(',')}) RETURNING id`,[g,...values])).rows[0].id;
}
try{
 for(const [id,email,confirmed] of [[O,'owner@example.test',true],[A,'admin@example.test',true],[R,'reception@example.test',true],[U,'pending@example.test',false]])
  await db.query('INSERT INTO auth.users(id,email,email_confirmed_at) VALUES($1,$2,case when $3 then now() else null end)',[id,email,confirmed]);
 await db.query('INSERT INTO private.software_owners(user_id) VALUES($1)',[O]);await user(O);
 const create=async name=>(await rpc('owner_create_gym',{p_name:name,p_email:'initial@example.test',p_monthly_price:100})).gym_id;
 const g=await create('Origen'), other=await create('Destino');
 const snapshot0=await backup(other);
 ok(snapshot0.format==='GymSoft-CLOUD-2'&&!JSON.stringify(snapshot0).includes('code_hash')&&!JSON.stringify(snapshot0).includes('device_hash')&&!snapshot0.gym.join_code,'backup has no invite or device secrets');
 ok((await backup(other)).fingerprint===snapshot0.fingerprint,'export history does not invalidate snapshot');
 await rpc('owner_editor_profile',{p_gym_id:g,p_name:'Gimnasio editado',p_email:'contact@example.test',p_timezone:'America/Bogota',p_plan:'Profesional',p_reason:reason});
 ok((await backup(g)).gym.name==='Gimnasio editado','rename without changing gym id');
 await deny(()=>rpc('owner_editor_profile',{p_gym_id:g,p_name:'x',p_email:'bad',p_timezone:'bad',p_plan:'p',p_reason:reason}),/Revisa/);
 await deny(()=>rpc('owner_editor_profile',{p_gym_id:g,p_name:'x',p_email:'x@y.co',p_timezone:'bad',p_plan:'p',p_reason:reason}),/horaria/);
 const email=async(gym,email,role)=>rpc('owner_editor_email',{p_gym_id:gym,p_email:email,p_role:role,p_reason:reason});
 ok((await email(g,'admin@example.test','admin')).state==='assigned','confirmed admin assigned by email');
 ok((await email(g,'reception@example.test','receptionist')).state==='assigned','confirmed reception assigned by email');
 ok((await email(g,'admin@example.test','receptionist')).role==='receptionist','owner changes role');
 await email(g,'admin@example.test','admin');
 await deny(()=>email(other,'admin@example.test','admin'),/otro gimnasio/);
 await deny(()=>email(g,'owner@example.test','admin'),/propietaria/);
 await deny(()=>email(g,'x@y.test','root'),/correo válido/);
 ok((await email(g,'new@example.test','admin')).state==='invited','unknown email returns code, no password');
 ok((await email(g,'pending@example.test','receptionist')).state==='invited','unconfirmed email still requires confirmation');
 await email(g,'pending@example.test','admin');
 const access=await rpc('owner_editor_access',{p_gym_id:g});
 ok(access.users.length===2&&access.invitations.some(i=>i.email==='pending@example.test'),'pending emails and active users listed');
 await rpc('owner_editor_revoke_invite',{p_gym_id:g,p_email:'new@example.test',p_reason:reason});
 ok(!(await rpc('owner_editor_access',{p_gym_id:g})).invitations.some(i=>i.email==='new@example.test'),'pending invitation revoked');
 await db.exec('RESET ROLE');
 ok((await db.query("select count(*) as n from private.activation_invites where gym_id=$1 and email='pending@example.test' and used_at is null",[g])).rows[0].n===1,'one pending invite after role correction');
 const client=await seed(g,'clients','document,first_name',['C-001','Cliente']);
 const plan=(await db.query('select id from public.plans where gym_id=$1 limit 1',[g])).rows[0].id;
 const trainer=await seed(g,'trainers','name',['Entrenador']);
 const product=await seed(g,'store_products','name,sale_price,stock_quantity',['Agua',5000,10]);
 const member=await seed(g,'memberships','client_id,plan_id,start_date,end_date,amount,amount_paid,payment_method',[client,plan,'2026-09-01','2026-09-30',10000,10000,'Efectivo']);
 await seed(g,'checkins','client_id,membership_id,method,result',[client,member,'manual','PERMITIDA']);
 const routine=await seed(g,'routines','client_id,trainer_id,name,start_date',[client,trainer,'Rutina','2026-09-07']);
 const klass=await seed(g,'classes','trainer_id,name,starts_at,capacity',[trainer,'Clase','2026-09-07T12:00:00Z',10]);
 await seed(g,'exercises','routine_id,day_name,name',[routine,'Lunes','Ejercicio']);
 await seed(g,'reservations','class_id,client_id',[klass,client]);
 await seed(g,'staff_shifts','trainer_id',[trainer]);
 await seed(g,'accounting_expenses','expense_date,category,description,amount',['2026-09-07','Limpieza','Gasto',5000]);
 await seed(g,'store_sales','product_id,product_name,quantity,unit_price,total_amount',[product,'Agua',2,5000,10000]);
 await seed(g,'marketing_messages','client_id,automation_type,source_date,phone,template_name',[client,'BIRTHDAY','2026-09-07','+570000','template']);
 await user(O);
 const patches={clients:{first_name:'Nuevo'},plans:{price:6000},memberships:{amount:9000},checkins:{notes:'Corrección'},trainers:{name:'Entrenador nuevo'},routines:{goal:'Fuerza'},classes:{capacity:20},exercises:{sets:'4'},reservations:{status:'CANCELADA'},staff_shifts:{notes:'Turno confirmado'},accounting_expenses:{amount:4500},store_products:{low_stock_threshold:2},store_sales:{quantity:3,unit_price:4000}};
 for(const [table,patch] of Object.entries(patches)){
  const rows=await list(g,table);const item=rows.rows.find(i=>table!=='plans'||i.data.id===plan)||rows.rows[0];
  const changed=await edit(g,table,item,patch);
  ok(Object.entries(patch).every(([k,v])=>changed.data[k]===v),table+' fields persisted');
  await deny(()=>edit(g,table,item,patch),/cambió/);
 }
 let rows=await list(g,'memberships');
 ok(rows.rows[0].data.payment_revision===1&&rows.rows[0].data.amount_paid===9000,'membership edit increments revision and paid amount');
 let products=await list(g,'store_products');
 ok(products.rows[0].data.stock_quantity===9,'sale quantity reduces stock by difference');
 let sales=await list(g,'store_sales');ok(sales.rows[0].data.total_amount===12000,'sale total recomputed');
 await deny(()=>edit(g,'store_sales',sales.rows[0],{quantity:100}),/existencias/);
 ok((await list(g,'store_sales')).rows[0].version===sales.rows[0].version,'invalid sale rolls back');
 const clientItem=(await list(g,'clients')).rows[0];
 await deny(()=>edit(g,'clients',clientItem,{gym_id:other}),/campo gym_id/);
 await deny(()=>edit(other,'clients',clientItem,{first_name:'Ataque'}),/no existe/);
 await deny(()=>edit(g,'clients',clientItem,{},true),/relacionados/);
 await deny(()=>list(g,'gyms'),/Tabla/);
 await deny(()=>list(g,'clients; delete from public.gyms'),/Tabla/);
 const audit=(await list(g,'audit_logs')).rows[0];
 await deny(()=>edit(g,'audit_logs',audit,{},true),/consulta/);
 for(const id of [A,R,U]){
  await user(id);
  for(const [name,params] of [
   ['owner_editor_backup',{p_gym_id:g}],['owner_editor_rows',{p_gym_id:g,p_table:'clients'}],
   ['owner_editor_access',{p_gym_id:g}],['owner_editor_revoke_invite',{p_gym_id:g,p_email:'new@example.test',p_reason:reason}],
   ['owner_editor_record',{p_gym_id:g,p_table:'clients',p_id:client,p_expected:clientItem.version,p_patch:{first_name:'Ataque'},p_reason:reason}],
   ['owner_editor_profile',{p_gym_id:g,p_name:'Ataque',p_email:'x@y.co',p_timezone:'America/Bogota',p_plan:'x',p_reason:reason}],
   ['owner_editor_email',{p_gym_id:g,p_email:'admin@example.test',p_role:'admin',p_reason:reason}],
   ['owner_editor_delete_gym',{p_gym_id:g,p_name:'Gimnasio editado',p_expected:'x',p_reason:reason}],
   ['owner_editor_import',{p_gym_id:g,p_data:snapshot0,p_name:'Gimnasio editado',p_expected:'x',p_reason:reason}],
   ['owner_editor_validate_import',{p_data:snapshot0}]
  ])await deny(()=>rpc(name,params),/propietario/);
 }
 await user('','anon');await deny(()=>backup(g),/permission denied/);await user(O);
 const source=await backup(g);const targetInitial=await backup(other);
 const preview=await rpc('owner_editor_validate_import',{p_data:source});ok(preview.total>10,'preview counts');
 await deny(()=>importTo(other,targetInitial,source,'Destino'),/Suspende/);
 await suspend(other);
 let dest=await backup(other);
 await deny(()=>importTo(other,dest,source,'Nombre equivocado'),/exactamente/);
 const bad=structuredClone(source);bad.tables.clients[0].gym_id=other;
 await deny(()=>rpc('owner_editor_validate_import',{p_data:bad}),/mezcla/);
 const duplicate=structuredClone(source);duplicate.tables.clients.push(duplicate.tables.clients[0]);
 await deny(()=>rpc('owner_editor_validate_import',{p_data:duplicate}),/duplicado/);
 const missing=structuredClone(source);delete missing.tables.store_sales;
 await deny(()=>rpc('owner_editor_validate_import',{p_data:missing}),/incompleto/);
 const broken=structuredClone(source);broken.tables.checkins[0].membership_id=999999;
 await deny(()=>importTo(other,dest,broken,'Destino'),/Relación incompleta/);
 ok((await backup(other)).fingerprint===dest.fingerprint,'invalid import fully rolls back including deletes and audit');
 const imported=await importTo(other,dest,source,'Destino');ok(imported.imported>10,'import succeeds');
 const after=await backup(other);
 ok(after.gym.name==='Destino'&&after.gym_id===other&&after.contract.status==='suspended','import preserves gym id, name and contract');
 ok(after.users.length===0&&after.payments.length===0,'import cannot assign source users or monthly charges');
 for(const table of Object.keys(patches)){
  ok(after.tables[table].every(row=>row.gym_id===other),'import isolates '+table);
  ok(after.tables[table].every(row=>!source.tables[table].some(old=>old.id===row.id)),'new IDs for '+table);
 }
 const cm=after.tables.memberships[0],cc=after.tables.clients[0];
 ok(cm.client_id===cc.id&&after.tables.checkins[0].membership_id===cm.id,'dependent IDs remapped');
 ok(after.tables.marketing_messages[0].status==='SKIPPED'&&!after.tables.marketing_settings[0].whatsapp_enabled,'import does not resend queued messages');
 ok((await backup(g)).fingerprint===source.fingerprint,'source gym unchanged by import');
 const stale=after;
 await edit(other,'clients',(await list(other,'clients')).rows[0],{first_name:'Editado destino'});
 await deny(()=>importTo(other,stale,source,'Destino'),/cambiaron/);
 sales=await list(other,'store_sales');const beforeStock=(await list(other,'store_products')).rows[0].data.stock_quantity;
 await edit(other,'store_sales',sales.rows[0],{},true);
 ok((await list(other,'store_products')).rows[0].data.stock_quantity===beforeStock+3,'delete sale restores stock');
 // Límite de cuentas y revocación de sesión en cambio de rol.
 await rpc('owner_update_contract',{p_gym_id:other,p_price:100,p_currency:'COP',p_max_devices:2,p_max_users:1,p_notes:''});
 await db.exec('RESET ROLE');const B='50000000-0000-4000-8000-000000000001',C='60000000-0000-4000-8000-000000000001';
 for(const [id,email] of [[B,'dest@example.test'],[C,'excess@example.test']])await db.query('insert into auth.users(id,email) values($1,$2)',[id,email]);
 await user(O);await email(other,'dest@example.test','admin');
 await deny(()=>email(other,'excess@example.test','receptionist'),/límite/);
 const renewal=await rpc('owner_renew',{p_gym_id:other,p_months:1,p_amount:100,p_currency:'COP',p_reference:'TEST-DELETE',p_idempotency_key:'80000000-0000-4000-8000-000000000001'});
 ok(renewal.id,'gym has commercial payment before deleting');
 await suspend(other);dest=await backup(other);
 const deletion=await rpc('owner_editor_delete_gym',{p_gym_id:other,p_name:'Destino',p_expected:dest.fingerprint,p_reason:reason});ok(deletion.deleted,'complete deletion succeeds');
 await db.exec('RESET ROLE');
 const tables=(await db.query("select table_schema,table_name from information_schema.columns where column_name='gym_id' and table_schema in ('public','private')")).rows;
 for(const t of tables){const n=(await db.query(`select count(*) as n from ${t.table_schema}.${t.table_name} where gym_id=$1`,[other])).rows[0].n;ok(n===0,'delete leaves no '+t.table_schema+'.'+t.table_name);}
 ok((await db.query('select count(*) as n from public.gyms where id=$1',[other])).rows[0].n===0,'gym itself deleted');
 ok((await db.query('select count(*) as n from auth.users where id=$1',[B])).rows[0].n===1,'global login identity remains without gym access');
 await user(O);ok((await backup(g)).fingerprint===source.fingerprint,'other gym survives full deletion');
 await deny(()=>rpc('owner_editor_delete_gym',{p_gym_id:other,p_name:'Destino',p_expected:dest.fingerprint,p_reason:reason}),/no existe/);
 console.log(`PASS: ${checks} owner editor checks (roles, conflicts, all edit tables, import rollback, ID remapping, stock and complete isolated deletion).`);
}catch(e){console.error('FAILED owner editor after',checks,'checks:',e.message,e.detail||'',e.where||'');process.exitCode=1;}
finally{await db.close();}
