import React,{useEffect,useState} from 'react';
import {call} from './api';
type ProfileData={name:string;phone:string|null;email:string|null;document_hint:string;attendance:string[]};
export function MemberProfile({gym,gymName}:{gym:string;gymName:string}){
 const [data,setData]=useState<ProfileData|null>(null),[error,setError]=useState('');
 useEffect(()=>{let current=true;setData(null);setError('');if(gym)void call<ProfileData>('gym.profile',{gym_id:gym}).then(v=>{if(current)setData(v);}).catch(e=>{if(current)setError(e.message);});return()=>{current=false;};},[gym]);
 return <>{error&&<p role="alert">{error}</p>}{data&&<><section className="card"><h2>{data.name}</h2><p>{gymName}</p><p>Cédula terminada en {data.document_hint}</p>{data.phone&&<p>{data.phone}</p>}{data.email&&<p>{data.email}</p>}<p>Solicita los cambios en tus datos personales al gimnasio.</p></section><section className="card"><h2>Mis asistencias</h2>{data.attendance.length?data.attendance.map(d=><p key={d}>{new Intl.DateTimeFormat('es-CO',{timeZone:'UTC',day:'numeric',month:'long',year:'numeric'}).format(new Date(d+'T12:00:00Z'))}</p>):<p>Tus próximas asistencias registradas aparecerán aquí.</p>}</section></>}</>;
}
