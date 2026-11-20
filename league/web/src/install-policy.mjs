/** Installation is a UX decision only. Every member API still requires authentication. */
export function deviceEnvironment({userAgent='',platform='',maxTouchPoints=0,mobileHint=false,displayStandalone=false,standalone=false}={}){
 const ios=/iPad|iPhone|iPod/i.test(userAgent)||(platform==='MacIntel'&&maxTouchPoints>1);
 const android=/Android/i.test(userAgent);
 const embedded=/FBAN|FBAV|Instagram|Line\/|MicroMessenger|TikTok|; wv\)/i.test(userAgent);
 const browser=ios?(/CriOS/i.test(userAgent)?'chrome':/FxiOS/i.test(userAgent)?'firefox':/EdgiOS/i.test(userAgent)?'edge':/Safari/i.test(userAgent)?'safari':'other'):
  /SamsungBrowser/i.test(userAgent)?'samsung':/EdgA|Edg\//i.test(userAgent)?'edge':/Firefox/i.test(userAgent)?'firefox':/Chrome|Chromium/i.test(userAgent)?'chrome':'other';
 return {os:ios?'ios':android?'android':'other',mobile:ios||android||mobileHint||/Mobi|Mobile|Windows Phone/i.test(userAgent),installed:displayStandalone||standalone===true,embedded,browser};
}
export function essentialAccessFlow(href){
 try{
  const u=new URL(href,'https://league.invalid'),hash=new URLSearchParams(u.hash.replace(/^#/,''));
  if(u.hash.startsWith('#/')&&essentialAccessFlow(new URL(u.hash.slice(1),'https://league.invalid').href))return true;
  if(/^\/(?:auth(?:\/|$)|callback(?:\/|$)|recover(?:y)?(?:\/|$)|reset(?:-password)?(?:\/|$)|activate(?:\/|$)|invite(?:\/|$)|invitacion(?:\/|$)|confirm(?:\/|$))/i.test(u.pathname))return true;
  for(const p of [u.searchParams,hash]){
   if(['code','token','token_hash','access_token','refresh_token','error','error_code','error_description'].some(k=>p.has(k)))return true;
   if(['recovery','invite','signup','magiclink','email_change'].includes(p.get('type')||''))return true;
  }
  return false;
 }catch{return false;}
}
export function installDecision(environment,href){
 if(!environment.mobile||environment.installed)return 'app';
 return essentialAccessFlow(href)?'auth':'install';
}
