export type Exercise={id:string;name:string;muscle:string;equipment:string;instructions:string;gym_id?:string|null;owner_id?:string|null};
export type SetEntry={exercise_id:string;weight_kg:number;reps:number};
export type WorkoutPayload={id:string;name:string;started_at:string;sets:SetEntry[];draft_id?:string};
export type SavedWorkout={id:string;name:string;finished_at:string;sets:SetEntry[];routine_snapshot?:unknown};
export type GymLink={gym_id:string;name:string;status:'APPROVED'|'REVOKED'};
export type StrengthRecord={id:string;exercise_name:string;weight_kg:number;reps:number;status:string;created_at:string};
export type Snapshot={profile:{id:string;alias:string;leaderboard_opt_in:boolean;weekly_goal?:number};xp:number;official_xp:number;weekly_days?:number;workouts:SavedWorkout[];links:GymLink[];requests:{gym_id:string;status:string}[];records:StrengthRecord[]};
export type PlanExercise={id:string;catalog_id:string|null;name:string;day:string;sets:string;reps:string;weight_kg:string;rest_seconds:number|null};
export type Routine={id:string;name:string;goal:string;notes?:string;exercises:PlanExercise[]};
export type GymEvent={id:string;name:string;starts_at:string;capacity:number;description:string;trainer:string|null;reserved:number;mine:boolean};
export type Rank={alias:string;score:number};
export const xpRank=(xp:number)=>xp>=5000?'Élite':xp>=2000?'Avanzado':xp>=750?'Constante':xp>=200?'En marcha':'Inicio';
export const nextXp=(xp:number)=>[200,750,2000,5000].find(n=>n>xp)||null;
export const strengthRank=(records:StrengthRecord[])=>{
 return records.some(r=>r.status==='APPROVED')?'Marca verificada':'Por verificar';
};
export const workoutVolume=(workout:Pick<SavedWorkout,'sets'>)=>workout.sets.reduce((total,s)=>total+Number(s.weight_kg)*s.reps,0);
export function currentStreak(workouts:SavedWorkout[],now=new Date()){
 const day=(d:Date)=>d.toISOString().slice(0,10),days=new Set(workouts.map(w=>day(new Date(w.finished_at))));
 const cursor=new Date(Date.UTC(now.getUTCFullYear(),now.getUTCMonth(),now.getUTCDate()));
 if(!days.has(day(cursor)))cursor.setUTCDate(cursor.getUTCDate()-1);
 let total=0;while(days.has(day(cursor))){total++;cursor.setUTCDate(cursor.getUTCDate()-1);}return total;
}
