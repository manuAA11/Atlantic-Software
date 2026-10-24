import {test} from 'node:test';
import assert from 'node:assert/strict';
import {PGlite} from '@electric-sql/pglite';
import {authFixture,sourceFixture,migrations} from './database-fixture.mjs';
import {trainingMigration} from './training-fixture.mjs';
import {assessPreflight,readPreflight} from '../scripts/training-preflight.mjs';
import {readFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

test('restore rehearsal rejects remote, overridden and malformed destinations before connecting without logging credentials',()=>{
 const secret='PRIVATE_SENTINEL_PASSWORD';
 for(const url of [`postgres://operator:${secret}@db.example.invalid/postgres`,`postgres://operator:${secret}@127.0.0.1/postgres?host=db.example.invalid`,`postgres://operator:${secret}@[invalid`]){
  const child=spawnSync(process.execPath,[fileURLToPath(new URL('./training-restore-postgres.mjs',import.meta.url))],{env:{...process.env,LEAGUE_TEST_DATABASE_URL:url,LEAGUE_TEST_DATABASE_ALLOW_LOCAL:'1'},timeout:5000,encoding:'utf8'});
  assert.equal(child.error,undefined);assert.notEqual(child.status,0);
  const output=child.stdout+child.stderr;assert(!output.includes(secret));assert.match(output,/disposable local PostgreSQL/);
 }
});

test('rollout preflight distinguishes baseline, installed, disabled and unsafe permissions without modifying data',async()=>{
 const db=new PGlite();try{
  await db.exec(authFixture+sourceFixture);await migrations(db,'hub');await migrations(db,'source');
  const before=JSON.stringify((await db.query('select * from public.clients order by id')).rows);
  const snapshot=await readPreflight(db);assert.equal(assessPreflight(snapshot).state,'ready_for_migration');
  const damaged=structuredClone(snapshot);delete damaged.new_columns;assert.equal(assessPreflight(damaged).state,'blocked');
  assert.equal(JSON.stringify((await db.query('select * from public.clients order by id')).rows),before);
  await db.exec(trainingMigration);assert.equal(assessPreflight(await readPreflight(db)).state,'installed');
  await db.exec(await readFile(new URL('../../training/rollback/disable_workspace.sql',import.meta.url),'utf8'));
  assert.equal(assessPreflight(await readPreflight(db)).state,'disabled');
  await db.exec(trainingMigration);await db.exec('grant select on public.gym_routine_templates to authenticated');
  assert(assessPreflight(await readPreflight(db)).blockers.includes('table_access:public.gym_routine_templates'));
  await db.exec('revoke select on public.gym_routine_templates from authenticated;grant execute on function public.gym_training(uuid,text,jsonb) to anon');
  assert(assessPreflight(await readPreflight(db)).blockers.includes('training_rpc_permissions'));
 }finally{await db.close();}
});

test('preflight blocks a disabled capacity trigger, lost uniqueness and partial migration',async()=>{
 const db=new PGlite();try{
  await db.exec(authFixture+sourceFixture);await migrations(db,'hub');await migrations(db,'source');
  await db.exec('alter table public.reservations disable trigger league_reservation_capacity');
  assert(assessPreflight(await readPreflight(db)).blockers.includes('reservation_capacity_guard'));
  await db.exec('alter table public.reservations enable trigger league_reservation_capacity;alter table public.reservations drop constraint reservations_class_id_client_id_key');
  assert(assessPreflight(await readPreflight(db)).blockers.includes('reservation_unique_constraint'));
  await db.exec('alter table public.reservations add unique(class_id,client_id);alter table public.classes add column conditions text');
  assert(assessPreflight(await readPreflight(db)).blockers.includes('partial_training_installation'));
 }finally{await db.close();}
});
