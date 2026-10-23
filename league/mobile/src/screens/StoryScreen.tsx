import React,{useRef,useState} from 'react';
import {Image,Platform,Text,View,useWindowDimensions} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as MediaLibrary from 'expo-media-library';
import * as Sharing from 'expo-sharing';
import {captureRef,releaseCapture} from 'react-native-view-shot';
import {useAthlete} from '../state/AthleteContext';
import {currentStreak,workoutVolume} from '../lib/domain';
import {Screen,Heading,Row,Label,Button,Chips,color} from '../components/ui';
export function StoryScreen(){
 const {snapshot,demo,setNotice}=useAthlete(),[photo,setPhoto]=useState<string|null>(null),[loaded,setLoaded]=useState(false),[template,setTemplate]=useState('workout'),[stat,setStat]=useState('volume'),[busy,setBusy]=useState(false),shot=useRef<React.ComponentRef<typeof View>>(null),{width}=useWindowDimensions();
 const w=Math.min(width-44,360),scale=w/360,last=snapshot?.workouts[0],record=snapshot?.records.find(r=>r.status==='APPROVED');
 const headline=template==='record'?'Una nueva marca':template==='streak'?'Seguir cuenta':template==='ranking'?'Mi lugar en League':last?.name||'Hoy entrené';
 const metric=template==='record'?(record?String(record.weight_kg)+' kg × '+record.reps:'Sin marca verificada'):template==='streak'?String(currentStreak(snapshot?.workouts||[]))+' días':template==='ranking'?String(snapshot?.official_xp||0)+' XP oficiales':stat==='volume'?Math.round(last?workoutVolume(last):0).toLocaleString('es-CO')+' kg':stat==='sets'?String(last?.sets.length||0)+' series':String(snapshot?.xp||0)+' XP';
 const detail=template==='record'?(record?.exercise_name||'Registra y verifica tu marca'):template==='streak'?'Racha de entrenamiento · UTC':template==='ranking'?'Resultados confirmados por mi gimnasio':stat==='volume'?'Volumen de entrenamiento':stat==='sets'?'Series completadas':'Mi progreso personal';
 const select=async(camera:boolean)=>{
  try{
   const permission=camera?await ImagePicker.requestCameraPermissionsAsync():await ImagePicker.requestMediaLibraryPermissionsAsync();
   if(!permission.granted){setNotice(camera?'Permite el acceso a la cámara para tomar tu foto.':'Permite el acceso a tus fotos para elegir una imagen.');return;}
   const result=camera?await ImagePicker.launchCameraAsync({mediaTypes:['images'],quality:1,allowsEditing:true,aspect:[9,16]}):await ImagePicker.launchImageLibraryAsync({mediaTypes:['images'],quality:1,allowsEditing:true,aspect:[9,16]});
   if(!result.canceled){setLoaded(false);setPhoto(result.assets[0].uri);}
  }catch{setNotice('No se pudo abrir la imagen. Vuelve a intentarlo.');}
 };
 const exportImage=async(share:boolean)=>{
  if(!photo||!loaded||!shot.current)return;
  if(Platform.OS==='web'){setNotice('Guarda y comparte historias desde la aplicación de iPhone o Android.');return;}
  setBusy(true);let uri:string|undefined;
  try{
   uri=await captureRef(shot,{format:'png',quality:1,result:'tmpfile',width:1080,height:1920});
   const size=await new Promise<{width:number;height:number}>((resolve,reject)=>Image.getSize(uri!, (width,height)=>resolve({width,height}),reject));
   if(size.width!==1080||size.height!==1920)throw Error('No se pudo generar la historia con el tamaño correcto.');
   if(share){if(!await Sharing.isAvailableAsync())throw Error('Este dispositivo no tiene una opción compatible para compartir.');await Sharing.shareAsync(uri,{mimeType:'image/png',UTI:'public.png',dialogTitle:'Compartir mi historia'});}
   else{const permission=await MediaLibrary.requestPermissionsAsync(true);if(!permission.granted)throw Error('Permite guardar fotos para conservar tu historia.');await MediaLibrary.Asset.create(uri);setNotice('Historia guardada en tus fotos.');}
  }catch(e){setNotice(e instanceof Error?e.message:'No se pudo generar la historia.');}
  finally{if(uri)releaseCapture(uri);setBusy(false);}
 };
 return <Screen><Heading eyebrow="Historias" title="Así se ve tu progreso" detail="Usa tu propia foto. La imagen se genera en tu dispositivo."/>
  <Row><View style={{flex:1}}><Button label="Cámara" kind="quiet" icon="camera-outline" onPress={()=>void select(true)}/></View><View style={{flex:1}}><Button label="Mis fotos" kind="quiet" icon="images-outline" onPress={()=>void select(false)}/></View></Row>
  <Chips value={template} onChange={setTemplate} items={[{value:'workout',label:'Entrenamiento'},{value:'record',label:'Récord personal'},{value:'streak',label:'Racha'},{value:'ranking',label:'Clasificación'}]}/>
  {template==='workout'&&<Chips value={stat} onChange={setStat} items={[{value:'volume',label:'Volumen'},{value:'sets',label:'Series'},{value:'xp',label:'XP personal'}]}/>}
  <View ref={shot} collapsable={false} style={{width:w,height:w*16/9,alignSelf:'center',backgroundColor:color.ink,overflow:'hidden'}}>
   {photo&&<Image source={{uri:photo}} resizeMode="cover" onLoad={()=>setLoaded(true)} onError={()=>{setLoaded(false);setNotice('No se pudo leer la imagen seleccionada.');}} style={{position:'absolute',width:'100%',height:'100%'}}/>}
   {!photo&&<View style={{flex:1,justifyContent:'center',alignItems:'center'}}><Text style={{color:'#AFC8DB',fontSize:16*scale}}>Elige una foto para comenzar</Text></View>}
   <View style={{position:'absolute',top:32*scale,left:26*scale,right:26*scale}}><Text style={{color:'white',fontWeight:'700',fontSize:12*scale,letterSpacing:3*scale}}>ATLANTIC LEAGUE</Text></View>
   <View style={{position:'absolute',bottom:0,left:0,right:0,padding:26*scale,paddingTop:30*scale,backgroundColor:'rgba(12,28,45,0.78)',gap:8*scale}}>
    <Text style={{color:'#7FE1E7',fontSize:11*scale,letterSpacing:1.5*scale,fontWeight:'600'}}>{snapshot?.profile.alias.toUpperCase()}</Text>
    <Text style={{color:'white',fontWeight:'600',fontSize:23*scale}}>{headline}</Text><Text style={{color:'white',fontWeight:'700',fontSize:38*scale,letterSpacing:-1*scale}}>{metric}</Text><Text style={{color:'#D1DFE8',fontSize:12*scale}}>{detail}</Text><View style={{height:1,backgroundColor:'rgba(255,255,255,.22)',marginTop:8*scale}}/><Text style={{color:'#D1DFE8',fontSize:10*scale}}>{demo?'DATOS SIMULADOS · DEMOSTRACIÓN':new Date().toLocaleDateString('es-CO')+' · Atlantic League'}</Text>
   </View>
  </View>
  <Label muted>Formato vertical · 1080 × 1920</Label><Button label="Compartir historia" icon="share-outline" busy={busy} disabled={!photo||!loaded} onPress={()=>void exportImage(true)}/><Button label="Guardar en mis fotos" kind="quiet" busy={busy} disabled={!photo||!loaded} onPress={()=>void exportImage(false)}/>
 </Screen>;
}
