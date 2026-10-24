import type {LeagueApi} from './api';
import type {Exercise,Snapshot,Routine,GymEvent,Rank} from './domain';
const GYM='d0000000-0000-4000-8000-000000000004';
export const demoCatalog:Exercise[]=[
 {id:'10000000-0000-4000-8000-000000000001',name:'Sentadilla con barra',muscle:'Piernas',equipment:'Barra',instructions:'Sigue las indicaciones de tu entrenador.'},
 {id:'10000000-0000-4000-8000-000000000002',name:'Press de banca',muscle:'Pecho',equipment:'Banco y barra',instructions:'Registra el peso total de la barra y los discos.'},
 {id:'10000000-0000-4000-8000-000000000003',name:'Peso muerto',muscle:'Cadena posterior',equipment:'Barra',instructions:'Registra las repeticiones completadas.'},
 {id:'10000000-0000-4000-8000-000000000006',name:'Jalón al pecho',muscle:'Espalda',equipment:'Polea alta',instructions:'Sigue las indicaciones de tu entrenador.'},
 {id:'10000000-0000-4000-8000-000000000007',name:'Prensa de piernas',muscle:'Piernas',equipment:'Prensa',instructions:'Registra la carga y las repeticiones completadas.'},
];
/** Explicitly simulated. This implementation never calls a real gym or database. */
export function demoApi():LeagueApi{
 const snapshot:Snapshot={profile:{id:'demo',alias:'Deportista de prueba',leaderboard_opt_in:false},xp:420,official_xp:150,links:[{gym_id:GYM,name:'Gimnasio de prueba',status:'APPROVED'}],requests:[],records:[],workouts:[{id:'demo-last',name:'Fuerza · Tren superior',finished_at:new Date().toISOString(),sets:[{exercise_id:demoCatalog[1].id,weight_kg:40,reps:10},{exercise_id:demoCatalog[1].id,weight_kg:40,reps:8}]}]};
 const events:GymEvent[]=[{id:'1',name:'Fuerza en grupo',starts_at:new Date(Date.now()+86400000).toISOString(),capacity:12,reserved:8,mine:false,trainer:'Entrenador de prueba',description:'Técnica y fuerza para todos los niveles.'}];
 return {async call<T>(action:string,data:Record<string,unknown>={}){
  let result:unknown;
  if(action==='snapshot'||action==='profile.ensure')result=snapshot;
  else if(action==='catalog')result=demoCatalog;
  else if(action==='gym.routines')result=[{id:'1',name:'Fuerza · Tren superior',goal:'Mejorar técnica y constancia',exercises:demoCatalog.map((e,i)=>({id:String(i),catalog_id:e.id,name:e.name,day:'Día 1',sets:'3',reps:'10',weight_kg:'20',rest_seconds:90}))}] satisfies Routine[];
  else if(action==='gym.calendar')result=events;
  else if(action==='gym.reserve'||action==='gym.cancel'){events[0].mine=action==='gym.reserve';result={reserved:events[0].mine};}
  else if(action==='gym.membership')result={active:true,frozen:false};
  else if(action==='gym.workout.start')result={draft_id:'demo-draft'};
  else if(action==='workout.save'){if(!snapshot.workouts.some(w=>w.id===data.id)){snapshot.workouts.unshift({...data,finished_at:new Date().toISOString()} as unknown as Snapshot['workouts'][number]);snapshot.xp+=20;}result={saved:true};}
  else if(action==='profile.update'){Object.assign(snapshot.profile,data);result=snapshot.profile;}
  else if(action==='gym.search')result=[{gym_id:GYM,name:'Gimnasio de prueba'}];
  else if(action==='gym.request'){snapshot.requests.push({gym_id:GYM,status:'PENDING'});result={status:'PENDING'};}
  else if(action==='record.submit'){snapshot.records.unshift({id:'demo-record',exercise_name:demoCatalog.find(x=>x.id===data.exercise_id)?.name||'Ejercicio',weight_kg:Number(data.weight_kg),reps:Number(data.reps),status:'PENDING',created_at:new Date().toISOString()});result={status:'PENDING'};}
  else if(action==='leaderboard')result=[{alias:'Laura',score:320},{alias:'Andrés',score:250},{alias:'Deportista de prueba',score:150}] satisfies Rank[];
  else if(action==='invitation.accept')result={status:'APPROVED'};
  else if(action==='gym.attendance')result={days:6};
  else throw Error('Esta acción no está disponible en la demostración.');
  return structuredClone(result) as T;
 }};
}
