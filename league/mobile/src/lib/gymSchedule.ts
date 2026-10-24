import type {GymEvent} from './domain';

export function gymEventTime(event:Pick<GymEvent,'starts_at'|'timezone'>){
 const instant=new Date(event.starts_at);
 if(!Number.isFinite(instant.getTime()))return {date:'Fecha por confirmar',time:'',zone:''};
 let timeZone=event.timezone||undefined;
 try{if(timeZone)new Intl.DateTimeFormat('es-CO',{timeZone}).format(instant);}catch{timeZone=undefined;}
 return {
  date:new Intl.DateTimeFormat('es-CO',{weekday:'short',day:'numeric',month:'short',timeZone}).format(instant),
  time:new Intl.DateTimeFormat('es-CO',{hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZone}).format(instant),
  zone:timeZone?'Hora del gimnasio':'Hora de tu dispositivo',
 };
}

export function canBookEvent(event:Pick<GymEvent,'capacity'|'reserved'|'requires_membership'>,membership:{active:boolean}|null){
 return event.reserved<event.capacity&&(event.requires_membership===false||membership?.active===true);
}
