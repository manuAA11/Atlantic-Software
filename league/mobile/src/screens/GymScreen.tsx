import React,{useCallback,useEffect,useRef,useState} from 'react';
import {useFocusEffect} from '@react-navigation/native';
import {AppState,Text,View} from 'react-native';
import {useAthlete} from '../state/AthleteContext';
import type {GymEvent} from '../lib/domain';
import {useUi,Screen,Heading,Card,Row,Label,Button,Field,Chips,Empty} from '../components/ui';
export function GymScreen(){
 const {color,s}=useUi();
 const {api,snapshot,refresh,setNotice}=useAthlete(),[gym,setGym]=useState(''),[events,setEvents]=useState<GymEvent[]>([]),[membership,setMembership]=useState<{active:boolean;frozen:boolean}|null>(null),[code,setCode]=useState(''),[search,setSearch]=useState(''),[found,setFound]=useState<{gym_id:string;name:string}[]>([]),[busy,setBusy]=useState(false);
 const links=snapshot?.links.filter(g=>g.status==='APPROVED')||[];
 useEffect(()=>{if(!gym&&links.length)setGym(links[0].gym_id);},[snapshot,gym]);
 const loadVersion=useRef(0);
 const load=useCallback(async()=>{
  if(!gym)return;
  const version=++loadVersion.current;
  try{const [calendar,member]=await Promise.all([api.call<GymEvent[]>('gym.calendar',{gym_id:gym}),api.call<{active:boolean;frozen:boolean}>('gym.membership',{gym_id:gym})]);if(version===loadVersion.current){setEvents(calendar);setMembership(member);}}
  catch(e){if(version===loadVersion.current){setEvents([]);setMembership(null);setNotice(e instanceof Error?e.message:'No se pudo consultar el gimnasio.');}}
 },[gym,api,setNotice]);
 useFocusEffect(useCallback(()=>{
  void load();
  const timer=setInterval(()=>{if(AppState.currentState==='active')void load();},30000);
  const subscription=AppState.addEventListener('change',state=>{if(state==='active')void load();});
  return()=>{++loadVersion.current;clearInterval(timer);subscription.remove();};
 },[load]));
 const perform=async(action:string,data:Record<string,unknown>,message:string)=>{
  setBusy(true);try{await api.call(action,data);setNotice(message);await load();await refresh();setNotice(message);}catch(e){setNotice(e instanceof Error?e.message:'No se pudo completar la operación.');}finally{setBusy(false);}
 };
 return <Screen onRefresh={()=>void load()} refreshing={busy}>
  <Heading eyebrow="Tu gimnasio" title="Agenda" detail={links.find(g=>g.gym_id===gym)?.name||'Clases y actividades de tu gimnasio.'}/>
  {links.length>1&&<Chips items={links.map(g=>({value:g.gym_id,label:g.name}))} value={gym} onChange={setGym}/>}
  {membership&&<Card><Row><Label>Membresía</Label><Text style={{fontWeight:'600',color:membership.active?color.green:color.muted}}>{membership.frozen?'Congelada':membership.active?'Activa':'Sin acceso vigente'}</Text></Row><Label muted>El estado lo confirma Atlantic Gym. Vincular tu cuenta no crea cobros ni cambia tu plan.</Label><Button label="Actualizar asistencias y XP" kind="quiet" busy={busy} onPress={()=>void perform('gym.attendance',{gym_id:gym},'Asistencias actualizadas.')}/></Card>}
  {!!links.length&&<Label>Próximas clases</Label>}
  {events.map(event=><Card key={event.id}><Row><Text style={s.eyebrow}>{new Date(event.starts_at).toLocaleDateString('es-CO',{weekday:'short',day:'numeric',month:'short'})}</Text><Label muted>{new Date(event.starts_at).toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'})}</Label></Row><Label>{event.name}</Label>{event.description&&<Label muted>{event.description}</Label>}{event.trainer&&<Label muted>{event.trainer}</Label>}<Label muted>{Math.max(0,event.capacity-event.reserved)} de {event.capacity} cupos disponibles</Label><Button label={event.mine?'Cancelar mi reserva':'Reservar clase'} kind={event.mine?'quiet':'primary'} disabled={!event.mine&&(!membership?.active||event.reserved>=event.capacity)} busy={busy} onPress={()=>void perform(event.mine?'gym.cancel':'gym.reserve',{gym_id:gym,class_id:event.id},event.mine?'Reserva cancelada.':'Tu cupo quedó reservado.')}/></Card>)}
  {!!links.length&&!events.length&&<Empty title="El calendario está al día" detail="Las nuevas clases aparecerán aquí cuando tu gimnasio las publique."/>}
  <Card><Label>Vincular otro gimnasio</Label><Field label="Buscar por nombre" value={search} onChangeText={setSearch}/><Button label="Buscar gimnasio" kind="quiet" onPress={()=>void api.call<typeof found>('gym.search',{query:search}).then(setFound).catch(e=>setNotice(e.message))}/>{found.map(item=><Text style={s.body} key={item.gym_id}>{item.name}</Text>)}<Field label="Código del gimnasio" value={code} onChangeText={setCode} autoCapitalize="characters" placeholder="Solicítalo en recepción"/><Button label="Solicitar vinculación" busy={busy} disabled={code.trim().length<6} onPress={()=>void perform('gym.request',{code:code.trim().toUpperCase()},'Solicitud enviada. El gimnasio comprobará tu identidad antes de aprobarla.')}/><Label muted>Conocer el código no permite consultar datos privados. El gimnasio debe aprobar tu solicitud.</Label></Card>
  {snapshot?.requests.filter(r=>r.status==='PENDING').map(r=><Text key={r.gym_id} style={s.body}>Tienes una solicitud pendiente de revisión.</Text>)}
 </Screen>;
}
