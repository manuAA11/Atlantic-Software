import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {signupHTML} from '../core/onboarding.mjs';
const backend='https://bawrakwhzkxmhmgkczqu.supabase.co/functions/v1/marketing';
const state='a'.repeat(64);
const html=signupHTML({allowedBackends:[backend]});
const script=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const settle=async()=>{for(let i=0;i<5;i++)await new Promise(setImmediate);};
function page(url,fetcher){
 const elements={status:{textContent:''},connect:{disabled:true}},scripts=[],calls=[],events={},replaced=[];
 const window={location:{href:url,pathname:'/conectar/'},history:{replaceState:(...a)=>replaced.push(a)},addEventListener:(n,f)=>events[n]=f};
 const FB={init:x=>calls.push({init:x}),login:(f,options)=>{calls.push({options});f({authResponse:{code:'official-code'}});}};
 const document={getElementById:id=>elements[id],createElement:()=>({}),head:{appendChild:x=>scripts.push(x)}};
 vm.runInNewContext(script,{window,document,FB,URL,fetch:fetcher});
 return {window,elements,scripts,calls,events,replaced};
}
function config(){return Response.json({app_id:'12345678',config_id:'87654321',endpoint:backend+'/oauth/callback'});}
test('Authorization page obtains configuration from a live, gym-bound state',async()=>{
 const requests=[];const p=page('https://authorized.test/conectar/?state='+state+'&backend='+encodeURIComponent(backend),async(u,o)=>{
  requests.push({url:u,body:JSON.parse(o.body)});return u.endsWith('/bootstrap')?config():Response.json({connected:true});
 });await settle();
 assert.deepEqual(requests,[{url:backend+'/oauth/bootstrap',body:{state}}]);
 assert.equal(p.replaced[0][2],'/conectar/');assert.equal(p.scripts[0].src,'https://connect.facebook.net/es_LA/sdk.js');
 p.window.fbAsyncInit();assert.equal(p.elements.connect.disabled,false);
 p.elements.connect.onclick();
 p.events.message({origin:'https://attacker.test',data:{type:'WA_EMBEDDED_SIGNUP',event:'FINISH',data:{waba_id:'11111'}}});
 await settle();assert.equal(requests.length,1);
 const finish={origin:'https://www.facebook.com',data:JSON.stringify({type:'WA_EMBEDDED_SIGNUP',event:'FINISH',data:{waba_id:'11111',phone_number_id:'22222'}})};
 p.events.message(finish);p.events.message(finish);await settle();
 assert.deepEqual(requests[1],{url:backend+'/oauth/callback',body:{state,code:'official-code',waba_id:'11111',phone_number_id:'22222'}});
 assert.equal(requests.length,2);assert.equal(p.elements.connect.disabled,true);
 assert.match(p.elements.status.textContent,/WhatsApp conectado/);
 assert.deepEqual(JSON.parse(JSON.stringify(p.calls[1].options.extras)),{});
});
test('Unknown backend, missing state and malformed state never contact a server',async()=>{
 for(const url of ['https://authorized.test/',
  'https://authorized.test/?state='+state+'&backend=https://attacker.test',
  'https://authorized.test/?state=short&backend='+encodeURIComponent(backend)]){
  let requests=0;const p=page(url,async()=>{requests++;return config();});await settle();
  assert.equal(requests,0);assert.equal(p.scripts.length,0);assert.equal(p.elements.connect.disabled,true);
  assert.match(p.elements.status.textContent,/desde Conectar WhatsApp/);
 }
});
test('Expired authorization never loads Meta or enables authorization',async()=>{
 const p=page('https://authorized.test/?state='+state+'&backend='+encodeURIComponent(backend),async()=>Response.json({message:'La autorización venció.'},{status:400}));await settle();
 assert.equal(p.scripts.length,0);assert.match(p.elements.status.textContent,/venció/);
});
test('A bootstrap cannot redirect authorization codes to another host',async()=>{
 const p=page('https://authorized.test/?state='+state+'&backend='+encodeURIComponent(backend),async()=>Response.json({app_id:'12345678',config_id:'87654321',endpoint:'https://attacker.test/callback'}));await settle();
 assert.equal(p.scripts.length,0);assert.match(p.elements.status.textContent,/configuración/);
});
test('Failed completion requires a new authorization instead of replaying a consumed state',async()=>{
 let calls=0;const p=page('https://authorized.test/?state='+state+'&backend='+encodeURIComponent(backend),async(u)=>{calls++;return u.endsWith('/bootstrap')?config():Response.json({message:'No se pudo autorizar.'},{status:400});});await settle();
 p.window.fbAsyncInit();p.elements.connect.onclick();p.events.message({origin:'https://web.facebook.com',data:{type:'WA_EMBEDDED_SIGNUP',event:'FINISH',data:{waba_id:'11111'}}});await settle();
 assert.equal(calls,2);assert.equal(p.elements.connect.disabled,true);assert.match(p.elements.status.textContent,/nueva autorización/);
});
test('Authorization configuration is encoded as JSON, not executable HTML',()=>{
 const injected=signupHTML({app_id:'12345678',config_id:'87654321',state:'</script><script>alert(1)</script>',endpoint:backend+'/oauth/callback'});
 assert.equal((injected.match(/<script>/g)||[]).length,1);assert.equal(injected.includes('app_secret'),false);assert.equal(injected.includes('localStorage'),false);
});
