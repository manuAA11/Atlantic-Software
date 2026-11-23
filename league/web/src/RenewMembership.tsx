import type {Membership} from './types';
import {renewalWhatsApp} from './renewal-whatsapp.mjs';

export function RenewMembership({member,gymName,disabled=false}:{member:Membership|null;gymName:string;disabled?:boolean}){
 if(!member)return null;
 if(member.renewable===false)return <p>Este plan no requiere renovación.</p>;
 const destination=renewalWhatsApp(member,gymName);
 const label=member.status==='NO_PLAN'?'Consultar planes por WhatsApp':'Renovar membresía';
 return <>
  {destination&&!disabled?<a className="button primary" href={destination.url} target="_blank" rel="noopener noreferrer">{label}</a>:<button className="primary" disabled>{label}</button>}
  {!destination?<p className="small">El gimnasio todavía no ha configurado su contacto de WhatsApp.</p>:destination.kind==='channel'?<p className="small">Abre el canal del gimnasio para consultar la información de renovación.</p>:<p className="small">Se abrirá WhatsApp con un mensaje que tú decides enviar.</p>}
 </>;
}

