import assert from 'node:assert/strict';
import {request} from 'node:https';
const origin='https://atlantic-league.atlanticsoftware11.workers.dev';
const api='https://srmquhwpawgipncmvfjf.supabase.co/functions/v1/';
function http(url,{method='GET',headers={},body}={}){
 return new Promise((resolve,reject)=>{
  const req=request(url,{method,headers:{'Accept':'*/*','Accept-Encoding':'identity',...headers}},res=>{
   const chunks=[];let bytes=0;
   res.on('data',chunk=>{bytes+=chunk.length;if(bytes>2*1024*1024){req.destroy(Error('Unexpected response size'));return;}chunks.push(chunk);});
   res.on('end',()=>resolve({status:res.statusCode,headers:res.headers,text:Buffer.concat(chunks).toString('utf8')}));
   res.on('error',reject);
  });
  req.setTimeout(20000,()=>req.destroy(Error('Request timed out')));req.on('error',reject);
  if(body)req.write(body);req.end();
 });
}
let root;
for(let attempt=0;attempt<5;attempt++){
 try{root=await http(origin+'/',{headers:{Accept:'text/html','Sec-Fetch-Mode':'navigate'}});if(root.status===200&&root.text.includes('<title>Atlantic League</title>'))break;}catch(error){if(attempt===4)throw error;}
 await new Promise(resolve=>setTimeout(resolve,3000));
}
assert.equal(root?.status,200);assert.ok(root.text.includes('<title>Atlantic League</title>'),'The public URL must serve League, not a placeholder');
const shell=await http(origin+'/');assert.equal(shell.status,200);assert.ok(shell.text.includes('<title>Atlantic League</title>'));
const directIndex=await http(origin+'/index.html');assert.equal(directIndex.status,200);
const manifest=await http(origin+'/manifest.webmanifest');assert.equal(manifest.status,200);
const metadata=JSON.parse(manifest.text);assert.equal(metadata.display,'standalone');assert.equal(metadata.start_url,'/');
const worker=await http(origin+'/sw.js');assert.equal(worker.status,200);assert.ok(worker.text.includes('atlantic-league-web-static-'));assert.ok(!worker.text.includes('__VERSION__'));assert.match(String(worker.headers['cache-control']),/no-cache/);
assert.equal(worker.headers['service-worker-allowed'],'/');
const script=root.text.match(/src="(\/assets\/[^"]+\.js)"/)?.[1];assert.ok(script);
const bundle=await http(origin+script);assert.equal(bundle.status,200);assert.ok(bundle.text.includes('Instala Atlantic League en tu celular'));assert.ok(bundle.text.includes('/functions/v1/atlantic-league-member-access'));assert.ok(bundle.text.includes('Entradas disponibles'));assert.ok(bundle.text.includes('Entradas consumidas'));assert.ok(bundle.text.includes('Renovar membresía'));assert.ok(bundle.text.includes('Evento cancelado'));
for(const icon of metadata.icons){const result=await http(new URL(icon.src,origin),{method:'HEAD'});assert.equal(result.status,200);assert.match(String(result.headers['content-type']),/image\/png/);}
for(const path of ['/agenda','/rutinas','/auth/callback?code=smoke-placeholder','/auth/recovery','/invite?token=smoke-placeholder']){
 const result=await http(origin+path,{headers:{Accept:'text/html','Sec-Fetch-Mode':'navigate'}});assert.equal(result.status,200);assert.ok(result.text.includes('<title>Atlantic League</title>'));
}
for(const name of ['atlantic-league-member-access','atlantic-league-members']){
 const preflight=await http(api+name,{method:'OPTIONS',headers:{Origin:origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type,authorization'}});
 assert.equal(preflight.status,204);assert.equal(preflight.headers['access-control-allow-origin'],origin);
 const foreign=await http(api+name,{method:'OPTIONS',headers:{Origin:'https://untrusted.example.invalid','Access-Control-Request-Method':'POST'}});
 assert.equal(foreign.status,403);assert.equal(foreign.headers['access-control-allow-origin'],undefined);
}
const anonymous=await http(api+'atlantic-league-members',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({audience:'athlete',action:'snapshot',data:{}})});
assert.equal(anonymous.status,401);assert.equal(anonymous.headers['access-control-allow-origin'],origin);assert.match(String(anonymous.headers['cache-control']),/no-store/);
console.log('PASS: public League assets, standalone manifest, service worker headers, SPA/auth URL access, exact-origin CORS, foreign-origin rejection and member authentication requirement.');
console.log('Physical iPhone/Android installation, valid-member login, session persistence and recovery-provider acceptance remain pending.');
