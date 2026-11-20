import React,{createContext,useContext,useEffect,useRef,useState,useSyncExternalStore} from 'react';
import {useLocation} from 'react-router';
import {createInstallController} from './install-runtime.mjs';
import {essentialAccessFlow} from './install-policy.mjs';
const install=createInstallController(window,navigator,document);
type WorkerState={update:ServiceWorker|null;applyUpdate:()=>void};
const WorkerContext=createContext<WorkerState>({update:null,applyUpdate:()=>{}});
export const usePwaUpdate=()=>useContext(WorkerContext);
function useWorkerRegistration(){
 const [update,setUpdate]=useState<ServiceWorker|null>(null),requested=useRef(false);
 useEffect(()=>{
  if(!('serviceWorker'in navigator))return;
  let live=true,registration:ServiceWorkerRegistration|undefined;
  const changed=()=>{if(requested.current&&!essentialAccessFlow(location.href))location.reload();};
  navigator.serviceWorker.addEventListener('controllerchange',changed);
  const watch=()=>{const worker=registration?.installing;worker?.addEventListener('statechange',()=>{if(live&&worker.state==='installed'&&navigator.serviceWorker.controller)setUpdate(worker);});};
  void navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).then(reg=>{if(!live)return;registration=reg;if(live&&reg.waiting)setUpdate(reg.waiting);reg.addEventListener('updatefound',watch);}).catch(()=>{});
  return()=>{live=false;registration?.removeEventListener('updatefound',watch);navigator.serviceWorker.removeEventListener('controllerchange',changed);};
 },[]);
 return {update,applyUpdate:()=>{if(!essentialAccessFlow(location.href)){requested.current=true;update?.postMessage({type:'ACTIVATE_UPDATE'});}}};
}
export function PwaEntry({children}:{children:(authOnly:boolean,installScreen:React.ReactNode)=>React.ReactNode}){
 const state=useSyncExternalStore(install.subscribe,install.getSnapshot,install.getSnapshot),route=useLocation(),worker=useWorkerRegistration();
 useEffect(()=>install.refresh(),[route.pathname,route.search,route.hash]);
 const welcome=<InstallWelcome/>;
 return <WorkerContext.Provider value={worker}>{state.mode==='install'?welcome:children(state.mode==='auth',welcome)}{!state.environment.mobile&&!state.environment.installed&&state.canPrompt&&<div className="desktop-install"><button disabled={state.prompting} onClick={()=>void install.install()}>Instalar en este equipo</button></div>}</WorkerContext.Provider>;
}
function InstructionIcon({share=false}:{share?:boolean}){return <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">{share?<><path d="M12 15V3m-4 4 4-4 4 4M7 10H4v11h16V10h-3"/></>:<><rect x="5" y="2" width="14" height="20" rx="3"/><path d="M10 18h4m-2-6V6m-3 3 3 3 3-3"/></>}</svg>;}
export function InstallWelcome(){
 const state=useSyncExternalStore(install.subscribe,install.getSnapshot,install.getSnapshot),{environment}=state,{update,applyUpdate}=usePwaUpdate();
 const [notice,setNotice]=useState(''),canonical=location.origin+'/';
 const prompt=async()=>{const outcome=await install.install();setNotice(outcome==='accepted'?'Abre Atlantic League desde el nuevo icono en tu pantalla de inicio.':outcome==='dismissed'?'Puedes instalarla cuando quieras desde el menú de tu navegador.':'Utiliza el menú de tu navegador para añadir la aplicación a tu pantalla de inicio.');};
 const copy=async()=>{try{await navigator.clipboard.writeText(canonical);setNotice('Enlace copiado. Ábrelo en el navegador que prefieras para instalar la aplicación.');}catch{setNotice('Mantén pulsado el enlace que aparece abajo para copiarlo y abrirlo en otro navegador.');}};
 return <main className="install-page">
  <div className="install-brand"><img src="/icons/icon-192.png" alt="Atlantic League" width="64" height="64"/><span>ATLANTIC LEAGUE</span></div>
  <div className="install-intro"><span className="eyebrow">TU GIMNASIO, CONTIGO</span><h1>Instala Atlantic League en tu celular</h1><p>Accede a tu mensualidad, rutinas, eventos y clases directamente desde tu pantalla de inicio.</p></div>
  {environment.embedded&&<section className="card"><h2>Abre el enlace en tu navegador</h2><p>Esta ventana puede tener opciones de instalación limitadas. Busca «Abrir en navegador» en su menú o copia el enlace para abrirlo en un navegador compatible.</p></section>}
  {state.canPrompt&&!environment.embedded&&<button className="primary install-primary" disabled={state.prompting} onClick={()=>void prompt()}><InstructionIcon/> {state.prompting?'Abriendo instalación…':'Instalar aplicación'}</button>}
  {state.installedNotice&&<p className="success" role="status">Ahora abre Atlantic League desde el nuevo icono de tu pantalla de inicio.</p>}
  <section className="card install-steps" aria-label="Instrucciones de instalación">
   <h2>{environment.os==='ios'?'En iPhone o iPad':environment.os==='android'?'En tu dispositivo Android':'En tu celular'}</h2>
   <ol>{environment.os==='ios'?<>
    <li><InstructionIcon share/><div><strong>Abre el menú Compartir</strong><p>Busca «Compartir» entre las opciones de tu navegador.</p></div></li>
    <li><InstructionIcon/><div><strong>Selecciona «Añadir a pantalla de inicio»</strong><p>Activa «Abrir como app» si aparece esa opción y confirma «Añadir».</p></div></li>
   </>:<>
    <li><InstructionIcon/><div><strong>Abre el menú de tu navegador</strong><p>La ubicación y las opciones del menú pueden variar según el navegador.</p></div></li>
    <li><InstructionIcon/><div><strong>Selecciona «Instalar aplicación» o «Añadir a pantalla de inicio»</strong><p>Usa la opción disponible en tu navegador y confirma la instalación.</p></div></li>
   </>}<li><InstructionIcon/><div><strong>Abre Atlantic League desde el nuevo icono</strong><p>Desde allí podrás iniciar sesión y entrar a tu gimnasio.</p></div></li></ol>
  </section>
  <details className="card install-help"><summary>¿No aparece la opción o el icono abre el navegador?</summary><p>Algunos navegadores crean un acceso directo que sigue abriéndose como una página web. Vuelve a añadir Atlantic League desde un navegador que permita instalar aplicaciones y activa «Abrir como app» si aparece.</p>{environment.os==='ios'?<p>Si no encuentras «Añadir a pantalla de inicio», abre el enlace en Safari u otro navegador de iOS que ofrezca esa opción.</p>:<p>En Android, prueba con Chrome u otro navegador compatible. Si no aparece un botón de instalación, revisa las opciones de su menú.</p>}<button onClick={()=>void copy()}>Copiar enlace</button><a href={canonical}>{canonical}</a><p>Después, abre la aplicación desde el icono instalado. Volver a esta pestaña seguirá mostrando estas instrucciones.</p></details>
  {notice&&<p role="status" className="install-notice">{notice}</p>}
  {update&&<div className="banner">Hay una nueva versión disponible.<button disabled={essentialAccessFlow(location.href)} onClick={applyUpdate}>Actualizar</button></div>}
  <p className="copyright">© Atlantic Tech Software · Tu gimnasio, contigo</p>
 </main>;
}
