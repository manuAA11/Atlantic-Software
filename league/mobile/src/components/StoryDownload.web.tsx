import React from 'react';
export function StoryDownload({url,color,background,line}:{url:string;color:string;background:string;line:string}){
 const style:React.CSSProperties={display:'flex',justifyContent:'center',alignItems:'center',minHeight:46,borderRadius:12,border:'1px solid '+line,background,color,fontFamily:'inherit',fontSize:14,fontWeight:600,textDecoration:'none',padding:'8px 12px',boxSizing:'border-box'};
 return <div style={{display:'grid',gap:8}}><a style={style} href={url} download="Atlantic-League.png">Descargar PNG</a><a style={style} href={url} target="_blank" rel="noopener noreferrer">Abrir imagen</a></div>;
}
