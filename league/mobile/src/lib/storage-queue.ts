import type {SmallStore} from './chunk-storage';
/** Serialize each key so a slow draft write cannot resurrect a cleared draft. */
export function serializedStorage(base:SmallStore):SmallStore{
 const pending=new Map<string,Promise<unknown>>();
 const serial=<T,>(key:string,task:()=>Promise<T>):Promise<T>=>{
  const result=(pending.get(key)||Promise.resolve()).catch(()=>{}).then(task);
  pending.set(key,result);void result.finally(()=>{if(pending.get(key)===result)pending.delete(key);}).catch(()=>{});return result;
 };
 return {getItem:key=>serial(key,()=>base.getItem(key)),setItem:(key,value)=>serial(key,()=>base.setItem(key,value)),removeItem:key=>serial(key,()=>base.removeItem(key))};
}
