import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
test('service worker ignores API, authenticated, foreign-origin and non-GET requests',async()=>{
 const source=(await readFile(new URL('../src/service-worker.js',import.meta.url),'utf8')).replace('__VERSION__','test').replace('__ASSETS__',JSON.stringify(['/','/index.html','/assets/app.js']));
 const handlers={},cacheReads=[];
 vm.runInNewContext(source,{URL,Response,Set,fetch:async()=>new Response('network'),caches:{open:async name=>({match:async key=>{cacheReads.push([name,key]);return new Response('static');}})},self:{location:{origin:'https://league.example'},addEventListener:(name,fn)=>handlers[name]=fn}});
 for(const request of [new Request('https://league.example/api/data'),new Request('https://league.example/assets/app.js',{headers:{Authorization:'Bearer secret'}}),new Request('https://api.example/assets/app.js'),new Request('https://league.example/assets/app.js?token=private'),new Request('https://league.example/api/data',{method:'POST'})]){
  let handled=false;handlers.fetch({request,respondWith(){handled=true;}});assert.equal(handled,false,request.url);
 }
 let response;handlers.fetch({request:new Request('https://league.example/assets/app.js'),respondWith(p){response=p;}});assert.equal(await(await response).text(),'static');assert.deepEqual(cacheReads,[['atlantic-league-web-static-test','/assets/app.js']]);
});
