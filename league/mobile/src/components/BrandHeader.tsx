import React from 'react';
import {Image,Pressable,Text,View} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';
import {useAthlete} from '../state/AthleteContext';
import {useUi} from './ui';
export function BrandHeader({onProfile}:{onProfile:()=>void}){
 const {snapshot}=useAthlete(),{color}=useUi(),insets=useSafeAreaInsets();
 const name=snapshot?.profile.alias||'Mi perfil',initials=name.trim().split(/\s+/).slice(0,2).map(part=>part[0]).join('').toUpperCase();
 const gym=snapshot?.links.find(link=>link.status==='APPROVED');
 return <View style={{paddingTop:insets.top+12,paddingBottom:11,paddingHorizontal:20,backgroundColor:color.background,borderBottomWidth:1,borderColor:color.line}}><View style={{maxWidth:600,width:'100%',alignSelf:'center',flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:12}}>
  <View style={{flexDirection:'row',alignItems:'center',gap:9,flex:1}}><Image source={require('../../assets/atlantic-icon.png')} accessibilityLabel="Atlantic League" style={{width:32,height:32,borderRadius:16}}/><View style={{flex:1}}><Text style={{fontSize:11,fontWeight:'700',letterSpacing:1.1,color:color.ink}}>ATLANTIC LEAGUE</Text><Text numberOfLines={1} style={{fontSize:11,lineHeight:17,color:color.muted}}>{gym?.name||'Tu espacio deportivo'}</Text></View></View>
  <Pressable accessibilityRole="button" accessibilityLabel="Abrir mi perfil" onPress={onProfile} style={{width:38,height:38,borderRadius:19,alignItems:'center',justifyContent:'center',backgroundColor:color.soft,borderWidth:1,borderColor:color.line}}><Text style={{fontSize:12,fontWeight:'700',color:color.blue}}>{initials}</Text></Pressable>
 </View></View>;
}
