// No provider SDK or credentials are bundled with either desktop application.
const encoder = new TextEncoder();
export class IntegrationError extends Error {
  constructor(code, message, status = 400) { super(message); this.code = code; this.status = status; }
}
export async function sha256(value) {
  const bytes = typeof value === 'string' ? encoder.encode(value) : value;
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), b => b.toString(16).padStart(2,'0')).join('');
}
export function constantEqual(a,b) {
  if(typeof a!=='string'||typeof b!=='string'||a.length!==b.length)return false;
  let diff=0;for(let i=0;i<a.length;i++)diff|=a.charCodeAt(i)^b.charCodeAt(i);return diff===0;
}
export async function hmacHex(secret, bytes) {
  const key=await crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',key,typeof bytes==='string'?encoder.encode(bytes):bytes)),b=>b.toString(16).padStart(2,'0')).join('');
}
export async function verifyMeta(raw, header, secret) {
  return !!secret && /^sha256=[a-f0-9]{64}$/i.test(header||'') && constantEqual((header||'').slice(7).toLowerCase(),await hmacHex(secret,raw));
}
function signedProperty(data,path) {
  if(typeof path!=='string'||!path||path.length>120)throw new IntegrationError('INVALID_SIGNATURE','Firma no válida.');
  let value=data;
  for(const key of path.split('.')) {
    if(['__proto__','constructor','prototype'].includes(key)||value===null||typeof value!=='object'||!Object.hasOwn(value,key))throw new IntegrationError('INVALID_SIGNATURE','Firma no válida.');
    value=value[key];
  }
  if(!['string','number','boolean'].includes(typeof value)||!Number.isFinite(typeof value==='number'?value:0))throw new IntegrationError('INVALID_SIGNATURE','Firma no válida.');
  return String(value);
}
export async function verifyWompi(event, header, secret) {
  try {
    const properties=event?.signature?.properties;
    if(!secret||!Array.isArray(properties)||properties.length<1||properties.length>30||!Number.isSafeInteger(event.timestamp))return false;
    const sum=properties.map(path=>signedProperty(event.data,path)).join('')+event.timestamp+secret;
    const expected=await sha256(sum);const signature=header||event.signature.checksum;
    return /^[a-f0-9]{64}$/i.test(signature||'')&&constantEqual(signature.toLowerCase(),expected);
  } catch { return false; }
}
export function normalizePhone(value, country='57') {
  let digits=String(value||'').replace(/\D/g,'');
  if(digits.length===10)digits=country+digits;
  return /^[1-9][0-9]{7,14}$/.test(digits)?digits:null;
}
export function randomToken() {return Array.from(crypto.getRandomValues(new Uint8Array(32)),b=>b.toString(16).padStart(2,'0')).join('');}
export function safeProviderError() {return 'El servicio externo no pudo completar la solicitud. Revisa el estado de la integración.';}
export function cleanText(value,max=4096) {return String(value??'').replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g,'').slice(0,max);}
export function requireUUID(value) {if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[1-8][a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(value||''))throw new IntegrationError('INVALID_GYM','Gimnasio no válido.');return value;}
