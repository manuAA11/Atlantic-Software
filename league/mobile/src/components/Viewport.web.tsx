import {useEffect} from 'react';

export function Viewport(){
 useEffect(()=>{
  const viewport=window.visualViewport;
  const update=()=>{
   // Keep the app above browser chrome and the keyboard. Preserve pinch zoom.
   if(viewport&&Math.abs(viewport.scale-1)>.01)return;
   const height=viewport?.height||window.innerHeight;
   document.documentElement.style.setProperty('--league-viewport-height',`${Math.round(height)}px`);
  };
  update();viewport?.addEventListener('resize',update);window.addEventListener('resize',update);
  return()=>{viewport?.removeEventListener('resize',update);window.removeEventListener('resize',update);document.documentElement.style.removeProperty('--league-viewport-height');};
 },[]);
 return null;
}
