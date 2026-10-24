import React,{useState} from 'react';
import {Image,KeyboardAvoidingView,Platform,Text,View} from 'react-native';
import {supabase,configured,authRedirect} from '../lib/api';
import {useUi,Screen,Heading,Card,Button,Field} from '../components/ui';
export function AuthScreen({onDemo,recovery=false,onRecovered}:{onDemo:()=>void;recovery?:boolean;onRecovered:()=>void}){
 const {color,s}=useUi();
 const [mode,setMode]=useState<'login'|'register'|'reset'>('login'),[email,setEmail]=useState(''),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState('');
 const submit=async()=>{
  setMessage('');if(!supabase)return;
  if((recovery||mode==='register')&&password.length<12){setMessage('Usa una contraseña de al menos 12 caracteres.');return;}
  setBusy(true);
  try{
   if(recovery){const {error}=await supabase.auth.updateUser({password});if(error)throw error;setMessage('Contraseña actualizada.');onRecovered();}
   else if(mode==='login'){const {error}=await supabase.auth.signInWithPassword({email:email.trim(),password});if(error)throw error;}
   else if(mode==='register'){
    const {error}=await supabase.auth.signUp({email:email.trim(),password,options:{emailRedirectTo:authRedirect()}});if(error)throw error;
    setMessage('Revisa tu correo para confirmar la cuenta. Después podrás iniciar sesión.');
   }else{const {error}=await supabase.auth.resetPasswordForEmail(email.trim(),{redirectTo:authRedirect()});if(error)throw error;setMessage('Si el correo tiene una cuenta, recibirás un enlace para cambiar la contraseña.');}
  }catch{setMessage(mode==='login'?'No pudimos iniciar sesión. Revisa el correo y la contraseña, y confirma tu cuenta.':'No se pudo completar la solicitud. Revisa los datos y vuelve a intentarlo.');}
  finally{setBusy(false);}
 };
 return <KeyboardAvoidingView style={{flex:1}} behavior={Platform.OS==='ios'?'padding':undefined}><Screen insetTop>
  <View style={{width:58,height:58,borderRadius:29,backgroundColor:color.ink,overflow:'hidden',marginTop:30}}><Image source={require('../../assets/atlantic-icon.png')} style={{width:58,height:58}} accessibilityLabel="Atlantic Tech Software"/></View>
  <Heading eyebrow="Atlantic Tech Software" title="Atlantic League" detail="Tu entrenamiento. Tu progreso."/>
  <Card><Text style={s.label}>{recovery?'Cambia tu contraseña':mode==='register'?'Crea tu cuenta':mode==='reset'?'Recupera tu acceso':'Qué bueno verte de nuevo'}</Text>
   {!recovery&&<Field label="Correo electrónico" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" autoComplete="email"/>}
   {(mode!=='reset'||recovery)&&<Field label={mode==='register'||recovery?'Contraseña · mínimo 12 caracteres':'Contraseña'} value={password} onChangeText={setPassword} secureTextEntry autoCapitalize="none" autoComplete={mode==='register'?'new-password':'current-password'}/>}
   {message!==''&&<Text accessibilityRole="alert" style={s.body}>{message}</Text>}
   <Button label={recovery?'Guardar contraseña':mode==='register'?'Crear cuenta gratuita':mode==='reset'?'Enviar enlace':'Iniciar sesión'} busy={busy} disabled={!configured} onPress={()=>void submit()}/>
   {!recovery&&<><Button kind="quiet" label={mode==='login'?'Crear una cuenta': 'Ya tengo una cuenta'} onPress={()=>{setMessage('');setMode(mode==='login'?'register':'login');}}/>{mode==='login'&&<Button kind="quiet" label="Olvidé mi contraseña" onPress={()=>setMode('reset')}/>}</>}
  </Card>
  {!configured&&<Text style={s.body}>Esta compilación aún no tiene una conexión de pruebas. Puedes explorar la demostración con datos simulados.</Text>}
  {!recovery&&<Button kind="quiet" icon="play-circle-outline" label="Explorar demostración" onPress={onDemo}/>}
  <Text style={[s.body,{fontSize:11,textAlign:'center',marginTop:12}]}>© Atlantic Tech Software — All rights reserved. By Manuel Cuellar</Text>
 </Screen></KeyboardAvoidingView>;
}
