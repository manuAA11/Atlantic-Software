import {readFile,writeFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const html=await readFile('dist/index.html','utf8');
const assets=(await readdir('dist/assets')).map(f=>'/assets/'+f);
const version=createHash('sha256').update(html).digest('hex').slice(0,16);
let source=await readFile('src/service-worker.js','utf8');
source=source.replace('__VERSION__',version).replace('__ASSETS__',JSON.stringify(['/','/index.html','/manifest.webmanifest','/icons/icon-192.png','/icons/icon-512.png',...assets]));
await writeFile('dist/sw.js',source);
console.log('Static-only service worker generated: '+version);
