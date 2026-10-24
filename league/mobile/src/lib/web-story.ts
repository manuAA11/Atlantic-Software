import type {StoryExport} from './story-export';
import type {StoryOptions} from './story-style';
export async function pickWebPhoto(_camera:boolean):Promise<string|null>{return null;}
export async function exportWebStory(_photo:string,_lines:string[],_share:boolean,_options?:StoryOptions):Promise<StoryExport>{return {shared:false};}
