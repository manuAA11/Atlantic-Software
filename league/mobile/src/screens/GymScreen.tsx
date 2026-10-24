import React,{useCallback,useEffect,useRef,useState} from 'react';
import {Text} from 'react-native';
import {useAthlete} from '../state/AthleteContext';
import type {GymEvent} from '../lib/domain';
import {canBookEvent,gymEventTime} from '../lib/gymSchedule';
import {useVisibleRefresh} from '../lib/useVisibleRefresh';
import {useUi,Screen,Heading,Card,Row,Label,Button,Field,Chips,Empty} from '../components/ui';
export function GymScreen(){
 const {color,s}=useUi();
 const {api,snapshot,refresh,setNotice}=useAthlete(),[gym,setGym]=useState(''),[events,setEvents]=useState<GymEvent[]>([]),[membership,setMembership]=useState<{active:boolean;frozen:boolean}|null>(null),[code,setCode]=useState(''),[search,setSearch]=useState(''),[found,setFound]=useState<{gym_id:string;name:string}[]>([]),[busy,setBusy]=useState(false);
 const links=snapshot?.links.filter(g=>g.status==='APPROVED')||[];
 useEffect(()=>{if(!links.some(link=>link.gym_id===gym)){setGym(links[0]?.gym_id||'');setEvents([]);setMembership(null);}},[snapshot,gym]);
 const loadVersion=useRef(0),currentGym=useRef(gym);currentGym.current=gym;
 const load=useCallback(async(isCurrent:()=>boolean=()=>true)=>{
  if(!gym||gym!==currentGym.current)return;
  const version=++loadVersion.current;
  try{const [calendar,member]=await Promise.all([api.call<GymEvent[]>('gym.calendar',{gym_id:gym}),api.call<{active:boolean;frozen:boolean}>('gym.membership',{gym_id:gym})]);if(gym===currentGym.current&&isCurrent()&&version===loadVersion.current){setEvents(calendar);setMembership(member);}}
  catch(e){if(gym===currentGym.current&&isCurrent()&&version===loadVersion.current){setEvents([]);setMembership(null);setNotice(e instanceof Error?e.message:'No se pudo consultar el gimnasio.');}}
 },[gym,api,setNotice]);
 useVisibleRefresh(load);
 const perform=async(action:string,data:Record<string,unknown>,message:string)=>{
  setBusy(true);try{await api.call(action,data);setNotice(message);await load();await refresh();setNotice(message);}catch(e){setNotice(e instanceof Error?e.message:'No se pudo completar la operación.');}finally{setBusy(false);}
 };
 return <Screen onRefresh={()=>void load()} refreshing={busy}>
  <Heading eyebrow="Tu gimnasio" title="Agenda" detail={links.find(g=>g.gym_id===gym)?.name||'Clases y actividades de tu gimnasio.'}/>
  {links.length>1&&<Chips items={links.map(g=>({value:g.gym_id,label:g.name}))} value={gym} onChange={setGym}/>}
  {membership&&<Card><Row><Label>Membresía</Label><Text style={{fontWeight:'600',color:membership.active?color.green:color.muted}}>{membership.frozen?'Congelada':membership.active?'Activa':'Sin acceso vigente'}</Text></Row><Label muted>El estado lo confirma Atlantic Gym. Vincular tu cuenta no crea cobros ni cambia tu plan.</Label><Button label="Actualizar asistencias y XP" kind="quiet" busy={busy} onPress={()=>void perform('gym.attendance',{gym_id:gym},'Asistencias actualizadas.')}/></Card>}
  {!!links.length&&<Label>Próximas clases</Label>}
  {events.map(event=>{
   const schedule=gymEventTime(event);
   return <Card key={event.id}>
    <Row><Text style={s.eyebrow}>{schedule.date}</Text><Label muted>{schedule.time}</Label></Row>
    <Label>{event.name}</Label>
    <Label muted>{[schedule.zone,event.duration_minutes?`${event.duration_minutes} min`:null].filter(Boolean).join(' · ')}</Label>
    {event.description&&<Label muted>{event.description}</Label>}
    {event.trainer&&<Label muted>{event.trainer}</Label>}
    {event.conditions&&<Label muted>{event.conditions}</Label>}
    {event.requires_membership===false&&<Label muted>No requiere membresía activa.</Label>}
    <Label muted>{Math.max(0,event.capacity-event.reserved)} de {event.capacity} cupos disponibles</Label>
    <Button label={event.mine?'Cancelar mi reserva':'Reservar clase'} kind={event.mine?'quiet':'primary'} disabled={!event.mine&&!canBookEvent(event,membership)} busy={busy} onPress={()=>void perform(event.mine?'gym.cancel':'gym.reserve',{gym_id:gym,class_id:event.id},event.mine?'Reserva cancelada.':'Tu cupo quedó reservado.')}/>
   </Card>;
  })}
  {!!links.length&&!events.length&&<Empty title="El calendario está al día" detail="Las nuevas clases aparecerán aquí cuando tu gimnasio las publique."/>}
  <Card><Label>Vincular otro gimnasio</Label><Field label="Buscar por nombre" value={search} onChangeText={setSearch}/><Button label="Buscar gimnasio" kind="quiet" onPress={()=>void api.call<typeof found>('gym.search',{query:search}).then(setFound).catch(e=>setNotice(e.message))}/>{found.map(item=><Text style={s.body} key={item.gym_id}>{item.name}</Text>)}<Field label="Código del gimnasio" value={code} onChangeText={setCode} autoCapitalize="characters" placeholder="Solicítalo en recepción"/><Button label="Solicitar vinculación" busy={busy} disabled={code.trim().length<6} onPress={()=>void perform('gym.request',{code:code.trim().toUpperCase()},'Solicitud enviada. El gimnasio comprobará tu identidad antes de aprobarla.')}/><Label muted>Conocer el código no permite consultar datos privados. El gimnasio debe aprobar tu solicitud.</Label></Card>
  {snapshot?.requests.filter(r=>r.status==='PENDING').map(r=><Text key={r.gym_id} style={s.body}>Tienes una solicitud pendiente de revisión.</Text>)}
 </Screen>;
}
