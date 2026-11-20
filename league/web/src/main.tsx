import React,{useCallback,useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter,NavLink,Route,Routes,Link} from 'react-router';
import type {Session} from '@supabase/supabase-js';
import {call,supabase,memberEndpoint,signInMember,accessEndpoint,accessGym} from './api';
import type {Membership,Snapshot,GymEvent,Renewal,Notice} from './types';
import {renewalLabels} from './types';
import {gymEventTime,canBookEvent} from './gymSchedule';
import './style.css';
import {Routines} from './Routines';
import {MemberProfile} from './Profile';
import {PwaEntry,usePwaUpdate} from './PwaEntry';

const formatDate=(s?:string|null)=>{
 if(!s)return 'Por confirmar';
 if(/^\d{4}-\d{2}-\d{2}$/.test(s)){const [y,m,d]=s.split('-').map(Number);return new Intl.DateTimeFormat('es-CO',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(Date.UTC(y,m-1,d)));}
 const date=new Date(s);return Number.isFinite(date.getTime())?date.toLocaleDateString('es-CO',{day:'numeric',month:'long',year:'numeric'}):'Por confirmar';
};
function Icon({name}:{name:string}){
 const paths:Record<string,React.ReactNode>={home:<><path d="m3 10 9-7 9 7v10H3z"/><path d="M9 20v-7h6v7"/></>,calendar:<><rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4m10-4v4M3 11h18M8 15h2m4 0h2"/></>,routine:<><path d="M5 8v8m3-10v12m8-12v12m3-10v8M8 12h8"/></>,bell:<><path d="M5 17h14l-2-3V9a5 5 0 0 0-10 0v5zM10 21h4"/></>,user:<><circle cx="12" cy="8" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/></>,arrow:<path d="m9 5 7 7-7 7"/>,refresh:<><path d="M20 11a8 8 0 1 0-2 6M20 4v7h-7"/></>};
 return <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}
function Card({children,className=''}:{children:React.ReactNode;className?:string}){return <section className={'card '+className}>{children}</section>;}
function Empty({title,children}:{title:string;children:React.ReactNode}){return <Card><h2>{title}</h2><p>{children}</p></Card>;}
function App({authOnly=false,installScreen}:{authOnly?:boolean;installScreen?:React.ReactNode}){
 const [session,setSession]=useState<Session|null>(null),[starting,setStarting]=useState(true),[snapshot,setSnapshot]=useState<Snapshot|null>(null),[gym,setGym]=useState('');
 const [member,setMember]=useState<Membership|null>(null),[events,setEvents]=useState<GymEvent[]>([]),[renewals,setRenewals]=useState<Renewal[]>([]),[notices,setNotices]=useState<Notice[]>([]);
 const [error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[pendingAction,setPendingAction]=useState(false),[fresh,setFresh]=useState(false),[extraError,setExtraError]=useState('');
 const [online,setOnline]=useState(navigator.onLine),[dark,setDark]=useState(()=>{try{return localStorage.getItem('atlantic-league-appearance')==='dark';}catch{return false;}});
 const {update,applyUpdate}=usePwaUpdate(),epoch=useRef(0),gymRef=useRef(gym);gymRef.current=gym;
 useEffect(()=>{document.documentElement.dataset.theme=dark?'dark':'light';document.querySelector('meta[name="theme-color"]')?.setAttribute('content',dark?'#0b1423':'#f5f7fb');try{localStorage.setItem('atlantic-league-appearance',dark?'dark':'light');}catch{}},[dark]);
 useEffect(()=>{
  if(!supabase){setStarting(false);return;}
  let live=true;
  void supabase.auth.getSession().then(({data,error})=>{if(live){setSession(data.session);setStarting(false);if(error)setError('No se pudo recuperar la sesión. Vuelve a entrar.');}}).catch(()=>{if(live){setStarting(false);setError('No se pudo recuperar la sesión.');}});
  const {data}=supabase.auth.onAuthStateChange((_event,next)=>{if(live){setSession(next);if(!next){epoch.current++;setSnapshot(null);setMember(null);setEvents([]);setNotices([]);setRenewals([]);setGym('');setFresh(false);}}});
  return()=>{live=false;data.subscription.unsubscribe();};
 },[]);
 const refresh=useCallback(async()=>{
  if(!session||authOnly)return;
  const version=++epoch.current;setBusy(true);setError('');setExtraError('');setFresh(false);setMember(null);setEvents([]);setRenewals([]);setNotices([]);
  try{
   const next=await call<Snapshot>('snapshot');if(version!==epoch.current)return;setSnapshot(next);
   const links=next.links.filter(x=>x.status==='APPROVED'),id=links.some(x=>x.gym_id===gymRef.current)?gymRef.current:links[0]?.gym_id||'';
   if(id!==gymRef.current){setGym(id);gymRef.current=id;}
   if(!id)return;
   const [membership,calendar]=await Promise.all([memberEndpoint?call<Membership>('membership.details',{gym_id:id},true):call<Membership>('gym.membership',{gym_id:id}),call<GymEvent[]>('gym.calendar',{gym_id:id})]);
   if(version!==epoch.current)return;setMember(membership);setEvents(calendar);setFresh(true);
   if(memberEndpoint){try{const [r,n]=await Promise.all([call<Renewal[]>('renewals.list',{gym_id:id},true),call<Notice[]>('notifications.list',{gym_id:id},true)]);if(version===epoch.current){setRenewals(r);setNotices(n);}}catch(e){if(version===epoch.current)setExtraError(e instanceof Error?e.message:'No se pudieron actualizar tus solicitudes y avisos.');}}
  }catch(e){if(version===epoch.current)setError(e instanceof Error?e.message:'No se pudieron actualizar tus datos.');}
  finally{if(version===epoch.current)setBusy(false);}
 },[session?.user.id,gym,authOnly]);
 useEffect(()=>{void refresh();return()=>{epoch.current++;};},[refresh]);
 useEffect(()=>{
  const reconnect=()=>{setOnline(true);void refresh();},offline=()=>{setOnline(false);epoch.current++;setFresh(false);setBusy(false);setMember(null);setEvents([]);setNotices([]);setRenewals([]);},visible=()=>{if(document.visibilityState==='visible'&&navigator.onLine)void refresh();};
  window.addEventListener('online',reconnect);window.addEventListener('offline',offline);document.addEventListener('visibilitychange',visible);
  return()=>{window.removeEventListener('online',reconnect);window.removeEventListener('offline',offline);document.removeEventListener('visibilitychange',visible);};
 },[refresh]);
 const perform=async(action:string,data:Record<string,unknown>={},extended=false)=>{
  if(pendingAction)return;setPendingAction(true);setMessage('');setError('');
  try{await call(action,{...data,gym_id:gym},extended);setMessage(action==='renewals.create'?'Solicitud guardada. El gimnasio debe revisarla; tu membresía conserva su fecha actual.':action==='gym.reserve'?'Reserva confirmada.':action==='gym.cancel'?'Reserva cancelada.':'Cambio guardado.');await refresh();}
  catch(e){setError(e instanceof Error?e.message:'No se pudo confirmar el cambio.');setFresh(false);}
  finally{setPendingAction(false);}
 };
 if(starting)return <main className="login"><p role="status">Abriendo tu espacio…</p></main>;
 if(!session)return <Login error={error}/>;
 if(authOnly)return <>{installScreen}</>;
 const links=snapshot?.links.filter(x=>x.status==='APPROVED')||[],gymName=links.find(x=>x.gym_id===gym)?.name||'Tu gimnasio';
 const activeRenewal=renewals.find(x=>x.status==='PENDING'||x.status==='REVIEW'),unread=notices.filter(x=>!x.read_at).length;
 const statusLabels:Record<string,string>={ACTIVE:'Activa',EXPIRED:'Vencida',FROZEN:'Congelada',SUSPENDED:'Suspendida',NO_PLAN:'Sin plan asignado',INACTIVE:'Sin acceso vigente',SCHEDULED:'Programada','SIN ENTRADAS':'Sin entradas'};
 const status=member?.frozen?'Congelada':member?.status?(statusLabels[member.status]||'Sin acceso vigente'):member?.active?'Activa':'Sin acceso vigente';
 const renew=()=>{if(window.confirm('¿Enviar una solicitud de renovación al gimnasio? Esto no registra un pago ni cambia tu vencimiento.'))void perform('renewals.create',{request_key:crypto.randomUUID()},true);};
 return <div className="app">
  <header><Link to="/" className="brand"><strong>ATLANTIC LEAGUE</strong><span>{gymName}</span></Link><Link to="/perfil" className="avatar" aria-label="Abrir mi perfil">{snapshot?.profile.alias.slice(0,2).toUpperCase()||'AL'}</Link></header>
  {!online&&<div className="banner" role="status">Sin conexión. Tus datos y operaciones necesitan internet.</div>}
  {update&&<div className="banner">Hay una nueva versión. <button disabled={pendingAction} onClick={applyUpdate}>Actualizar</button></div>}
  <main>
   {links.length>1&&<label className="gym-selector">Gimnasio<select disabled={pendingAction} value={gym} onChange={e=>{epoch.current++;setFresh(false);setMember(null);setEvents([]);setNotices([]);setRenewals([]);setGym(e.target.value);}}>{links.map(x=><option key={x.gym_id} value={x.gym_id}>{x.name}</option>)}</select></label>}
   {error&&<div className="alert" role="alert">{error}<button disabled={busy||!online} onClick={()=>void refresh()}>Volver a intentar</button></div>}
   {extraError&&<div className="alert" role="alert">{extraError}</div>}
   {message&&<div className="success" role="status">{message}</div>}
   {busy&&<p className="subtle" role="status">Actualizando con tu gimnasio…</p>}
   {!busy&&snapshot&&!links.length&&<Empty title="Tu cuenta aún no está vinculada">El gimnasio debe habilitar tu perfil existente. No necesitas registrarte de nuevo.</Empty>}
   <Routes>
    <Route path="/" element={<>
     <div className="heading"><span className="eyebrow">TU ESPACIO</span><h1>Hola{snapshot?', '+snapshot.profile.alias.split(' ')[0]:''}</h1><p>Todo lo que necesitas para tu próxima visita.</p></div>
     <Card className="membership"><div className="row"><span className="eyebrow">MI MEMBRESÍA</span>{member&&<span className={'badge '+(member.active?'good':'')}>{status}</span>}</div><h2>{member?.plan_name||'Mi plan'}</h2>{!member?.plan_name&&<p>El nombre del plan aún no está disponible en la conexión actual.</p>}<div className="dates"><div><span>Inicio</span><strong>{formatDate(member?.starts_at)}</strong></div><div><span>Vencimiento</span><strong>{formatDate(member?.ends_at)}</strong></div></div>{member?.remaining_days!=null&&<p>{member.remaining_days} días restantes, según tu gimnasio.</p>}
      <button className="primary" disabled={!fresh||!online||!memberEndpoint||busy||pendingAction||!!activeRenewal||!!extraError||member?.renewable===false} onClick={renew}>{member?.renewable===false?'Este plan no requiere renovación':activeRenewal?'Renovación '+renewalLabels[activeRenewal.status].toLowerCase():'Solicitar renovación'}</button>
      {!memberEndpoint&&<p className="small">Las solicitudes de renovación todavía no están habilitadas en este piloto.</p>}
      <p className="small">Tu gimnasio confirma el pago y la renovación.</p>
     </Card>
     <div className="tiles"><Link to="/agenda"><Icon name="calendar"/><strong>Eventos y clases</strong><span>Prepara tu próxima visita</span></Link><Link to="/rutinas"><Icon name="routine"/><strong>Mis rutinas</strong><span>Tu plan de entrenamiento</span></Link></div>
     <h2>Tu próxima clase</h2>{events.find(x=>x.mine&&new Date(x.starts_at)>new Date()&&x.status!=='CANCELADA')?<EventCard event={events.find(x=>x.mine&&new Date(x.starts_at)>new Date()&&x.status!=='CANCELADA')!} membership={member} disabled={!fresh||pendingAction||!online} perform={perform}/>:<Empty title="Tu agenda, a tu ritmo">Tus próximas reservas aparecerán aquí.</Empty>}
     <h2>Solicitudes recientes</h2>{renewals.length?renewals.map(r=><Card key={r.id}><div className="row"><strong>Renovación de membresía</strong><span className="badge">{renewalLabels[r.status]}</span></div><p>{formatDate(r.created_at)}</p>{(r.status==='PENDING'||r.status==='REVIEW')&&<button disabled={!fresh||pendingAction||!online} onClick={()=>{if(confirm('¿Cancelar esta solicitud?'))void perform('renewals.cancel',{id:r.id},true);}}>Cancelar solicitud</button>}</Card>):<p>Aún no hay solicitudes para mostrar.</p>}
    </>}/>
    <Route path="/agenda" element={<Agenda events={events} member={member} disabled={!fresh||pendingAction||!online} perform={perform}/>}/>
    <Route path="/rutinas" element={<Routines key={gym} gym={gym}/>}/>
    <Route path="/notificaciones" element={<><div className="heading"><span className="eyebrow">AL DÍA</span><h1>Notificaciones</h1><p>Los avisos de tu gimnasio, en un solo lugar.</p></div>{!memberEndpoint?<Empty title="Avisos pendientes de conexión">El centro de notificaciones se habilitará cuando esté conectado el nuevo servicio del piloto.</Empty>:notices.length?notices.map(n=><Card key={n.id}><div className="row"><h2>{n.title}</h2>{!n.read_at&&<span className="badge good">Nuevo</span>}</div><p>{n.body}</p><span className="small">{formatDate(n.created_at)}</span><Link to={n.target}>Ver detalle</Link>{!n.read_at&&<button disabled={pendingAction||!online} onClick={()=>void perform('notifications.read',{id:n.id},true)}>Marcar como leído</button>}</Card>):<Empty title="Estás al día">Aquí aparecerán tus nuevos avisos.</Empty>}</>}/>
    <Route path="/perfil" element={<><div className="heading"><span className="eyebrow">TU CUENTA</span><h1>Mi perfil</h1></div><MemberProfile key={gym} gym={gym}/><Card><h2>{snapshot?.profile.alias||'Socio'}</h2><p>{gymName}</p>{session.user.email&&!session.user.email.endsWith('@members.atlantic.invalid')&&<p>{session.user.email}</p>}<p>Los cambios en tus datos personales se solicitan al gimnasio.</p></Card><Card><h2>Preferencias</h2><label className="toggle">Modo oscuro<input type="checkbox" checked={dark} onChange={e=>setDark(e.target.checked)}/></label><PushSettings gym={gym} enabled={!!memberEndpoint&&fresh}/></Card><Card><h2>Instalar en tu celular</h2><p>Abre el menú de tu navegador y selecciona Instalar aplicación o Añadir a pantalla de inicio. Después abre Atlantic League desde el nuevo icono.</p><p className="small">Las notificaciones en iPhone requieren abrir la app desde la pantalla de inicio.</p></Card><button disabled={pendingAction} onClick={()=>{void supabase?.auth.signOut({scope:'local'}).then(({error})=>{if(error)setError('No se pudo cerrar la sesión. Vuelve a intentarlo.');});}}>Cerrar sesión en este dispositivo</button><p className="copyright">© Atlantic Tech Software — All rights reserved. By Manuel Cuellar</p></>}/>
    <Route path="*" element={<Empty title="Página no encontrada"><Link to="/">Volver a Inicio</Link></Empty>}/>
   </Routes>
   <button className="refresh" disabled={busy||pendingAction||!online} onClick={()=>void refresh()}><Icon name="refresh"/>Actualizar información</button>
  </main>
  <nav aria-label="Navegación principal">{[{to:'/',name:'home',label:'Inicio'},{to:'/agenda',name:'calendar',label:'Agenda'},{to:'/rutinas',name:'routine',label:'Rutinas'},{to:'/notificaciones',name:'bell',label:'Avisos'},{to:'/perfil',name:'user',label:'Perfil'}].map(n=><NavLink key={n.to} to={n.to} end><Icon name={n.name}/><span>{n.label}{n.name==='bell'&&unread>0?` (${unread})`:''}</span></NavLink>)}</nav>
 </div>;
}
function Login({error}:{error:string}){
 const [document,setDocument]=useState(''),[password,setPassword]=useState(''),[busy,setBusy]=useState(false),[problem,setProblem]=useState(error);
 const configured=!!supabase&&!!accessEndpoint&&!!accessGym;
 const submit=async(e:React.FormEvent)=>{e.preventDefault();if(busy)return;setBusy(true);setProblem('');try{await signInMember(document,password);}catch(e){setProblem(e instanceof Error?e.message:'No se pudo iniciar sesión. Vuelve a intentarlo.');}finally{setBusy(false);}};
 return <main className="login"><div className="wordmark">ATLANTIC LEAGUE</div><span className="eyebrow">TU GIMNASIO, CONTIGO</span><h1>Tu próxima visita<br/>empieza aquí.</h1><p>Consulta tu membresía, prepara tu entrenamiento y reserva tu próxima clase.</p><Card><h2>Iniciar sesión</h2><p>Tu acceso se habilita automáticamente al registrarte en el gimnasio.</p><form onSubmit={e=>void submit(e)}><label>Cédula<input required inputMode="numeric" autoComplete="username" pattern="[0-9]{5,20}" maxLength={20} value={document} disabled={busy} onChange={e=>setDocument(e.target.value)} placeholder="Tu número de cédula"/></label><label>Contraseña<input required type="password" autoComplete="current-password" value={password} disabled={busy} onChange={e=>setPassword(e.target.value)} placeholder="Tu número de cédula"/></label><p className="small">Ingresa tu cédula en los dos campos.</p><button className="primary" disabled={busy||!configured}>{busy?'Ingresando…':'Iniciar sesión'}</button></form>{!configured&&<p className="small">El acceso todavía no está habilitado en este entorno de pruebas.</p>}{(problem||error)&&<p className="alert" role="alert">{problem||error}</p>}</Card><p className="copyright">Atlantic Tech Software · Piloto privado</p></main>;
}
type Action=(action:string,data?:Record<string,unknown>,extended?:boolean)=>Promise<void>;
function EventCard({event,membership,disabled,perform}:{event:GymEvent;membership:Membership|null;disabled:boolean;perform:Action}){
 const time=gymEventTime(event);return <Card><div className="row"><span className="eyebrow">{time.date}</span><strong>{time.time}</strong></div><h2>{event.name}</h2><p>{event.description}</p>{event.trainer&&<p>{event.trainer}</p>}<p>{time.zone}{event.duration_minutes?` · ${event.duration_minutes} min`:''}</p>{event.conditions&&<p>{event.conditions}</p>}<p>{Math.max(0,event.capacity-event.reserved)} de {event.capacity} cupos disponibles</p><button className={event.mine?'':'primary'} disabled={disabled||event.kind==='EVENT'||event.status==='CANCELADA'||new Date(event.starts_at)<=new Date()||(!event.mine&&!canBookEvent(event,membership))} onClick={()=>{if(event.mine&&!confirm('¿Cancelar tu reserva?'))return;void perform(event.mine?'gym.cancel':'gym.reserve',{class_id:event.id});}}>{event.status==='CANCELADA'?'Actividad cancelada':event.kind==='EVENT'?'Evento del gimnasio':new Date(event.starts_at)<=new Date()?'Actividad finalizada':event.mine?'Cancelar reserva':'Reservar cupo'}</button></Card>;
}
function Agenda({events,member,disabled,perform}:{events:GymEvent[];member:Membership|null;disabled:boolean;perform:Action}){
 const [query,setQuery]=useState(''),[day,setDay]=useState(''),[onlyMine,setOnlyMine]=useState(false),[past,setPast]=useState(false);
 const filtered=events.filter(e=>(past?new Date(e.starts_at)<new Date():new Date(e.starts_at)>=new Date())&&e.name.toLocaleLowerCase('es').includes(query.toLocaleLowerCase('es'))&&(!onlyMine||e.mine)&&(!day||new Intl.DateTimeFormat('en-CA',{timeZone:e.timezone||undefined,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(e.starts_at))===day));
 return <><div className="heading"><span className="eyebrow">TU GIMNASIO</span><h1>Eventos y clases</h1><p>Encuentra tu próxima actividad.</p></div><Card><label className="toggle">Ver actividades pasadas<input type="checkbox" checked={past} onChange={e=>setPast(e.target.checked)}/></label><label>Buscar actividad<input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Nombre de la clase"/></label><label>Fecha<input type="date" value={day} onChange={e=>setDay(e.target.value)}/></label><label className="toggle">Solo mis reservas<input type="checkbox" checked={onlyMine} onChange={e=>setOnlyMine(e.target.checked)}/></label></Card>{filtered.map(e=><EventCard key={e.id} event={e} membership={member} disabled={disabled} perform={perform}/>)}{!filtered.length&&<Empty title="Tu agenda está al día">Las actividades publicadas aparecerán aquí. Prueba otra búsqueda o fecha.</Empty>}</>;
}
function PushSettings({gym,enabled}:{gym:string;enabled:boolean}){
 const [status,setStatus]=useState(''),[busy,setBusy]=useState(false),[key,setKey]=useState(import.meta.env.VITE_VAPID_PUBLIC_KEY||'');
 useEffect(()=>{let current=true;if(enabled&&gym)void call<{publicKey:string|null}>('push.config',{gym_id:gym},true).then(v=>{if(current)setKey(v.publicKey||'');}).catch(()=>{});return()=>{current=false;};},[gym,enabled]);
 const compatible='serviceWorker'in navigator&&'PushManager'in window&&'Notification'in window;
 async function change(on:boolean){setBusy(true);try{if(!compatible)throw Error('Este navegador todavía no permite notificaciones.');const reg=await navigator.serviceWorker.ready;
  if(on){if(await Notification.requestPermission()!=='granted')throw Error('Puedes seguir consultando tus avisos dentro de la app.');const decoded=atob(key.replace(/-/g,'+').replace(/_/g,'/'));const applicationServerKey=Uint8Array.from(decoded,c=>c.charCodeAt(0));const sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey});await call('push.subscribe',{gym_id:gym,subscription:sub.toJSON()},true);setStatus('Notificaciones activadas en este dispositivo.');}
  else{const sub=await reg.pushManager.getSubscription();if(sub){await call('push.unsubscribe',{gym_id:gym,endpoint:sub.endpoint},true);await sub.unsubscribe();}setStatus('Notificaciones desactivadas en este dispositivo.');}
 }catch(e){setStatus(e instanceof Error?e.message:'No se pudo cambiar la preferencia.');}finally{setBusy(false);}}
 return <><h3>Notificaciones en tu celular</h3><p className="small">En iPhone, abre la app instalada desde tu pantalla de inicio. Los avisos internos siguen disponibles aunque no actives los push.</p><button disabled={!enabled||!key||!compatible||busy} onClick={()=>void change(true)}>Activar notificaciones</button><button disabled={!enabled||!compatible||busy} onClick={()=>void change(false)}>Desactivar en este dispositivo</button>{(!enabled||!key)&&<p className="small">El envío push todavía no está habilitado en este piloto.</p>}{status&&<p role="status">{status}</p>}</>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><PwaEntry>{(authOnly,screen)=><App authOnly={authOnly} installScreen={screen}/>}</PwaEntry></BrowserRouter></React.StrictMode>);
