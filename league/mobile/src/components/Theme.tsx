import React,{createContext,useContext,useEffect,useRef,useState} from 'react';
import {Platform} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import {palettes,type Palette} from '../lib/theme-colors';
export type {Palette} from '../lib/theme-colors';
type Theme={dark:boolean;color:Palette;setDark:(value:boolean)=>Promise<void>};
const Context=createContext<Theme|null>(null),KEY='atlantic-league-appearance';
export function ThemeProvider({children}:{children:React.ReactNode}){
 const [isDark,setIsDark]=useState(()=>{try{return Platform.OS==='web'&&localStorage.getItem(KEY)==='dark';}catch{return false;}}),chosen=useRef(false);
 const color=isDark?palettes.dark:palettes.light;
 useEffect(()=>{let active=true;void AsyncStorage.getItem(KEY).then(value=>{if(active&&!chosen.current)setIsDark(value==='dark');}).catch(()=>{});return()=>{active=false;};},[]);
 useEffect(()=>{
  if(Platform.OS!=='web')return;
  document.documentElement.dataset.leagueTheme=isDark?'dark':'light';
  document.documentElement.style.colorScheme=isDark?'dark':'light';document.body.style.backgroundColor=color.background;
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',color.background);
 },[isDark,color]);
 const setDark=async(value:boolean)=>{chosen.current=true;setIsDark(value);await AsyncStorage.setItem(KEY,value?'dark':'light');};
 return <Context.Provider value={{dark:isDark,color,setDark}}>{children}</Context.Provider>;
}
export function useTheme(){const theme=useContext(Context);if(!theme)throw Error('Missing appearance context');return theme;}
