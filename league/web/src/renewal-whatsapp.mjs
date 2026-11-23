/** Build an official WhatsApp link without sending a message or changing membership. */
export function renewalWhatsApp(member,gymName=''){
 const configured=member?.renewal_whatsapp_url;
 if(typeof configured!=='string'||configured.length>512)return null;
 let url;try{url=new URL(configured.trim());}catch{return null;}
 if(url.protocol!=='https:'||url.username||url.password||url.port||url.search||url.hash)return null;
 const path=url.pathname.replace(/\/$/,'');
 if((url.hostname==='whatsapp.com'||url.hostname==='www.whatsapp.com')&&/^\/channel\/[A-Za-z0-9_-]{8,128}$/.test(path)){
  return {url:'https://whatsapp.com'+path,kind:'channel'};
 }
 if(url.hostname!=='wa.me'||!/^\/[1-9][0-9]{6,14}$/.test(path))return null;
 const gym=String(gymName||'el gimnasio').slice(0,150),plan=String(member?.plan_name||'').trim().slice(0,150);
 const message=member?.status==='NO_PLAN'
  ? 'Hola, quiero información sobre los planes de '+gym+'.'
  : 'Hola, quiero renovar mi '+(member?.entry_limit!=null?'tiquetera':'mensualidad')+(plan?' del plan '+plan:'')+' en '+gym+'.';
 const target=new URL('https://wa.me'+path);target.searchParams.set('text',message);
 return {url:target.href,kind:'chat'};
}

