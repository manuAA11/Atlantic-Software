import React,{useEffect,useRef,useState} from 'react';
import {Alert,Text,View} from 'react-native';
import * as Crypto from 'expo-crypto';
import type {NativeStackScreenProps} from '@react-navigation/native-stack';
import type {RootStack} from '../navigation';
import type {SetEntry,WorkoutPayload} from '../lib/domain';
import {confirmAction} from '../lib/confirm';
import {secureStorage} from '../lib/storage';
import {useAthlete} from '../state/AthleteContext';
import {useUi,Screen,Heading,Card,Row,Button,Label,Field,Chips} from '../components/ui';
export function WorkoutScreen({route,navigation}:NativeStackScreenProps<RootStack,'Workout'>){
 const {color,s}=useUi();
 const {api,catalog,snapshot,saveWorkout,setNotice}=useAthlete();
 const [routine,setRoutine]=useState(route.params?.routine),[hydrated,setHydrated]=useState(false);
 const gymId=route.params?.gymId;
 const [name,setName]=useState(routine?.name||'Mi entrenamiento'),[exercise,setExercise]=useState(''),[kg,setKg]=useState(''),[reps,setReps]=useState(''),[sets,setSets]=useState<SetEntry[]>([]),[busy,setBusy]=useState(false),[draft,setDraft]=useState<string>(),[day,setDay]=useState(routine?.exercises[0]?.day||'');
 const payload=useRef<WorkoutPayload|null>(null),id=useRef(Crypto.randomUUID()),started=useRef(new Date().toISOString()),dirty=useRef(false);
 const cacheKey='league-active-'+(snapshot?.profile.id||'anonymous');
 useEffect(()=>{
  let active=true;
  void secureStorage.getItem(cacheKey).then(text=>{
   if(!active)return;
   if(text){
    const saved=JSON.parse(text) as WorkoutPayload;
    if(saved.sets?.length){id.current=saved.id;started.current=saved.started_at;setName(saved.name);setSets(saved.sets);setDraft(saved.draft_id);setRoutine(undefined);setNotice('Retomaste el entrenamiento que tenías en curso.');}
   }
  }).catch(()=>setNotice('No se pudo abrir el borrador del entrenamiento.')).finally(()=>{if(active)setHydrated(true);});
  return()=>{active=false;};
 },[cacheKey,setNotice]);
 useEffect(()=>{
  if(catalog.length&&!exercise)setExercise(routine?.exercises.find(e=>e.catalog_id)?.catalog_id||catalog[0].id);
 },[catalog,routine,exercise]);
 useEffect(()=>{
  if(!routine||!hydrated)return;
  let active=true;
  api.call<{draft_id:string}>('gym.workout.start',{gym_id:gymId,routine_id:routine.id}).then(value=>{if(active)setDraft(value.draft_id);}).catch(e=>setNotice(e.message));
  return()=>{active=false;};
 },[api,gymId,routine,hydrated,setNotice]);
 useEffect(()=>{if(!hydrated)return;const save=sets.length?secureStorage.setItem(cacheKey,JSON.stringify({id:id.current,name,started_at:started.current,sets,...(draft?{draft_id:draft}:{})})):secureStorage.removeItem(cacheKey);void save.catch(()=>setNotice('No se pudo guardar el borrador. Revisa el espacio del dispositivo.'));dirty.current=sets.length>0;},[sets,name,draft,cacheKey,setNotice,hydrated]);
 useEffect(()=>navigation.addListener('beforeRemove',e=>{
  if(!dirty.current)return;e.preventDefault();
  confirmAction('¿Salir del entrenamiento?','El borrador se conserva en este dispositivo.','Salir',()=>{dirty.current=false;navigation.dispatch(e.data.action);});
 }),[navigation]);
 const add=()=>{
  const weight=Number(kg.replace(',','.')),count=Number(reps);
  if(!exercise||kg.trim()===''||!Number.isFinite(weight)||weight<0||weight>1000||!Number.isInteger(count)||count<1||count>100){setNotice('Revisa el peso y las repeticiones antes de añadir la serie.');return;}
  if(sets.length>=100){setNotice('Guarda este entrenamiento antes de añadir más series.');return;}
  setSets([...sets,{exercise_id:exercise,weight_kg:weight,reps:count}]);setNotice('Serie añadida.');
 };
 const finish=async()=>{
  if(!sets.length||!name.trim())return;setBusy(true);
  try{
   // Once queued, retries always use exactly the same payload.
   payload.current||={id:id.current,name:name.trim(),started_at:started.current,sets,...(draft?{draft_id:draft}:{})};
   await saveWorkout(payload.current);await secureStorage.removeItem(cacheKey);dirty.current=false;navigation.goBack();
  }catch(e){setNotice(e instanceof Error?e.message:'No se pudo guardar el entrenamiento.');}finally{setBusy(false);}
 };
 const planItems=routine?.exercises.filter(e=>e.day===day)||[];
 return <Screen insetTop={false}><Heading eyebrow={routine?'Rutina asignada':'Entrenamiento libre'} title="Cada serie cuenta"/>
  <Field label="Nombre del entrenamiento" value={name} onChangeText={setName} maxLength={120}/>
  {routine&&<><Chips items={Array.from(new Set(routine.exercises.map(e=>e.day))).map(d=>({value:d,label:d}))} value={day} onChange={setDay}/>{planItems.map(e=><Card key={e.id}><Label>{e.name}</Label><Label muted>{e.sets} series × {e.reps} repeticiones · {e.weight_kg} kg sugeridos · {e.rest_seconds||0} s de descanso</Label>{e.catalog_id&&<Button label="Registrar este ejercicio" kind="quiet" onPress={()=>{setExercise(e.catalog_id!);setKg(String(e.weight_kg));setReps(String(e.reps));}}/>}</Card>)}{!draft&&<Label muted>Esperando la confirmación de la rutina. Puedes registrar actividad personal mientras tanto.</Label>}</>}
  <Card><Label>Añadir una serie</Label><Chips items={catalog.map(e=>({value:e.id,label:e.name}))} value={exercise} onChange={setExercise}/><Row><View style={{flex:1}}><Field label="Peso total · kg" value={kg} onChangeText={setKg} keyboardType="decimal-pad" placeholder="0"/></View><View style={{flex:1}}><Field label="Repeticiones" value={reps} onChangeText={setReps} keyboardType="number-pad" placeholder="10"/></View></Row><Button label="Añadir serie" icon="add-outline" onPress={add}/></Card>
  <Label>{sets.length} {sets.length===1?'serie registrada':'series registradas'}</Label>
  {sets.map((item,index)=><Row key={index}><View style={{flex:1}}><Text style={{fontSize:14,color:color.ink}}>{catalog.find(e=>e.id===item.exercise_id)?.name}</Text><Text style={s.body}>{item.weight_kg} kg × {item.reps}</Text></View><Button kind="quiet" label="Quitar" onPress={()=>setSets(sets.filter((_,i)=>i!==index))}/></Row>)}
  <Button label="Terminar y guardar" busy={busy} disabled={!sets.length||!name.trim()} onPress={()=>void finish()}/>
 </Screen>;
}
