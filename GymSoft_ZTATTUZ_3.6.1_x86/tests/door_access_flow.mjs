import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import path from 'node:path';
import {fixture} from './membership_feature_fixture.mjs';

// Real migrated SQL decisions, passed to the real driver with simulated USB.
// This proves the boundary contract; it does not test a remote server or hardware.
const f=await fixture();
const cases=[];
let checks=0;
async function check(name,client,allowed,method='HUELLA BIOMÉTRICA'){
 const result=await f.enter(client,false,method);
 assert.equal(result.result,allowed?'PERMITIDA':'DENEGADA',name);checks++;
 cases.push({name,client,result,allowed,method});return result;
}
try{
 const normal=await f.monthly();await check('monthly_active',normal.c,true);
 const expired=await f.monthly({end:'2026-10-19'});await check('monthly_expired',expired.c,false);
 const frozen=await f.monthly();
 const event=await f.rpc('membership_freeze',{p_gym_id:f.gym,p_membership_id:frozen.m,p_request_id:randomUUID()});
 await check('membership_frozen',frozen.c,false);
 await f.clock('2026-10-22T14:00:00Z');
 await f.rpc('membership_resume_freeze',{p_gym_id:f.gym,p_freeze_id:event.id,p_expected_days:2});
 await check('early_resumed_without_waiting_seven_days',frozen.c,true);
 const staff=await f.rpc('save_membership_plan',{p_gym_id:f.gym,p_reason:'Personal autorizado',p_data:{name:'STAFF',plan_type:'INTERNAL',price:0,duration_days:null,duration_months:null,has_expiration:false,unlimited_access:true,entry_limit:null,include_in_financial_stats:false}});
 const person=await f.person();
 const [membership]=await f.tableRpc('assign_internal_membership',{p_gym_id:f.gym,p_client_id:person,p_plan_id:staff.id,p_request_id:randomUUID()});
 const active=await check('staff_active',person,true);
 assert.equal(active.membership_end,null);checks++;
 await f.rpc('set_internal_membership_active',{p_gym_id:f.gym,p_membership_id:membership.membership_id,p_active:false,p_reason:'Fin de autorización'});
 await check('staff_inactive',person,false);
 const tickets=await f.monthly({ticket:1});
 const first=await check('ticket_with_entry',tickets.c,true);
 const repeat=await check('ticket_same_day_no_second_consumption',tickets.c,true);
 assert.equal(first.entries_remaining,repeat.entries_remaining);checks++;
 assert.equal(repeat.ticket_consumed,false);checks++;
 await f.clock('2026-10-23T14:00:00Z');await check('ticket_exhausted_next_day',tickets.c,false);
 await check('authorized_code',normal.c,true,'CÓDIGO');
 await f.system();await f.db.query("update public.gyms set timezone='America/New_York' where id=$1",[f.gym]);
 await f.clock('2026-11-01T03:30:00Z');
 const dst=await f.monthly({end:'2026-11-30'});
 const dstfreeze=await f.rpc('membership_freeze',{p_gym_id:f.gym,p_membership_id:dst.m,p_request_id:randomUUID()});
 await check('timezone_freeze_blocks',dst.c,false);
 await f.clock('2026-11-08T03:30:00Z');
 await check('timezone_automatic_resume_without_scheduler',dst.c,true);
 const history=await f.rpc('membership_freeze_info',{p_gym_id:f.gym,p_client_id:dst.c});
 assert.equal(history.history[0].freeze_used_days,7);checks++;
 const output=execFileSync(process.env.PYTHON||'python3',[path.join(f.root,'tests/door_server_bridge.py')],
                          {input:JSON.stringify(cases),encoding:'utf8'});
 process.stdout.write(output);
 console.log(`DOOR ACCESS FLOW ${checks} SQL CHECKS PASS (${f.commercial?'Comercial':'ZTATTUZ'}; real PGlite decisions, simulated USB)`);
}finally{await f.db.close();}
