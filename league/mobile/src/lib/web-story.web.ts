import type {StoryExport} from './story-export';
import {storyStyle,type StoryOptions} from './story-style';
export async function pickWebPhoto(camera:boolean):Promise<string|null>{
 return new Promise((resolve,reject)=>{const input=document.createElement('input');input.type='file';input.accept='image/*';if(camera)input.setAttribute('capture','environment');input.oncancel=()=>resolve(null);input.onchange=()=>{const file=input.files?.[0];if(!file){resolve(null);return;}if(!file.type.startsWith('image/')||file.size>25*1024*1024){reject(Error('Elige una foto de menos de 25 MB.'));return;}const reader=new FileReader();reader.onload=()=>resolve(String(reader.result));reader.onerror=()=>reject(Error('No se pudo leer la foto.'));reader.readAsDataURL(file);};input.click();});
}
export async function exportWebStory(photo:string,lines:string[],share:boolean,options:StoryOptions={style:'white'}):Promise<StoryExport>{
 const image=await new Promise<HTMLImageElement>((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(Error('No se pudo leer la foto.'));img.src=photo;});
 const canvas=document.createElement('canvas');canvas.width=1080;canvas.height=1920;const ctx=canvas.getContext('2d');if(!ctx)throw Error('No se pudo crear la imagen en este navegador.');
 const ratio=Math.max(1080/image.width,1920/image.height),w=image.width*ratio,h=image.height*ratio;ctx.drawImage(image,(1080-w)/2,(1920-h)/2,w,h);
 const theme=storyStyle(options.style),x=options.style==='card'?114:78,maxWidth=options.style==='card'?852:924;
 if(theme.card){ctx.fillStyle='rgba(255,255,255,.94)';ctx.beginPath();ctx.roundRect(60,1440,960,408,30);ctx.fill();}
 else{const gradient=ctx.createLinearGradient(0,1350,0,1920);gradient.addColorStop(0,options.style==='white'?'rgba(0,0,0,0)':'rgba(255,255,255,0)');gradient.addColorStop(1,options.style==='white'?'rgba(0,0,0,.64)':'rgba(255,255,255,.84)');ctx.fillStyle=gradient;ctx.fillRect(0,1350,1080,570);}
 const text=(value:string,size:number,y:number,color=theme.ink,bold=false)=>{ctx.font=`${bold?'650':'500'} ${size}px system-ui, sans-serif`;let shown=value;while(ctx.measureText(shown).width>maxWidth&&shown.length>1)shown=shown.slice(0,-2)+'…';ctx.fillStyle=color;ctx.fillText(shown,x,y);};
 text((lines[0]||'').toUpperCase(),26,1508,theme.muted);
 text(lines[1]||'',46,1576,theme.ink,true);text(lines[2]||'',68,1660,theme.ink,true);text(lines[3]||'',31,1714,theme.muted);
 const extra=[options.gym,options.xp!==undefined?options.xp.toLocaleString('es-CO')+' XP personales':null].filter(Boolean).join(' · ');
 if(extra)text(extra,28,1766,theme.muted);
 text((lines[4]||'')+' · ATLANTIC LEAGUE',23,1810,theme.muted);
 const blob=await new Promise<Blob>((resolve,reject)=>canvas.toBlob(value=>value?resolve(value):reject(Error('No se pudo generar la historia.')),'image/png'));
 const file=new File([blob],'Atlantic-League.png',{type:'image/png'});
 if(share&&navigator.canShare?.({files:[file]})){try{await navigator.share({files:[file],title:'Mi progreso en Atlantic League'});return {shared:true};}catch(error){if(error instanceof DOMException&&error.name==='AbortError')return {shared:false,cancelled:true};}}
 const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=file.name;document.body.append(link);link.click();link.remove();return {shared:false,url};
}
