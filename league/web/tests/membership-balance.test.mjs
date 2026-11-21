import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import vm from 'node:vm';
const require=createRequire(import.meta.url),React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),ts=require('typescript');
const source=await readFile(new URL('../src/MembershipBalance.tsx',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
const mod={exports:{}};
vm.runInNewContext(compiled,{exports:mod.exports,module:mod,require});
const render=member=>renderToStaticMarkup(React.createElement(mod.exports.MembershipBalance,{member}));
test('ticket balance shows the server values and leaves the supplied membership unchanged',()=>{
 const member={active:true,entry_limit:12,entries_used:3,entries_remaining:9,already_consumed_today:false};
 const before=JSON.stringify(member),html=render(member);
 assert.match(html,/Entradas disponibles<\/span><strong>9<\/strong>/);
 assert.match(html,/Entradas consumidas<\/span><strong>3<\/strong>/);
 assert.match(html,/Total del plan: 12 entradas/);assert.equal(JSON.stringify(member),before);
 assert.ok(!html.includes('hoy ya está registrada'));
});
test('exhausted and frozen tickets retain zero balance and the server daily registration',()=>{
 for(const frozen of [false,true]){
  const html=render({active:false,frozen,entry_limit:12,entries_used:12,entries_remaining:0,already_consumed_today:true});
  assert.match(html,/Entradas disponibles<\/span><strong>0<\/strong>/);
  assert.match(html,/Entradas consumidas<\/span><strong>12<\/strong>/);
  assert.ok(html.includes('Tu entrada de hoy ya está registrada.'));
 }
 const unused=render({entry_limit:12,entries_used:0,entries_remaining:12});
 assert.match(unused,/Entradas consumidas<\/span><strong>0<\/strong>/);
});
test('monthly, unlimited, missing and no-plan memberships do not show a ticket counter',()=>{
 for(const member of [null,{active:true},{active:true,entry_limit:null,entries_used:0,entries_remaining:null},{active:false,status:'NO_PLAN',entry_limit:null}]){
  assert.equal(render(member),'');
 }
});
test('unknown or invalid ticket counts stay unavailable instead of becoming an invented zero',()=>{
 for(const fields of [{},{entries_used:-1,entries_remaining:'7'},{entries_used:NaN,entries_remaining:Infinity}]){
  const html=render({entry_limit:12,...fields});
  assert.ok(html.includes('El saldo de entradas aún no está disponible.'));
  assert.ok(!html.includes('<strong>0</strong>'));assert.ok(!html.includes('<strong>7</strong>'));
 }
});
