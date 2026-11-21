import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {PGlite} from '@electric-sql/pglite';
const alice='a0000000-0000-4000-8000-000000000001',bob='b0000000-0000-4000-8000-000000000002',gym='d0000000-0000-4000-8000-000000000004',other='e0000000-0000-4000-8000-000000000005';
const key1='10000000-0000-4000-8000-000000000001',key2='10000000-0000-4000-8000-000000000002';
test('local SQL: RLS isolation, duplicate renewal prevention, retries and unchanged Gym records',async()=>{
 const db=new PGlite();
 try{
  await db.exec(`create role anon;create role authenticated;create role service_role bypassrls;
   create schema auth;grant usage on schema auth to authenticated;
   create function auth.uid() returns uuid language sql stable as $$select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$;
   create table public.league_profiles(id uuid primary key,alias text);
   create table public.league_gym_directory(gym_id uuid primary key,enabled boolean not null,name text,source_ref text);
   create table public.league_links(athlete_id uuid,gym_id uuid,status text default 'APPROVED',source_profile_id uuid,approved_by uuid,unique(athlete_id,gym_id),unique(gym_id,source_profile_id));
   create table public.league_client_profiles(profile_id uuid default gen_random_uuid(),gym_id uuid,client_id bigint,unique(gym_id,client_id));
   alter table public.league_links enable row level security;
   grant select on public.league_links to authenticated;
   create policy own_link on public.league_links to authenticated using(athlete_id=(select auth.uid()));
   create table public.memberships(id int primary key,ends_at date,paid numeric);
   insert into public.memberships values(1,'2026-11-10',200000);
   insert into public.league_profiles(id) values('${alice}'),('${bob}');
   insert into public.league_gym_directory values('${gym}',true,'QA Gym','abcdefghijklmnopqrst'),('${other}',true,'Other Gym','abcdefghijklmnopqrst');
   insert into public.league_links(athlete_id,gym_id,status,source_profile_id) values('${alice}','${gym}','APPROVED','${alice}'),('${bob}','${other}','APPROVED','${bob}');
   insert into public.league_client_profiles values('${alice}','${gym}',1),('${bob}','${other}',2);
   create schema private;
   create function private.gym_local_date(uuid) returns date language sql as $$select date '2026-11-16'$$;
   create function private.membership_snapshot_json(uuid,bigint) returns jsonb language sql as $$select jsonb_build_object('membership_id',1,'plan_name','QA Plan','allowed',false,'membership_type','COMMERCIAL','membership_end','2026-11-10','status','EXPIRED','document','NEVER_RETURN_ME')$$;
   grant usage on schema private to service_role;
   grant execute on function private.gym_local_date(uuid),private.membership_snapshot_json(uuid,bigint) to service_role;
   grant select on public.league_profiles,public.league_links,public.league_gym_directory,public.league_client_profiles to service_role;`);
  await db.exec(`create table public.clients(id bigint,gym_id uuid,document text,active boolean,first_name text,last_name text,full_name text,created_by uuid);
   create table public.league_gym_settings(gym_id uuid,enabled boolean,allow_all_clients boolean,pilot_client_ids bigint[]);
   create table public.gym_users(gym_id uuid,user_id uuid);
   create schema league_private;create table league_private.pilot_accounts(user_id uuid primary key);
   insert into public.clients values(1,'${gym}','123456789',true,'Test','Member','Test Member',null);
   insert into public.league_gym_settings values('${gym}',true,false,array[1]::bigint[]);
   grant select,insert,update on public.clients,public.league_gym_settings,public.gym_users,public.league_profiles,public.league_links,public.league_client_profiles to service_role;
   grant usage on schema league_private to service_role;grant all on league_private.pilot_accounts to service_role;`);
  await db.exec(`alter table public.clients add column phone text;alter table public.clients add column email text;
   alter table public.memberships add column gym_id uuid;alter table public.memberships add column client_id bigint;alter table public.memberships add column payment_status text default 'posted';
   create table public.gyms(id uuid,name text,timezone text);
   create table public.trainers(id bigint,gym_id uuid,name text);
   create table public.classes(id bigint,gym_id uuid,trainer_id bigint,name text,starts_at timestamptz,capacity int,notes text,status text,duration_minutes int,conditions text,requires_membership boolean,version int);
   create table public.reservations(id bigint,gym_id uuid,class_id bigint,client_id bigint,status text);
   create table public.league_exercise_catalog(id uuid,name text,muscle text,equipment text,instructions text,gym_id uuid,owner_id uuid);
   create table public.gym_routine_templates(id uuid,gym_id uuid,name text,goal text,notes text,exercises jsonb,active boolean);
   create table public.checkins(gym_id uuid,client_id bigint,result text,local_date date);
   create table public.routines(id bigint,gym_id uuid,client_id bigint,name text,goal text,notes text,active boolean);
   create table public.exercises(id bigint,gym_id uuid,routine_id bigint,name text);
   insert into public.gyms values('${gym}','QA Gym','America/Bogota'),('${other}','Other','America/Bogota');
   insert into public.classes values(1,'${gym}',null,'My class',now()+interval '58 minutes',2,'Details','PROGRAMADA',60,'',true,1),(2,'${other}',null,'PRIVATE_OTHER_GYM',now()+interval '1 day',2,'Private','PROGRAMADA',60,'',true,1);
   insert into public.reservations values(1,'${gym}',1,1,'RESERVADA');
   insert into public.league_exercise_catalog values('${key1}','Public exercise','','','',null,null),('${key2}','PRIVATE_EXERCISE','','','',null,'${bob}');
   insert into public.gym_routine_templates values('${key1}','${gym}','My template','','','[]',true),('${key2}','${other}','PRIVATE_TEMPLATE','','','[]',true);
   insert into public.checkins values('${gym}',1,'PERMITIDA',current_date),('${gym}',2,'PERMITIDA',current_date-1);`);
  await db.exec(await readFile(new URL('../../member/sql/schema.sql',import.meta.url),'utf8'));
  await db.exec(await readFile(new URL('../../member/sql/access.sql',import.meta.url),'utf8'));
  await db.exec(await readFile(new URL('../../member/sql/content.sql',import.meta.url),'utf8'));
  await db.exec(await readFile(new URL('../../member/sql/notifications.sql',import.meta.url),'utf8'));
  await db.exec(await readFile(new URL('../../member/sql/activity.sql',import.meta.url),'utf8'));
  await db.exec(await readFile(new URL('../../member/sql/settings.sql',import.meta.url),'utf8'));
  const rpc=async(actor,g,action,data={})=>(await db.query('select public.league_member_gateway($1,$2,$3,$4::jsonb) as data',[actor,g,action,JSON.stringify(data)])).rows[0].data;
  await db.exec('set role service_role');
  const secret=(await db.query("select public.league_member_settings('get') as data")).rows[0].data;assert.ok(secret.access_pepper.length>=64);
  const details=await rpc(alice,gym,'membership.details');
  assert.equal(details.plan_name,'QA Plan');assert.equal(details.status,'EXPIRED');assert.equal(details.remaining_days,0);assert.ok(!JSON.stringify(details).includes('NEVER_RETURN_ME'));
  // Exercise the deployed upgrade twice as well as the clean schema. Neither read changes source rows.
  await db.exec('reset role');
  const ticketMigration=await readFile(new URL('../../member/sql/ticket-balance.sql',import.meta.url),'utf8');
  await db.exec(ticketMigration);await db.exec(ticketMigration);
  const monthly={membership_id:1,plan_name:'QA Plan',allowed:false,membership_type:'COMMERCIAL',membership_end:'2026-11-10',status:'EXPIRED',document:'NEVER_RETURN_ME'};
  const fixtures=[
   {entry_limit:12,entries_used:3,entries_remaining:9,allowed:true,status:'ACTIVE'},
   {entry_limit:12,entries_used:12,entries_remaining:0,already_consumed_today:true,status:'SIN ENTRADAS'},
   {entry_limit:12,entries_used:12,entries_remaining:0,already_consumed_today:true,allowed:true,status:'ACTIVE'},
   {entry_limit:12,entries_used:0,entries_remaining:12,has_expiration:false,allowed:true,status:'ACTIVE'},
   {entry_limit:12,entries_used:3,entries_remaining:9,frozen:true,status:'FROZEN'},
   {entry_limit:null,entries_used:0,entries_remaining:null,allowed:true,status:'ACTIVE'},
   {entry_limit:null,entries_used:null,entries_remaining:null,membership_id:null,status:'INACTIVE'}
  ];
  const snapshot=async value=>db.exec("create or replace function private.membership_snapshot_json(uuid,bigint) returns jsonb language sql as $$select '"+JSON.stringify(value).replaceAll("'","''")+"'::jsonb$$;");
  for(const fixture of fixtures){
   await snapshot({...monthly,...fixture});await db.exec('set role service_role');
   const balance=await rpc(alice,gym,'membership.details');
   for(const field of ['entry_limit','entries_used','entries_remaining'])assert.equal(balance[field],fixture[field]);
   assert.equal(balance.already_consumed_today,fixture.already_consumed_today===true);
   assert.equal(balance.active,fixture.allowed===true);
   assert.equal(balance.status,fixture.frozen?'FROZEN':fixture.membership_id===null?'NO_PLAN':fixture.status);
   assert.equal(balance.has_expiration,fixture.has_expiration!==false);
   if(fixture.has_expiration===false)assert.equal(balance.ends_at,null);
   assert.ok(!JSON.stringify(balance).includes('NEVER_RETURN_ME'));
   assert.deepEqual(await rpc(alice,gym,'membership.details'),balance);
   await assert.rejects(rpc(bob,gym,'membership.details'),/Vinculación/);
   await db.exec('reset role');
  }
  await snapshot(monthly);await db.exec('set role service_role');

  const first=await rpc(alice,gym,'renewals.create',{request_key:key1,period_key:'2026-11-10'});
  const again=await rpc(alice,gym,'renewals.create',{request_key:key1,period_key:'2026-11-10'});
  const secondDevice=await rpc(alice,gym,'renewals.create',{request_key:key2,period_key:'2026-11-10'});
  assert.equal(first.status,'PENDING');assert.equal(first.id,again.id);assert.equal(first.id,secondDevice.id);
  assert.equal((await rpc(alice,gym,'renewals.list')).length,1);
  const notices=await rpc(alice,gym,'notifications.list');assert.equal(notices.length,1);
  await assert.rejects(rpc(bob,gym,'renewals.list'),/Vinculación/);
  await assert.rejects(rpc(bob,other,'notifications.read',{id:notices[0].id}),/Aviso/);
  await rpc(alice,gym,'notifications.read',{id:notices[0].id});assert.ok((await rpc(alice,gym,'notifications.list'))[0].read_at);
  await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[bob]);await db.exec('set role authenticated');
  assert.equal((await db.query('select * from public.league_member_renewals')).rows.length,0);
  assert.equal((await db.query('select * from public.league_member_notifications')).rows.length,0);
  await assert.rejects(db.query("select public.league_member_settings('get')"),/permission denied/);
  await assert.rejects(db.query('select public.league_member_gateway($1,$2,$3,$4::jsonb)',[alice,gym,'renewals.list','{}']),/permission denied/);
  await assert.rejects(db.exec(`update public.league_member_renewals set status='APPROVED'`),/permission denied/);
  await db.exec('reset role');await db.query("select set_config('request.jwt.claim.sub',$1,false)",[alice]);await db.exec('set role authenticated');
  assert.equal((await db.query('select * from public.league_member_renewals')).rows.length,1);
  await db.exec('reset role');await db.exec('set role service_role');
  await rpc(alice,gym,'renewals.cancel',{id:first.id});await rpc(alice,gym,'renewals.cancel',{id:first.id});
  assert.equal((await rpc(alice,gym,'notifications.list')).length,2);
  await db.exec('reset role');
  const source=(await db.query('select ends_at::text,paid from public.memberships')).rows;
  assert.deepEqual(source,[{ends_at:'2026-11-10',paid:'200000'}]);
  await db.exec(`update public.league_links set status='REVOKED' where athlete_id='${alice}'`);
  await db.query("select set_config('request.jwt.claim.sub',$1,false)",[alice]);await db.exec('set role authenticated');
  assert.equal((await db.query('select * from public.league_member_renewals')).rows.length,0);
  await db.exec('reset role');
  await db.exec(`update public.league_links set status='APPROVED' where athlete_id='${alice}'`);
  await db.exec('set role service_role');
  const access=async(action,data)=>(await db.query('select public.league_member_access($1,$2,$3::jsonb) as value',[action,gym,JSON.stringify(data)])).rows[0].value;
  assert.equal((await access('resolve',{document:'123456789'})).client_id,'1');
  assert.equal(await access('resolve',{document:'000000000'}),null);
  for(let i=0;i<10;i++)assert.equal(await access('attempt',{bucket:'a'.repeat(64)}),true);
  assert.equal(await access('attempt',{bucket:'a'.repeat(64)}),false);
  const mobile='c0000000-0000-4000-8000-000000000003';
  await access('activate',{client_id:'1',auth_user_id:mobile});
  await access('activate',{client_id:'1',auth_user_id:mobile});
  assert.equal((await db.query('select * from public.league_client_profiles where gym_id=$1',[gym])).rows.length,1);
  const link=(await db.query('select athlete_id,source_profile_id from public.league_links where gym_id=$1',[gym])).rows[0];
  assert.deepEqual(link,{athlete_id:alice,source_profile_id:alice});
  assert.equal((await rpc(mobile,gym,'membership.details')).plan_name,'QA Plan');
  assert.equal((await rpc(mobile,null,'snapshot')).links[0].gym_id,gym);
  await assert.rejects(rpc(mobile,other,'membership.details'),/Vinculación/);
  const content=async(action)=>(await db.query('select public.league_member_content($1,$2,$3) as data',[mobile,gym,action])).rows[0].data;
  assert.equal((await content('calendar')).length,1);
  assert.equal((await content('calendar'))[0].mine,true);
  assert.equal((await content('catalog')).length,1);
  assert.equal((await content('templates'))[0].name,'My template');
  assert.equal((await content('profile')).document_hint,'6789');
  assert.equal((await content('profile')).attendance.length,1);
  await rpc(mobile,gym,'push.subscribe',{endpoint:'https://fcm.googleapis.com/test',p256dh:'test',auth:'test'});
  const jobs=async(action,data={})=>(await db.query('select public.league_member_jobs($1,$2::jsonb) as value',[action,JSON.stringify(data)])).rows[0].value;
  await jobs('reconcile',{actor:mobile,gym});
  const firstNotices=await rpc(mobile,gym,'notifications.list');
  assert.equal(firstNotices.length,2); // expiry plus next-hour class
  await jobs('reconcile',{actor:mobile,gym});
  assert.equal((await rpc(mobile,gym,'notifications.list')).length,firstNotices.length);
  await db.query('select public.league_member_reservation_notice($1,$2,$3)',[mobile,gym,1]);
  await db.query('select public.league_member_reservation_notice($1,$2,$3)',[mobile,gym,1]);
  assert.equal((await rpc(mobile,gym,'notifications.list')).length,3);
  const delivery=await jobs('claim');assert.equal(delivery.length,3);
  for(const item of delivery)assert.equal(await jobs('validate_delivery',{id:item.id}),true);
  await db.exec('reset role');
  await db.exec(`create or replace function private.membership_snapshot_json(uuid,bigint) returns jsonb language sql as $$select jsonb_build_object('membership_id',1,'allowed',false,'membership_type','COMMERCIAL','membership_end','2026-11-10','frozen',true)$$;`);
  await db.exec('set role service_role');
  let invalidated=0;for(const item of delivery)if(!await jobs('validate_delivery',{id:item.id}))invalidated++;
  assert.equal(invalidated,1); // expiry was queued before the freeze and is now suppressed
  for(const item of delivery)await jobs('finish',{id:item.id,outcome:'GONE'});
  assert.equal((await jobs('claim')).length,0);
  await assert.rejects(access('activate',{client_id:'1',auth_user_id:bob}),/Identidad/);
  await db.exec('reset role');
  await db.exec(`create or replace function private.membership_snapshot_json(uuid,bigint) returns jsonb language sql as $$select jsonb_build_object('membership_id','','plan_name','','allowed',false,'membership_type','COMMERCIAL','membership_start','','membership_end','','status','INACTIVE','frozen',false)$$;`);
  await db.exec('set role service_role');
  const noPlan=await rpc(mobile,gym,'membership.details');assert.equal(noPlan.status,'NO_PLAN');assert.equal(noPlan.remaining_days,null);assert.equal(noPlan.ends_at,null);assert.equal(noPlan.starts_at,null);
  await db.exec('reset role');
  assert.deepEqual((await db.query('select ends_at::text,paid from public.memberships')).rows,source);
 }finally{await db.close();}
});
