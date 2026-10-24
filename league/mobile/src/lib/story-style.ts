export type StoryStyle='white'|'dark'|'card';
export type StoryOptions={style:StoryStyle;gym?:string;xp?:number};
export const storyStyle=(style:StoryStyle)=>({ink:style==='white'?'#FFFFFF':'#192435',muted:style==='white'?'#E3EAF1':'#526278',card:style==='card'});
