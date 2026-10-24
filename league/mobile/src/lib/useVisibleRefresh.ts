import {useCallback} from 'react';
import {AppState} from 'react-native';
import {useFocusEffect} from '@react-navigation/native';

// Poll only the visible screen. A stopped cycle cannot apply an old gym response.
export function useVisibleRefresh(load:(isCurrent:()=>boolean)=>Promise<void>){
 useFocusEffect(useCallback(()=>{
  let active=true,version=0;
  const refresh=()=>{const request=++version;void load(()=>active&&request===version);};
  refresh();
  const timer=setInterval(()=>{if(AppState.currentState==='active')refresh();},30000);
  const subscription=AppState.addEventListener('change',state=>{if(state==='active')refresh();});
  return()=>{active=false;clearInterval(timer);subscription.remove();};
 },[load]));
}
