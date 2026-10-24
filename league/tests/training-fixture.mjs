import {readFile} from 'node:fs/promises';
import {authFixture,sourceFixture,migrations,identity,ADMIN} from './database-fixture.mjs';
export const trainingMigration=await readFile(new URL('../../training/supabase/migrations/20261024013933_gym_training_workspace.sql',import.meta.url),'utf8');
export const trainingSeed=await readFile(new URL('../../training/seeds/examples.sql',import.meta.url),'utf8');
export async function setupTraining(db){
 await db.exec(authFixture+sourceFixture+"select setval(pg_get_serial_sequence('public.classes','id'),(select max(id) from public.classes));");
 await migrations(db,'hub');await migrations(db,'source');
 await db.exec(trainingMigration);await db.exec(trainingMigration);await db.exec(trainingSeed);await db.exec(trainingSeed);
 await identity(db,ADMIN);
}
