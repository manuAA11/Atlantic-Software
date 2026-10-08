import { PGlite } from '@electric-sql/pglite';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
export const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export async function database({daily=true,marketing=true,freezes=true}={}) {
 const db=new PGlite();
 await db.exec(`
 CREATE ROLE anon NOLOGIN; CREATE ROLE authenticated NOLOGIN; CREATE ROLE service_role NOLOGIN BYPASSRLS;
 CREATE SCHEMA auth;
 CREATE TABLE auth.users(id uuid PRIMARY KEY, email text UNIQUE, email_confirmed_at timestamptz DEFAULT now());
 CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS
 $$ SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
 CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE AS
 $$ SELECT coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb $$;
 GRANT USAGE ON SCHEMA auth TO authenticated,anon;
 GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA auth TO authenticated,anon;
 CREATE PUBLICATION supabase_realtime;
 `);
 for (const name of fs.readdirSync(path.join(root,'sql')).filter(n=>n.endsWith('.sql')).sort()) {
  try { await db.exec(fs.readFileSync(path.join(root,'sql',name),'utf8')); }
  catch(e){ console.error('MIGRATION FAILED',name,e.message,e.detail||'',e.where||''); throw new Error('Migration '+name+' failed'); }
 }
 await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_EDITOR_PROPIETARIO_3.1.0.sql'),'utf8'));
 await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_TIQUETERAS_3.3.0.sql'),'utf8'));
 await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_HUELLAS_3.5.0.sql'),'utf8'));
 if(daily) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_CONSUMO_DIARIO.sql'),'utf8'));
 if(marketing && daily) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_MARKETING.sql'),'utf8'));
 if(freezes && marketing && daily) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_CONGELACION_Y_HORAS.sql'),'utf8'));
 if(freezes && marketing && daily) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_SCHEDULER.sql'),'utf8'));
 return db;
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const db=await database();
 console.log('ALL MIGRATIONS OK');
 await db.close();
}
