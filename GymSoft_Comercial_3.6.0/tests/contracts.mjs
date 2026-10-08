import {database,root} from './migrations.mjs';
import fs from 'node:fs';
import path from 'node:path';
const db=await database();
let failures=[];
const contract=JSON.parse(fs.readFileSync(path.join(root,'tests/contracts.json'),'utf8'));
const functions=(await db.query(`SELECT p.proname,p.proargnames,p.pronargs,p.pronargdefaults FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public'`)).rows;
for(const call of contract.calls){
 const matches=functions.filter(f=>f.proname===call.name);
 const accepts=matches.some(f=>{
  const args=(f.proargnames||[]).slice(0,f.pronargs);
  return call.args.every(x=>args.includes(x)) && args.slice(0,f.pronargs-f.pronargdefaults).every(x=>call.args.includes(x));
 });
 if(!accepts)failures.push(`${call.file}: RPC ${call.name}(${call.args.join(',')}) has no matching SQL signature`);
}
for(const [table,expected] of Object.entries(contract.columns)){
 const columns=(await db.query(`SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=$1`,[table])).rows.map(r=>r.column_name);
 for(const col of expected)if(!columns.includes(col))failures.push(`${table}.${col}: client expects a missing column`);
}
if(failures.length){console.error(failures.join('\n'));process.exitCode=1;}
else console.log(`PASS: ${contract.calls.length} RPC call contracts and ${Object.keys(contract.columns).length} table contracts.`);
await db.close();
