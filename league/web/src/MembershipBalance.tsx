import type {Membership} from './types';

const count=(value:unknown)=>typeof value==='number'&&Number.isSafeInteger(value)&&value>=0?String(value):'—';

export function MembershipBalance({member}:{member:Membership|null}){
 if(member?.entry_limit==null)return null;
 const available=count(member.entries_remaining),used=count(member.entries_used);
 return <>
  <div className="dates" role="group" aria-label="Saldo de tiquetera">
   <div><span>Entradas disponibles</span><strong>{available}</strong></div>
   <div><span>Entradas consumidas</span><strong>{used}</strong></div>
  </div>
  <p>Total del plan: {count(member.entry_limit)} entradas.</p>
  {(available==='—'||used==='—')&&<p>El saldo de entradas aún no está disponible.</p>}
  {member.already_consumed_today===true&&<p>Tu entrada de hoy ya está registrada.</p>}
 </>;
}
