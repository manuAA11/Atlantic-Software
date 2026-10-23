import {BackendDB} from '../core/database.mjs';
import {createCoreHandler} from './handler.mjs';
const url=Deno.env.get('SUPABASE_URL');
const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
if(!url||!key)throw new Error('Core server configuration is missing.');
// The Edge gateway must allow JWTs from registered external projects. The handler
// validates every bearer token and gym role with its original Auth/Data service.
Deno.serve(createCoreHandler({core:new BackendDB(url,key)}));
