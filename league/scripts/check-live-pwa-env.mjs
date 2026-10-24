import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';

export function validateLivePwaConfig(env){
 const url=env.EXPO_PUBLIC_SUPABASE_URL||'',key=env.EXPO_PUBLIC_SUPABASE_PUBLISHABLE_KEY||'',endpoint=env.EXPO_PUBLIC_LEAGUE_ENDPOINT||'';
 if(!/^https:\/\/[a-z0-9]{20}\.supabase\.co$/.test(url)||!key.startsWith('sb_publishable_')||endpoint!==url+'/functions/v1/atlantic-league'){
  throw Error('La PWA real necesita URL de proyecto, clave publicable moderna y pasarela del mismo proyecto. No se muestran claves.');
 }
 return {ready:true,project_ref:new URL(url).hostname.split('.')[0]};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 try{
  const text=await readFile(new URL('../mobile/.env',import.meta.url),'utf8');
  const env=Object.fromEntries(text.split(/\r?\n/).filter(line=>line.includes('=')&&!line.trimStart().startsWith('#')).map(line=>{const at=line.indexOf('=');return[line.slice(0,at).trim(),line.slice(at+1).trim()];}));
  console.log(JSON.stringify(validateLivePwaConfig(env)));
 }catch{console.error('Configuración real de PWA incompleta o incompatible. Revisa mobile/.env; no se publicaron claves.');process.exitCode=1;}
}
