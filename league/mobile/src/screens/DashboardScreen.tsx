import React from 'react';
import {Text,View} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import type {RootStack} from '../navigation';
import {useAthlete} from '../state/AthleteContext';
import {currentStreak,nextXp,xpRank,workoutVolume} from '../lib/domain';
import {Screen,Heading,Card,Row,Button,Label,Empty,dateText,color,s} from '../components/ui';
export function DashboardScreen(){
 const {snapshot,busy,refresh,pending}=useAthlete(),nav=useNavigation<NativeStackNavigationProp<RootStack>>();
 const goal=snapshot?nextXp(Number(snapshot.xp)):200;
 return <Screen refreshing={busy} onRefresh={()=>void refresh()}>
  <Heading eyebrow="Tu espacio" title={snapshot?'Hola, '+snapshot.profile.alias.split(' ')[0]:'Hola'} detail="Un entrenamiento a la vez."/>
  <Card style={{backgroundColor:color.ink,borderColor:color.ink}}>
   <Text style={{fontSize:12,letterSpacing:1.5,color:'#7DDCE5',fontWeight:'600'}}>RANGO XP · {xpRank(Number(snapshot?.xp||0)).toUpperCase()}</Text>
   <Row><Text style={[s.metric,{fontSize:43,color:color.white}]}>{snapshot?.xp||0} <Text style={{fontSize:16}}>XP</Text></Text><View><Text style={{fontSize:24,color:color.white,fontWeight:'700'}}>{currentStreak(snapshot?.workouts||[])}</Text><Text style={{fontSize:12,color:'#BDCDD9'}}>días de racha · UTC</Text></View></Row>
   <View style={{height:5,backgroundColor:'#365066',borderRadius:9}}><View style={{height:5,borderRadius:9,backgroundColor:'#63D7E0',width:`${Math.min(100,Number(snapshot?.xp||0)/(goal||5000)*100)}%`}}/></View>
   <Text style={{color:'#BDCDD9',fontSize:12}}>{goal?`${goal-Number(snapshot?.xp||0)} XP para tu próximo rango`:'Llegaste al rango Élite'}</Text>
  </Card>
  <Button label="Registrar entrenamiento" icon="add-circle-outline" onPress={()=>nav.navigate('Workout')}/>
  <Card><Row><Label>Tu objetivo de la semana</Label><Label muted>{snapshot?.weekly_days||0} / {snapshot?.profile.weekly_goal||3} días</Label></Row><Label muted>+20 XP por entrenar en el día, +10 por constancia desde el tercer día seguido y +50 al completar tu objetivo semanal. Calendario UTC.</Label></Card>
  {pending>0&&<Label muted>{pending} entrenamiento{pending===1?'':'s'} pendiente{pending===1?'':'s'} de sincronizar.</Label>}
  <Row><Label>Tu última actividad</Label><Button label="Crear historia" kind="quiet" onPress={()=>nav.navigate('Story')}/></Row>
  {snapshot?.workouts.slice(0,3).map(workout=><Card key={workout.id}><Row><Text style={s.eyebrow}>{dateText(workout.finished_at)}</Text><Text style={s.body}>Entrenamiento</Text></Row><Label>{workout.name}</Label><Row><Label muted>{workout.sets.length} series</Label><Label muted>{Math.round(workoutVolume(workout)).toLocaleString('es-CO')} kg de volumen</Label></Row></Card>)}
  {!snapshot?.workouts.length&&<Empty title="Aquí empieza tu historia" detail="Registra tu primer entrenamiento. Puedes empezar sin pertenecer a un gimnasio."/>}
 </Screen>;
}
