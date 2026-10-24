import React from 'react';
import type {IconName,IconProps} from './Icon.types';
export type {IconName,IconProps} from './Icon.types';

// Inline paths keep PWA navigation independent of font downloads and font caches.
const paths:Record<IconName,React.ReactNode>={
 'calendar-outline':<><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4m10-4v4M3 10h18"/></>,
 'trophy-outline':<><path d="M8 21h8m-4-4v4M7 3h10v8a5 5 0 0 1-10 0ZM7 5H4v3a4 4 0 0 0 3 4m10-7h3v3a4 4 0 0 1-3 4"/></>,
 'home-outline':<><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/></>,
 'barbell-outline':<><path d="M7 12h10M2 10v4m20-4v4M5 7v10m14-10v10"/><rect x="5" y="8" width="3" height="8" rx=".7"/><rect x="16" y="8" width="3" height="8" rx=".7"/></>,
 'business-outline':<><rect x="4" y="3" width="11" height="18" rx="1"/><path d="M15 9h5v12H3m5-14h3m-3 4h3m-3 4h3m-1 6v-3m8-5h.01M18 17h.01"/></>,
 'podium-outline':<><path d="M3 21V11h6v10m0 0V4h6v17m0 0v-7h6v7M2 21h20"/></>,
 'person-circle-outline':<><circle cx="12" cy="12" r="9"/><circle cx="12" cy="9" r="3"/><path d="M5 18c1-5 13-5 14 0"/></>,
 'refresh-outline':<><path d="M20 8a8 8 0 1 0 .2 7M20 3v5h-5"/></>,
 'play-circle-outline':<><circle cx="12" cy="12" r="9"/><path d="m10 8 6 4-6 4Z"/></>,
 'add-circle-outline':<><circle cx="12" cy="12" r="9"/><path d="M8 12h8m-4-4v8"/></>,
 'add-outline':<path d="M5 12h14m-7-7v14"/>,
 'camera-outline':<><path d="M3 7h4l2-3h6l2 3h4v13H3Z"/><circle cx="12" cy="13" r="4"/></>,
 'images-outline':<><rect x="6" y="3" width="15" height="15" rx="2"/><path d="M3 7v13a1 1 0 0 0 1 1h13m-11-5 4-4 3 3 3-4 5 6"/><circle cx="16" cy="7" r="1"/></>,
 'share-outline':<><path d="M8 9H4v12h16V9h-4m-4 6V3m-4 4 4-4 4 4"/></>,
 'leaf-outline':<><path d="M20 3c1 11-4 17-11 14C3 15 3 8 3 4c4 3 11 0 17-1ZM7 9l12 12"/></>,
};
export function Icon({name,size=22,color='currentColor'}:IconProps){
 return <svg data-league-icon={name} aria-hidden="true" focusable="false" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{display:'block',flexShrink:0}}>{paths[name]}</svg>;
}
