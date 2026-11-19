/* No Auth requests, API responses or personal data are ever placed in Cache Storage. */
const PREFIX='atlantic-league-web-static-',CACHE=PREFIX+'__VERSION__';
const FILES=__ASSETS__;
const paths=new Set(FILES);
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(FILES))));
self.addEventListener('message',event=>{if(event.data?.type==='ACTIVATE_UPDATE')self.skipWaiting();});
self.addEventListener('activate',event=>event.waitUntil((async()=>{
 for(const key of await caches.keys())if(key.startsWith(PREFIX)&&key!==CACHE)await caches.delete(key);
 await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
 const request=event.request,url=new URL(request.url);
 if(request.method!=='GET'||url.origin!==self.location.origin||url.search||request.headers.has('Authorization'))return;
 if(request.mode==='navigate'){
  event.respondWith(fetch(request).catch(async()=>{
   const shell=await (await caches.open(CACHE)).match('/index.html');
   return shell||new Response('Conéctate para abrir Atlantic League.',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8'}});
  }));return;
 }
 if(!paths.has(url.pathname))return;
 event.respondWith((async()=>await (await caches.open(CACHE)).match(url.pathname)||fetch(request))());
});
self.addEventListener('push',event=>{
 // Push payload is never rendered: lock-screen content stays generic and private.
 event.waitUntil(self.registration.showNotification('Atlantic League',{body:'Tienes un nuevo aviso de tu gimnasio.',icon:'/icons/icon-192.png',tag:'atlantic-league-notice',data:{path:'/notificaciones'}}));
});
self.addEventListener('notificationclick',event=>{
 event.notification.close();
 event.waitUntil((async()=>{
  const url=new URL('/notificaciones',self.location.origin).href;
  const clients=await self.clients.matchAll({type:'window',includeUncontrolled:true});
  const existing=clients.find(c=>new URL(c.url).origin===self.location.origin);
  if(existing){await existing.navigate(url);return existing.focus();}return self.clients.openWindow(url);
 })());
});
