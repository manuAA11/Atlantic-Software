import {normalizePhone,cleanText} from './security.mjs';
export const VARIABLES=['nombre','apellido','gimnasio','plan','precio','fecha_vencimiento','dias_restantes','entradas_restantes','fecha_ultima_entrada','telefono','link_pago'];
const dayNumber=s=>Math.floor(Date.parse(String(s).slice(0,10)+'T12:00:00Z')/86400000);
export function localParts(instant,zone='America/Bogota') {
 const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(instant)).map(x=>[x.type,x.value]));
 return {date:`${p.year}-${p.month}-${p.day}`,time:`${p.hour}:${p.minute}`};
}
export function facts(context,event=null) {
 const m=context.membership||{},p=context.plan||{},today=context.today;
 const last=context.last_checkin?localParts(context.last_checkin,context.timezone).date:null;
 return {plan_id:p.id??m.plan_id,plan_type:(m.entry_limit??p.entry_limit)!=null?'ticket':'monthly',active:context.active===true,status:m.status,
 entries_remaining:m.entries_remaining??null,days_remaining:m.end_date?dayNumber(m.end_date)-dayNumber(today):null,
 days_absent:dayNumber(today)-dayNumber(last||localParts(context.created_at,context.timezone).date),whatsapp_opt_in:context.whatsapp_opt_in===true,
 payment_method:event?.payload?.payment_method??null,payment_pending:event?.payload?.status==='PENDING',client_type:(m.entry_limit??p.entry_limit)===1?'session':(m.entry_limit??p.entry_limit)!=null?'ticket':'monthly'};
}
export function conditionsMatch(conditions,values) {
 return (conditions||[]).every(c=>{
  if(!Object.hasOwn(values,c.field))return false;const actual=values[c.field],expected=c.value;
  if(c.op==='in')return Array.isArray(expected)&&expected.some(v=>String(v)===String(actual));
  if(c.op==='eq')return String(actual)===String(expected);if(c.op==='ne')return String(actual)!==String(expected);
  if(actual==null||!Number.isFinite(Number(actual))||!Number.isFinite(Number(expected)))return false;
  return {lt:()=>Number(actual)<Number(expected),lte:()=>Number(actual)<=Number(expected),gt:()=>Number(actual)>Number(expected),gte:()=>Number(actual)>=Number(expected)}[c.op]?.()??false;
 });
}
export function triggerMatches(rule,c,event=null) {
 const f=facts(c,event),o=rule.trigger_options||{},n=Number(o.value||0),today=c.today,m=c.membership||{},now=localParts(c.server_now,c.timezone);
 const birthday=c.birth_date?.slice(5,10);const thisYearBirthday=birthday?today.slice(0,4)+'-'+birthday:null;
 let birthdayDays=birthday?dayNumber(thisYearBirthday)-dayNumber(today):null;
 if(birthdayDays<0)birthdayDays=dayNumber(String(Number(today.slice(0,4))+1)+'-'+birthday)-dayNumber(today);
 const et=event?.event_type,ep=event?.payload||{};
 if((m.frozen===true||m.status==='FROZEN')&&['MEMBERSHIP_BEFORE','MEMBERSHIP_TODAY','MEMBERSHIP_AFTER','MEMBERSHIP_OVERDUE_REPEAT','TICKET_EXPIRING','TICKET_REMAINING','INACTIVITY'].includes(rule.trigger_type))return false;
 switch(rule.trigger_type){
 case 'MEMBERSHIP_BEFORE':return f.plan_type==='monthly'&&f.days_remaining===n;
 case 'MEMBERSHIP_TODAY':return f.plan_type==='monthly'&&f.days_remaining===0;
 case 'MEMBERSHIP_AFTER':return f.plan_type==='monthly'&&f.days_remaining===-n;
 case 'MEMBERSHIP_OVERDUE_REPEAT':return f.plan_type==='monthly'&&n>0&&f.days_remaining<0&&(-f.days_remaining)%n===0;
 case 'MEMBERSHIP_RENEWED':return et==='MEMBERSHIP_RENEWED'||et==='ONLINE_APPROVED';
 case 'TICKET_REMAINING':return f.plan_type==='ticket'&&f.entries_remaining===n;
 case 'TICKET_EXPIRING':return f.plan_type==='ticket'&&f.days_remaining===n;
 case 'TICKET_CONSUMED':return et==='CHECK_IN_SUCCESS'&&ep.ticket_consumed===true;
 case 'CHECK_IN_SUCCESS':return et==='CHECK_IN_SUCCESS';
 case 'FIRST_CHECK_IN_DAY':return et==='CHECK_IN_SUCCESS'&&ep.first_of_day===true;
 case 'EVERY_N_CHECKINS':return et==='CHECK_IN_SUCCESS'&&n>0&&Number(ep.checkin_count)%n===0;
 case 'FIRST_CHECK_IN_RENEWAL':return et==='CHECK_IN_SUCCESS'&&ep.first_of_membership===true;
 case 'INACTIVITY':return f.days_absent===n*(o.unit==='weeks'?7:1);
 case 'BIRTHDAY':return birthday===today.slice(5,10);
 case 'BIRTHDAY_BEFORE':return birthdayDays===n;
 case 'MANUAL_PAYMENT':return et==='MEMBERSHIP_RENEWED'&&ep.payment_source!=='WOMPI'&&ep.payment_method!=='Wompi';
 case 'ONLINE_APPROVED':case 'ONLINE_DECLINED':return et===rule.trigger_type;
 case 'PAYMENT_PENDING':case 'UNUSED_PAYMENT_LINK':return et===rule.trigger_type&&Number(ep.age_hours)>=n;
 case 'CUSTOM_DATE':return o.date===today;
 case 'DAILY':return true;
 case 'WEEKLY':return new Date(today+'T12:00:00Z').getUTCDay()===Number(o.weekday??1);
 case 'MONTHLY':return Number(today.slice(8,10))===Number(o.monthday??1);
 default:return false;
 }
}
export const EVENT_TRIGGERS=new Set(['MEMBERSHIP_RENEWED','TICKET_CONSUMED','CHECK_IN_SUCCESS','FIRST_CHECK_IN_DAY','EVERY_N_CHECKINS','FIRST_CHECK_IN_RENEWAL','MANUAL_PAYMENT','ONLINE_APPROVED','ONLINE_DECLINED','PAYMENT_PENDING','UNUSED_PAYMENT_LINK']);
export function evaluate(rule,c,event=null) {
 if(!rule.enabled||rule.deleted_at||!c.whatsapp_opt_in||!normalizePhone(c.phone))return null;
 if(EVENT_TRIGGERS.has(rule.trigger_type)!==!!event)return null;
 if(!event&&localParts(c.server_now,c.timezone).time<(rule.trigger_options?.time||'09:00'))return null;
 if(!triggerMatches(rule,c,event)||!conditionsMatch(rule.conditions,facts(c,event)))return null;
 const occurrence=event?'event-'+event.id:rule.trigger_type==='TICKET_REMAINING'?`ticket-${c.membership?.membership_id}-${rule.trigger_options?.value}`:c.today;
 return {key:`${rule.id}/${rule.revision}/${c.client_id}/${occurrence}`,phone:normalizePhone(c.phone)};
}
export function variablesFor(c,paymentLink='') {
 const f=facts(c),m=c.membership||{};
 return {nombre:c.first_name||'',apellido:c.last_name||'',gimnasio:c.gym_name||'',plan:c.plan?.name||m.plan_name||'Sin plan',precio:new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(c.plan?.price||0),fecha_vencimiento:m.end_date?.slice(0,10)||'Sin plan',dias_restantes:String(f.days_remaining??0),entradas_restantes:f.entries_remaining==null?'Sin límite':String(f.entries_remaining),fecha_ultima_entrada:c.last_checkin?localParts(c.last_checkin,c.timezone).date:'Sin registros',telefono:c.phone||'',link_pago:paymentLink};
}
export function renderMessage(body,variables) {return cleanText(body.replace(/\{\{([a-z_]+)\}\}/g,(_,name)=>{if(!VARIABLES.includes(name))throw new Error('Variable no admitida');return variables[name]??'';}));}
export function recommendedRules() {
 return [
 ['Vencimiento en 3 días','MEMBERSHIP_BEFORE',3,'Hola {{nombre}}, tu plan {{plan}} en {{gimnasio}} vence el {{fecha_vencimiento}}.'],
 ['Vence hoy','MEMBERSHIP_TODAY',0,'Hola {{nombre}}, tu membresía en {{gimnasio}} vence hoy. Te esperamos para renovarla.'],
 ['Quedan 2 entradas','TICKET_REMAINING',2,'Hola {{nombre}}, te quedan {{entradas_restantes}} entradas en {{gimnasio}}.'],
 ['Última entrada','TICKET_REMAINING',1,'Hola {{nombre}}, te queda 1 entrada en {{gimnasio}}.'],
 ['Confirmación de pago','ONLINE_APPROVED',0,'Pago recibido. {{nombre}}, tu plan {{plan}} quedó renovado hasta el {{fecha_vencimiento}}.'],
 ['Cumpleaños','BIRTHDAY',0,'¡Feliz cumpleaños, {{nombre}}! Te deseamos un gran día de parte de {{gimnasio}}.'],
 ['14 días sin asistir','INACTIVITY',14,'Hola {{nombre}}, te esperamos de nuevo en {{gimnasio}}. ¿Podemos ayudarte?']
 ].map(([name,trigger_type,value,body])=>({name,trigger_type,trigger_options:{value,time:'09:00'},body,enabled:false,conditions:[],frequency:{count:1,hours:24},include_payment_link:false}));
}
