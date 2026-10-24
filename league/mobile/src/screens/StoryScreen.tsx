import React,{useEffect,useRef,useState} from 'react';
import {Image,Platform,Switch,Text,View,useWindowDimensions} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as MediaLibrary from 'expo-media-library';
import * as Sharing from 'expo-sharing';
import {captureRef,releaseCapture} from 'react-native-view-shot';
import {StoryDownload} from '../components/StoryDownload';
import {storyStyle,type StoryStyle} from '../lib/story-style';
import {pickWebPhoto,exportWebStory} from '../lib/web-story';
import {useAthlete} from '../state/AthleteContext';
import {currentStreak,workoutVolume} from '../lib/domain';
import {useUi,Screen,Heading,Row,Label,Button,Chips} from '../components/ui';
export function StoryScreen(){
 const {color,s}=useUi();
 const {snapshot,demo,setNotice}=useAthlete(),[photo,setPhoto]=useState<string|null>(null),[loaded,setLoaded]=useState(false),[template,setTemplate]=useState('workout'),[stat,setStat]=useState('volume'),[style,setStyle]=useState<StoryStyle>('white'),[showGym,setShowGym]=useState(true),[showXp,setShowXp]=useState(false),[busy,setBusy]=useState(false),[exported,setExported]=useState<string|null>(null),shot=useRef<React.ComponentRef<typeof View>>(null),{width}=useWindowDimensions();
 useEffect(()=>()=>{if(Platform.OS==='web'&&exported)URL.revokeObjectURL(exported);},[exported]);
 const w=Math.min(width-44,360),scale=w/360,last=snapshot?.workouts[0],record=snapshot?.records.find(r=>r.status==='APPROVED');
 const theme=storyStyle(style),gym=snapshot?.links.find(link=>link.status==='APPROVED'),extra=[showGym?gym?.name:null,showXp?(snapshot?.xp||0)+' XP personales':null].filter(Boolean).join(' · ');
 const headline=template==='record'?'Una nueva marca':template==='streak'?'Cada día cuenta':template==='ranking'?'Mi lugar en League':last?.name||'Hoy entrené';
 const metric=template==='record'?(record?String(record.weight_kg)+' kg × '+record.reps:'Sin marca verificada'):template==='streak'?String(currentStreak(snapshot?.workouts||[]))+(currentStreak(snapshot?.workouts||[])===1?' día':' días'):template==='ranking'?String(snapshot?.official_xp||0)+' XP oficiales':stat==='volume'?Math.round(last?workoutVolume(last):0).toLocaleString('es-CO')+' kg':stat==='sets'?String(last?.sets.length||0)+((last?.sets.length||0)===1?' serie':' series'):String(snapshot?.xp||0)+' XP';
 const detail=template==='record'?(record?.exercise_name||'Registra y verifica tu marca'):template==='streak'?'Racha de entrenamiento · UTC':template==='ranking'?'Resultados confirmados por mi gimnasio':stat==='volume'?'Volumen de entrenamiento':stat==='sets'?'Series completadas':'Mi progreso personal';
 const select=async(camera:boolean)=>{
  try{
   if(Platform.OS==='web'){const uri=await pickWebPhoto(camera);if(uri){setLoaded(false);setPhoto(uri);}return;}
   const permission=camera?await ImagePicker.requestCameraPermissionsAsync():await ImagePicker.requestMediaLibraryPermissionsAsync();
   if(!permission.granted){setNotice(camera?'Permite el acceso a la cámara para tomar tu foto.':'Permite el acceso a tus fotos para elegir una imagen.');return;}
   const result=camera?await ImagePicker.launchCameraAsync({mediaTypes:['images'],quality:1,allowsEditing:true,aspect:[9,16]}):await ImagePicker.launchImageLibraryAsync({mediaTypes:['images'],quality:1,allowsEditing:true,aspect:[9,16]});
   if(!result.canceled){setLoaded(false);setPhoto(result.assets[0].uri);}
  }catch{setNotice('No se pudo abrir la imagen. Vuelve a intentarlo.');}
 };
 const exportImage=async(share:boolean)=>{
  if(!photo||!loaded||!shot.current)return;
  setBusy(true);let uri:string|undefined;
  try{
   if(Platform.OS==='web'){const result=await exportWebStory(photo,[snapshot?.profile.alias.toUpperCase()||'',headline,metric,detail,demo?'DATOS SIMULADOS · DEMOSTRACIÓN':new Date().toLocaleDateString('es-CO')],share,{style,...(showGym&&gym?{gym:gym.name}:{}),...(showXp?{xp:snapshot?.xp||0}:{})});if(result.url)setExported(result.url);if(!result.cancelled)setNotice(result.shared?'Historia compartida.':'Tu imagen está lista. Puedes descargarla o abrirla para guardarla.');return;}
   uri=await captureRef(shot,{format:'png',quality:1,result:'tmpfile',width:1080,height:1920});
   const size=await new Promise<{width:number;height:number}>((resolve,reject)=>Image.getSize(uri!, (width,height)=>resolve({width,height}),reject));
   if(size.width!==1080||size.height!==1920)throw Error('No se pudo generar la historia con el tamaño correcto.');
   if(share){if(!await Sharing.isAvailableAsync())throw Error('Este dispositivo no tiene una opción compatible para compartir.');await Sharing.shareAsync(uri,{mimeType:'image/png',UTI:'public.png',dialogTitle:'Compartir mi historia'});}
   else{const permission=await MediaLibrary.requestPermissionsAsync(true);if(!permission.granted)throw Error('Permite guardar fotos para conservar tu historia.');await MediaLibrary.Asset.create(uri);setNotice('Historia guardada en tus fotos.');}
  }catch(e){setNotice(e instanceof Error?e.message:'No se pudo generar la historia.');}
  finally{if(uri)releaseCapture(uri);setBusy(false);}
 };
 return <Screen insetTop={false}><Heading eyebrow="Comparte tu progreso" title="Crea tu historia" detail="Tu foto, tu entrenamiento y los datos que tú elijas."/>
  <Row><View style={{flex:1}}><Button label="Cámara" kind="quiet" icon="camera-outline" onPress={()=>void select(true)}/></View><View style={{flex:1}}><Button label="Mis fotos" kind="quiet" icon="images-outline" onPress={()=>void select(false)}/></View></Row>
  <Chips value={template} onChange={setTemplate} items={[{value:'workout',label:'Entrenamiento'},{value:'record',label:'Récord personal'},{value:'streak',label:'Racha'},{value:'ranking',label:'Clasificación'}]}/>
  {template==='workout'&&<Chips value={stat} onChange={setStat} items={[{value:'volume',label:'Volumen'},{value:'sets',label:'Series'},{value:'xp',label:'XP personal'}]}/>}
  <Chips value={style} onChange={setStyle} items={[{value:'white',label:'Texto blanco'},{value:'dark',label:'Texto oscuro'},{value:'card',label:'Tarjeta discreta'}]}/>
  <Row><Label>Mostrar gimnasio</Label><Switch accessibilityLabel="Mostrar gimnasio" value={showGym} onValueChange={setShowGym}/></Row><Row><Label>Añadir XP personal</Label><Switch accessibilityLabel="Añadir XP personal" value={showXp} onValueChange={setShowXp}/></Row>
  <View ref={shot} collapsable={false} style={{width:w,height:w*16/9,alignSelf:'center',backgroundColor:'#13243A',overflow:'hidden'}}>
   {photo&&<Image source={{uri:photo}} resizeMode="cover" onLoad={()=>setLoaded(true)} onError={()=>{setLoaded(false);setNotice('No se pudo leer la imagen seleccionada.');}} style={{position:'absolute',width:'100%',height:'100%'}}/>}
   {!photo&&<View style={{flex:1,justifyContent:'center',alignItems:'center'}}><Text style={{color:'#AFC8DB',fontSize:16*scale}}>Elige una foto para comenzar</Text></View>}
   <View style={{position:'absolute',bottom:24*scale,left:style==='card'?20*scale:0,right:style==='card'?20*scale:0,padding:style==='card'?18*scale:26*scale,paddingTop:20*scale,borderRadius:style==='card'?10*scale:0,backgroundColor:style==='card'?'rgba(255,255,255,.94)':style==='white'?'rgba(0,0,0,.28)':'rgba(255,255,255,.66)',gap:8*scale}}>
    <Text style={{color:theme.muted,fontSize:9*scale,letterSpacing:1*scale}}>{snapshot?.profile.alias.toUpperCase()}</Text>
    <Text numberOfLines={1} style={{color:theme.ink,fontWeight:'600',fontSize:15*scale}}>{headline}</Text><Text numberOfLines={1} style={{color:theme.ink,fontWeight:'700',fontSize:23*scale}}>{metric}</Text><Text style={{color:theme.muted,fontSize:10.3*scale}}>{detail}</Text>{!!extra&&<Text style={{color:theme.muted,fontSize:9.3*scale}}>{extra}</Text>}<Text style={{color:theme.muted,fontSize:7.7*scale,marginTop:5*scale}}>{demo?'DATOS SIMULADOS · DEMOSTRACIÓN':new Date().toLocaleDateString('es-CO')} · ATLANTIC LEAGUE</Text>
   </View>
  </View>
  <Label muted>Formato vertical · 1080 × 1920</Label><Button label="Compartir historia" icon="share-outline" busy={busy} disabled={!photo||!loaded} onPress={()=>void exportImage(true)}/><Button label={Platform.OS==='web'?'Guardar imagen':'Guardar en mis fotos'} kind="quiet" busy={busy} disabled={!photo||!loaded} onPress={()=>void exportImage(false)}/>
  {exported&&<StoryDownload url={exported} color={color.blue} background={color.surface} line={color.line}/>}
 </Screen>;
}
