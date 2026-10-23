import React,{useEffect,useState} from 'react';
import {Text,View} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import type {RootStack} from '../navigation';
import type {Routine} from '../lib/domain';
import {useAthlete} from '../state/AthleteContext';
import {Screen,Heading,Card,Row,Label,Button,Chips,Empty,Field,s} from '../components/ui';
export function TrainingScreen(){
 const {api,snapshot,catalog,setNotice}=useAthlete(),nav=useNavigation<NativeStackNavigationProp<RootStack>>();
 const [gymId,setGymId]=useState(''),[plans,setPlans]=useState<Routine[]>([]),[query,setQuery]=useState('');
 const links=snapshot?.links.filter(g=>g.status==='APPROVED')||[];
 useEffect(()=>{if(!gymId&&links.length)setGymId(links[0].gym_id);},[snapshot,gymId]);
 useEffect(()=>{let active=true;if(gymId)api.call<Routine[]>('gym.routines',{gym_id:gymId}).then(rows=>{if(active)setPlans(rows);}).catch(e=>{if(active){setPlans([]);setNotice(e.message);}});return()=>{active=false;};},[gymId,api,setNotice]);
 return <Screen>
  <Heading eyebrow="Entrenar" title="Hazlo a tu ritmo" detail="Tus planes y ejercicios, en un solo lugar."/>
  <Button label="Entrenamiento libre" icon="barbell-outline" onPress={()=>nav.navigate('Workout')}/>
  {links.length>1&&<Chips items={links.map(g=>({value:g.gym_id,label:g.name}))} value={gymId} onChange={setGymId}/>}
  <Label>Planes de tu gimnasio</Label>
  {plans.map(plan=><Card key={plan.id}><Label>{plan.name}</Label>{plan.goal&&<Label muted>{plan.goal}</Label>}<Label muted>{plan.exercises.length} ejercicios · {Array.from(new Set(plan.exercises.map(e=>e.day))).join(', ')}</Label><Button label="Empezar rutina" onPress={()=>nav.navigate('Workout',{routine:plan,gymId})}/></Card>)}
  {!plans.length&&<Empty title={links.length?'Todavía no tienes una rutina asignada':'Entrena por tu cuenta'} detail={links.length?'Tu entrenador puede enviarte un plan desde Atlantic Gym.':'Puedes registrar tus ejercicios desde hoy. Vincula tu gimnasio cuando quieras.'}/>}
  <Heading title="Ejercicios" detail="Consulta las indicaciones antes de empezar."/>
  <Field label="Buscar ejercicio" value={query} onChangeText={setQuery} placeholder="Nombre o grupo muscular"/>
  {catalog.filter(e=>(e.name+' '+e.muscle).toLowerCase().includes(query.toLowerCase())).map(e=><Card key={e.id}><Row><Label>{e.name}</Label></Row><Text style={s.eyebrow}>{e.muscle} · {e.equipment}</Text><Label muted>{e.instructions}</Label></Card>)}
 </Screen>;
}
