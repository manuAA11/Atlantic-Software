import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import {createInstallController} from '../src/install-runtime.mjs';
import * as policy from '../src/install-policy.mjs';
const require=createRequire(import.meta.url),React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),{MemoryRouter}=require('react-router'),ts=require('typescript');
const source=await readFile(new URL('../src/PwaEntry.tsx',import.meta.url),'utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText;
function fixture({ua='Mozilla/5.0 (iPhone) Version/18.0 Mobile Safari/604.1',standalone=false,path='/'}={}){
 const win=new EventTarget(),doc=new EventTarget(),media=new EventTarget();media.matches=standalone;
 win.matchMedia=()=>media;win.location=new URL(path,'https://league.example');doc.visibilityState='visible';
 const nav={userAgent:ua,platform:'',maxTouchPoints:0,standalone};
 const mod={exports:{}};
 vm.runInNewContext(compiled,{exports:mod.exports,module:mod,require:id=>id==='./install-runtime.mjs'?{createInstallController}:id==='./install-policy.mjs'?policy:require(id),window:win,navigator:nav,document:doc,location:win.location,URL,URLSearchParams});
 let calls=[];
 return {win,render(){calls=[];const page=React.createElement(MemoryRouter,{initialEntries:[path]},React.createElement(mod.exports.PwaEntry,{children:authOnly=>{calls.push(authOnly);return React.createElement('div',{'data-surface':authOnly?'essential-auth':'member-content'},authOnly?'Essential authentication flow':'Private member content');}}));return {html:renderToStaticMarkup(page),calls};}};
}
test('mobile browser renders the universal installation page without mounting member content',()=>{
 const f=fixture(),{html,calls}=f.render();assert.deepEqual(calls,[]);
 assert.ok(html.includes('Instala Atlantic League en tu celular'));assert.ok(html.includes('Accede a tu mensualidad, rutinas, eventos y clases directamente desde tu pantalla de inicio.'));
 assert.ok(html.includes('Abrir como app'));assert.ok(html.includes('alt="Atlantic League"'));assert.ok(!html.includes('Private member content'));
});
test('installed iPhone and Android render the existing application normally',()=>{
 for(const ua of ['Mozilla/5.0 (iPhone) Mobile Safari/604.1','Mozilla/5.0 (Linux; Android 15) Chrome/140 Mobile']){
  const {html,calls}=fixture({ua,standalone:true}).render();assert.deepEqual(calls,[false]);assert.ok(html.includes('Private member content'));assert.ok(!html.includes('Instala Atlantic League en tu celular'));
 }
});
test('Android prompt is conditional and alternative browsers retain menu instructions',()=>{
 const f=fixture({ua:'Mozilla/5.0 (Linux; Android 15) Chrome/140 Mobile'});
 let {html}=f.render();assert.ok(html.includes('Abre el menú de tu navegador'));assert.ok(!html.includes('install-primary'));
 const offered=new Event('beforeinstallprompt',{cancelable:true});offered.prompt=async()=>{};offered.userChoice=Promise.resolve({outcome:'accepted'});f.win.dispatchEvent(offered);
 html=f.render().html;assert.ok(html.includes('install-primary'));assert.ok(html.includes('Instalar aplicación'));
 const alternative=fixture({ua:'Mozilla/5.0 (Linux; Android 15) Firefox/140 Mobile'}).render().html;
 assert.ok(alternative.includes('según el navegador'));assert.ok(alternative.includes('Añadir a pantalla de inicio'));
});
test('embedded browsers and non-standalone shortcuts always explain how to recover',()=>{
 const html=fixture({ua:'Mozilla/5.0 (iPhone) Mobile Instagram 300'}).render().html;
 assert.ok(html.includes('Abre el enlace en tu navegador'));assert.ok(html.includes('¿No aparece la opción o el icono abre el navegador?'));assert.ok(html.includes('Copiar enlace'));
 assert.ok(!html.includes('Private member content'));
});
test('auth callbacks and recovery render only the essential flow, while desktop keeps web access',()=>{
 for(const path of ['/auth/callback?code=example','/reset-password','/?token=example']){
  const {html,calls}=fixture({path}).render();assert.deepEqual(calls,[true]);assert.ok(html.includes('Essential authentication flow'));assert.ok(!html.includes('Private member content'));
 }
 const {html,calls}=fixture({ua:'Mozilla/5.0 (Windows NT 10.0) Chrome/140'}).render();assert.deepEqual(calls,[false]);assert.ok(html.includes('Private member content'));
});
