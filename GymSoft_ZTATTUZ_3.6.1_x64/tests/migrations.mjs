import { PGlite } from '@electric-sql/pglite';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
export const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
export async function database({upgrade=true,daily=true,marketing=true,freezes=true}={}) {
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
 await db.exec(fs.readFileSync(path.join(root,'tests/legacy_schema.sql'),'utf8'));
 if(upgrade) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_ZTATTUZ_3.4.5.sql'),'utf8'));
 await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_HUELLAS_3.5.0.sql'),'utf8'));
 if(daily && upgrade) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_CONSUMO_DIARIO.sql'),'utf8'));
 if(marketing && daily && upgrade) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_MARKETING.sql'),'utf8'));
 if(freezes && marketing && daily && upgrade) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_CONGELACION_Y_HORAS.sql'),'utf8'));
 if(freezes && marketing && daily && upgrade) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_SCHEDULER.sql'),'utf8'));
 if(freezes && marketing && daily && upgrade) await db.exec(fs.readFileSync(path.join(root,'ACTUALIZAR_INDICES_INTEGRACION.sql'),'utf8'));
 return db;
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const db=await database();
 console.log('ALL MIGRATIONS OK');
 await db.close();
}
