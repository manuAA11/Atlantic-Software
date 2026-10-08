// Operator/server utility. Never ship credentials or run this from a customer desktop.
import {BackendDB} from '../backend/core/database.mjs';
const required=name=>{const value=process.env[name];if(!value)throw new Error(`Falta ${name}.`);return value;};
try{
 const url=required('GSOFT_SUPABASE_URL');
 if(!/^https:\/\/[a-z0-9]+\.supabase\.co$/.test(url))throw new Error('URL del proyecto no válida.');
 const page=new URL(required('META_ONBOARDING_URL'));
 if(page.protocol!=='https:'||page.search||page.hash)throw new Error('Usa la dirección HTTPS de la página de autorización, sin parámetros.');
 const db=new BackendDB(url,required('GSOFT_SERVICE_ROLE_KEY'));
 await db.rpc('marketing_service_configure_meta',{p_data:{app_id:required('META_APP_ID'),
  config_id:required('META_BUSINESS_CONFIG_ID'),app_secret:required('META_APP_SECRET'),
  verify_token:required('META_VERIFY_TOKEN'),onboarding_origin:page.origin,onboarding_url:page.href}});
 console.log('Configuración de Meta guardada en Vault. Falta autorizar el número y comprobar el piloto.');
}catch(error){console.error(error.message);process.exitCode=1;}
