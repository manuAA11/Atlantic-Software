import type {WorkoutPayload} from './domain';
import type {LeagueApi} from './api';
import type {SmallStore} from './chunk-storage';
/** Retrying the unchanged UUID + payload is safe, including after an ambiguous timeout. */
export function workoutOutbox(storage:SmallStore,userId:string){
 const key='league-workout-outbox-'+userId;
 const read=async():Promise<WorkoutPayload[]>=>JSON.parse(await storage.getItem(key)||'[]');
 let running=Promise.resolve();
 const serial=<T,>(fn:()=>Promise<T>)=>{const result=running.then(fn,fn);running=result.then(()=>{},()=>{});return result;};
 return {
  list:()=>serial(read),
  add:(payload:WorkoutPayload)=>serial(async()=>{
   const entries=await read();const old=entries.find(x=>x.id===payload.id);
   if(old&&JSON.stringify(old)!==JSON.stringify(payload))throw Error('El entrenamiento ya está pendiente con otro contenido.');
   if(!old){if(entries.length>=30)throw Error('Sincroniza tus entrenamientos pendientes antes de continuar.');entries.push(payload);await storage.setItem(key,JSON.stringify(entries));}
  }),
  flush:(api:LeagueApi)=>serial(async()=>{
   const entries=await read();let sent=0;
   while(entries.length){await api.call('workout.save',entries[0] as unknown as Record<string,unknown>);entries.shift();sent++;await storage.setItem(key,JSON.stringify(entries));}
   return sent;
  }),
  clear:()=>serial(()=>storage.removeItem(key)),
 };
}
