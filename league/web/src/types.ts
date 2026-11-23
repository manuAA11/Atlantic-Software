import type {GymEvent, Snapshot} from './legacy-domain';
export type {GymEvent, Snapshot};
export type Membership={active:boolean;frozen:boolean;ends_at?:string|null;starts_at?:string|null;plan_name?:string|null;status?:string;remaining_days?:number|null;renewable?:boolean;renewal_whatsapp_url?:string|null;has_expiration?:boolean;entry_limit?:number|null;entries_used?:number|null;entries_remaining?:number|null;already_consumed_today?:boolean};
export type Renewal={id:string;status:'PENDING'|'REVIEW'|'APPROVED'|'REJECTED'|'CANCELLED';created_at:string;period_key:string};
export type Notice={id:string;title:string;body:string;target:'/'|'/agenda'|'/rutinas'|'/perfil';created_at:string;read_at:string|null};
export const renewalLabels={PENDING:'Pendiente',REVIEW:'En revisión',APPROVED:'Aprobada',REJECTED:'Rechazada',CANCELLED:'Cancelada'};
