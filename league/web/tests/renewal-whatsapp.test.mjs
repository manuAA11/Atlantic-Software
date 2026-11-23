import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import * as whatsapp from '../src/renewal-whatsapp.mjs';
const require=createRequire(import.meta.url),React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),ts=require('typescript');
const source=await readFile(new URL('../src/RenewMembership.tsx',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
const mod={exports:{}};
vm.runInNewContext(compiled,{module:mod,exports:mod.exports,require:id=>id==='./renewal-whatsapp.mjs'?whatsapp:require(id)});
const member={renewable:true,status:'ACTIVE',plan_name:'Plan mensual',renewal_whatsapp_url:'https://wa.me/15555550123',document:'NEVER_SEND_DOCUMENT',access_token:'NEVER_SEND_TOKEN'};
const render=(m,disabled=false)=>renderToStaticMarkup(React.createElement(mod.exports.RenewMembership,{member:m,gymName:'Gym QA',disabled}));
test('monthly and ticket renewal opens the configured gym chat with a minimal draft',()=>{
 for(const [extra,word] of [[{},'mensualidad'],[{entry_limit:12,plan_name:'Tiquetera de 12'},'tiquetera']]){
  const value=Object.freeze({...member,...extra}),before=JSON.stringify(value),target=whatsapp.renewalWhatsApp(value,'Gym QA');
  const url=new URL(target.url);assert.equal(url.origin,'https://wa.me');assert.equal(url.pathname,'/15555550123');assert.ok(url.searchParams.get('text').includes(word));assert.ok(url.searchParams.get('text').includes(value.plan_name));
  assert.ok(!target.url.includes('NEVER_SEND'));assert.equal(JSON.stringify(value),before);
  const html=render(value);assert.ok(html.includes('Renovar membresía'));assert.ok(html.includes('target="_blank"'));assert.ok(html.includes('noopener noreferrer'));assert.ok(html.includes('tú decides enviar'));
 }
});
test('no-plan and internal plans have honest renewal labels',()=>{
 const noPlan={...member,status:'NO_PLAN',plan_name:null};
 assert.ok(render(noPlan).includes('Consultar planes por WhatsApp'));
 assert.ok(new URL(whatsapp.renewalWhatsApp(noPlan,'Gym QA').url).searchParams.get('text').includes('información'));
 const internal=render({...member,renewable:false});assert.ok(internal.includes('no requiere renovación'));assert.ok(!internal.includes('href='));
});
test('missing configuration or offline renewal cannot navigate or create a request',()=>{
 for(const value of [null,{...member,renewal_whatsapp_url:null},member]){
  const html=render(value,true);assert.ok(!html.includes('href='));
 }
 assert.ok(render({...member,renewal_whatsapp_url:null}).includes('todavía no ha configurado'));
});
test('official channel links are opened without inventing a chat or sending account data',()=>{
 const value={...member,renewal_whatsapp_url:'https://www.whatsapp.com/channel/Abc12345678/'};
 assert.deepEqual(whatsapp.renewalWhatsApp(value,'Gym QA'),{url:'https://whatsapp.com/channel/Abc12345678',kind:'channel'});
 const html=render(value);assert.ok(html.includes('canal del gimnasio'));assert.ok(!html.includes('?text='));
});
test('unsafe destinations, tracking queries and embedded credentials are rejected',()=>{
 for(const target of ['javascript:alert(1)','http://wa.me/15555550123','https://wa.me.evil.example/15555550123','https://evil.example/channel/Abc12345678','https://owner:password@wa.me/15555550123','https://wa.me:444/15555550123','https://wa.me/15555550123?text=private','https://wa.me/15555550123#token','https://wa.me/+15555550123']){
  assert.equal(whatsapp.renewalWhatsApp({...member,renewal_whatsapp_url:target},'Gym QA'),null,target);
 }
});

