import { BackendDB } from './core/database.mjs';
import { createHandler } from './handler.mjs';
const url = Deno.env.get('SUPABASE_URL');
const key = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
if (!url || !key) throw new Error('Configuración del servidor incompleta.');
const db = new BackendDB(url, key);
Deno.serve(createHandler({db, baseURL:url+'/functions/v1/marketing'}));
