import {spawnSync} from 'node:child_process';
import {readdir,readFile,writeFile,mkdir,rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {generateImageAsync} from '@expo/image-utils';
const root=fileURLToPath(new URL('../',import.meta.url)),out=path.join(root,'mobile/dist-web');
await rm(out,{recursive:true,force:true});
const result=spawnSync(process.platform==='win32'?'npm.cmd':'npm',['exec','--workspace','@atlantic/league-mobile','--','expo','export','--platform','web','--output-dir','dist-web'],{cwd:root,stdio:'inherit'});
if(result.status!==0)process.exit(result.status||1);
await mkdir(path.join(out,'icons'),{recursive:true});
for(const size of [180,192,512]){const {source}=await generateImageAsync({projectRoot:path.join(root,'mobile'),cacheType:'pwa-icons'},{src:path.join(root,'mobile/assets/atlantic-icon.png'),width:size,height:size,resizeMode:'contain'});await writeFile(path.join(out,`icons/atlantic-${size}.png`),source);}
await writeFile(path.join(out,'manifest.webmanifest'),JSON.stringify({id:'/',name:'Atlantic League',short_name:'League',lang:'es',start_url:'/',scope:'/',display:'standalone',background_color:'#F5F7FA',theme_color:'#14283E',icons:[192,512].map(size=>({src:`/icons/atlantic-${size}.png`,sizes:`${size}x${size}`,type:'image/png',purpose:'any'}))},null,2));
let html=await readFile(path.join(out,'index.html'),'utf8');
html=html.replace('<html lang="en">','<html lang="es">').replace('</head>','<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#14283E"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Atlantic League"><link rel="apple-touch-icon" href="/icons/atlantic-180.png"></head>');
html=html.replace('width=device-width, initial-scale=1, shrink-to-fit=no','width=device-width, initial-scale=1, viewport-fit=cover');
html=html.replace('</head>',`<meta name="apple-mobile-web-app-status-bar-style" content="default"><meta name="mobile-web-app-capable" content="yes"><style>
html,body{width:100%;height:100%;margin:0;background:#F5F8FB;overflow:hidden;overscroll-behavior-y:none}
#root{width:100%;height:100%;height:100dvh;height:min(100dvh,var(--league-viewport-height,100dvh));max-height:100dvh;min-height:0;overflow:hidden;isolation:isolate}
</style></head>`);
await writeFile(path.join(out,'index.html'),html);
async function walk(dir){const result=[];for(const entry of await readdir(dir,{withFileTypes:true})){const name=path.join(dir,entry.name);if(entry.isDirectory())result.push(...await walk(name));else result.push(name);}return result;}
const files=(await walk(out)).filter(f=>!f.endsWith('.map')&&!['sw.js','_headers'].includes(path.basename(f))).sort();
const hash=createHash('sha256');for(const f of files)hash.update(await readFile(f));
const version='atlantic-league-'+hash.digest('hex').slice(0,16),urls=files.map(f=>'/'+path.relative(out,f).split(path.sep).join('/'));
await writeFile(path.join(out,'sw.js'),`const CACHE=${JSON.stringify(version)},ASSETS=${JSON.stringify(urls)};
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS))));
self.addEventListener('message',event=>{if(event.data?.type==='ACTIVATE_UPDATE')self.skipWaiting();});
self.addEventListener('activate',event=>event.waitUntil((async()=>{for(const name of await caches.keys())if(name.startsWith('atlantic-league-')&&name!==CACHE)await caches.delete(name);await self.clients.claim();})()));
self.addEventListener('fetch',event=>{const url=new URL(event.request.url);if(event.request.method!=='GET'||url.origin!==self.location.origin||url.search)return;if(event.request.mode==='navigate'){event.respondWith(fetch(event.request).catch(()=>caches.match('/index.html')));return;}if(ASSETS.includes(url.pathname))event.respondWith(caches.open(CACHE).then(async cache=>(await cache.match(url.pathname))||fetch(event.request)));});
`);
await writeFile(path.join(out,'_headers'),'/sw.js\n  Cache-Control: no-cache\n/index.html\n  Cache-Control: no-cache\n/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n  Permissions-Policy: camera=(self), microphone=()\n');
console.log('PWA ready:',version,'— static shell only; no API responses cached.');
