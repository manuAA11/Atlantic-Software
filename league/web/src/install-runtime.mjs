import {deviceEnvironment,installDecision} from './install-policy.mjs';
/** Shared observable controller, independent of member sessions and browser storage. */
export function createInstallController(win,nav,doc){
 const media=win.matchMedia('(display-mode: standalone)'),listeners=new Set();
 let promptEvent=null,installedNotice=false,prompting=false,disposed=false,snapshot;
 const read=()=>{
  const environment=deviceEnvironment({userAgent:nav.userAgent,platform:nav.platform,maxTouchPoints:nav.maxTouchPoints,mobileHint:nav.userAgentData?.mobile,displayStandalone:media.matches,standalone:nav.standalone});
  return {environment,mode:installDecision(environment,win.location.href),canPrompt:!!promptEvent,prompting,installedNotice};
 };
 const publish=()=>{if(disposed)return;snapshot=read();for(const listener of listeners)listener();};
 const offered=event=>{event.preventDefault();promptEvent=event;publish();};
 const installed=()=>{promptEvent=null;installedNotice=true;publish();};
 const visible=()=>{if(doc.visibilityState==='visible')publish();};
 win.addEventListener('beforeinstallprompt',offered);win.addEventListener('appinstalled',installed);
 win.addEventListener('pageshow',publish);win.addEventListener('popstate',publish);win.addEventListener('hashchange',publish);
 doc.addEventListener('visibilitychange',visible);
 if(media.addEventListener)media.addEventListener('change',publish);else media.addListener(publish);
 snapshot=read();
 return {
  getSnapshot:()=>snapshot,
  subscribe(listener){listeners.add(listener);return()=>listeners.delete(listener);},
  refresh:publish,
  async install(){
   const event=promptEvent;if(!event||prompting)return 'unavailable';
   // A browser install prompt may only be used once, and only after a user action.
   promptEvent=null;prompting=true;publish();
   try{await event.prompt();const choice=await event.userChoice;if(choice.outcome==='accepted')installedNotice=true;return choice.outcome;}
   catch{return 'unavailable';}finally{prompting=false;publish();}
  },
  dispose(){disposed=true;listeners.clear();win.removeEventListener('beforeinstallprompt',offered);win.removeEventListener('appinstalled',installed);win.removeEventListener('pageshow',publish);win.removeEventListener('popstate',publish);win.removeEventListener('hashchange',publish);doc.removeEventListener('visibilitychange',visible);if(media.removeEventListener)media.removeEventListener('change',publish);else media.removeListener(publish);},
 };
}
