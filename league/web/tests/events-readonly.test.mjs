import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
const require=createRequire(import.meta.url),React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),ts=require('typescript');
function load(path){
 const source=readFileSync(new URL(path,import.meta.url),'utf8');
 const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX}}).outputText;
 const mod={exports:{}};
 vm.runInNewContext(compiled,{exports:mod.exports,module:mod,Date,Intl,require:id=>id==='./gymSchedule'?load('../src/gymSchedule.ts'):require(id)});
 return mod.exports;
}
const {EventCard}=load('../src/EventCard.tsx');
const event={id:'event',kind:'EVENT',name:'Encuentro',description:'Actividad del gimnasio',starts_at:'2099-06-15T23:00:00Z',timezone:'America/Bogota',location:'Sala principal',capacity:0,reserved:0,mine:false,status:'PUBLISHED'};
const render=e=>renderToStaticMarkup(React.createElement(EventCard,{event:e,membership:{active:true},disabled:false,perform:()=>{throw Error('Reading an event must not write');}}));
test('mobile events are informational and show the gym location and time without booking controls',()=>{
 const html=render(event);assert.ok(html.includes('Sala principal'));assert.ok(html.includes('18:00'));assert.ok(html.includes('Evento del gimnasio'));
 assert.ok(!html.includes('<button'));assert.ok(!html.includes('cupos disponibles'));assert.ok(!html.includes('Reservar'));
});
test('cancelled and past events retain a read-only state',()=>{
 assert.ok(render({...event,status:'CANCELLED'}).includes('Evento cancelado'));
 assert.ok(render({...event,starts_at:'2020-06-15T23:00:00Z'}).includes('Evento finalizado'));
});
test('classes preserve existing member booking and cancellation behavior',()=>{
 const book=render({...event,kind:'CLASS',capacity:10,status:'PROGRAMADA'});assert.ok(book.includes('Reservar cupo'));assert.ok(!book.includes('disabled='));
 assert.ok(render({...event,kind:'CLASS',capacity:10,mine:true,status:'PROGRAMADA'}).includes('Cancelar reserva'));
 assert.ok(render({...event,kind:'CLASS',capacity:10,status:'CANCELADA'}).includes('disabled='));
});
