import {serializedStorage} from './storage-queue';
/** Browser-local encryption. A same-origin script can use the key; this is not an XSS boundary. */
const DB='atlantic-league-private-v1';
let connection:Promise<IDBDatabase>|undefined;
function database(){
 if(!window.isSecureContext||!crypto.subtle)throw Error('Abre Atlantic League mediante HTTPS para guardar la sesión y los entrenamientos de forma segura.');
 return connection??=new Promise<IDBDatabase>((resolve,reject)=>{
  const request=indexedDB.open(DB,1);
  request.onupgradeneeded=()=>{request.result.createObjectStore('records');request.result.createObjectStore('keys');};
  request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(Error('No se pudo abrir el almacenamiento del navegador.'));
 });
}
async function read(store:string,key:string){const db=await database();return new Promise<any>((resolve,reject)=>{const tx=db.transaction(store,'readonly'),request=tx.objectStore(store).get(key);request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});}
async function write(store:string,key:string,value:unknown,remove=false){const db=await database();return new Promise<void>((resolve,reject)=>{const tx=db.transaction(store,'readwrite');if(remove)tx.objectStore(store).delete(key);else tx.objectStore(store).put(value,key);tx.oncomplete=()=>resolve();tx.onabort=()=>reject(Error('No se pudo guardar. Revisa el espacio disponible en el navegador.'));tx.onerror=()=>reject(tx.error);});}
// add(), rather than put(), prevents two tabs from replacing each other's key.
let keyPromise:Promise<CryptoKey>|undefined;
async function encryptionKey(){return keyPromise??=(async()=>{
 const existing=await read('keys','device');if(existing)return existing as CryptoKey;
 const key=await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']);
 const db=await database();await new Promise<void>((resolve)=>{const tx=db.transaction('keys','readwrite');tx.objectStore('keys').add(key,'device');tx.oncomplete=()=>resolve();tx.onabort=()=>resolve();});
 return await read('keys','device') as CryptoKey;
 })().catch(error=>{keyPromise=undefined;throw error;});}
export const secureStorage=serializedStorage({
 async getItem(key:string):Promise<string|null>{const record=await read('records',key);if(!record)return null;const decoded=await crypto.subtle.decrypt({name:'AES-GCM',iv:record.iv},await encryptionKey(),record.data);return new TextDecoder().decode(decoded);},
 async setItem(key:string,value:string){if(value.length>409600)throw Error('Sincroniza tus entrenamientos para liberar espacio.');await database();const iv=crypto.getRandomValues(new Uint8Array(12));const data=await crypto.subtle.encrypt({name:'AES-GCM',iv},await encryptionKey(),new TextEncoder().encode(value));await write('records',key,{iv,data});},
 async removeItem(key:string){await write('records',key,null,true);},
});
