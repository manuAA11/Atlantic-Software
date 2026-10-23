import React from 'react';
import {ActivityIndicator,Pressable,ScrollView,StyleSheet,Text,TextInput,View,type TextInputProps,type ViewStyle} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';
import {Ionicons} from '@expo/vector-icons';
export const color={ink:'#14283E',muted:'#66788A',blue:'#087CBF',cyan:'#29BFCF',background:'#F5F8FB',line:'#E1E9F0',white:'#FFFFFF',danger:'#B73A4A',green:'#227D62'};
export function Screen({children,refreshing,onRefresh}:{children:React.ReactNode;refreshing?:boolean;onRefresh?:()=>void}){
 const insets=useSafeAreaInsets();
 return <ScrollView style={{flex:1,backgroundColor:color.background}} contentContainerStyle={{padding:22,paddingTop:Math.max(insets.top,18)+12,paddingBottom:32,gap:18,maxWidth:640,width:'100%',alignSelf:'center'}} keyboardShouldPersistTaps="handled">
  {children}{onRefresh&&<Button label={refreshing?'Actualizando…':'Actualizar'} icon="refresh-outline" kind="quiet" disabled={refreshing} onPress={onRefresh}/>}
 </ScrollView>;
}
export const Heading=({eyebrow,title,detail}:{eyebrow?:string;title:string;detail?:string})=><View style={{gap:7}}>{eyebrow&&<Text style={s.eyebrow}>{eyebrow.toUpperCase()}</Text>}<Text accessibilityRole="header" style={s.title}>{title}</Text>{detail&&<Text style={s.body}>{detail}</Text>}</View>;
export const Card=({children,style}:{children:React.ReactNode;style?:ViewStyle})=><View style={[s.card,style]}>{children}</View>;
export const Label=({children,muted=false}:{children:React.ReactNode;muted?:boolean})=><Text style={muted?s.body:s.label}>{children}</Text>;
export const Row=({children}:{children:React.ReactNode})=><View style={s.row}>{children}</View>;
export function Button({label,onPress,disabled=false,busy=false,kind='primary',icon}:{label:string;onPress:()=>void;disabled?:boolean;busy?:boolean;kind?:'primary'|'quiet'|'danger';icon?:React.ComponentProps<typeof Ionicons>['name']}){
 return <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{disabled:disabled||busy,busy}} disabled={disabled||busy} onPress={onPress} style={({pressed})=>[s.button,{backgroundColor:kind==='primary'?color.blue:kind==='danger'?'#FAEAED':color.white,opacity:(disabled||busy)?0.5:pressed?0.8:1,borderWidth:kind==='quiet'?1:0,borderColor:color.line}]}>
  {busy?<ActivityIndicator color={kind==='primary'?color.white:color.blue}/>:icon&&<Ionicons name={icon} size={19} color={kind==='primary'?color.white:color.blue}/>}
  <Text style={{fontSize:15,fontWeight:'600',color:kind==='primary'?color.white:kind==='danger'?color.danger:color.ink}}>{label}</Text>
 </Pressable>;
}
export function Field({label,...props}:TextInputProps&{label:string}){return <View style={{gap:7}}><Text style={s.fieldLabel}>{label}</Text><TextInput accessibilityLabel={label} placeholderTextColor="#91A0AE" {...props} style={[s.input,props.style]}/></View>;}
export function Chips<T extends string>({items,value,onChange}:{items:{value:T;label:string}[];value:T;onChange:(value:T)=>void}){
 return <View style={{flexDirection:'row',flexWrap:'wrap',gap:8}}>{items.map(item=><Pressable accessibilityRole="button" accessibilityState={{selected:item.value===value}} key={item.value} onPress={()=>onChange(item.value)} style={[s.chip,item.value===value&&{backgroundColor:color.ink,borderColor:color.ink}]}><Text style={{fontSize:13,color:item.value===value?color.white:color.ink,fontWeight:'500'}}>{item.label}</Text></Pressable>)}</View>;
}
export function Empty({title,detail}:{title:string;detail:string}){return <Card><Ionicons name="leaf-outline" size={26} color={color.blue}/><Text style={s.label}>{title}</Text><Text style={s.body}>{detail}</Text></Card>;}
export const dateText=(value:string)=>new Date(value).toLocaleDateString('es-CO',{month:'short',day:'numeric'});
export const s=StyleSheet.create({
 title:{fontSize:31,lineHeight:37,fontWeight:'700',letterSpacing:-.8,color:color.ink},
 eyebrow:{fontSize:11,fontWeight:'700',letterSpacing:2,color:color.blue},
 body:{fontSize:14,lineHeight:21,color:color.muted},label:{fontSize:17,fontWeight:'600',color:color.ink},
 card:{padding:20,borderRadius:22,backgroundColor:color.white,gap:12,borderWidth:1,borderColor:'#EAF0F5'},
 row:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:12},
 button:{minHeight:48,paddingHorizontal:16,paddingVertical:12,borderRadius:15,flexDirection:'row',justifyContent:'center',alignItems:'center',gap:9},
 input:{minHeight:48,borderWidth:1,borderColor:color.line,borderRadius:13,padding:13,fontSize:16,color:color.ink,backgroundColor:color.white},
 fieldLabel:{fontSize:13,fontWeight:'600',color:color.ink},chip:{borderRadius:99,paddingVertical:9,paddingHorizontal:13,borderWidth:1,borderColor:color.line,backgroundColor:color.white},
 metric:{fontSize:29,fontWeight:'700',letterSpacing:-.8,color:color.ink},divider:{height:1,backgroundColor:color.line},
});
