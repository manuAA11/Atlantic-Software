/** Atomic, serialized manifests keep long sessions within SecureStore's item limit. */
export type SmallStore={getItem:(key:string)=>Promise<string|null>;setItem:(key:string,value:string)=>Promise<void>;removeItem:(key:string)=>Promise<void>};
export function chunkStorage(base:SmallStore,nonce:()=>string){
 const pending=new Map<string,Promise<unknown>>();
 const serial=<T,>(key:string,task:()=>Promise<T>):Promise<T>=>{
  const result=(pending.get(key)||Promise.resolve()).catch(()=>{}).then(task);
  pending.set(key,result);void result.finally(()=>{if(pending.get(key)===result)pending.delete(key);}).catch(()=>{});return result;
 };
 const manifest=async(key:string)=>{
  const text=await base.getItem(key+'.manifest');if(!text)return null;
  try{const parsed=JSON.parse(text);return /^[a-zA-Z0-9-]{1,80}$/.test(parsed.generation)&&Number.isInteger(parsed.parts)&&parsed.parts>0&&parsed.parts<=1024?parsed as {generation:string;parts:number}:null;}catch{return null;}
 };
 const removeParts=async(key:string,m:{generation:string;parts:number}|null)=>{
  if(m)await Promise.all(Array.from({length:m.parts},(_,i)=>base.removeItem(`${key}.${m.generation}.${i}`)));
 };
 return {
  getItem:(key:string)=>serial(key,async()=>{
   const m=await manifest(key);if(!m)return null;let text='';
   for(let i=0;i<m.parts;i++){const part=await base.getItem(`${key}.${m.generation}.${i}`);if(part===null)return null;text+=part;}return text;
  }),
  setItem:(key:string,value:string)=>serial(key,async()=>{
   if(value.length>409600)throw Error('El almacenamiento local está lleno. Sincroniza tus entrenamientos.');
   const previous=await manifest(key),chars=Array.from(value),m={generation:nonce(),parts:Math.max(1,Math.ceil(chars.length/400))};
   try{
    for(let i=0;i<m.parts;i++)await base.setItem(`${key}.${m.generation}.${i}`,chars.slice(i*400,(i+1)*400).join(''));
    await base.setItem(key+'.manifest',JSON.stringify(m));
   }catch(error){await removeParts(key,m).catch(()=>{});throw error;}
   await removeParts(key,previous).catch(()=>{});
  }),
  removeItem:(key:string)=>serial(key,async()=>{const m=await manifest(key);await base.removeItem(key+'.manifest');await removeParts(key,m);}),
 };
}
