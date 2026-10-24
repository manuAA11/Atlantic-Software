import React,{useEffect,useState} from 'react';
import {Pressable,Text,View} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import type {RootStack} from '../navigation';
import type {Routine} from '../lib/domain';
import {useAthlete} from '../state/AthleteContext';
import {Icon} from '../components/Icon';
import {Screen,Heading,Card,Label,Button,Chips,Empty,Field,useUi} from '../components/ui';
export function TrainingScreen(){
 const {api,snapshot,catalog,setNotice}=useAthlete(),{color,s}=useUi(),nav=useNavigation<NativeStackNavigationProp<RootStack>>();
 const [gymId,setGymId]=useState(''),[plans,setPlans]=useState<Routine[]>([]),[query,setQuery]=useState(''),[expanded,setExpanded]=useState<string|null>(null);
 const links=snapshot?.links.filter(g=>g.status==='APPROVED')||[];
 useEffect(()=>{if(!gymId&&links.length)setGymId(links[0].gym_id);},[snapshot,gymId]);
 useEffect(()=>{let active=true;if(gymId)api.call<Routine[]>('gym.routines',{gym_id:gymId}).then(rows=>{if(active)setPlans(rows);}).catch(e=>{if(active){setPlans([]);setNotice(e.message);}});return()=>{active=false;};},[gymId,api,setNotice]);
 const normalize=(value:string)=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
 const filtered=catalog.filter(e=>normalize(e.name+' '+e.muscle+' '+e.equipment).includes(normalize(query.trim())));
 return <Screen>
  <Heading eyebrow="Plan de entrenamiento" title="Mis rutinas" detail="Tus planes y ejercicios, en un solo lugar."/>
  <Button label="Entrenamiento libre" icon="barbell-outline" onPress={()=>nav.navigate('Workout')}/>
  {links.length>1&&<Chips items={links.map(g=>({value:g.gym_id,label:g.name}))} value={gymId} onChange={setGymId}/>}
  <Label>Planes de tu gimnasio</Label>
  {plans.map(plan=><Card key={plan.id}><Label>{plan.name}</Label>{plan.goal&&<Text style={s.body}>{plan.goal}</Text>}<Text style={s.body}>{plan.exercises.length} ejercicios · {Array.from(new Set(plan.exercises.map(e=>e.day))).join(', ')}</Text><Button label="Empezar rutina" onPress={()=>nav.navigate('Workout',{routine:plan,gymId})}/></Card>)}
  {!plans.length&&<Empty title={links.length?'Todavía no tienes una rutina asignada':'Entrena por tu cuenta'} detail={links.length?'Tu entrenador puede enviarte un plan desde Atlantic Gym.':'Puedes registrar tus ejercicios desde hoy. Vincula tu gimnasio cuando quieras.'}/>}
  <Heading title="Ejercicios" detail="Toca un ejercicio para consultar sus indicaciones."/>
  <Field label="Buscar ejercicio" value={query} onChangeText={setQuery} placeholder="Nombre, grupo muscular o equipo"/>
  <Card style={{gap:0,paddingVertical:2}}>{filtered.map((exercise,index)=><View key={exercise.id} style={{borderBottomWidth:index===filtered.length-1?0:1,borderColor:color.line}}><Pressable accessibilityRole="button" accessibilityLabel={'Ver '+exercise.name} accessibilityState={{expanded:expanded===exercise.id}} onPress={()=>setExpanded(expanded===exercise.id?null:exercise.id)} style={{minHeight:68,flexDirection:'row',gap:12,alignItems:'center',paddingVertical:12}}><View style={{width:35,height:35,borderRadius:18,backgroundColor:color.soft,justifyContent:'center',alignItems:'center'}}><Icon name="barbell-outline" size={19} color={color.blue}/></View><View style={{flex:1}}><Text style={{fontSize:14,lineHeight:20,fontWeight:'600',color:color.ink}}>{exercise.name}</Text><Text style={{fontSize:12,lineHeight:18,color:color.muted,marginTop:3}}>{exercise.muscle} · {exercise.equipment}</Text></View><Icon name="add-outline" size={16} color={color.muted}/></Pressable>{expanded===exercise.id&&<Text style={[s.body,{paddingBottom:14,paddingLeft:47}]}>{exercise.instructions||'Tu entrenador te indicará cómo realizar este ejercicio.'}</Text>}</View>)}{!filtered.length&&<Text style={[s.body,{paddingVertical:18}]}>No encontramos ejercicios con ese nombre.</Text>}</Card>
 </Screen>;
}
