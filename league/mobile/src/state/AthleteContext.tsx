import React,{createContext,useCallback,useContext,useEffect,useMemo,useState} from 'react';
import {AppState} from 'react-native';
import type {LeagueApi} from '../lib/api';
import type {Snapshot,Exercise,WorkoutPayload} from '../lib/domain';
import {secureStorage} from '../lib/storage';
import {workoutOutbox} from '../lib/outbox';

type State={api:LeagueApi;snapshot:Snapshot|null;catalog:Exercise[];demo:boolean;busy:boolean;notice:string;pending:number;refresh:()=>Promise<void>;saveWorkout:(payload:WorkoutPayload)=>Promise<void>;signOut:()=>Promise<void>;setNotice:(text:string)=>void};
const Context=createContext<State|null>(null);
export const useAthlete=()=>{const value=useContext(Context);if(!value)throw Error('Missing athlete context');return value;};
export function AthleteProvider({children,api,userId,demo,signOut}:{children:React.ReactNode;api:LeagueApi;userId:string;demo:boolean;signOut:()=>Promise<void>}){
 const [snapshot,setSnapshot]=useState<Snapshot|null>(null),[catalog,setCatalog]=useState<Exercise[]>([]),[busy,setBusy]=useState(true),[notice,setNotice]=useState(''),[pending,setPending]=useState(0);
 const outbox=useMemo(()=>workoutOutbox(secureStorage,userId),[userId]);
 const cacheKey='league-cache-'+userId;
 const refresh=useCallback(async()=>{
  setBusy(true);
  try{
   await api.call('profile.ensure');
   await outbox.flush(api);
   const [next,exercises]=await Promise.all([api.call<Snapshot>('snapshot'),api.call<Exercise[]>('catalog')]);
   setSnapshot(next);setCatalog(exercises);setNotice('');
   await secureStorage.setItem(cacheKey,JSON.stringify({snapshot:{...next,workouts:next.workouts.slice(0,20)},catalog:exercises.slice(0,100)}));
  }catch(error){setNotice(error instanceof Error?error.message:'No se pudieron actualizar los datos.');}
  finally{setPending((await outbox.list()).length);setBusy(false);}
 },[api,outbox,cacheKey]);
 useEffect(()=>{
  let mounted=true;
  void (async()=>{try{const cached=await secureStorage.getItem(cacheKey);if(cached&&mounted){const data=JSON.parse(cached);setSnapshot(data.snapshot);setCatalog(data.catalog);}}catch{}if(mounted)await refresh();})();
  const subscription=AppState.addEventListener('change',state=>{if(state==='active')void refresh();});
  return()=>{mounted=false;subscription.remove();};
 },[refresh,cacheKey]);
 const saveWorkout=async(payload:WorkoutPayload)=>{
  await outbox.add(payload);setPending((await outbox.list()).length);
  try{await outbox.flush(api);await refresh();setNotice('Entrenamiento guardado.');}
  catch{setNotice('Entrenamiento guardado en este dispositivo. Se enviará al recuperar la conexión.');}
  setPending((await outbox.list()).length);
 };
 const logout=async()=>{
  await secureStorage.removeItem(cacheKey);
  // Unsynced workouts remain encrypted under this user's ID for their next sign-in.
  await signOut();
 };
 return <Context.Provider value={{api,snapshot,catalog,demo,busy,notice,pending,refresh,saveWorkout,signOut:logout,setNotice}}>{children}</Context.Provider>;
}
