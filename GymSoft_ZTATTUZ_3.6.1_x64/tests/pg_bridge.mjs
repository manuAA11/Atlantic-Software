// Transporte exclusivo de pruebas: PostgreSQL en memoria por stdin/stdout.
// No escucha puertos ni acepta URL, credenciales o bases remotas.
import readline from 'node:readline';
import {database} from './migrations.mjs';
const db=await database();
// PostgREST devuelve fechas como texto, no objetos Date de JavaScript.
for(const oid of [1082,1114,1184])db.parsers[oid]=value=>value;
const identifier=name=>{if(!/^[a-z_][a-z_0-9]*$/i.test(name))throw Error('Identificador de prueba inválido: '+name);return '"'+name+'"';};
const relations={clients:'client_id',plans:'plan_id',trainers:'trainer_id',classes:'class_id',routines:'routine_id'};
function fields(text, alias='t'){
 let depth=0,part='',parts=[];
 for(const ch of text){if(ch==='(')depth++;if(ch===')')depth--;if(ch===','&&!depth){parts.push(part.trim());part='';}else part+=ch;}
 if(part.trim())parts.push(part.trim());
 return parts.map(part=>{
  if(part==='*')return alias+'.*';
  const nested=/^(\w+)\((.*)\)$/.exec(part);
  if(nested){const [,table,inner]=nested;const fk=relations[table];if(!fk)throw Error('Relación sin adaptar: '+table);
   return `(SELECT row_to_json(related) FROM (SELECT ${fields(inner,'r')} FROM public.${identifier(table)} r WHERE r.id=${alias}.${identifier(fk)} AND r.gym_id=${alias}.gym_id) related) AS ${identifier(table)}`;}
  return alias+'.'+identifier(part);
 }).join(',');
}
async function tableQuery(request){
 const name=identifier(request.table),steps=request.steps,values=[];
 const param=value=>{values.push(value);return '$'+values.length;};
 let action='select',payload,columns='*',where=[],order=[],limit='',offset='',single=false,conflict='';
 for(const {method,args,kwargs} of steps){
  if(method==='select'){columns=args[0]||'*';continue;}
  if(['insert','update','upsert','delete'].includes(method)){action=method;payload=args[0];conflict=kwargs.on_conflict||'';continue;}
  if(['eq','neq','gt','gte','lt','lte','like','ilike'].includes(method)){
   const op={eq:'=',neq:'<>',gt:'>',gte:'>=',lt:'<',lte:'<=',like:'LIKE',ilike:'ILIKE'}[method];where.push(`t.${identifier(args[0])} ${op} ${param(args[1])}`);continue;}
  if(method==='is_'){if(!['null','true','false'].includes(String(args[1]).toLowerCase()))throw Error('IS no soportado');where.push(`t.${identifier(args[0])} IS ${String(args[1]).toUpperCase()}`);continue;}
  if(method==='in_'){where.push(args[1].length?`t.${identifier(args[0])} IN (${args[1].map(param).join(',')})`:'FALSE');continue;}
  if(method==='order'){order.push(`t.${identifier(args[0])} ${kwargs.desc?'DESC':'ASC'}`);continue;}
  if(method==='limit'){limit=' LIMIT '+Number(args[0]);continue;}
  if(method==='range'){limit=' LIMIT '+(Number(args[1])-Number(args[0])+1);offset=' OFFSET '+Number(args[0]);continue;}
  if(['single','maybe_single'].includes(method)){single=true;continue;}
  throw Error('Operación PostgREST sin adaptar en la prueba: '+method);
 }
 const filter=where.length?' WHERE '+where.join(' AND '):'';
 let sql;
 if(action==='select')sql=`SELECT ${fields(columns)} FROM public.${name} t${filter}${order.length?' ORDER BY '+order.join(','):''}${limit}${offset}`;
 else if(action==='delete')sql=`DELETE FROM public.${name} t${filter} RETURNING *`;
 else if(action==='update'){sql=`UPDATE public.${name} t SET ${Object.entries(payload).map(([key,value])=>identifier(key)+'='+param(value)).join(',')}${filter} RETURNING *`;}
 else{
  const rows=Array.isArray(payload)?payload:[payload];if(!rows.length)return {data:[],count:0};
  const keys=Object.keys(rows[0]);
  sql=`INSERT INTO public.${name} (${keys.map(identifier).join(',')}) VALUES ${rows.map(row=>'('+keys.map(key=>param(row[key]??null)).join(',')+')').join(',')}`;
  if(action==='upsert')sql+=` ON CONFLICT (${(conflict||'id').split(',').map(x=>identifier(x.trim())).join(',')}) DO UPDATE SET ${keys.map(key=>`${identifier(key)}=EXCLUDED.${identifier(key)}`).join(',')}`;
  sql+=' RETURNING *';
 }
 const result=await db.query(sql,values);
 if(single&&result.rows.length!==1)throw Object.assign(Error('Se esperaba un registro.'),{code:'PGRST116'});
 return {data:single?result.rows[0]:result.rows,count:result.rows.length};
}
async function rpc(request){
 const name=identifier(request.name),params=request.params||{},keys=Object.keys(params);
 const args=keys.map((key,i)=>identifier(key)+' => $'+(i+1)).join(',');
 const signatures=(await db.query(`SELECT p.proretset,p.proargnames,p.pronargs,p.pronargdefaults FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' AND p.proname=$1`,[request.name])).rows;
 const match=signatures.find(p=>keys.every(key=>(p.proargnames||[]).slice(0,p.pronargs).includes(key))&&(p.proargnames||[]).slice(0,p.pronargs-p.pronargdefaults).every(key=>keys.includes(key)));
 if(!match)throw Error('Firma RPC no encontrada: '+request.name);
 const result=await db.query(match.proretset?`SELECT * FROM public.${name}(${args})`:`SELECT public.${name}(${args}) AS data`,Object.values(params));
 return {data:match.proretset?result.rows:result.rows[0].data};
}
console.log(JSON.stringify({ready:true}));
for await(const line of readline.createInterface({input:process.stdin,crlfDelay:Infinity})){
 try{
  const request=JSON.parse(line);
  if(request.op==='close')break;
  await db.exec('RESET ROLE');
  if(request.user){
   await db.query("SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[request.user,JSON.stringify({sub:request.user,session_id:request.user})]);
   await db.exec('SET ROLE authenticated');
  }
  let result;
  if(request.op==='sql')result={data:(await db.query(request.sql,request.params||[])).rows};
  else if(request.op==='rpc')result=await rpc(request);
  else if(request.op==='table')result=await tableQuery(request);
  else throw Error('Solicitud de prueba desconocida');
  console.log(JSON.stringify(result));
 }catch(error){console.log(JSON.stringify({error:{message:error.message,code:error.code||'',detail:error.detail||''}}));}
}
await db.close();
