import React,{useEffect,useState} from 'react';
import {Pressable,Text,View} from 'react-native';
import {useTheme} from './Theme';
export function PwaStatus(){
 const {color}=useTheme();
 const [offline,setOffline]=useState(!navigator.onLine),[waiting,setWaiting]=useState<ServiceWorker|null>(null),[guide,setGuide]=useState(false);
 useEffect(()=>{
  const online=()=>setOffline(!navigator.onLine);window.addEventListener('online',online);window.addEventListener('offline',online);
  try{setGuide(!matchMedia('(display-mode: standalone)').matches&&sessionStorage.getItem('league-install-dismissed')!=='1');}catch{setGuide(false);}
  if('serviceWorker' in navigator&&window.isSecureContext)void navigator.serviceWorker.register('/sw.js').then(reg=>{
   if(reg.waiting)setWaiting(reg.waiting);
   reg.addEventListener('updatefound',()=>{const worker=reg.installing;worker?.addEventListener('statechange',()=>{if(worker.state==='installed'&&navigator.serviceWorker.controller)setWaiting(worker);});});
  }).catch(()=>{});
  return()=>{window.removeEventListener('online',online);window.removeEventListener('offline',online);};
 },[]);
 return <View>{offline&&<Text accessibilityRole="alert" style={{backgroundColor:'#FFF0C2',padding:10,textAlign:'center'}}>Sin conexión · Las reservas y verificaciones necesitan internet.</Text>}
 {waiting&&<Pressable accessibilityRole="button" onPress={()=>{if(window.confirm('Hay una nueva versión. Guarda tu entrenamiento antes de actualizar. ¿Actualizar ahora?')){navigator.serviceWorker.addEventListener('controllerchange',()=>location.reload(),{once:true});waiting.postMessage({type:'ACTIVATE_UPDATE'});}}}><Text style={{padding:10,color:color.ink,backgroundColor:color.soft,textAlign:'center'}}>Nueva versión disponible · Actualizar</Text></Pressable>}
 {guide&&<Pressable accessibilityRole="button" accessibilityLabel="Cerrar instrucciones de instalación" onPress={()=>{try{sessionStorage.setItem('league-install-dismissed','1');}catch{}setGuide(false);}}><Text style={{padding:10,color:color.ink,backgroundColor:color.soft,fontSize:12,textAlign:'center'}}>Instala Atlantic League: en iPhone, Compartir → Añadir a pantalla de inicio. En Android, menú → Instalar aplicación. Toca para cerrar.</Text></Pressable>}
 </View>;
}
