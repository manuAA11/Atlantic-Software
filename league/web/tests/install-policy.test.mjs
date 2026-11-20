import test from 'node:test';
import assert from 'node:assert/strict';
import {deviceEnvironment,essentialAccessFlow,installDecision} from '../src/install-policy.mjs';
import {createInstallController} from '../src/install-runtime.mjs';
const iphone='Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1';
const android='Mozilla/5.0 (Linux; Android 15; Pixel) AppleWebKit/537.36 Chrome/140.0.0.0 Mobile Safari/537.36';
const url='https://league.example/';
test('iPhone browser shows installation; standalone uses either supported signal',()=>{
 const browser=deviceEnvironment({userAgent:iphone});assert.equal(browser.os,'ios');assert.equal(installDecision(browser,url),'install');
 for(const mode of [{displayStandalone:true},{standalone:true}])assert.equal(installDecision(deviceEnvironment({userAgent:iphone,...mode}),url),'app');
 assert.equal(installDecision(browser,url+'?installed=true'),'install');
});
test('Android Chrome and alternative browsers keep the mobile gate until standalone',()=>{
 for(const userAgent of [android,android.replace('Chrome/140.0.0.0','SamsungBrowser/25.0 Chrome/140.0'),android.replace('Chrome/140.0.0.0','Firefox/140.0')]){
  assert.equal(installDecision(deviceEnvironment({userAgent}),url),'install');
  assert.equal(installDecision(deviceEnvironment({userAgent,displayStandalone:true}),url),'app');
 }
});
test('iPadOS desktop UA, embedded browsers and desktop computers receive the right experience',()=>{
 assert.equal(deviceEnvironment({userAgent:'Mozilla/5.0 (Macintosh) Safari/605.1.15',platform:'MacIntel',maxTouchPoints:5}).os,'ios');
 assert.equal(deviceEnvironment({userAgent:iphone+' Instagram 300.0'}).embedded,true);
 assert.equal(deviceEnvironment({userAgent:android.replace('Pixel','Pixel; wv')}).embedded,true);
 const desktop=deviceEnvironment({userAgent:'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140 Safari/537'});
 assert.equal(desktop.mobile,false);assert.equal(installDecision(desktop,url),'app');
});
test('authentication, recovery, invitations and URL fragments bypass only the installation UX',()=>{
 const mobile=deviceEnvironment({userAgent:iphone});
 for(const path of ['auth/callback?code=example','recovery','reset-password','activate?token=example','invite/example','?token_hash=example&type=recovery','#access_token=example&refresh_token=example','?code=example','?error=access_denied','#/auth/callback?code=example']){
  assert.equal(essentialAccessFlow(url+path),true,path);assert.equal(installDecision(mobile,url+path),'auth',path);
 }
 for(const path of ['rutinas','agenda','perfil','notificaciones'])assert.equal(essentialAccessFlow(url+path),false,path);
});
function fixture({ua=android,legacyMedia=false}={}){
 const win=new EventTarget(),doc=new EventTarget(),media=new EventTarget();
 win.location={href:url};media.matches=false;win.matchMedia=()=>media;doc.visibilityState='visible';
 if(legacyMedia){media.addListener=fn=>EventTarget.prototype.addEventListener.call(media,'change',fn);media.removeListener=fn=>EventTarget.prototype.removeEventListener.call(media,'change',fn);media.addEventListener=undefined;media.removeEventListener=undefined;}
 const nav={userAgent:ua,platform:'',maxTouchPoints:0};
 return {win,doc,media,nav,controller:createInstallController(win,nav,doc)};
}
test('install prompt is user-initiated, single-use, and does not unlock the browser after acceptance',async()=>{
 const f=fixture();let prompts=0;const offered=new Event('beforeinstallprompt',{cancelable:true});
 offered.prompt=async()=>{prompts++;};offered.userChoice=Promise.resolve({outcome:'accepted'});
 f.win.dispatchEvent(offered);assert.equal(offered.defaultPrevented,true);assert.equal(prompts,0);assert.equal(f.controller.getSnapshot().canPrompt,true);
 assert.equal(await f.controller.install(),'accepted');assert.equal(prompts,1);assert.equal(await f.controller.install(),'unavailable');
 assert.equal(f.controller.getSnapshot().mode,'install');assert.equal(f.controller.getSnapshot().installedNotice,true);
 f.media.matches=true;f.media.dispatchEvent(new Event('change'));assert.equal(f.controller.getSnapshot().mode,'app');f.controller.dispose();
});
test('dismissal falls back to instructions; a later browser prompt can be offered again',async()=>{
 const f=fixture();const offered=new Event('beforeinstallprompt',{cancelable:true});offered.prompt=async()=>{};offered.userChoice=Promise.resolve({outcome:'dismissed'});f.win.dispatchEvent(offered);
 assert.equal(await f.controller.install(),'dismissed');assert.equal(f.controller.getSnapshot().canPrompt,false);assert.equal(f.controller.getSnapshot().mode,'install');
 f.win.dispatchEvent(offered);assert.equal(f.controller.getSnapshot().canPrompt,true);f.controller.dispose();
});
test('manual installation, browser shortcuts, visibility changes and older Safari media listeners',()=>{
 const f=fixture({ua:iphone,legacyMedia:true});let updates=0;f.controller.subscribe(()=>updates++);
 f.win.dispatchEvent(new Event('appinstalled'));assert.equal(f.controller.getSnapshot().mode,'install');
 f.nav.standalone=true;f.win.dispatchEvent(new Event('pageshow'));assert.equal(f.controller.getSnapshot().mode,'app');
 f.nav.standalone=false;f.doc.dispatchEvent(new Event('visibilitychange'));assert.equal(f.controller.getSnapshot().mode,'install');
 f.media.matches=true;f.media.dispatchEvent(new Event('change'));assert.equal(f.controller.getSnapshot().mode,'app');
 const before=updates;f.controller.dispose();f.media.matches=false;f.media.dispatchEvent(new Event('change'));assert.equal(updates,before);
});
test('routing changes preserve essential callbacks and the controller never touches member session storage',()=>{
 const f=fixture({ua:iphone});Object.defineProperty(f.win,'localStorage',{get(){throw Error('Member sessions must not be accessed by the install controller');}});
 f.win.location.href=url+'auth/callback?code=example';f.win.dispatchEvent(new Event('popstate'));assert.equal(f.controller.getSnapshot().mode,'auth');
 f.win.location.href=url;f.controller.refresh();assert.equal(f.controller.getSnapshot().mode,'install');
 f.controller.dispose();
});
