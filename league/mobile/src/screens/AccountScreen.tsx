import React,{useEffect,useState} from 'react';
import {Alert,Switch,Text,View} from 'react-native';
import {useAthlete} from '../state/AthleteContext';
import {confirmAction} from '../lib/confirm';
import {supabase} from '../lib/api';
import {secureStorage} from '../lib/storage';
import {useUi,Screen,Heading,Card,Row,Label,Field,Button,Chips} from '../components/ui';
export function AccountScreen(){
 const {color,s,dark,setDark}=useUi();
 const {api,snapshot,refresh,demo,pending,signOut,setNotice}=useAthlete();
 const [alias,setAlias]=useState(snapshot?.profile.alias||''),[optIn,setOptIn]=useState(snapshot?.profile.leaderboard_opt_in||false),[token,setToken]=useState(''),[busy,setBusy]=useState(false),[password,setPassword]=useState('');
 const [goal,setGoal]=useState(String(snapshot?.profile.weekly_goal||3));
 useEffect(()=>{if(snapshot){setAlias(snapshot.profile.alias);setOptIn(snapshot.profile.leaderboard_opt_in);}},[snapshot?.profile.alias,snapshot?.profile.leaderboard_opt_in]);
 useEffect(()=>{if(!demo)void secureStorage.getItem('league-activation').then(value=>{if(value)setToken(value);}).catch(()=>setNotice('No se pudo abrir la invitación guardada.'));},[demo]);
 const perform=async(action:string,data:Record<string,unknown>,message:string)=>{setBusy(true);try{await api.call(action,data);if(action==='invitation.accept'){await secureStorage.removeItem('league-activation');setToken('');}await refresh();setNotice(message);}catch(e){setNotice(e instanceof Error?e.message:'No se pudo completar la operación.');}finally{setBusy(false);}};
 const leave=()=>void signOut().catch(error=>setNotice(error instanceof Error?error.message:'No se pudo cerrar la sesión.'));
 const logout=()=>{if(!pending)leave();else confirmAction('Hay entrenamientos pendientes','Se conservan en este dispositivo y se enviarán cuando vuelvas a iniciar sesión con esta cuenta.','Cerrar sesión',leave);};
 const remove=async()=>{
  if(demo||!password||!supabase){setNotice('Escribe tu contraseña para confirmar tu identidad.');return;}
  setBusy(true);
  try{
   const {data}=await supabase.auth.getUser();
   const {error}=await supabase.auth.signInWithPassword({email:data.user!.email!,password});if(error)throw Error('Revisa tu contraseña.');
   await api.call('account.delete',{confirm:'ELIMINAR'});
   await secureStorage.removeItem('league-workout-outbox-'+snapshot!.profile.id);
   await secureStorage.removeItem('league-active-'+snapshot!.profile.id);
   await signOut();
  }catch(e){setNotice(e instanceof Error?e.message:'No se pudo eliminar la cuenta.');}finally{setPassword('');setBusy(false);}
 };
 return <Screen><Heading eyebrow="Tu cuenta deportiva" title="Mi perfil" detail={snapshot?.profile.alias}/>
  <Card><Row><View style={{flex:1}}><Label>Modo oscuro</Label><Label muted>La apariencia se guarda en este dispositivo.</Label></View><Switch accessibilityLabel="Modo oscuro" value={dark} onValueChange={value=>void setDark(value).catch(()=>setNotice('La apariencia cambió, pero no se pudo guardar para la próxima vez.'))}/></Row></Card>
  <Card><Field label="Nombre visible" value={alias} onChangeText={setAlias} maxLength={60}/><Row><View style={{flex:1}}><Label>Participar en clasificaciones</Label><Label muted>Se mostrará este nombre junto a tus resultados oficiales.</Label></View><Switch accessibilityLabel="Participar en clasificaciones" value={optIn} onValueChange={setOptIn}/></Row><Button label="Guardar perfil" busy={busy} disabled={alias.trim().length<2} onPress={()=>void perform('profile.update',{alias:alias.trim(),leaderboard_opt_in:optIn},'Perfil actualizado.')}/></Card>
  <Card><Label>¿Recibiste una invitación?</Label><Label muted>Usa el enlace que te envió el gimnasio o pega su código de activación. Debes confirmar el mismo correo al que se dirigió la invitación.</Label><Field label="Código de activación" value={token} onChangeText={setToken} autoCapitalize="none" autoCorrect={false}/><Button label="Activar vinculación" kind="quiet" busy={busy} disabled={token.length!==64} onPress={()=>void perform('invitation.accept',{token},'Tu cuenta quedó vinculada al gimnasio.')}/></Card>
  <Card><Label>Mi objetivo semanal</Label><Chips value={goal} onChange={setGoal} items={[1,2,3,4,5,6,7].map(n=>({value:String(n),label:String(n)+(n===1?' día':' días')}))}/><Button label="Guardar objetivo" kind="quiet" busy={busy} onPress={()=>void perform('profile.update',{alias,leaderboard_opt_in:optIn,weekly_goal:Number(goal)},'Objetivo actualizado.')}/></Card>
  <Button label="Cerrar sesión" kind="quiet" onPress={logout}/>
  {!demo&&<Card><Label>Eliminar mi cuenta de League</Label><Label muted>Se eliminarán tu perfil deportivo, entrenamientos y evidencias de League. Tu registro y las obligaciones con el gimnasio se conservan en Atlantic Gym.</Label><Field label="Confirma tu contraseña" value={password} onChangeText={setPassword} secureTextEntry autoCapitalize="none"/><Button label="Eliminar mi cuenta" kind="danger" busy={busy} onPress={()=>confirmAction('¿Eliminar tu cuenta de League?','Esta operación no se puede deshacer. Sincroniza o conserva tus registros antes de continuar.','Eliminar cuenta',()=>void remove())}/></Card>}
  <Text style={[s.body,{textAlign:'center',fontSize:11}]}>Atlantic League · 0.3.0 · Piloto{'\n'}© Atlantic Tech Software — All rights reserved. By Manuel Cuellar</Text>
 </Screen>;
}
