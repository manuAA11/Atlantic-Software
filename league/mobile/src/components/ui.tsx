import React,{useMemo} from 'react';
import {ActivityIndicator,Pressable,ScrollView,StyleSheet,Text,TextInput,View,type TextInputProps,type ViewStyle} from 'react-native';
import {useSafeAreaInsets} from 'react-native-safe-area-context';
import {Icon,type IconName} from './Icon';
import {useTheme,type Palette} from './Theme';
export function useUi(){const theme=useTheme();const s=useMemo(()=>styles(theme.color),[theme.color]);return {...theme,s};}
export function Screen({children,refreshing,onRefresh,insetTop=false}:{children:React.ReactNode;refreshing?:boolean;onRefresh?:()=>void;insetTop?:boolean}){
 const insets=useSafeAreaInsets(),{color}=useUi();
 return <ScrollView style={{flex:1,minHeight:0,backgroundColor:color.background}} contentContainerStyle={{padding:20,paddingTop:insetTop?Math.max(insets.top+16,28):18,paddingBottom:28,gap:16,maxWidth:640,width:'100%',alignSelf:'center'}} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled" keyboardDismissMode="on-drag">
  {children}{onRefresh&&<Button label={refreshing?'Actualizando…':'Actualizar'} icon="refresh-outline" kind="quiet" disabled={refreshing} onPress={onRefresh}/>}
 </ScrollView>;
}
export function Heading({eyebrow,title,detail}:{eyebrow?:string;title:string;detail?:string}){const {s}=useUi();return <View style={{gap:6}}>{eyebrow&&<Text style={s.eyebrow}>{eyebrow.toUpperCase()}</Text>}<Text accessibilityRole="header" style={s.title}>{title}</Text>{detail&&<Text style={s.body}>{detail}</Text>}</View>;}
export function Card({children,style}:{children:React.ReactNode;style?:ViewStyle}){const {s}=useUi();return <View style={[s.card,style]}>{children}</View>;}
export function Label({children,muted=false}:{children:React.ReactNode;muted?:boolean}){const {s}=useUi();return <Text style={muted?s.body:s.label}>{children}</Text>;}
export function Row({children}:{children:React.ReactNode}){const {s}=useUi();return <View style={s.row}>{children}</View>;}
export function Button({label,onPress,disabled=false,busy=false,kind='primary',icon}:{label:string;onPress:()=>void;disabled?:boolean;busy?:boolean;kind?:'primary'|'quiet'|'danger';icon?:IconName}){
 const {color,s}=useUi();
 return <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{disabled:disabled||busy,busy}} disabled={disabled||busy} onPress={onPress} style={({pressed})=>[s.button,{backgroundColor:kind==='primary'?color.primary:kind==='danger'?color.dangerSoft:color.surface,opacity:(disabled||busy)?0.5:pressed?0.8:1,borderWidth:kind==='quiet'?1:0,borderColor:color.line}]}>
  {busy?<ActivityIndicator color={kind==='primary'?color.white:color.blue}/>:icon&&<Icon name={icon} size={19} color={kind==='primary'?color.white:color.blue}/>}
  <Text style={{fontSize:14,lineHeight:20,fontWeight:'600',flexShrink:1,textAlign:'center',color:kind==='primary'?color.white:kind==='danger'?color.danger:color.ink}}>{label}</Text>
 </Pressable>;
}
export function ActionTile({label,icon,onPress}:{label:string;icon:IconName;onPress:()=>void}){const {color,s}=useUi();return <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} style={({pressed})=>[s.card,{flex:1,minWidth:110,gap:12,opacity:pressed?.75:1}]}><Icon name={icon} color={color.blue} size={21}/><Text style={{fontSize:13,lineHeight:18,fontWeight:'600',color:color.ink}}>{label}</Text></Pressable>;}
export function Field({label,...props}:TextInputProps&{label:string}){const {s,color}=useUi();return <View style={{gap:7}}><Text style={s.fieldLabel}>{label}</Text><TextInput accessibilityLabel={label} placeholderTextColor={color.placeholder} {...props} style={[s.input,props.style]}/></View>;}
export function Chips<T extends string>({items,value,onChange}:{items:{value:T;label:string}[];value:T;onChange:(value:T)=>void}){
 const {s,color}=useUi();return <View style={{flexDirection:'row',flexWrap:'wrap',gap:7}}>{items.map(item=><Pressable accessibilityRole="button" accessibilityState={{selected:item.value===value}} key={item.value} onPress={()=>onChange(item.value)} style={[s.chip,item.value===value&&{backgroundColor:color.soft,borderColor:color.blue}]}><Text style={{fontSize:12,lineHeight:17,color:item.value===value?color.blue:color.muted,fontWeight:'600'}}>{item.label}</Text></Pressable>)}</View>;
}
export function Empty({title,detail}:{title:string;detail:string}){const {s,color}=useUi();return <Card><Icon name="leaf-outline" size={23} color={color.blue}/><Text style={s.label}>{title}</Text><Text style={s.body}>{detail}</Text></Card>;}
export const dateText=(value:string)=>new Date(value).toLocaleDateString('es-CO',{month:'short',day:'numeric'});
const styles=(color:Palette)=>StyleSheet.create({
 title:{fontSize:24,lineHeight:30,fontWeight:'700',letterSpacing:-.6,color:color.ink},
 eyebrow:{fontSize:10,lineHeight:15,fontWeight:'700',letterSpacing:1.5,color:color.blue},
 body:{fontSize:13,lineHeight:20,color:color.muted},label:{fontSize:15,lineHeight:21,fontWeight:'600',color:color.ink,flexShrink:1},
 card:{padding:16,borderRadius:17,backgroundColor:color.surface,gap:11,borderWidth:1,borderColor:color.line},
 row:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',gap:10,flexWrap:'wrap'},
 button:{minHeight:46,paddingHorizontal:14,paddingVertical:11,borderRadius:12,flexDirection:'row',justifyContent:'center',alignItems:'center',gap:8},
 input:{minHeight:46,borderWidth:1,borderColor:color.line,borderRadius:11,padding:12,fontSize:16,color:color.ink,backgroundColor:color.surface},
 fieldLabel:{fontSize:12,lineHeight:18,fontWeight:'600',color:color.ink},chip:{minHeight:40,justifyContent:'center',borderRadius:99,paddingVertical:9,paddingHorizontal:12,borderWidth:1,borderColor:color.line,backgroundColor:color.surface},
 metric:{fontSize:23,lineHeight:29,fontWeight:'700',letterSpacing:-.5,color:color.ink},divider:{height:1,backgroundColor:color.line},
});
