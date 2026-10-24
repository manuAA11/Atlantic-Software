import React from 'react';
import {Pressable,Text,View} from 'react-native';
import {useNavigation,type NavigationProp} from '@react-navigation/native';
import type {NativeStackNavigationProp} from '@react-navigation/native-stack';
import type {RootStack,Tabs} from '../navigation';
import {useAthlete} from '../state/AthleteContext';
import {currentStreak,nextXp,xpRank,workoutVolume} from '../lib/domain';
import {Screen,Heading,Card,Row,Button,Label,Empty,ActionTile,dateText,useUi} from '../components/ui';
export function DashboardScreen(){
 const {snapshot,busy,refresh,pending}=useAthlete(),{color,s}=useUi(),nav=useNavigation<NativeStackNavigationProp<RootStack>>(),tabs=useNavigation<NavigationProp<Tabs>>();
 const streak=currentStreak(snapshot?.workouts||[]);
 const xp=Number(snapshot?.xp||0),next=nextXp(xp),weeklyGoal=snapshot?.profile.weekly_goal||3,days=snapshot?.weekly_days||0;
 const verified=snapshot?.records.filter(record=>record.status==='APPROVED')||[],gym=snapshot?.links.find(link=>link.status==='APPROVED');
 return <Screen refreshing={busy} onRefresh={()=>void refresh()}>
  <Heading title={snapshot?'Hola, '+snapshot.profile.alias.split(' ')[0]:'Tu progreso'} detail="Un entrenamiento a la vez."/>
  <Card><Row><Text style={s.eyebrow}>TU SEMANA</Text><Text style={{fontSize:11,color:color.blue,fontWeight:'600'}}>Meta personal</Text></Row><Text style={{fontSize:20,lineHeight:26,fontWeight:'700',color:color.ink}}>{days} de {weeklyGoal} días</Text><Text style={s.body}>Tu objetivo de la semana</Text><View style={{height:5,backgroundColor:color.surfaceAlt,borderRadius:8,overflow:'hidden'}}><View style={{height:5,backgroundColor:color.primary,width:`${Math.min(100,days/weeklyGoal*100)}%`}}/></View></Card>
  <View style={{flexDirection:'row',gap:10,alignItems:'stretch'}}>
   <Card style={{flex:1,minWidth:0,padding:14,gap:7}}><Text style={s.eyebrow}>RANGO XP</Text><Text style={{fontSize:21,lineHeight:27,color:color.ink,fontWeight:'700'}}>{xpRank(xp)}</Text><Text style={s.body}>{xp.toLocaleString('es-CO')} XP personales</Text><Text style={{fontSize:11,lineHeight:17,color:color.muted}}>{next?`${next-xp} XP para avanzar`:'Rango Élite alcanzado'}</Text></Card>
   <Card style={{flex:1,minWidth:0,padding:14,gap:7}}><Text style={s.eyebrow}>FUERZA</Text><Text style={{fontSize:21,lineHeight:27,color:color.ink,fontWeight:'700'}}>{verified.length?'Verificada':'Sin marcas'}</Text><Text style={s.body}>{verified.length} marca{verified.length===1?'':'s'} verificada{verified.length===1?'':'s'}</Text><Text style={{fontSize:11,lineHeight:17,color:color.muted}}>Cada ejercicio cuenta por separado</Text></Card>
  </View>
  <View style={{flexDirection:'row',gap:10}}><ActionTile label="Registrar marca" icon="barbell-outline" onPress={()=>tabs.navigate('League')}/><ActionTile label="Crear historia" icon="camera-outline" onPress={()=>nav.navigate('Story')}/></View>
  <Button label="Registrar entrenamiento" icon="add-circle-outline" onPress={()=>nav.navigate('Workout')}/>
  <View style={{flexDirection:'row',gap:10}}><Card style={{flex:1,minWidth:0,padding:14,gap:7}}><Text style={s.body}>Racha actual</Text><Text style={s.metric}>{streak} {streak===1?'día':'días'}</Text><Text style={{fontSize:11,color:color.muted}}>Días consecutivos · UTC</Text></Card><Card style={{flex:1,minWidth:0,padding:14,gap:7}}><Text style={s.body}>XP oficiales</Text><Text style={s.metric}>{snapshot?.official_xp||0}</Text><Text style={{fontSize:11,color:color.muted}}>Confirmados por tu gimnasio</Text></Card></View>
  {pending>0&&<Label muted>{pending} entrenamiento{pending===1?'':'s'} pendiente{pending===1?'':'s'} de sincronizar.</Label>}
  <Row><Label>Tu última actividad</Label><Pressable accessibilityRole="button" accessibilityLabel="Ver mis rutinas" onPress={()=>tabs.navigate('Entrenar')} style={{minHeight:44,justifyContent:'center'}}><Text style={{fontSize:12,fontWeight:'600',color:color.blue}}>Mis rutinas</Text></Pressable></Row>
  {snapshot?.workouts.slice(0,3).map(workout=><Card key={workout.id}><Row><Text style={s.eyebrow}>{dateText(workout.finished_at)}</Text><Text style={s.body}>Entrenamiento</Text></Row><Label>{workout.name}</Label><Row><Label muted>{workout.sets.length} {workout.sets.length===1?'serie':'series'}</Label><Label muted>{Math.round(workoutVolume(workout)).toLocaleString('es-CO')} kg de volumen</Label></Row></Card>)}
  {!snapshot?.workouts.length&&<Empty title="Aquí empieza tu historia" detail="Registra tu primer entrenamiento para ver aquí tu progreso."/>}
  {gym&&<Card><Label>{gym.name}</Label><Label muted>Tu perfil está vinculado. Consulta las clases y el estado de tu membresía en la agenda.</Label><Button label="Ver agenda" kind="quiet" onPress={()=>tabs.navigate('Gimnasio')}/></Card>}
 </Screen>;
}
