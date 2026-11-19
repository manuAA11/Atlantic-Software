export type GymLink={gym_id:string;name:string;status:'APPROVED'|'REVOKED'};
export type Snapshot={profile:{id:string;alias:string};links:GymLink[]};
export type GymEvent={kind?:string;status?:string;reservation_status?:string;location?:string;image_url?:string;id:string;name:string;starts_at:string;capacity:number;description:string;trainer:string|null;reserved:number;mine:boolean;duration_minutes?:number|null;conditions?:string;requires_membership?:boolean|null;timezone?:string|null};
