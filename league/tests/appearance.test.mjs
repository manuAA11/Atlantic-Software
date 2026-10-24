import {test} from 'node:test';
import assert from 'node:assert/strict';
import {palettes} from '../mobile/src/lib/theme-colors.ts';
const luminance=hex=>{
 const values=[1,3,5].map(i=>parseInt(hex.slice(i,i+2),16)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);
 return values[0]*.2126+values[1]*.7152+values[2]*.0722;
};
const contrast=(a,b)=>{const x=luminance(a),y=luminance(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05);};
test('light and dark themes preserve readable body text, active controls and primary actions',()=>{
 for(const [name,p] of Object.entries(palettes)){
  for(const background of [p.background,p.surface]){
   assert.ok(contrast(p.ink,background)>=7,name+' primary text');
   assert.ok(contrast(p.muted,background)>=4.5,name+' body text');
   assert.ok(contrast(p.blue,background)>=4.5,name+' active controls');
  }
  assert.ok(contrast(p.white,p.primary)>=4.5,name+' primary action');
 }
 assert.notEqual(palettes.light.background,palettes.dark.background);
});
