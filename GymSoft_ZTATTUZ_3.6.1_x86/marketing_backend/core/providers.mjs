import {IntegrationError,sha256,constantEqual} from './security.mjs';
export const GRAPH_VERSION='v26.0';
export const WOMPI_BASE={test:'https://sandbox.wompi.co/v1',prod:'https://production.wompi.co/v1'};
// Deliberately never logs request headers, payloads, API keys or provider responses.
export async function providerJSON(url,options={},fetcher=fetch) {
  let response;
  try {response=await fetcher(url,{...options,signal:options.signal??AbortSignal.timeout(12000)});}
  catch {throw new IntegrationError('PROVIDER_UNCERTAIN','No se pudo confirmar la respuesta del proveedor.',503);}
  let data;try{data=await response.json();}catch{throw new IntegrationError('PROVIDER_UNCERTAIN','El proveedor devolvió una respuesta incompleta.',502);}
  if(!response.ok)throw new IntegrationError(response.status===429?'PROVIDER_RATE_LIMIT':'PROVIDER_REJECTED','El proveedor rechazó la solicitud.',response.status===429?429:502);
  return data;
}
export function wompiMode(keys) {
  const mode=keys.public_key?.startsWith('pub_test_')?'test':keys.public_key?.startsWith('pub_prod_')?'prod':null;
  if(!mode||!keys.private_key?.startsWith('prv_'+mode+'_')||!keys.events_secret?.startsWith(mode+'_events_')||!keys.integrity_secret?.startsWith(mode+'_integrity_'))throw new IntegrationError('WOMPI_KEYS','Revisa las cuatro credenciales y utiliza el mismo ambiente en todas.');
  return mode;
}
export async function validateWompi(keys,fetcher=fetch) {
  const mode=wompiMode(keys);
  const merchant=await providerJSON(`${WOMPI_BASE[mode]}/merchants/${encodeURIComponent(keys.public_key)}`,{},fetcher);
  // The published API does not document a credential-inspection endpoint.
  // The private/events/integrity keys are verified by a signed sandbox payment,
  // never by an invented endpoint or a charge made without user confirmation.
  return {mode,merchant_name:merchant.data?.name||merchant.data?.legal_name||'',private_key_verified:false,events_verified:false,integrity_verified:false};
}
export async function checkoutURL(request,keys) {
  const mode=wompiMode(keys);if(mode!==request.mode)throw new IntegrationError('WRONG_MODE','El ambiente del pago no coincide.');
  const expiration=new Date(request.expires_at).toISOString();
  const signature=await sha256(request.reference+String(request.amount_in_cents)+request.currency+expiration+keys.integrity_secret);
  const params=new URLSearchParams({'public-key':keys.public_key,currency:request.currency,'amount-in-cents':String(request.amount_in_cents),reference:request.reference,'signature:integrity':signature,'expiration-time':expiration});
  return 'https://checkout.wompi.co/p/?'+params;
}
export async function canonicalTransaction(id,keys,fetcher=fetch) {
  if(typeof id!=='string'||!/^[a-zA-Z0-9_-]{1,150}$/.test(id))throw new IntegrationError('INVALID_TRANSACTION','Transacción no válida.');
  const mode=wompiMode(keys);
  const result=await providerJSON(`${WOMPI_BASE[mode]}/transactions/${encodeURIComponent(id)}`,{headers:{Authorization:`Bearer ${keys.private_key}`}},fetcher);
  if(result.data?.id!==id)throw new IntegrationError('INVALID_TRANSACTION','No se pudo verificar la transacción.');
  return {...result.data,mode};
}
export async function metaRequest(path,token,{method='GET',body,fetcher=fetch}={}) {
  if(!/^\/?[a-zA-Z0-9_/?=&.,%-]+$/.test(path))throw new IntegrationError('INVALID_META_PATH','Solicitud no válida.');
  return providerJSON(`https://graph.facebook.com/${GRAPH_VERSION}/${path.replace(/^\//,'')}`,{method,headers:{Authorization:`Bearer ${token}`,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})},fetcher);
}
export async function sendTemplate(connection,secret,message,fetcher=fetch) {
  const parameters=(message.template_parameters||[]).map(text=>({type:'text',text:String(text)}));
  const body={messaging_product:'whatsapp',recipient_type:'individual',to:message.phone,type:'template',template:{name:message.template_name,language:{code:message.language_code},...(parameters.length?{components:[{type:'body',parameters}]}:{})}};
  return metaRequest(`${connection.phone_number_id}/messages`,secret.access_token,{method:'POST',body,fetcher});
}
export async function sendSessionMessage(connection,secret,to,content,lastInbound,now=Date.now(),fetcher=fetch) {
  if(!lastInbound||now-new Date(lastInbound).getTime()>=86400000)throw new IntegrationError('WINDOW_CLOSED','Se necesita una plantilla aprobada para volver a contactar al cliente.');
  return metaRequest(`${connection.phone_number_id}/messages`,secret.access_token,{method:'POST',body:{messaging_product:'whatsapp',to,...content},fetcher});
}
export function templateComponents(body,variables,samples) {
  let text=body;variables.forEach((name,i)=>{text=text.replaceAll('{{'+name+'}}','{{'+(i+1)+'}}');});
  return [{type:'BODY',text,...(variables.length?{example:{body_text:[variables.map(v=>String(samples[v]||'Ejemplo'))]}}:{})}];
}
