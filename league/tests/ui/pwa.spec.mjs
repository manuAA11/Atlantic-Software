import {test,expect} from '@playwright/test';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

test('PWA has install metadata, encrypted persistent draft, and an offline shell',async({page,context})=>{
 await page.goto('/');
 const manifest=await (await page.request.get('/manifest.webmanifest')).json();
 expect(manifest.display).toBe('standalone');expect(manifest.name).toBe('Atlantic League');
 await page.getByRole('button',{name:'Explorar demostración'}).click();
 await page.getByRole('button',{name:'Registrar entrenamiento'}).click();
 await page.getByLabel('Peso total · kg',{exact:true}).fill('42');
 await page.getByLabel('Repeticiones',{exact:true}).fill('9');
 await page.getByRole('button',{name:'Añadir serie',exact:true}).click();
 await expect.poll(()=>page.evaluate(async()=>{
  const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('atlantic-league-private-v1');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
  const stored=await new Promise(resolve=>{const r=db.transaction('records').objectStore('records').get('league-active-demo');r.onsuccess=()=>resolve(r.result);});
  db.close();return !!stored&&stored.data instanceof ArrayBuffer&&stored.iv.byteLength===12;
 })).toBe(true);
 await page.reload();
 await page.getByRole('button',{name:'Explorar demostración'}).click();
 await page.getByRole('button',{name:'Registrar entrenamiento'}).click();
 await expect(page.getByText('1 serie registrada',{exact:true})).toBeVisible();
 await expect(page.getByText('42 kg × 9',{exact:true})).toBeVisible();
 await page.evaluate(()=>navigator.serviceWorker.ready.then(async()=>{if(navigator.serviceWorker.controller)return;await new Promise(resolve=>navigator.serviceWorker.addEventListener('controllerchange',resolve,{once:true}));}));
 await context.setOffline(true);await page.reload();
 await expect(page.getByRole('button',{name:'Explorar demostración'})).toBeVisible();
 await expect(page.getByText(/Sin conexión · Las reservas/)).toBeVisible();
 await context.setOffline(false);
});

test('browser story exports a real vertical PNG',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Explorar demostración'}).click();
 await page.getByRole('button',{name:'Crear historia',exact:true}).click();
 const chooser=page.waitForEvent('filechooser');await page.getByRole('button',{name:'Mis fotos',exact:true}).click();
 await (await chooser).setFiles(fileURLToPath(new URL('../../mobile/assets/atlantic-icon.png',import.meta.url)));
 await expect(page.getByRole('button',{name:'Guardar imagen',exact:true})).toBeEnabled();
 const download=page.waitForEvent('download');await page.getByRole('button',{name:'Guardar imagen',exact:true}).click();
 const downloaded=await download;expect(downloaded.suggestedFilename()).toBe('Atlantic-League.png');
 const {readFile}=await import('node:fs/promises');const png=await readFile(await downloaded.path());
 expect(png.subarray(1,4).toString()).toBe('PNG');expect(png.readUInt32BE(16)).toBe(1080);expect(png.readUInt32BE(20)).toBe(1920);
});
