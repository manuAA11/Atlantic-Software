import type {GymEvent,Membership} from './types';
import {gymEventTime,canBookEvent} from './gymSchedule';
type Action=(action:string,data?:Record<string,unknown>,extended?:boolean)=>Promise<void>;
export function EventCard({event,membership,disabled,perform}:{event:GymEvent;membership:Membership|null;disabled:boolean;perform:Action}){
 const time=gymEventTime(event),informational=event.kind==='EVENT',cancelled=['CANCELADA','CANCELLED'].includes(event.status||''),finished=new Date(event.starts_at)<=new Date();
 return <section className="card"><div className="row"><span className="eyebrow">{time.date}</span><strong>{time.time}</strong></div><h2>{event.name}</h2><p>{event.description}</p>{event.trainer&&<p>{event.trainer}</p>}{event.location&&<p>{event.location}</p>}<p>{time.zone}{event.duration_minutes?` · ${event.duration_minutes} min`:''}</p>{event.conditions&&<p>{event.conditions}</p>}
  {informational?<p className="badge">{cancelled?'Evento cancelado':finished?'Evento finalizado':'Evento del gimnasio'}</p>:<><p>{Math.max(0,event.capacity-event.reserved)} de {event.capacity} cupos disponibles</p><button className={event.mine?'':'primary'} disabled={disabled||cancelled||finished||(!event.mine&&!canBookEvent(event,membership))} onClick={()=>{if(event.mine&&!confirm('¿Cancelar tu reserva?'))return;void perform(event.mine?'gym.cancel':'gym.reserve',{class_id:event.id});}}>{cancelled?'Actividad cancelada':finished?'Actividad finalizada':event.mine?'Cancelar reserva':'Reservar cupo'}</button></>}
 </section>;
}
