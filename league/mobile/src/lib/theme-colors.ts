const light={ink:'#192435',muted:'#606F82',blue:'#2766DE',primary:'#2766DE',cyan:'#29BFCF',background:'#F6F8FA',line:'#E5EAF0',surface:'#FFFFFF',surfaceAlt:'#EDF2F8',soft:'#E9F0FF',white:'#FFFFFF',danger:'#B73A4A',dangerSoft:'#FAEAED',green:'#16835E',placeholder:'#68788B'};
const dark:typeof light={ink:'#EDF3FA',muted:'#A4B3C5',blue:'#82B4FF',primary:'#2766DE',cyan:'#55D3DE',background:'#0B1423',line:'#263B53',surface:'#13253B',surfaceAlt:'#1A304A',soft:'#1A3455',white:'#FFFFFF',danger:'#FF9AAA',dangerSoft:'#3A2335',green:'#6CD6AD',placeholder:'#8DA0B7'};
export type Palette=typeof light;

export const palettes={light,dark};
