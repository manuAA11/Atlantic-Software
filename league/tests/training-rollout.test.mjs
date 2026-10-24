import test from 'node:test';
import assert from 'node:assert/strict';
import {PGlite} from '@electric-sql/pglite';
import {authFixture,sourceFixture,migrations} from './database-fixture.mjs';
import {trainingMigration} from './training-fixture.mjs';
import {guardedTrainingMigration} from '../scripts/training-rollout.mjs';

test('atomic training rollout preserves legacy records and rejects changes to existing access',async()=>{
 const db=new PGlite();
 try{
  await db.exec(authFixture+sourceFixture);
  await migrations(db,'hub');await migrations(db,'source');
  await db.exec(guardedTrainingMigration(trainingMigration));
  assert.equal((await db.query('select count(*)::int n from public.clients')).rows[0].n,4);
  const unsafe=trainingMigration.replace("notify pgrst,'reload schema';","update public.gym_users set enabled=false;notify pgrst,'reload schema';");
  await assert.rejects(db.exec(guardedTrainingMigration(unsafe)),/existing records, accounts or legacy RPCs changed/);
  await db.exec('rollback');
  assert.equal((await db.query('select count(*)::int n from public.gym_users where not enabled')).rows[0].n,0);
  assert.throws(()=>guardedTrainingMigration('select 1;'),/Expected atomic/);
 }finally{await db.close();}
});
