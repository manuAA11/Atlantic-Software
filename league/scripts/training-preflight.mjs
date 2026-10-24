import {readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
export const preflightSql=await readFile(new URL('../source/training-preflight.sql',import.meta.url),'utf8');
const migration=await readFile(new URL('../../training/supabase/migrations/20261024013933_gym_training_workspace.sql',import.meta.url));

export async function readPreflight(db){
 await db.query('begin read only');
 try{return (await db.query(preflightSql)).rows[0].preflight;}
 finally{await db.query('rollback');}
}

export function assessPreflight(s){
 if(s?.format!=='atlantic.training.preflight.v1')throw Error('Unrecognized preflight format');
 const blockers=[];
 const shapes={required_tables:12,required_functions:8,required_columns:14,new_tables:4,new_functions:4,new_columns:12};
 for(const [section,size] of Object.entries(shapes)){
  if(!s[section]||Object.keys(s[section]).length!==size)blockers.push('metadata:'+section);
  if(section!=='new_tables'&&Object.values(s[section]||{}).some(v=>typeof v!=='boolean'))blockers.push('metadata:'+section+':boolean');
 }
 if(!Number.isInteger(s.server_version_num)||s.server_version_num<150000)blockers.push('postgres_version');
 for(const section of ['required_tables','required_functions','required_columns']){
  if(!s[section]||!Object.keys(s[section]).length)blockers.push(section);
  for(const [name,ok] of Object.entries(s[section]||{}))if(ok!==true)blockers.push(name);
 }
 if(s.capacity_guard!==true)blockers.push('reservation_capacity_guard');
 if(s.reservation_unique!==true)blockers.push('reservation_unique_constraint');
 if(!s.source_api||s.source_api.definer!==false||s.source_api.anon_execute!==false||s.source_api.authenticated_execute!==false||s.source_api.service_execute!==true)blockers.push('source_api_permissions');
 const tables=Object.values(s.new_tables||{}),functions=Object.values(s.new_functions||{}),columns=Object.values(s.new_columns||{});
 const anyNew=tables.some(t=>t.exists)||functions.some(Boolean)||columns.some(Boolean);
 const allNew=tables.length===4&&tables.every(t=>t.exists)&&functions.length===4&&functions.every(Boolean)&&columns.length===12&&columns.every(Boolean);
 if(anyNew&&!allNew)blockers.push('partial_training_installation');
 if(anyNew){
  for(const [name,t] of Object.entries(s.new_tables||{}))if(!t.rls||t.client_grants)blockers.push('table_access:'+name);
  if(!s.rpc||s.rpc.definer!==false||s.rpc.anon_execute!==false)blockers.push('training_rpc_permissions');
 }
 return {format:'atlantic.training.rollout.v1',state:blockers.length?'blocked':allNew?(s.rpc.authenticated_execute?'installed':'disabled'):'ready_for_migration',
  blockers,migration_sha256:createHash('sha256').update(migration).digest('hex'),
  preflight_sha256:createHash('sha256').update(preflightSql).digest('hex'),
  scope:'Schema metadata only. Does not authorize a deployment or prove a production backup.',snapshot:s};
}

async function main(){
 const args=process.argv.slice(2),value=name=>{const i=args.indexOf(name);return i<0?null:args[i+1];};
 if(args.includes('--help')){console.log('Training preflight (read-only)\n  node scripts/training-preflight.mjs [--snapshot metadata.json] [--output report.json]\n  Without --snapshot, set ATLANTIC_TRAINING_DB_URL privately. No credentials are printed.');return;}
 if(args.some((a,i)=>i%2===0&&!['--snapshot','--output'].includes(a))||args.length%2)throw Error('Arguments');
 let snapshot;
 if(value('--snapshot')){snapshot=JSON.parse(await readFile(value('--snapshot'),'utf8'));snapshot=snapshot.preflight||snapshot;}
 else{
  const url=process.env.ATLANTIC_TRAINING_DB_URL;
  if(!url)throw Error('Connection required');
  const {default:pg}=await import('pg');const db=new pg.Client({connectionString:url,application_name:'Atlantic training read-only preflight',connectionTimeoutMillis:10000,statement_timeout:10000});
  try{await db.connect();snapshot=await readPreflight(db);}finally{await db.end();}
 }
 const report=assessPreflight(snapshot),json=JSON.stringify(report,null,2)+'\n';
 if(value('--output'))await writeFile(value('--output'),json,{mode:0o600});else console.log(json);
 process.exitCode=report.state==='blocked'?2:0;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main().catch(()=>{
 console.error('No se pudo completar la comprobación. Revisa la conexión privada, el archivo y los argumentos; no se aplicaron cambios.');process.exitCode=1;
});
