import React,{useEffect,useRef,useState} from 'react';
import {Platform,Text,View} from 'react-native';
import * as Crypto from 'expo-crypto';
import * as ImagePicker from 'expo-image-picker';
import {File as NativeFile} from 'expo-file-system';
import {useAthlete} from '../state/AthleteContext';
import {supabase} from '../lib/api';
import type {Rank} from '../lib/domain';
import {strengthRank} from '../lib/domain';
import {useUi,Screen,Heading,Card,Row,Label,Button,Field,Chips,Empty} from '../components/ui';
const divisions=[{value:'OPEN',label:'Abierta'},{value:'WOMEN',label:'Mujeres'},{value:'MEN',label:'Hombres'}];
const weights=[{value:'OPEN',label:'Abierto'},{value:'LE60',label:'≤ 60 kg'},{value:'60-75',label:'60–75 kg'},{value:'75-90',label:'75–90 kg'},{value:'GT90',label:'> 90 kg'}];
export function LeagueScreen(){
 const {color,s}=useUi();
 const {api,snapshot,catalog,demo,refresh,setNotice}=useAthlete();
 const [kind,setKind]=useState('XP'),[gym,setGym]=useState(''),[exercise,setExercise]=useState(''),[division,setDivision]=useState('OPEN'),[category,setCategory]=useState('OPEN'),[ranks,setRanks]=useState<Rank[]>([]),[kg,setKg]=useState(''),[reps,setReps]=useState(''),[evidence,setEvidence]=useState<ImagePicker.ImagePickerAsset|null>(null),[busy,setBusy]=useState(false);
 const requestAttempt=useRef<{fingerprint:string;key:string;path?:string}|null>(null);
 const links=snapshot?.links.filter(g=>g.status==='APPROVED')||[],official=catalog.filter(e=>!e.owner_id);
 useEffect(()=>{if(!exercise&&official.length)setExercise(official[0].id);},[catalog,exercise]);
 const load=async()=>{try{setRanks(await api.call<Rank[]>('leaderboard',{kind,gym_id:gym,exercise_id:exercise,division,weight_class:category}));}catch(e){setNotice(e instanceof Error?e.message:'No se pudo consultar la clasificación.');}};
 useEffect(()=>{if(kind==='XP'||exercise)void load();},[api,kind,gym,exercise,division,category]);
 const photo=async()=>{
  try{
   const permission=await ImagePicker.requestMediaLibraryPermissionsAsync();if(!permission.granted){setNotice('Permite el acceso a tus fotos para adjuntar una evidencia.');return;}
   const selected=await ImagePicker.launchImageLibraryAsync({mediaTypes:['images'],allowsEditing:true,quality:.8});
   if(!selected.canceled)setEvidence(selected.assets[0]);
  }catch{setNotice('No se pudo abrir la imagen. Vuelve a intentarlo.');}
 };
 const submit=async()=>{
  const weight=Number(kg.replace(',','.')),count=Number(reps),gymId=gym||links[0]?.gym_id;
  if(!gymId||!exercise||!Number.isFinite(weight)||weight<=0||weight>1000||!Number.isInteger(count)||count<1||count>12){setNotice('Selecciona tu gimnasio y registra un peso válido con 1 a 12 repeticiones.');return;}
  setBusy(true);
  try{
   const fingerprint=JSON.stringify([gymId,exercise,weight,count,division,category,evidence?.uri]);
   if(requestAttempt.current?.fingerprint!==fingerprint)requestAttempt.current={fingerprint,key:Crypto.randomUUID()};
   const attempt=requestAttempt.current!;let path=attempt.path;
   if(evidence&&!demo&&supabase&&!path){
    const bytes=Platform.OS==='web'?await (await fetch(evidence.uri)).arrayBuffer():await new NativeFile(evidence.uri).arrayBuffer();
    if(bytes.byteLength>6291456)throw Error('Elige una imagen de menos de 6 MB.');
    const mime=evidence.mimeType||'image/jpeg',extension=mime==='image/png'?'png':mime==='image/webp'?'webp':'jpg';
    if(!['image/jpeg','image/png','image/webp'].includes(mime))throw Error('Selecciona una imagen JPG, PNG o WebP.');
    path=snapshot!.profile.id+'/'+attempt.key+'.'+extension;
    const {error}=await supabase.storage.from('league-evidence').upload(path,bytes,{contentType:mime,upsert:false});if(error&&Number((error as {statusCode?:string;status?:number}).statusCode||(error as {status?:number}).status)!==409)throw Error('No se pudo adjuntar la evidencia. Inténtalo de nuevo.');attempt.path=path;
   }
   await api.call('record.submit',{gym_id:gymId,exercise_id:exercise,weight_kg:weight,reps:count,division,weight_class:category,request_key:attempt.key,...(path?{evidence_path:path}:{})});
   await refresh();requestAttempt.current=null;setEvidence(null);setKg('');setReps('');setNotice('Marca enviada. Tu entrenador debe verificarla antes de que aparezca en la clasificación.');
  }catch(e){setNotice(e instanceof Error?e.message:'No se pudo enviar la marca.');}finally{setBusy(false);}
 };
 return <Screen refreshing={busy} onRefresh={()=>void load()}>
  <Heading eyebrow="Atlantic League" title="Clasificaciones" detail="Tu XP personal y tus marcas de fuerza avanzan por separado."/>
  <Card><Row><View><Text style={s.eyebrow}>XP OFICIAL</Text><Text style={s.metric}>{snapshot?.official_xp||0}</Text></View><View style={{flex:1,alignItems:'flex-end'}}><Text style={s.eyebrow}>FUERZA</Text><Text style={[s.label,{textAlign:'right'}]}>{strengthRank(snapshot?.records||[])}</Text></View></Row><Label muted>Las clasificaciones oficiales incluyen asistencias confirmadas y marcas verificadas. Los entrenamientos personales se conservan en tu historial.</Label></Card>
  <Chips value={kind} onChange={setKind} items={[{value:'XP',label:'Clasificación XP'},{value:'STRENGTH',label:'Fuerza por ejercicio'}]}/>
  <Chips value={gym} onChange={setGym} items={[{value:'',label:'Global'},...links.map(l=>({value:l.gym_id,label:l.name}))]}/>
  {kind==='STRENGTH'&&<><Chips value={exercise} onChange={setExercise} items={official.map(e=>({value:e.id,label:e.name}))}/><Label muted>División</Label><Chips value={division} onChange={setDivision} items={divisions}/><Label muted>Categoría de peso corporal</Label><Chips value={category} onChange={setCategory} items={weights}/><Label muted>Se compara la mejor estimación de 1RM por deportista, dentro del mismo ejercicio y categoría.</Label></>}
  <Card>{ranks.map((r,i)=><Row key={i}><Text style={[s.label,{width:22,color:i===0?color.blue:color.muted}]}>{i+1}</Text><Text style={[s.label,{flex:1,fontSize:15}]}>{r.alias}</Text><Text style={s.label}>{Number(r.score).toLocaleString('es-CO',{maximumFractionDigits:1})}{kind==='XP'?' XP':' kg'}</Text></Row>)}{!ranks.length&&<Label muted>Aún no hay resultados en esta categoría.</Label>}</Card>
  {!!links.length&&<Card><Label>Solicitar verificación de una marca</Label><Chips value={exercise} onChange={setExercise} items={official.map(e=>({value:e.id,label:e.name}))}/>{links.length>1&&<Chips value={gym||links[0].gym_id} onChange={setGym} items={links.map(l=>({value:l.gym_id,label:l.name}))}/>}<Row><View style={{flex:1}}><Field label="Peso levantado · kg" value={kg} onChangeText={setKg} keyboardType="decimal-pad"/></View><View style={{flex:1}}><Field label="Repeticiones · 1 a 12" value={reps} onChangeText={setReps} keyboardType="number-pad"/></View></Row><Chips value={division} onChange={setDivision} items={divisions}/><Chips value={category} onChange={setCategory} items={weights}/><Button label={evidence?'Imagen adjunta · cambiar':'Adjuntar foto · opcional'} kind="quiet" onPress={()=>void photo()}/><Button label="Enviar a mi entrenador" busy={busy} onPress={()=>void submit()}/></Card>}
  <Label>Mis solicitudes</Label>{snapshot?.records.map(record=><Card key={record.id}><Label>{record.exercise_name}</Label><Row><Label muted>{record.weight_kg} kg × {record.reps}</Label><Label muted>{record.status==='APPROVED'?'Verificada':record.status==='REJECTED'?'No aprobada':'En revisión'}</Label></Row></Card>)}
  {!links.length&&<Empty title="Tu progreso personal sigue contando" detail="Vincula un gimnasio autorizado para solicitar verificaciones y participar en las clasificaciones oficiales."/>}
 </Screen>;
}
